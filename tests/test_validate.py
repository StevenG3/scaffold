import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HARNESS = REPO_ROOT / "template" / ".harness"
VALIDATOR = SOURCE_HARNESS / "bin" / "validate.py"


def run_validator(root=SOURCE_HARNESS, output_format="text", validator=VALIDATOR):
    return subprocess.run(
        [sys.executable, str(validator), "--root", str(root), "--format", output_format],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


@contextmanager
def copied_harness():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / ".harness"
        shutil.copytree(SOURCE_HARNESS, root)
        yield root


def read_manifest(root):
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(root, manifest):
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class ValidatorTests(unittest.TestCase):
    def test_official_bundle_is_valid(self):
        result = run_validator()
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertEqual("Harness contract is valid.\n", result.stdout)
        self.assertEqual("", result.stderr)

    def test_json_success_contract(self):
        result = run_validator(output_format="json")
        payload = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(payload["valid"])
        self.assertEqual([], payload["errors"])
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual(str(SOURCE_HARNESS.resolve()), payload["root"])
