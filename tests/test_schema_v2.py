import unittest

from test_validate import copied_harness, read_manifest, run_validator, write_manifest


def error_codes(result):
    import json

    payload = json.loads(result.stdout)
    return [item["code"] for item in payload["errors"]]


class SchemaV2AcceptanceTests(unittest.TestCase):
    def test_v2_minimal_is_valid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 2
            write_manifest(root, manifest)
            result = run_validator(root=root)
            self.assertEqual(0, result.returncode, result.stdout)

    def test_v2_full_fields_are_valid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 2
            manifest["template_version"] = "1.0.0"
            manifest["adapters"] = ["claude-code", "codex", "cursor", "x-my-adapter"]
            manifest["origin"] = {
                "template_name": "portable-harness",
                "template_version": "1.0.0",
                "initialized_at_schema": 2,
            }
            write_manifest(root, manifest)
            result = run_validator(root=root)
            self.assertEqual(0, result.returncode, result.stdout)

    def test_v2_origin_null_is_valid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 2
            manifest["origin"] = None
            write_manifest(root, manifest)
            self.assertEqual(0, run_validator(root=root).returncode)


class SchemaV2RejectionTests(unittest.TestCase):
    def _errors(self, mutate):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 2
            mutate(manifest)
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode, result.stdout)
            return error_codes(result)

    def test_v1_rejects_v2_fields(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["schema_version"] = 1
            for key in ("template_version", "adapters", "origin"):
                manifest.pop(key, None)
            manifest["adapters"] = ["claude-code"]
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            self.assertIn("FIELD_UNKNOWN", error_codes(result))

    def test_schema_version_3_is_unsupported(self):
        codes = self._errors(lambda m: m.update(schema_version=3))
        self.assertIn("SCHEMA_VERSION_UNSUPPORTED", codes)

    def test_template_version_must_be_semver(self):
        for bad in ("1.0", "01.2.3", "1.2.3-rc1", ""):
            codes = self._errors(lambda m, bad=bad: m.update(template_version=bad))
            self.assertIn("FIELD_VALUE_INVALID", codes, bad)
        codes = self._errors(lambda m: m.update(template_version=1))
        self.assertIn("FIELD_VALUE_INVALID", codes)

    def test_adapters_member_rules(self):
        codes = self._errors(lambda m: m.update(adapters=["claude-code", "claude-code"]))
        self.assertIn("FIELD_VALUE_INVALID", codes)
        codes = self._errors(lambda m: m.update(adapters=["vscode"]))
        self.assertIn("FIELD_VALUE_INVALID", codes)
        codes = self._errors(lambda m: m.update(adapters=[""]))
        self.assertIn("FIELD_TYPE_INVALID", codes)
        codes = self._errors(lambda m: m.update(adapters="claude-code"))
        self.assertIn("FIELD_TYPE_INVALID", codes)

    def test_origin_member_rules(self):
        codes = self._errors(
            lambda m: m.update(origin={"template_version": "1.0.0", "initialized_at_schema": 2})
        )
        self.assertIn("FIELD_MISSING", codes)
        codes = self._errors(
            lambda m: m.update(
                origin={
                    "template_name": "portable-harness",
                    "template_version": "1.0.0",
                    "initialized_at_schema": 9,
                }
            )
        )
        self.assertIn("FIELD_VALUE_INVALID", codes)
        codes = self._errors(
            lambda m: m.update(
                origin={
                    "template_name": "portable-harness",
                    "template_version": "1.0.0",
                    "initialized_at_schema": 2,
                    "extra": True,
                }
            )
        )
        self.assertIn("FIELD_UNKNOWN", codes)
        codes = self._errors(lambda m: m.update(origin=[]))
        self.assertIn("FIELD_TYPE_INVALID", codes)


if __name__ == "__main__":
    unittest.main()
