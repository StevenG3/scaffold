import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HARNESS = REPO_ROOT / "template" / ".harness"
HARNESS_CLI = SOURCE_HARNESS / "bin" / "harness.py"
VALIDATOR = SOURCE_HARNESS / "bin" / "validate.py"


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


if __name__ == "__main__":
    unittest.main()
