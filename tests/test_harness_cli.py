import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HARNESS = REPO_ROOT / "template" / ".harness"
HARNESS_CLI = SOURCE_HARNESS / "bin" / "harness.py"
VALIDATOR = SOURCE_HARNESS / "bin" / "validate.py"

# Import harness.py in-process (some tests drive cmd_init directly to inject
# faults). Suppress bytecode BEFORE the import so the loader never writes a .pyc
# into the read-only bundle tree, mirroring tests/test_adapters.py.
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("harness", HARNESS_CLI)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def run_cli(cli, *args):
    return subprocess.run(
        [sys.executable, str(cli), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ValidateSubcommandTests(unittest.TestCase):
    def test_matches_validate_py_text_output(self):
        via_cli = run_cli(HARNESS_CLI, "validate", "--root", str(SOURCE_HARNESS))
        direct = run_cli(VALIDATOR, "--root", str(SOURCE_HARNESS))
        self.assertEqual(direct.returncode, via_cli.returncode)
        self.assertEqual(direct.stdout, via_cli.stdout)

    def test_matches_validate_py_json_output(self):
        via_cli = run_cli(
            HARNESS_CLI, "validate", "--root", str(SOURCE_HARNESS), "--format", "json"
        )
        direct = run_cli(VALIDATOR, "--root", str(SOURCE_HARNESS), "--format", "json")
        self.assertEqual(0, via_cli.returncode)
        self.assertEqual(json.loads(direct.stdout), json.loads(via_cli.stdout))

    def test_unknown_command_exits_2(self):
        result = run_cli(HARNESS_CLI, "upgrade")
        self.assertEqual(2, result.returncode)
        self.assertIn("[ARGUMENT_INVALID]", result.stderr)

    def test_root_unreadable_json_emits_envelope_on_stdout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does-not-exist"
            result = run_cli(
                HARNESS_CLI, "validate", "--root", str(missing), "--format", "json"
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("validate", payload["command"])
            self.assertEqual(
                ["ROOT_UNREADABLE"], [e["code"] for e in payload["errors"]]
            )

    def test_root_unreadable_text_still_goes_to_stderr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does-not-exist"
            result = run_cli(HARNESS_CLI, "validate", "--root", str(missing))
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("[ROOT_UNREADABLE]", result.stderr)


PROJECTIONS = ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc")


@contextmanager
def temp_project():
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir) / "project"
        project.mkdir()
        yield project


def tree_fingerprint(root, exclude=()):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item + "/") for item in exclude):
            continue
        metadata = path.lstat()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if stat.S_ISLNK(metadata.st_mode):
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif stat.S_ISREG(metadata.st_mode):
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class InitCommandTests(unittest.TestCase):
    def test_init_success_end_to_end(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI, "init", "--target", str(project), "--format", "json"
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(sorted(PROJECTIONS), sorted(payload["projected_files"]))

            root = project / ".harness"
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {
                    "template_name": "portable-harness",
                    "template_version": manifest["template_version"],
                    "initialized_at_schema": 2,
                },
                manifest["origin"],
            )
            for name in PROJECTIONS:
                self.assertTrue((project / name).is_file(), name)
            self.assertFalse(list(root.rglob("__pycache__")))

    def test_init_success_text_prints_next_step(self):
        with temp_project() as project:
            result = run_cli(HARNESS_CLI, "init", "--target", str(project))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("init: ok", result.stdout)
            self.assertIn("harness-bootstrap", result.stdout)

    def test_initialized_copy_is_self_sufficient(self):
        with temp_project() as project:
            run_cli(HARNESS_CLI, "init", "--target", str(project))
            instance_cli = project / ".harness" / "bin" / "harness.py"
            for args in (("validate",), ("adapt", "--check")):
                result = run_cli(instance_cli, *args)
                self.assertEqual(0, result.returncode, args)

    def test_init_refuses_existing_harness(self):
        with temp_project() as project:
            (project / ".harness").mkdir()
            result = run_cli(HARNESS_CLI, "init", "--target", str(project))
            self.assertEqual(1, result.returncode)
            self.assertIn("[INIT_TARGET_EXISTS]", result.stdout)

    def test_init_requires_existing_target_directory(self):
        with temp_project() as project:
            result = run_cli(HARNESS_CLI, "init", "--target", str(project / "missing"))
            self.assertEqual(1, result.returncode)
            self.assertIn("[INIT_TARGET_MISSING]", result.stdout)

    def test_init_adapters_override(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI, "init", "--target", str(project), "--adapters", "claude-code"
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertFalse((project / "AGENTS.md").exists())
            manifest = json.loads(
                (project / ".harness" / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(["claude-code"], manifest["adapters"])

    def test_init_rejects_bad_adapter_names_before_copying(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI, "init", "--target", str(project), "--adapters", "vscode"
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("[ARGUMENT_INVALID]", result.stderr)
            self.assertFalse((project / ".harness").exists())

    def test_init_bad_adapter_json_emits_envelope_on_stdout(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI,
                "init",
                "--target",
                str(project),
                "--adapters",
                "vscode",
                "--format",
                "json",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["ARGUMENT_INVALID"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual([], payload["notices"])
            self.assertIsNone(payload["target"])
            self.assertEqual([], payload["projected_files"])
            self.assertFalse((project / ".harness").exists())

    def test_init_excludes_hidden_caches_from_copy(self):
        # Plant a cache in a COPY of the template so the repo template is not
        # polluted, then init from that copy.
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "template" / ".harness"
            shutil.copytree(SOURCE_HARNESS, source)
            (source / ".pytest_cache").mkdir()
            (source / ".pytest_cache" / "marker").write_text("x\n", encoding="utf-8")
            project = Path(temp_dir) / "project"
            project.mkdir()
            result = run_cli(
                source / "bin" / "harness.py", "init", "--target", str(project)
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse((project / ".harness" / ".pytest_cache").exists())
            self.assertFalse(list((project / ".harness").rglob(".pytest_cache")))

    def test_init_refuses_dangling_harness_symlink(self):
        with temp_project() as project:
            destination = project / ".harness"
            os.symlink(project / "missing-target", destination)
            result = run_cli(HARNESS_CLI, "init", "--target", str(project))
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("[INIT_TARGET_EXISTS]", result.stdout)
            # The symlink is untouched: no copytree ran through it.
            self.assertTrue(destination.is_symlink())
            self.assertEqual(
                str(project / "missing-target"), os.readlink(destination)
            )
            self.assertFalse(destination.exists())  # still dangling

    def test_command_error_text_escapes_control_characters(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI,
                "init",
                "--target",
                str(project),
                "--adapters",
                "bad\nname",
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("bad\\u000aname", result.stderr)
            self.assertNotIn("bad\nname", result.stderr)
            # Exactly one physical line for the single error (plus trailing \n).
            self.assertEqual(1, result.stderr.count("\n"))
            self.assertFalse((project / ".harness").exists())

    def test_init_copy_io_failure_emits_envelope_and_cleanup_hint(self):
        # H2: a dangling symlink inside the init SOURCE bundle makes copytree
        # raise shutil.Error. That copy-stage fault must render as an
        # INIT_IO_ERROR envelope (exit 2) with an INIT_CLEANUP_HINT notice when
        # the destination was partially created; stderr stays empty for json.
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "template" / ".harness"
            shutil.copytree(SOURCE_HARNESS, source)
            os.symlink(source / "does-not-exist", source / "dangling-link")
            project = Path(temp_dir) / "project"
            project.mkdir()
            result = run_cli(
                source / "bin" / "harness.py",
                "init",
                "--target",
                str(project),
                "--format",
                "json",
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertEqual("", result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            destination = project / ".harness"
            if destination.exists():
                self.assertIn(
                    "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
                )
            self.assertEqual([], payload["projected_files"])

    def test_init_writes_only_declared_paths(self):
        with temp_project() as project:
            (project / "src").mkdir()
            (project / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (project / "CLAUDE.md").write_text("user notes\n", encoding="utf-8")
            declared = (".harness", ".cursor") + ("CLAUDE.md", "AGENTS.md")
            before = tree_fingerprint(project, exclude=declared)
            run_cli(HARNESS_CLI, "init", "--target", str(project))
            after = tree_fingerprint(project, exclude=declared)
            self.assertEqual(before, after)
            self.assertTrue(
                (project / "CLAUDE.md")
                .read_text(encoding="utf-8")
                .startswith("user notes\n")
            )

    def test_init_manifest_stamp_io_failure_emits_envelope_and_cleanup_hint(self):
        # The manifest read/stamp/write stage runs after copytree, so .harness is
        # fully on disk. An OSError there must render as INIT_IO_ERROR (exit 2)
        # with an INIT_CLEANUP_HINT notice, not a bare INTERNAL_ERROR.
        with temp_project() as project:
            real_write_text = Path.write_text

            def fail_manifest_write(self, *args, **kwargs):
                if self.name == "manifest.json":
                    raise OSError("simulated manifest write failure")
                return real_write_text(self, *args, **kwargs)

            buffer = io.StringIO()
            with mock.patch.object(Path, "write_text", fail_manifest_write):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self.assertEqual([], payload["projected_files"])
            # The copied tree is left in place for the user to inspect/remove.
            self.assertTrue((project / ".harness").is_dir())

    def test_source_manifest_reread_io_failure_emits_init_io_error(self):
        # J1(a): source validation succeeds, then the source manifest re-read
        # raises OSError. That post-parse I/O fault must render as INIT_IO_ERROR
        # (exit 2), not escape to a bare INTERNAL_ERROR. It happens before
        # copytree, so no destination exists and target is null.
        real_read_text = Path.read_text
        manifest_reads = {"count": 0}

        def flaky_read_text(self, *args, **kwargs):
            if self.name == "manifest.json":
                manifest_reads["count"] += 1
                # 1st read is source validation; 2nd is the harness re-read.
                if manifest_reads["count"] >= 2:
                    raise OSError("simulated source manifest re-read failure")
            return real_read_text(self, *args, **kwargs)

        with temp_project() as project:
            buffer = io.StringIO()
            with mock.patch.object(Path, "read_text", flaky_read_text):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIsNone(payload["target"])
            self.assertEqual([], payload["projected_files"])
            self.assertFalse((project / ".harness").exists())

    def test_source_validate_oserror_emits_init_io_error(self):
        # Source validation reads files inside the source bundle; a bare OSError
        # (e.g. a present-but-unreadable manifest.json, which validate.py guards
        # only for JSONDecodeError) must render as INIT_IO_ERROR (exit 2), not
        # escape to a bare INTERNAL_ERROR. Nothing is copied yet: target null,
        # projected_files empty, no cleanup hint.
        real_validate = harness.validate.validate_harness
        calls = {"count": 0}

        def flaky_validate(root):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("simulated source read failure")
            return real_validate(root)

        with temp_project() as project:
            buffer = io.StringIO()
            with mock.patch.object(
                harness.validate, "validate_harness", flaky_validate
            ):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertEqual([], payload["notices"])
            self.assertIsNone(payload["target"])
            self.assertEqual([], payload["projected_files"])
            self.assertFalse((project / ".harness").exists())

    def test_final_validate_io_failure_emits_hint_and_real_progress(self):
        # J1(b): copy, stamp and all three projections succeed, then the FINAL
        # validate_harness(destination) raises OSError. It must render as
        # INIT_IO_ERROR (exit 2) with an INIT_CLEANUP_HINT notice and the real
        # committed projected_files, not escape to INTERNAL_ERROR.
        real_validate = harness.validate.validate_harness
        calls = {"count": 0}

        def flaky_validate(root):
            calls["count"] += 1
            # 1st call validates the source; 2nd is the final destination check.
            if calls["count"] >= 2:
                raise OSError("simulated final validate failure")
            return real_validate(root)

        with temp_project() as project:
            buffer = io.StringIO()
            with mock.patch.object(
                harness.validate, "validate_harness", flaky_validate
            ):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self.assertEqual(
                sorted(PROJECTIONS), sorted(payload["projected_files"])
            )
            for name in PROJECTIONS:
                self.assertTrue((project / name).is_file(), name)
            self.assertTrue((project / ".harness").is_dir())

    def test_init_exit1_reports_partial_projection_progress(self):
        # J3: AGENTS.md pre-exists as a DIRECTORY. init commits CLAUDE.md, hits a
        # PROJECTION_TARGET_INVALID on AGENTS.md, continues and commits the Cursor
        # projection. The exit-1 envelope must report the two committed files, not
        # a fixed empty list, and carry the cleanup hint.
        with temp_project() as project:
            (project / "AGENTS.md").mkdir()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = harness.cmd_init(project, None, "json")
            self.assertEqual(1, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn(
                "PROJECTION_TARGET_INVALID", [e["code"] for e in payload["errors"]]
            )
            self.assertEqual(
                ["CLAUDE.md", ".cursor/rules/harness.mdc"],
                payload["projected_files"],
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            # projected_files matches what is actually on disk.
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertTrue((project / ".cursor" / "rules" / "harness.mdc").is_file())

    @unittest.skipIf(sys.platform == "win32", "POSIX surrogateescape argv only")
    def test_non_utf8_argv_rejected_before_json_envelope(self):
        # H4: a non-UTF-8 argv byte (0xff) must be rejected before any subcommand
        # so JSON stdout can never emit invalid UTF-8. stdout must be empty; the
        # single stderr line must decode as strict UTF-8.
        result = subprocess.run(
            [
                sys.executable,
                str(HARNESS_CLI),
                "adapt",
                "--root",
                b"/tmp/x\xff",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        # stderr decodes strictly and is exactly one physical line.
        text = result.stderr.decode("utf-8")
        self.assertIn("[ARGUMENT_INVALID]", text)
        self.assertEqual(1, text.count("\n"))

    def test_parser_error_escapes_control_characters(self):
        # H5: an unknown option carrying a newline must not split the single
        # parser-level error line. A valid subcommand makes argparse echo the
        # offending option text into its "unrecognized arguments" message.
        result = run_cli(HARNESS_CLI, "validate", "--bad\nname")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("\\u000a", result.stderr)
        self.assertNotIn("--bad\nname", result.stderr)
        self.assertEqual(1, result.stderr.count("\n"))


def _decode_error():
    # A genuine UnicodeDecodeError, as read_text(encoding="utf-8") raises on a
    # non-UTF-8 byte. It is a UnicodeError but NOT an OSError or JSONDecodeError.
    return UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")


@contextmanager
def _temp_source_with_manifest_bytes(raw):
    """A copy of the source bundle whose manifest.json holds ``raw`` bytes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "template" / ".harness"
        shutil.copytree(
            SOURCE_HARNESS, source, ignore=shutil.ignore_patterns("__pycache__")
        )
        (source / "manifest.json").write_bytes(raw)
        yield source


BAD_UTF8 = b"\xff\xfe" + b'{"schema_version": 2}\n'


class R5UnicodeDecodeTests(unittest.TestCase):
    def test_init_real_invalid_utf8_source_manifest_maps_to_init_io_error(self):
        # F1: a genuinely non-UTF-8 source manifest. Source validation's
        # read_text raises UnicodeDecodeError (not OSError/JSONDecodeError); it
        # must render as INIT_IO_ERROR (exit 2) on stdout as valid UTF-8 JSON,
        # never a bare INTERNAL_ERROR.
        with _temp_source_with_manifest_bytes(BAD_UTF8) as source:
            with tempfile.TemporaryDirectory() as temp_dir:
                project = Path(temp_dir) / "project"
                project.mkdir()
                result = run_cli(
                    source / "bin" / "harness.py",
                    "init",
                    "--target",
                    str(project),
                    "--format",
                    "json",
                )
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertEqual("", result.stderr)
                # stdout is strict UTF-8 and parses as JSON.
                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual("init", payload["command"])
                self.assertEqual(
                    ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
                )
                self.assertNotIn("INTERNAL_ERROR", result.stdout + result.stderr)
                self.assertFalse((project / ".harness").exists())

    def test_validate_real_invalid_utf8_maps_to_validate_io_error(self):
        # F1: harness.py validate on a non-UTF-8 manifest must render
        # VALIDATE_IO_ERROR through the unified envelope, both formats.
        with _temp_source_with_manifest_bytes(BAD_UTF8) as source:
            cli = source / "bin" / "harness.py"
            js = run_cli(cli, "validate", "--root", str(source), "--format", "json")
            self.assertEqual(2, js.returncode)
            self.assertEqual("", js.stderr)
            payload = json.loads(js.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual("validate", payload["command"])
            self.assertEqual(
                ["VALIDATE_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertNotIn("INTERNAL_ERROR", js.stdout + js.stderr)

            tx = run_cli(cli, "validate", "--root", str(source))
            self.assertEqual(2, tx.returncode)
            self.assertEqual("", tx.stdout)
            self.assertIn("[VALIDATE_IO_ERROR]", tx.stderr)
            self.assertEqual(1, tx.stderr.count("\n"))

    def test_standalone_validate_py_keeps_v0_behavior_on_invalid_utf8(self):
        # F1: the standalone validate.py contract is untouched — a non-UTF-8
        # manifest still surfaces as v0 INTERNAL_ERROR / exit 2 on stderr.
        with _temp_source_with_manifest_bytes(BAD_UTF8) as source:
            result = run_cli(VALIDATOR, "--root", str(source))
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("[INTERNAL_ERROR]", result.stderr)

    def test_normal_validation_stays_byte_identical_to_validate_py(self):
        # F1 companion: with a valid bundle, harness.py validate and validate.py
        # remain byte-for-byte identical across both formats and exit codes.
        for extra in ((), ("--format", "json")):
            via_cli = run_cli(
                HARNESS_CLI, "validate", "--root", str(SOURCE_HARNESS), *extra
            )
            direct = run_cli(VALIDATOR, "--root", str(SOURCE_HARNESS), *extra)
            self.assertEqual(direct.returncode, via_cli.returncode)
            self.assertEqual(direct.stdout, via_cli.stdout)
            self.assertEqual(direct.stderr, via_cli.stderr)

    def test_init_source_manifest_reread_decode_race_maps_to_init_io_error(self):
        # F2: source validation succeeds, then the source manifest re-read raises
        # UnicodeDecodeError (a decode race). It happens before copytree, so no
        # destination and no cleanup hint.
        real_read_text = Path.read_text
        reads = {"count": 0}

        def flaky(self, *a, **k):
            if self.name == "manifest.json":
                reads["count"] += 1
                if reads["count"] >= 2:
                    raise _decode_error()
            return real_read_text(self, *a, **k)

        with temp_project() as project:
            buffer = io.StringIO()
            with mock.patch.object(Path, "read_text", flaky):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIsNone(payload["target"])
            self.assertEqual([], payload["projected_files"])
            self.assertEqual([], payload["notices"])
            self.assertFalse((project / ".harness").exists())

    def test_init_post_copy_stamp_decode_race_maps_to_init_io_error(self):
        # F2: copytree succeeds, then the copied-manifest stamp read raises
        # UnicodeDecodeError. Post-copy: INIT_IO_ERROR + cleanup hint, target set,
        # projected_files empty (adapt has not run).
        real_read_text = Path.read_text

        with temp_project() as project:
            destination_manifest = project / ".harness" / "manifest.json"

            def flaky(self, *a, **k):
                if self == destination_manifest:
                    raise _decode_error()
                return real_read_text(self, *a, **k)

            buffer = io.StringIO()
            with mock.patch.object(Path, "read_text", flaky):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self.assertEqual([], payload["projected_files"])
            self.assertTrue((project / ".harness").is_dir())

    def test_init_final_validate_decode_race_maps_to_init_io_error(self):
        # F2: copy, stamp and all three projections succeed, then the FINAL
        # validate raises UnicodeDecodeError. INIT_IO_ERROR + cleanup hint and the
        # real committed projections (semantics A: all three, none unchanged).
        real_validate = harness.validate.validate_harness
        calls = {"count": 0}

        def flaky_validate(root):
            calls["count"] += 1
            if calls["count"] >= 2:
                raise _decode_error()
            return real_validate(root)

        with temp_project() as project:
            buffer = io.StringIO()
            with mock.patch.object(
                harness.validate, "validate_harness", flaky_validate
            ):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self.assertEqual(
                sorted(PROJECTIONS), sorted(payload["projected_files"])
            )


class R5ValidateSymmetryTests(unittest.TestCase):
    def _drive(self, boom, fmt):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".harness"
            root.mkdir()
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(harness.validate, "validate_harness", boom):
                with redirect_stdout(out), __import__(
                    "contextlib"
                ).redirect_stderr(err):
                    rc = harness.cmd_validate(root, fmt)
            return rc, out.getvalue(), err.getvalue()

    def test_validate_oserror_json_envelope(self):
        def boom(root):
            raise OSError("simulated validate read failure")

        rc, out, err = self._drive(boom, "json")
        self.assertEqual(2, rc)
        self.assertEqual("", err)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertEqual("validate", payload["command"])
        self.assertEqual(
            ["VALIDATE_IO_ERROR"], [e["code"] for e in payload["errors"]]
        )

    def test_validate_decode_error_json_envelope(self):
        def boom(root):
            raise _decode_error()

        rc, out, err = self._drive(boom, "json")
        self.assertEqual(2, rc)
        self.assertEqual("", err)
        payload = json.loads(out)
        self.assertEqual(
            ["VALIDATE_IO_ERROR"], [e["code"] for e in payload["errors"]]
        )

    def test_validate_oserror_text_single_escaped_line(self):
        def boom(root):
            raise OSError("bad\nread")  # embedded newline must be escaped

        rc, out, err = self._drive(boom, "text")
        self.assertEqual(2, rc)
        self.assertEqual("", out)
        self.assertIn("[VALIDATE_IO_ERROR]", err)
        self.assertIn("\\u000a", err)
        self.assertNotIn("bad\nread", err)
        self.assertEqual(1, err.count("\n"))


class R5TargetResolveTests(unittest.TestCase):
    def test_success_target_resolve_fault_maps_to_init_io_error(self):
        # F4: the normalized target resolve runs BEFORE copytree, so a resolve
        # fault is a pre-copy INIT_IO_ERROR (exit 2) with NO partial target on
        # disk — never a bare INTERNAL_ERROR after files land. R6: the resolve is
        # taken on the PARENT target (never following the .harness leaf), so the
        # fault is injected on the project directory itself.
        real_resolve = Path.resolve
        with temp_project() as project:
            destination = project / ".harness"

            def failing_resolve(self, *a, **k):
                if self == project:
                    raise OSError("simulated target resolve failure")
                return real_resolve(self, *a, **k)

            buffer = io.StringIO()
            with mock.patch.object(Path, "resolve", failing_resolve):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual("init", payload["command"])
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertNotIn("INTERNAL_ERROR", buffer.getvalue())
            self.assertEqual([], payload["projected_files"])
            # No partial target: the resolve failed before any copy.
            self.assertFalse(destination.exists())


class R5ProjectedFilesSemanticsTests(unittest.TestCase):
    def test_unchanged_file_is_not_reported_as_projected(self):
        # F5 (semantics A): pre-seed a byte-identical CLAUDE.md, then make the
        # AGENTS.md projection write fail. CLAUDE.md is unchanged this run and
        # MUST NOT appear in projected_files; its inode and bytes stay intact.
        with temp_project() as scratch:
            self.assertEqual(
                0, run_cli(HARNESS_CLI, "init", "--target", str(scratch)).returncode
            )
            expected_claude = (scratch / "CLAUDE.md").read_bytes()

        with temp_project() as project:
            claude = project / "CLAUDE.md"
            claude.write_bytes(expected_claude)
            inode_before = claude.stat().st_ino

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
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            # CLAUDE.md was unchanged, not written this run: excluded.
            self.assertNotIn("CLAUDE.md", payload["projected_files"])
            self.assertEqual([], payload["projected_files"])
            # The pre-existing file is byte-identical and same inode.
            self.assertEqual(inode_before, claude.stat().st_ino)
            self.assertEqual(expected_claude, claude.read_bytes())


@contextmanager
def _chdir(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class R6InitTargetCheckTests(unittest.TestCase):
    """R6 finding 1: the init target/destination directory-entry checks live
    inside the init I/O boundary (§7.2 stage 3). A genuinely absent/non-dir
    target is INIT_TARGET_MISSING (exit 1); a runtime path fault (loop,
    inaccessible, EILSEQ) is INIT_IO_ERROR (exit 2); an existing entry —
    including a dangling symlink — is INIT_TARGET_EXISTS (exit 1)."""

    def test_symlink_loop_target_maps_to_init_io_error(self):
        # A real self-referential symlink: os.stat follows and raises ELOOP.
        # That is NOT the predictable "target missing" state; it must surface as
        # INIT_IO_ERROR / exit 2, not be swallowed by Path.is_dir() into
        # INIT_TARGET_MISSING / exit 1.
        with tempfile.TemporaryDirectory() as temp_dir:
            loop = Path(temp_dir) / "loop"
            os.symlink(loop, loop)
            for fmt in ("text", "json"):
                result = run_cli(
                    HARNESS_CLI, "init", "--target", str(loop), "--format", fmt
                )
                self.assertEqual(
                    2, result.returncode, (fmt, result.stdout, result.stderr)
                )
                if fmt == "json":
                    self.assertEqual("", result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(
                        ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
                    )
                    self.assertEqual([], payload["projected_files"])
                    self.assertIsNone(payload["target"])
                else:
                    self.assertEqual("", result.stdout)
                    self.assertIn("[INIT_IO_ERROR]", result.stderr)

    def test_target_stat_oserror_maps_to_init_io_error(self):
        with temp_project() as project:
            real_stat = os.stat

            def flaky_stat(path, *a, **k):
                if os.fspath(path) == os.fspath(project):
                    raise OSError("simulated target stat failure")
                return real_stat(path, *a, **k)

            buffer = io.StringIO()
            with mock.patch.object(harness.os, "stat", side_effect=flaky_stat):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertNotIn("INTERNAL_ERROR", buffer.getvalue())
            self.assertEqual([], payload["projected_files"])
            self.assertFalse((project / ".harness").exists())

    def test_destination_lstat_oserror_maps_to_init_io_error(self):
        with temp_project() as project:
            destination = project / ".harness"
            real_lstat = os.lstat

            def flaky_lstat(path, *a, **k):
                if os.fspath(path) == os.fspath(destination):
                    raise OSError("simulated destination lstat failure")
                return real_lstat(path, *a, **k)

            buffer = io.StringIO()
            with mock.patch.object(harness.os, "lstat", side_effect=flaky_lstat):
                with redirect_stdout(buffer):
                    rc = harness.cmd_init(project, None, "json")
            self.assertEqual(2, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertNotIn("INTERNAL_ERROR", buffer.getvalue())
            # Fail closed: no copy happened.
            self.assertFalse(destination.exists())

    def test_missing_target_still_reports_target_missing(self):
        with temp_project() as project:
            result = run_cli(
                HARNESS_CLI, "init", "--target", str(project / "missing")
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("[INIT_TARGET_MISSING]", result.stdout)

    def test_regular_file_target_reports_target_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            afile = Path(temp_dir) / "afile"
            afile.write_text("x\n", encoding="utf-8")
            result = run_cli(HARNESS_CLI, "init", "--target", str(afile))
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("[INIT_TARGET_MISSING]", result.stdout)

    def test_regular_file_harness_reports_target_exists(self):
        with temp_project() as project:
            (project / ".harness").write_text("x\n", encoding="utf-8")
            result = run_cli(HARNESS_CLI, "init", "--target", str(project))
            self.assertEqual(1, result.returncode)
            self.assertIn("[INIT_TARGET_EXISTS]", result.stdout)
            # Zero copy: the plain file is untouched.
            self.assertEqual("x\n", (project / ".harness").read_text(encoding="utf-8"))

    def test_directory_harness_reports_target_exists(self):
        with temp_project() as project:
            (project / ".harness").mkdir()
            result = run_cli(HARNESS_CLI, "init", "--target", str(project))
            self.assertEqual(1, result.returncode)
            self.assertIn("[INIT_TARGET_EXISTS]", result.stdout)


class R6CachedAbsoluteTargetTests(unittest.TestCase):
    """R6 finding 2: every post-resolve envelope (copytree, stamp,
    ProjectionIOError, exit-1 node error, final-validate ×2, cleanup hint,
    success) reuses the ONE normalized absolute target cached before the copy.
    Driven with a RELATIVE --target from a temporary cwd so a relative leak is
    observable."""

    def _assert_absolute_target(self, payload):
        target = payload["target"]
        self.assertTrue(target and os.path.isabs(target), target)
        self.assertTrue(target.endswith("/.harness"), target)
        # INIT_* command-level errors and the cleanup hint carry the same
        # cached absolute path. Projection displays (PROJECTION_*) stay relative
        # to the project root by design and are exempt.
        for err in payload["errors"]:
            if err["code"] in ("INIT_IO_ERROR", "INIT_TARGET_EXISTS"):
                self.assertEqual(target, err["path"], err)
        for notice in payload["notices"]:
            if notice["code"] == "INIT_CLEANUP_HINT":
                self.assertEqual(target, notice["path"], notice)
        return target

    def _run_relative_init(self, temp_dir, *cm):
        proj = Path(temp_dir) / "proj"
        if not proj.exists():
            proj.mkdir()
        buffer = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(_chdir(temp_dir))
            for context in cm:
                stack.enter_context(context)
            stack.enter_context(redirect_stdout(buffer))
            rc = harness.cmd_init(Path("proj"), None, "json")
        return rc, json.loads(buffer.getvalue())

    def test_copytree_failure_uses_absolute_target(self):
        def failing_copytree(*a, **k):
            raise shutil.Error("simulated copytree failure")

        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(
                temp_dir,
                mock.patch.object(harness.shutil, "copytree", failing_copytree),
            )
            self.assertEqual(2, rc)
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self._assert_absolute_target(payload)

    def test_manifest_stamp_failure_uses_absolute_target(self):
        real_write_text = Path.write_text

        def fail_manifest_write(self, *a, **k):
            if self.name == "manifest.json":
                raise OSError("simulated manifest write failure")
            return real_write_text(self, *a, **k)

        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(
                temp_dir,
                mock.patch.object(Path, "write_text", fail_manifest_write),
            )
            self.assertEqual(2, rc)
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self._assert_absolute_target(payload)

    def test_projection_io_error_uses_absolute_target(self):
        fd_paths = {}
        real_open = os.open
        real_write = os.write

        def tracking_open(path, *a, **k):
            fd = real_open(path, *a, **k)
            fd_paths[fd] = os.fspath(path)
            return fd

        def fail_projection_write(fd, data):
            if fd_paths.get(fd, "").endswith(".harness-tmp"):
                raise OSError("simulated projection write failure")
            return real_write(fd, data)

        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(
                temp_dir,
                mock.patch.object(harness.os, "open", side_effect=tracking_open),
                mock.patch.object(
                    harness.os, "write", side_effect=fail_projection_write
                ),
            )
            self.assertEqual(2, rc)
            self.assertEqual(
                ["PROJECTION_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self._assert_absolute_target(payload)

    def test_exit1_node_error_uses_absolute_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proj = Path(temp_dir) / "proj"
            proj.mkdir()
            (proj / "AGENTS.md").mkdir()
            rc, payload = self._run_relative_init(temp_dir)
            self.assertEqual(1, rc)
            self.assertIn(
                "PROJECTION_TARGET_INVALID", [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self._assert_absolute_target(payload)

    def test_final_validate_io_uses_absolute_target(self):
        real_validate = harness.validate.validate_harness
        calls = {"n": 0}

        def flaky_validate(root):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise OSError("simulated final validate failure")
            return real_validate(root)

        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(
                temp_dir,
                mock.patch.object(
                    harness.validate, "validate_harness", flaky_validate
                ),
            )
            self.assertEqual(2, rc)
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self._assert_absolute_target(payload)

    def test_final_validation_invalid_uses_absolute_target(self):
        real_validate = harness.validate.validate_harness
        calls = {"n": 0}

        def flaky_validate(root):
            calls["n"] += 1
            result = real_validate(root)
            if calls["n"] >= 2:
                return harness.validate.ValidationResult(
                    root=result.root,
                    schema_version=result.schema_version,
                    errors=(
                        harness.validate.ContractError(
                            "MANIFEST_INVALID", "manifest.json", "seeded invalid"
                        ),
                    ),
                )
            return result

        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(
                temp_dir,
                mock.patch.object(
                    harness.validate, "validate_harness", flaky_validate
                ),
            )
            self.assertEqual(1, rc)
            self.assertIn(
                "MANIFEST_INVALID", [e["code"] for e in payload["errors"]]
            )
            self.assertIn(
                "INIT_CLEANUP_HINT", [n["code"] for n in payload["notices"]]
            )
            self.assertEqual(
                sorted(PROJECTIONS), sorted(payload["projected_files"])
            )
            self._assert_absolute_target(payload)

    def test_success_uses_absolute_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rc, payload = self._run_relative_init(temp_dir)
            self.assertEqual(0, rc)
            self._assert_absolute_target(payload)

    def test_existing_harness_reports_absolute_non_followed_target(self):
        # A .harness symlink pointing at an OUTSIDE directory: the reported
        # target must be the safely-normalized parent + "/.harness", NEVER the
        # symlink's resolved outside destination.
        with tempfile.TemporaryDirectory() as temp_dir:
            proj = Path(temp_dir) / "proj"
            proj.mkdir()
            outside = Path(temp_dir) / "outside-dir"
            outside.mkdir()
            os.symlink(outside, proj / ".harness")
            rc, payload = self._run_relative_init(temp_dir)
            self.assertEqual(1, rc)
            self.assertEqual(
                ["INIT_TARGET_EXISTS"], [e["code"] for e in payload["errors"]]
            )
            target = self._assert_absolute_target(payload)
            self.assertNotIn("outside-dir", target)
            self.assertEqual(str(proj.resolve() / ".harness"), target)
            # The symlink is untouched.
            self.assertTrue((proj / ".harness").is_symlink())


class R6JsonUtf8Tests(unittest.TestCase):
    """R6 finding 3: command-level JSON envelopes must be strictly valid UTF-8
    even when an OSError/shutil.Error path or message carries a POSIX
    surrogateescape code point (e.g. \\udcff from byte 0xff)."""

    def _capture_raw_stdout(self, func):
        raw = io.BytesIO()
        wrapper = io.TextIOWrapper(
            raw, encoding="utf-8", errors="surrogateescape", newline=""
        )
        with redirect_stdout(wrapper):
            rc = func()
        wrapper.flush()
        data = raw.getvalue()
        wrapper.detach()
        return rc, data

    @unittest.skipIf(sys.platform == "win32", "POSIX surrogateescape only")
    def test_copytree_error_message_surrogate_stays_valid_utf8(self):
        with temp_project() as project:
            def failing_copytree(*a, **k):
                raise shutil.Error("bad source node \udcff here")

            def run():
                with mock.patch.object(
                    harness.shutil, "copytree", failing_copytree
                ):
                    return harness.cmd_init(project, None, "json")

            rc, data = self._capture_raw_stdout(run)
            self.assertEqual(2, rc)
            # The raw bytes must strictly decode as UTF-8 and parse as JSON.
            text = data.decode("utf-8")
            payload = json.loads(text)
            self.assertEqual(
                ["INIT_IO_ERROR"], [e["code"] for e in payload["errors"]]
            )
            # ASCII-safe encoding: no raw high bytes escaped into stdout.
            self.assertFalse(any(byte > 0x7F for byte in data))
            # The surrogate survived (as an escape) in the message.
            self.assertIn("\udcff", payload["errors"][0]["message"])

    @unittest.skipIf(sys.platform == "win32", "POSIX surrogateescape only")
    def test_error_path_surrogate_stays_valid_utf8(self):
        # A --target whose string carries a lone surrogate: whatever envelope
        # the target check produces, its raw bytes must be valid UTF-8. This
        # guards against a fix that sanitizes only the message, and exercises
        # the emit() render path (not just emit_command_error).
        with tempfile.TemporaryDirectory() as temp_dir:
            bogus = Path(temp_dir + "/nope\udcff")

            def run():
                return harness.cmd_init(bogus, None, "json")

            rc, data = self._capture_raw_stdout(run)
            self.assertIn(rc, (1, 2))
            text = data.decode("utf-8")
            payload = json.loads(text)
            self.assertFalse(any(byte > 0x7F for byte in data))
            surrogate_in_path = "\udcff" in (payload.get("target") or "") or any(
                "\udcff" in err["path"] for err in payload["errors"]
            )
            self.assertTrue(surrogate_in_path, payload)


validate = harness.validate


def _make_surrogate_result(*, path, message):
    """A failing ValidationResult whose path/message carry a lone surrogate.

    Mirrors what validate_change_management produces for a Change Record whose
    directory name arrived via POSIX surrogateescape (a non-UTF-8 filesystem
    name); constructed directly so the render egress can be exercised on any
    platform, including filesystems that reject non-UTF-8 names.
    """
    return validate.ValidationResult(
        root=Path("/harness"),
        schema_version=1,
        errors=(
            validate.ContractError(
                "CHANGE_REQUIRED_FILE_MISSING", path, message
            ),
        ),
    )


class R7ValidateSurrogateTests(unittest.TestCase):
    """R7: cmd_validate's exit-1 validation results flow through validate.py's
    render_json/render_text. A path or message carrying a POSIX surrogateescape
    code point (e.g. U+DCFF from byte 0xff in a Change Record directory name)
    must still emit strictly valid UTF-8 on stdout (design §7.4 ruling), at both
    the unified entry (harness.py validate) and the standalone validate.py."""

    def _capture_raw_stdout(self, func):
        raw = io.BytesIO()
        wrapper = io.TextIOWrapper(
            raw, encoding="utf-8", errors="surrogateescape", newline=""
        )
        with redirect_stdout(wrapper):
            rc = func()
        wrapper.flush()
        data = raw.getvalue()
        wrapper.detach()
        return rc, data

    @unittest.skipIf(sys.platform == "win32", "POSIX surrogateescape only")
    def test_cmd_validate_surrogate_result_stays_valid_utf8_both_formats(self):
        # Drive the REAL cmd_validate and the standalone validate.main over a
        # ValidationResult whose path AND message carry a lone surrogate,
        # capturing raw stdout bytes. Both must be pure ASCII, strictly decode
        # as UTF-8, and be byte-identical unified-vs-standalone.
        result = _make_surrogate_result(
            path="changes/bad\udcff/summary.md",
            message="required change file missing near \udcff here",
        )
        for fmt in ("json", "text"):
            with mock.patch.object(
                validate, "validate_harness", return_value=result
            ):
                rc_u, data_u = self._capture_raw_stdout(
                    lambda: harness.cmd_validate(SOURCE_HARNESS, fmt)
                )
                rc_s, data_s = self._capture_raw_stdout(
                    lambda: validate.main(
                        ["--root", str(SOURCE_HARNESS), "--format", fmt]
                    )
                )
            self.assertEqual(1, rc_u, fmt)
            self.assertEqual(1, rc_s, fmt)
            # Pure ASCII: no raw high byte (0xff) leaked onto stdout.
            self.assertFalse(any(byte > 0x7F for byte in data_u), (fmt, data_u))
            # Strict UTF-8 decode must succeed (would raise on a raw 0xff).
            text_u = data_u.decode("utf-8")
            # Unified and standalone renderers are byte-identical (§7.4).
            self.assertEqual(data_s, data_u, fmt)
            if fmt == "json":
                payload = json.loads(text_u)
                self.assertEqual(
                    ["CHANGE_REQUIRED_FILE_MISSING"],
                    [e["code"] for e in payload["errors"]],
                )
                # The escape identifies the original code unit in both fields.
                self.assertIn("\\udcff", payload["errors"][0]["path"])
                self.assertIn("\\udcff", payload["errors"][0]["message"])
            else:
                # Exactly one physical line for the single error (no split).
                self.assertEqual(1, text_u.count("\n"), repr(text_u))
                self.assertIn("\\udcff", text_u)

    @unittest.skipIf(sys.platform == "win32", "POSIX surrogateescape only")
    def test_real_nonutf8_change_record_dir_stays_valid_utf8(self):
        # The genuine filesystem probe: a Change Record directory named with a
        # non-UTF-8 byte makes validate report CHANGE_REQUIRED_FILE_MISSING with
        # a surrogate in the path. Some POSIX filesystems (e.g. APFS) reject
        # non-UTF-8 names with EILSEQ; skip there, but the Linux CI exercises it.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".harness"
            shutil.copytree(
                SOURCE_HARNESS, root, ignore=shutil.ignore_patterns("__pycache__")
            )
            changes_dir = os.fsencode(str(root / "changes"))
            try:
                os.mkdir(changes_dir + b"/bad\xff")
            except OSError as error:
                self.skipTest(f"filesystem rejects non-UTF-8 names: {error}")
            outputs = {}
            for label, argv in (
                ("unified", [str(HARNESS_CLI), "validate", "--root", str(root)]),
                ("standalone", [str(VALIDATOR), "--root", str(root)]),
            ):
                for fmt in ("json", "text"):
                    proc = subprocess.run(
                        argv + ["--format", fmt],
                        cwd=REPO_ROOT,
                        capture_output=True,
                        check=False,
                    )
                    outputs[(label, fmt)] = proc
                    self.assertEqual(1, proc.returncode, (label, fmt, proc.stderr))
                    raw = proc.stdout
                    self.assertFalse(
                        any(byte > 0x7F for byte in raw), (label, fmt, raw)
                    )
                    text = raw.decode("utf-8")  # strict; raises on a raw 0xff
                    if fmt == "json":
                        payload = json.loads(text)
                        self.assertFalse(payload["valid"])
                        self.assertTrue(
                            any(
                                "\\udcff" in e["path"] for e in payload["errors"]
                            ),
                            payload,
                        )
                    else:
                        # One physical line per error: line count == error count.
                        lines = [ln for ln in text.split("\n") if ln]
                        self.assertTrue(lines)
                        self.assertTrue(
                            any("\\udcff" in ln for ln in lines), text
                        )
            # Unified and standalone are byte-identical on this fixture too.
            for fmt in ("json", "text"):
                self.assertEqual(
                    outputs[("standalone", fmt)].stdout,
                    outputs[("unified", fmt)].stdout,
                    fmt,
                )


class R7ValidateByteParityTests(unittest.TestCase):
    """R7: the surrogate hardening must not disturb any encodable result.
    Surrogate-free failing fixtures and legitimate non-ASCII (raw UTF-8) output
    must stay unified-vs-standalone byte-identical, with ensure_ascii=False's
    raw-UTF-8 behavior preserved for valid text (§7.4 compatibility restatement).
    """

    @contextmanager
    def _failing_harness(self, mutate):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".harness"
            shutil.copytree(
                SOURCE_HARNESS, root, ignore=shutil.ignore_patterns("__pycache__")
            )
            mutate(root)
            yield root

    def _run_both(self, root, fmt):
        unified = subprocess.run(
            [sys.executable, str(HARNESS_CLI), "validate", "--root", str(root),
             "--format", fmt],
            cwd=REPO_ROOT, capture_output=True, check=False,
        )
        standalone = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root), "--format", fmt],
            cwd=REPO_ROOT, capture_output=True, check=False,
        )
        return unified, standalone

    def test_surrogate_free_failing_fixture_unified_equals_standalone(self):
        def mutate(root):
            manifest = json.loads((root / "manifest.json").read_text("utf-8"))
            # Duplicate a component id -> COMPONENT_ID_DUPLICATE, exit 1.
            manifest["components"][0]["id"] = manifest["components"][1]["id"]
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

        with self._failing_harness(mutate) as root:
            for fmt in ("json", "text"):
                unified, standalone = self._run_both(root, fmt)
                self.assertEqual(1, unified.returncode, fmt)
                self.assertEqual(1, standalone.returncode, fmt)
                self.assertEqual(standalone.stdout, unified.stdout, fmt)

    @unittest.skipIf(sys.platform == "win32", "POSIX path semantics")
    def test_legitimate_non_ascii_path_stays_raw_utf8(self):
        # A Change Record directory named with valid non-ASCII (Chinese) yields
        # CHANGE_REQUIRED_FILE_MISSING with those scalars in the path. They must
        # render as raw UTF-8 (ensure_ascii=False preserved), NOT \uXXXX.
        chinese = "变更记录"

        def mutate(root):
            (root / "changes" / chinese).mkdir()

        with self._failing_harness(mutate) as root:
            unified, standalone = self._run_both(root, "json")
            self.assertEqual(1, unified.returncode, unified.stderr)
            # Raw UTF-8 bytes for the Chinese scalars are present ...
            self.assertIn(chinese.encode("utf-8"), unified.stdout)
            # ... and they are NOT ASCII-escaped as 变 etc.
            self.assertNotIn(b"\\u53d8", unified.stdout)
            self.assertEqual(standalone.stdout, unified.stdout)
            payload = json.loads(unified.stdout.decode("utf-8"))
            self.assertTrue(
                any(chinese in e["path"] for e in payload["errors"]), payload
            )


if __name__ == "__main__":
    unittest.main()
