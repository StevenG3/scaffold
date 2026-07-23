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
