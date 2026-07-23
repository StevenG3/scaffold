import json
import subprocess
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
