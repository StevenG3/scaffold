import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HARNESS = REPO_ROOT / "template" / ".harness"

# This process imports harness.py directly; suppress bytecode so the loader
# never writes a .pyc into the read-only bundle tree.
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location(
    "harness", SOURCE_HARNESS / "bin" / "harness.py"
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def read_manifest(root):
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(root, manifest):
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@contextmanager
def instantiated_project():
    """A temp project holding a Harness copy stamped as an installed instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir) / "project"
        root = project / ".harness"
        shutil.copytree(SOURCE_HARNESS, root, ignore=shutil.ignore_patterns("__pycache__"))
        manifest = read_manifest(root)
        manifest["origin"] = {
            "template_name": "portable-harness",
            "template_version": manifest["template_version"],
            "initialized_at_schema": manifest["schema_version"],
        }
        write_manifest(root, manifest)
        yield project, root


def run_instance_cli(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "bin" / "harness.py"), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


BODY = "example body"
BODY_BYTES = BODY.encode("utf-8")
BEGIN = harness.MARKER_BEGIN_BYTES
END = harness.MARKER_END_BYTES
BLOCK = BEGIN + b"\n" + BODY_BYTES + b"\n" + END + b"\n"


class ManagedBlockTests(unittest.TestCase):
    def test_create_when_file_absent(self):
        self.assertEqual(BLOCK, harness.apply_managed_block(None, BODY_BYTES))

    def test_create_when_file_empty(self):
        self.assertEqual(BLOCK, harness.apply_managed_block(b"", BODY_BYTES))

    def test_append_when_no_markers(self):
        result = harness.apply_managed_block(b"user text\n", BODY_BYTES)
        self.assertEqual(b"user text\n\n" + BLOCK, result)
        result = harness.apply_managed_block(b"no trailing newline", BODY_BYTES)
        self.assertEqual(b"no trailing newline\n\n" + BLOCK, result)

    def test_replace_between_markers_preserves_user_text(self):
        existing = b"before\n" + BEGIN + b"\nold\n" + END + b"\n" + b"after\n"
        result = harness.apply_managed_block(existing, BODY_BYTES)
        self.assertEqual(b"before\n" + BLOCK + b"after\n", result)

    def test_apply_is_idempotent(self):
        once = harness.apply_managed_block(b"user text\n", BODY_BYTES)
        twice = harness.apply_managed_block(once, BODY_BYTES)
        self.assertEqual(once, twice)

    def test_crlf_prefix_is_preserved_byte_for_byte(self):
        existing = b"USER\r\nNOTES\r\n\r\n" + BEGIN + b"\nold\n" + END + b"\n"
        result = harness.apply_managed_block(existing, BODY_BYTES)
        self.assertTrue(result.startswith(b"USER\r\nNOTES\r\n\r\n" + BEGIN))
        # Second pass is byte-identical (no newline translation, no drift).
        self.assertEqual(result, harness.apply_managed_block(result, BODY_BYTES))

    def test_blank_lines_after_end_are_preserved(self):
        # Review probe: b'\n\n\nUSER-SUFFIX\n' after END must survive unchanged.
        existing = BEGIN + b"\nold\n" + END + b"\n\n\nUSER-SUFFIX\n"
        result = harness.apply_managed_block(existing, BODY_BYTES)
        self.assertEqual(BLOCK + b"\n\nUSER-SUFFIX\n", result)
        self.assertTrue(result.endswith(b"\n\n\nUSER-SUFFIX\n"))
        self.assertEqual(result, harness.apply_managed_block(result, BODY_BYTES))

    def test_file_without_trailing_newline_after_end(self):
        existing = BEGIN + b"\nold\n" + END
        result = harness.apply_managed_block(existing, BODY_BYTES)
        # No trailing newline and at file end: block terminates without newline.
        self.assertEqual(BEGIN + b"\n" + BODY_BYTES + b"\n" + END, result)
        self.assertEqual(result, harness.apply_managed_block(result, BODY_BYTES))

    def test_non_ascii_user_content_is_preserved(self):
        existing = "笔记 café\n".encode("utf-8") + BEGIN + b"\nold\n" + END + b"\n"
        result = harness.apply_managed_block(existing, BODY_BYTES)
        self.assertTrue(result.startswith("笔记 café\n".encode("utf-8")))
        self.assertEqual(result, harness.apply_managed_block(result, BODY_BYTES))

    def test_broken_markers_raise(self):
        for text in (
            BEGIN + b"\nno end\n",
            b"no begin\n" + END + b"\n",
            END + b"\nswapped\n" + BEGIN + b"\n",
            BEGIN + b"\n" + BEGIN + b"\n" + END + b"\n",
        ):
            with self.assertRaises(harness.MarkerBrokenError):
                harness.apply_managed_block(text, BODY_BYTES)


class RenderTests(unittest.TestCase):
    def test_block_body_lists_components_and_workflow(self):
        manifest = read_manifest(SOURCE_HARNESS)
        body = harness.render_block_body(manifest)
        self.assertIn("`.harness/README.md`", body)
        self.assertIn("- harness-bootstrap (skill): `.harness/skills/harness-bootstrap/SKILL.md`", body)
        self.assertIn("python3 .harness/bin/harness.py validate", body)
        self.assertNotIn("\n\n\n", body)

    def test_cursor_file_starts_with_frontmatter(self):
        manifest = read_manifest(SOURCE_HARNESS)
        text = harness.render_cursor_file(manifest)
        self.assertTrue(text.startswith("---\n"))
        self.assertIn(harness.MARKER_BEGIN, text)
        self.assertTrue(text.endswith(harness.MARKER_END + "\n"))

    def test_adapter_table_matches_validator_names(self):
        self.assertEqual(
            set(harness.validate.BUILTIN_ADAPTER_NAMES), set(harness.ADAPTERS)
        )


class AdaptCommandTests(unittest.TestCase):
    def test_creates_all_three_projections(self):
        with instantiated_project() as (project, root):
            result = run_instance_cli(root, "adapt")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc"):
                self.assertTrue((project / name).is_file(), name)
            self.assertIn("adapt: ok", result.stdout)

    def test_preserves_existing_user_content(self):
        with instantiated_project() as (project, root):
            (project / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
            run_instance_cli(root, "adapt")
            text = (project / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("my own notes\n"))
            self.assertIn(harness.MARKER_BEGIN, text)

    def test_adapt_is_idempotent(self):
        with instantiated_project() as (project, root):
            run_instance_cli(root, "adapt")
            snapshot = {
                name: (project / name).read_bytes()
                for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc")
            }
            second = run_instance_cli(root, "adapt", "--format", "json")
            payload = json.loads(second.stdout)
            self.assertEqual([], payload["written"])
            self.assertEqual(3, len(payload["unchanged"]))
            for name, content in snapshot.items():
                self.assertEqual(content, (project / name).read_bytes(), name)

    def test_broken_markers_fail(self):
        with instantiated_project() as (project, root):
            (project / "CLAUDE.md").write_text(
                harness.MARKER_BEGIN + "\nno end\n", encoding="utf-8"
            )
            result = run_instance_cli(root, "adapt")
            self.assertEqual(1, result.returncode)
            self.assertIn("[PROJECTION_MARKER_BROKEN] CLAUDE.md", result.stdout)

    def test_check_reports_missing_and_stale(self):
        with instantiated_project() as (project, root):
            result = run_instance_cli(root, "adapt", "--check", "--format", "json")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(3, len(payload["stale"]))
            self.assertIn("PROJECTION_MISSING", [e["code"] for e in payload["errors"]])

            run_instance_cli(root, "adapt")
            ok = run_instance_cli(root, "adapt", "--check")
            self.assertEqual(0, ok.returncode, ok.stdout)

            claude = project / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8").replace("Workflow", "Werkflow"),
                encoding="utf-8",
            )
            stale = run_instance_cli(root, "adapt", "--check", "--format", "json")
            self.assertEqual(1, stale.returncode)
            self.assertIn(
                "PROJECTION_STALE",
                [e["code"] for e in json.loads(stale.stdout)["errors"]],
            )

    def test_check_never_writes(self):
        with instantiated_project() as (project, root):
            run_instance_cli(root, "adapt", "--check")
            for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc"):
                self.assertFalse((project / name).exists(), name)

    def test_template_origin_null_skips_projection(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE_HARNESS / "bin" / "harness.py"),
                "adapt",
                "--check",
                "--root",
                str(SOURCE_HARNESS),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[ADAPT_SKIPPED_TEMPLATE]", result.stdout)

    def test_external_adapter_is_notice_not_error(self):
        with instantiated_project() as (project, root):
            manifest = read_manifest(root)
            manifest["adapters"] = ["claude-code", "x-corp"]
            write_manifest(root, manifest)
            result = run_instance_cli(root, "adapt")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("[ADAPTER_EXTERNAL] x-corp", result.stdout)

    def test_output_is_deterministic(self):
        outputs = []
        for _ in range(2):
            with instantiated_project() as (project, root):
                run_instance_cli(root, "adapt")
                outputs.append(
                    tuple(
                        (project / name).read_bytes()
                        for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc")
                    )
                )
        self.assertEqual(outputs[0], outputs[1])


class ProjectionNodeSafetyTests(unittest.TestCase):
    def _codes(self, result):
        return [error["code"] for error in json.loads(result.stdout)["errors"]]

    def test_target_symlink_escaping_project_is_rejected(self):
        with instantiated_project() as (project, root):
            outside = project.parent / "outside.md"
            outside.write_bytes(b"OUTSIDE")
            os.symlink(outside, project / "CLAUDE.md")
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("PROJECTION_PATH_UNSAFE", self._codes(result))
            self.assertEqual(b"OUTSIDE", outside.read_bytes())
            self.assertTrue((project / "CLAUDE.md").is_symlink())

    def test_target_symlink_escaping_under_check_is_rejected(self):
        with instantiated_project() as (project, root):
            outside = project.parent / "outside.md"
            outside.write_bytes(b"OUTSIDE")
            os.symlink(outside, project / "CLAUDE.md")
            result = run_instance_cli(root, "adapt", "--check", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("PROJECTION_PATH_UNSAFE", self._codes(result))
            self.assertEqual(b"OUTSIDE", outside.read_bytes())

    def test_parent_directory_symlink_escape_is_rejected(self):
        with instantiated_project() as (project, root):
            outside_dir = project.parent / "outside_dir"
            outside_dir.mkdir()
            os.symlink(outside_dir, project / ".cursor")
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            errors = json.loads(result.stdout)["errors"]
            unsafe = [e for e in errors if e["code"] == "PROJECTION_PATH_UNSAFE"]
            self.assertTrue(unsafe)
            self.assertIn(".cursor/rules/harness.mdc", [e["path"] for e in unsafe])
            # Nothing was written through the symlink into the outside directory.
            self.assertEqual([], list(outside_dir.rglob("*")))

    def test_directory_target_is_rejected_without_reading(self):
        with instantiated_project() as (project, root):
            (project / "CLAUDE.md").mkdir()
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("PROJECTION_TARGET_INVALID", self._codes(result))
            self.assertTrue((project / "CLAUDE.md").is_dir())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO not supported on this platform")
    def test_fifo_target_is_rejected_without_hanging(self):
        with instantiated_project() as (project, root):
            os.mkfifo(project / "CLAUDE.md")
            # timeout=60 in run_instance_cli guards against a blocking open.
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("PROJECTION_TARGET_INVALID", self._codes(result))


class CursorMarkerIntegrityTests(unittest.TestCase):
    def _write_cursor(self, project, body):
        target = project / ".cursor" / "rules"
        target.mkdir(parents=True)
        (target / "harness.mdc").write_bytes(body)

    def test_broken_cursor_markers_are_not_overwritten(self):
        variants = {
            "begin-only": harness.MARKER_BEGIN_BYTES + b"\nno end\n",
            "end-only": b"no begin\n" + harness.MARKER_END_BYTES + b"\n",
            "reversed": harness.MARKER_END_BYTES
            + b"\nswapped\n"
            + harness.MARKER_BEGIN_BYTES
            + b"\n",
            "duplicated": harness.MARKER_BEGIN_BYTES
            + b"\n"
            + harness.MARKER_BEGIN_BYTES
            + b"\n"
            + harness.MARKER_END_BYTES
            + b"\n",
        }
        for label, body in variants.items():
            with self.subTest(variant=label):
                with instantiated_project() as (project, root):
                    self._write_cursor(project, body)
                    result = run_instance_cli(root, "adapt", "--format", "json")
                    self.assertEqual(1, result.returncode, label)
                    codes = [
                        e["code"] for e in json.loads(result.stdout)["errors"]
                    ]
                    self.assertIn("PROJECTION_MARKER_BROKEN", codes)
                    # File is untouched.
                    self.assertEqual(
                        body,
                        (project / ".cursor" / "rules" / "harness.mdc").read_bytes(),
                    )


class FailureAtomicWriteTests(unittest.TestCase):
    """Fault-injection around _write_projection (design §8.3 atomicity)."""

    REL = ("CLAUDE.md",)
    DISPLAY = "CLAUDE.md"
    PAYLOAD = b"EXPECTED-PROJECTION-BYTES\n"
    ORIGINAL = b"ORIGINAL USER BYTES\n"

    @contextmanager
    def _project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def _temp_path(self, project):
        return project / "CLAUDE.md.harness-tmp"

    def test_short_write_still_produces_complete_file(self):
        with self._project() as project:
            errors = []
            real_write = os.write

            def chunked(fd, data):
                # Force one byte at a time to exercise the short-write loop.
                return real_write(fd, bytes(data[:1]))

            with mock.patch.object(harness.os, "write", side_effect=chunked):
                ok = harness._write_projection(
                    project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                )
            self.assertTrue(ok)
            self.assertEqual([], errors)
            self.assertEqual(self.PAYLOAD, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())

    def test_zero_progress_write_fails_and_preserves_original(self):
        with self._project() as project:
            (project / "CLAUDE.md").write_bytes(self.ORIGINAL)
            errors = []
            with mock.patch.object(harness.os, "write", return_value=0):
                with self.assertRaises(harness.ProjectionIOError) as caught:
                    harness._write_projection(
                        project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                    )
            self.assertEqual("PROJECTION_IO_ERROR", caught.exception.error.code)
            self.assertEqual(self.ORIGINAL, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())

    def test_mid_write_exception_preserves_original_and_cleans_temp(self):
        with self._project() as project:
            (project / "CLAUDE.md").write_bytes(self.ORIGINAL)
            errors = []

            def boom(fd, data):
                raise OSError("simulated mid-write failure")

            with mock.patch.object(harness.os, "write", side_effect=boom):
                with self.assertRaises(harness.ProjectionIOError):
                    harness._write_projection(
                        project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                    )
            self.assertEqual(self.ORIGINAL, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())

    def test_replace_failure_preserves_original_and_cleans_temp(self):
        with self._project() as project:
            (project / "CLAUDE.md").write_bytes(self.ORIGINAL)
            errors = []
            with mock.patch.object(
                harness.os, "replace", side_effect=OSError("simulated replace failure")
            ):
                with self.assertRaises(harness.ProjectionIOError) as caught:
                    harness._write_projection(
                        project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                    )
            self.assertEqual("PROJECTION_IO_ERROR", caught.exception.error.code)
            self.assertEqual(self.ORIGINAL, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())

    def test_close_failure_is_io_error_and_leaves_no_temp(self):
        # H1: os.close performs the real close then raises OSError. The failure
        # must convert to PROJECTION_IO_ERROR, keep the original byte-identical,
        # and leave no *.harness-tmp node behind.
        with self._project() as project:
            (project / "CLAUDE.md").write_bytes(self.ORIGINAL)
            errors = []
            real_close = os.close

            def close_then_raise(fd):
                real_close(fd)
                raise OSError("simulated close failure")

            with mock.patch.object(harness.os, "close", side_effect=close_then_raise):
                with self.assertRaises(harness.ProjectionIOError) as caught:
                    harness._write_projection(
                        project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                    )
            self.assertEqual("PROJECTION_IO_ERROR", caught.exception.error.code)
            self.assertEqual(self.ORIGINAL, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())

    def test_preclose_fault_converts_and_does_not_retry_close(self):
        # J4: os.close raises BEFORE the real release (pre-close fault). Per the
        # §8.3 exactly-once contract the close is NOT retried: it must convert to
        # PROJECTION_IO_ERROR, keep the target byte-identical, leave no temp file,
        # and os.close must have been called exactly once.
        with self._project() as project:
            (project / "CLAUDE.md").write_bytes(self.ORIGINAL)
            errors = []

            def raise_before_close(fd):
                # Do NOT release the fd; simulate a fault before the real close.
                raise OSError("simulated pre-close failure")

            mock_close = mock.Mock(side_effect=raise_before_close)
            with mock.patch.object(harness.os, "close", mock_close):
                with self.assertRaises(harness.ProjectionIOError) as caught:
                    harness._write_projection(
                        project, self.REL, self.DISPLAY, self.PAYLOAD, errors
                    )
            self.assertEqual("PROJECTION_IO_ERROR", caught.exception.error.code)
            self.assertEqual(self.ORIGINAL, (project / "CLAUDE.md").read_bytes())
            self.assertFalse(self._temp_path(project).exists())
            self.assertEqual(1, mock_close.call_count)

    def test_partial_progress_reported_when_second_projection_fails(self):
        # H3: CLAUDE.md commits, then AGENTS.md write fails. The envelope must
        # report written == ["CLAUDE.md"] (never an empty lie) and CLAUDE.md must
        # be present on disk.
        with instantiated_project() as (project, root):
            # Drive cmd_adapt in-process so the fault injection is visible. Track
            # fd->path via os.open (portable, no /proc dependency) so the write
            # for AGENTS.md's temp file can be failed while CLAUDE.md commits.
            import io
            from contextlib import redirect_stdout

            fd_paths = {}
            real_open = os.open
            real_write = os.write

            def tracking_open(path, *a, **k):
                fd = real_open(path, *a, **k)
                fd_paths[fd] = os.fspath(path)
                return fd

            def fail_on_agents(fd, data):
                if fd_paths.get(fd, "").endswith("AGENTS.md.harness-tmp"):
                    raise OSError("simulated AGENTS.md write failure")
                return real_write(fd, data)

            buffer = io.StringIO()
            with mock.patch.object(harness.os, "open", side_effect=tracking_open), \
                    mock.patch.object(harness.os, "write", side_effect=fail_on_agents):
                with redirect_stdout(buffer):
                    rc = harness.cmd_adapt(root, False, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual(["CLAUDE.md"], payload["written"])
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertFalse((project / "AGENTS.md").exists())

    def test_init_projection_io_failure_carries_cleanup_hint(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            buffer = io.StringIO()
            with mock.patch.object(
                harness.os, "replace", side_effect=OSError("simulated replace failure")
            ):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            # projected_files follows semantics A (files written this run). The
            # very first projection fails to commit here, so it is empty.
            self.assertEqual([], payload["projected_files"])
            # The copied tree is left in place for the user to inspect/remove.
            self.assertTrue((project / ".harness").is_dir())

    @unittest.skipUnless(
        hasattr(os, "geteuid") and os.geteuid() != 0,
        "requires a non-root euid so file permissions are enforced",
    )
    def test_unreadable_target_json_returns_io_error_envelope(self):
        with instantiated_project() as (project, root):
            target = project / "CLAUDE.md"
            target.write_bytes(b"user\n")
            os.chmod(target, 0)
            try:
                result = run_instance_cli(root, "adapt", "--format", "json")
            finally:
                os.chmod(target, 0o644)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertEqual("", result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )


class AdaptErrorPathTests(unittest.TestCase):
    def test_adapt_with_invalid_manifest_exits_1_with_json_errors(self):
        with instantiated_project() as (project, root):
            (root / "manifest.json").write_text("{ not valid json", encoding="utf-8")
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertTrue(payload["errors"])

    def test_adapt_validate_oserror_emits_io_error_envelope(self):
        # Symmetric with the init source-validate boundary: a bare OSError raised
        # while validate_harness reads a present-but-unreadable file must render as
        # PROJECTION_IO_ERROR (exit 2) with the full adapt envelope, not escape to
        # a bare INTERNAL_ERROR.
        import io
        from contextlib import redirect_stdout

        def boom(root):
            raise OSError("simulated validate read failure")

        with instantiated_project() as (project, root):
            buffer = io.StringIO()
            with mock.patch.object(harness.validate, "validate_harness", boom):
                with redirect_stdout(buffer):
                    rc = harness.cmd_adapt(root, False, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual([], payload["written"])
            self.assertEqual([], payload["unchanged"])
            self.assertEqual([], payload["stale"])

    def test_adapt_manifest_reread_io_error_json_envelope(self):
        # J2: validate_harness succeeds, then the post-validate manifest re-read
        # raises OSError. It must render as PROJECTION_IO_ERROR (exit 2) with the
        # full adapt envelope on stdout, not escape to a bare INTERNAL_ERROR.
        import io
        from contextlib import redirect_stdout

        real_read_text = Path.read_text
        manifest_reads = {"count": 0}

        def flaky_read_text(self, *args, **kwargs):
            if self.name == "manifest.json":
                manifest_reads["count"] += 1
                # 1st read is validate_harness; 2nd is the adapt re-read.
                if manifest_reads["count"] >= 2:
                    raise OSError("simulated manifest re-read failure")
            return real_read_text(self, *args, **kwargs)

        with instantiated_project() as (project, root):
            buffer = io.StringIO()
            with mock.patch.object(Path, "read_text", flaky_read_text):
                with redirect_stdout(buffer):
                    rc = harness.cmd_adapt(root, False, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual([], payload["written"])
            self.assertEqual([], payload["unchanged"])
            self.assertEqual([], payload["stale"])

    def test_adapt_root_missing_dir_exits_2_with_json_envelope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does-not-exist"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SOURCE_HARNESS / "bin" / "harness.py"),
                    "adapt",
                    "--root",
                    str(missing),
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertEqual(
                ["ROOT_UNREADABLE"], [e["code"] for e in payload["errors"]]
            )


def _decode_error():
    # A genuine UnicodeDecodeError as read_text(encoding="utf-8") raises on a
    # non-UTF-8 byte: a UnicodeError, but NOT an OSError or JSONDecodeError.
    return UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")


class R5AdaptUnicodeTests(unittest.TestCase):
    def test_adapt_real_invalid_utf8_manifest_maps_to_projection_io_error(self):
        # F1: a genuinely non-UTF-8 manifest makes validate_harness's read_text
        # raise UnicodeDecodeError, which must render PROJECTION_IO_ERROR (exit 2)
        # with the full adapt envelope on stdout, never a bare INTERNAL_ERROR.
        with instantiated_project() as (project, root):
            (root / "manifest.json").write_bytes(
                b"\xff\xfe" + b'{"schema_version": 2}\n'
            )
            result = run_instance_cli(root, "adapt", "--format", "json")
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertEqual("", result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("adapt", payload["command"])
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertNotIn("INTERNAL_ERROR", result.stdout + result.stderr)

    def test_adapt_manifest_reread_decode_race_maps_to_projection_io_error(self):
        # F2: validate_harness succeeds, then the post-validate manifest re-read
        # raises UnicodeDecodeError. PROJECTION_IO_ERROR (exit 2), full envelope.
        import io
        from contextlib import redirect_stdout

        real_read_text = Path.read_text
        reads = {"count": 0}

        def flaky(self, *a, **k):
            if self.name == "manifest.json":
                reads["count"] += 1
                if reads["count"] >= 2:
                    raise _decode_error()
            return real_read_text(self, *a, **k)

        with instantiated_project() as (project, root):
            buffer = io.StringIO()
            with mock.patch.object(Path, "read_text", flaky):
                with redirect_stdout(buffer):
                    rc = harness.cmd_adapt(root, False, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual([], payload["written"])


class R5AdaptProgressSemanticsTests(unittest.TestCase):
    def test_written_and_unchanged_are_distinguished_when_a_later_write_fails(self):
        # F5 (semantics A): one projection unchanged, one freshly written, a third
        # fails. written must hold ONLY the file written this run; the byte-
        # identical file stays in unchanged and never leaks into written.
        import io
        from contextlib import redirect_stdout

        with instantiated_project() as (project, root):
            # First adapt materializes all three, then drop AGENTS.md and the
            # cursor file so the next run leaves CLAUDE.md unchanged, writes
            # AGENTS.md, and reaches the cursor projection.
            self.assertEqual(
                0, run_instance_cli(root, "adapt").returncode
            )
            (project / "AGENTS.md").unlink()
            shutil.rmtree(project / ".cursor")

            fd_paths = {}
            real_open = os.open
            real_write = os.write

            def tracking_open(path, *a, **k):
                fd = real_open(path, *a, **k)
                fd_paths[fd] = os.fspath(path)
                return fd

            def fail_on_cursor(fd, data):
                if fd_paths.get(fd, "").endswith("harness.mdc.harness-tmp"):
                    raise OSError("simulated cursor write failure")
                return real_write(fd, data)

            buffer = io.StringIO()
            with mock.patch.object(harness.os, "open", side_effect=tracking_open), \
                    mock.patch.object(harness.os, "write", side_effect=fail_on_cursor):
                with redirect_stdout(buffer):
                    rc = harness.cmd_adapt(root, False, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual(["AGENTS.md"], payload["written"])
            self.assertEqual(["CLAUDE.md"], payload["unchanged"])


if __name__ == "__main__":
    unittest.main()
