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


def error_pairs(result):
    payload = json.loads(result.stdout)
    return payload, [(item["code"], item["path"]) for item in payload["errors"]]


class ManifestStructureTests(unittest.TestCase):
    def test_missing_manifest(self):
        with copied_harness() as root:
            (root / "manifest.json").unlink()
            result = run_validator(root=root, output_format="json")
        payload, pairs = error_pairs(result)
        self.assertEqual(1, result.returncode)
        self.assertIsNone(payload["schema_version"])
        self.assertIn(("MANIFEST_MISSING", "manifest.json"), pairs)

    def test_invalid_json_manifest(self):
        with copied_harness() as root:
            (root / "manifest.json").write_text("{not-json", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
        payload, pairs = error_pairs(result)
        self.assertEqual(1, result.returncode)
        self.assertIsNone(payload["schema_version"])
        self.assertIn(("MANIFEST_JSON_INVALID", "manifest.json"), pairs)

    def test_missing_required_top_level_fields(self):
        with copied_harness() as root:
            write_manifest(root, {})
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        for field in ("schema_version", "entrypoint", "components", "change_management"):
            self.assertIn(("FIELD_MISSING", f"manifest.json#/{field}"), pairs)

    def test_boolean_schema_version_is_type_invalid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = True
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("FIELD_TYPE_INVALID", "manifest.json#/schema_version"), pairs)

    def test_unsupported_schema_version(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 2
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("SCHEMA_VERSION_UNSUPPORTED", "manifest.json#/schema_version"), pairs)

    def test_duplicate_component_id(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"].append(dict(manifest["components"][0]))
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("COMPONENT_ID_DUPLICATE", "manifest.json#/components/3/id"), pairs)

    def test_unsupported_component_kind(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"][0]["kind"] = "service"
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("COMPONENT_KIND_UNSUPPORTED", "manifest.json#/components/0/kind"), pairs)

    def test_extension_component_kind_accepted(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"][0]["kind"] = "x-service"
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_unknown_fields_rejected(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["custom"] = True
            manifest["components"][0]["custom"] = True
            manifest["change_management"]["custom"] = True
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("FIELD_UNKNOWN", "manifest.json#/custom"), pairs)
        self.assertIn(("FIELD_UNKNOWN", "manifest.json#/components/0/custom"), pairs)
        self.assertIn(("FIELD_UNKNOWN", "manifest.json#/change_management/custom"), pairs)

    def test_extension_fields_accepted(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["x-custom"] = True
            manifest["components"][0]["x-custom"] = True
            manifest["change_management"]["x-custom"] = True
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_empty_required_files_invalid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["change_management"]["required_files"] = []
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(
            ("FIELD_TYPE_INVALID", "manifest.json#/change_management/required_files"),
            pairs,
        )

    def test_duplicate_required_files_invalid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["change_management"]["required_files"] = [
                "summary.md",
                "summary.md",
            ]
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(
            ("FIELD_TYPE_INVALID", "manifest.json#/change_management/required_files"),
            pairs,
        )
