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




def tree_fingerprint(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        metadata = path.lstat()
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        if stat.S_ISLNK(metadata.st_mode):
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif stat.S_ISDIR(metadata.st_mode):
            digest.update(b"directory")
        elif stat.S_ISREG(metadata.st_mode):
            digest.update(b"file\0")
            digest.update(path.read_bytes())
        else:
            digest.update(f"other:{stat.S_IFMT(metadata.st_mode)}".encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()

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


class PathAndFrontmatterTests(unittest.TestCase):
    def _set_component_path(self, root, path_value):
        manifest = read_manifest(root)
        manifest["components"][0]["path"] = path_value
        write_manifest(root, manifest)

    def test_absolute_component_path(self):
        with copied_harness() as root:
            self._set_component_path(root, "/tmp/outside.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_ABSOLUTE", "manifest.json#/components/0/path"), pairs)

    def test_traversal_component_path(self):
        with copied_harness() as root:
            self._set_component_path(root, "../outside.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_TRAVERSAL", "manifest.json#/components/0/path"), pairs)

    def test_backslash_component_path(self):
        with copied_harness() as root:
            self._set_component_path(root, "agents\\coordinator.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_SYNTAX_INVALID", "manifest.json#/components/0/path"), pairs)

    def test_windows_drive_component_path(self):
        with copied_harness() as root:
            self._set_component_path(root, "C:/outside.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_SYNTAX_INVALID", "manifest.json#/components/0/path"), pairs)

    def test_missing_component_path(self):
        with copied_harness() as root:
            self._set_component_path(root, "agents/missing.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_MISSING", "agents/missing.md"), pairs)

    def test_component_path_directory_type_invalid(self):
        with copied_harness() as root:
            self._set_component_path(root, "agents")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_TYPE_INVALID", "agents"), pairs)

    def test_empty_component_file(self):
        with copied_harness() as root:
            target = root / "agents" / "coordinator.md"
            target.write_text("", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("FILE_EMPTY", "agents/coordinator.md"), pairs)

    def test_symlink_escape_component_path(self):
        with copied_harness() as root:
            outside = root.parent / "outside.md"
            outside.write_text("secret", encoding="utf-8")
            link = root / "agents" / "escaped.md"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("platform denied symlink creation")
            self._set_component_path(root, "agents/escaped.md")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("PATH_ESCAPE", "agents/escaped.md"), pairs)

    def _assert_frontmatter_invalid(self, mutate):
        with copied_harness() as root:
            path = root / "skills" / "change-delivery" / "SKILL.md"
            mutate(path)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(
            ("SKILL_FRONTMATTER_INVALID", "skills/change-delivery/SKILL.md"),
            pairs,
        )

    def test_skill_missing_opening_delimiter(self):
        def mutate(path):
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("---\n", "xxxx\n", 1), encoding="utf-8")

        self._assert_frontmatter_invalid(mutate)

    def test_skill_missing_closing_delimiter(self):
        def mutate(path):
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            # Remove the second --- line
            removed = 0
            out = []
            for line in lines:
                if line.strip() == "---":
                    removed += 1
                    if removed == 2:
                        continue
                out.append(line)
            path.write_text("".join(out), encoding="utf-8")

        self._assert_frontmatter_invalid(mutate)

    def test_skill_missing_name(self):
        def mutate(path):
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("name: change-delivery\n", ""), encoding="utf-8")

        self._assert_frontmatter_invalid(mutate)

    def test_skill_missing_description(self):
        def mutate(path):
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "description: Deliver a repository change through an explicit record, scoped execution, and reproducible verification.\n",
                    "",
                ),
                encoding="utf-8",
            )

        self._assert_frontmatter_invalid(mutate)


class ChangeManagementTests(unittest.TestCase):
    def test_missing_required_template_file(self):
        with copied_harness() as root:
            (root / "templates" / "change" / "spec.md").unlink()
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(("CHANGE_REQUIRED_FILE_MISSING", "templates/change/spec.md"), pairs)

    def test_incomplete_change_record_then_complete(self):
        with copied_harness() as root:
            record = root / "changes" / "example"
            record.mkdir()
            (record / "summary.md").write_text("summary\n", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            payload, pairs = error_pairs(result)
            self.assertEqual(
                [
                    ("CHANGE_REQUIRED_FILE_MISSING", "changes/example/spec.md"),
                    ("CHANGE_REQUIRED_FILE_MISSING", "changes/example/tasks.md"),
                ],
                sorted(pairs),
            )
            (record / "spec.md").write_text("spec\n", encoding="utf-8")
            (record / "tasks.md").write_text("tasks\n", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_hidden_incomplete_record_ignored(self):
        with copied_harness() as root:
            draft = root / "changes" / ".draft"
            draft.mkdir()
            (draft / "summary.md").write_text("summary\n", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_required_file_path_safety(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["change_management"]["required_files"] = [
                "/tmp/outside.md",
                "summary.md",
            ]
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(
                ("PATH_ABSOLUTE", "manifest.json#/change_management/required_files/0"),
                pairs,
            )

        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["change_management"]["required_files"] = [
                "../outside.md",
                "summary.md",
            ]
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(
                ("PATH_TRAVERSAL", "manifest.json#/change_management/required_files/0"),
                pairs,
            )

    def test_template_required_file_empty_and_directory(self):
        with copied_harness() as root:
            target = root / "templates" / "change" / "spec.md"
            target.write_text("", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("FILE_EMPTY", "templates/change/spec.md"), pairs)

        with copied_harness() as root:
            target = root / "templates" / "change" / "spec.md"
            target.unlink()
            target.mkdir()
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("PATH_TYPE_INVALID", "templates/change/spec.md"), pairs)

    def test_record_required_file_empty_and_directory(self):
        with copied_harness() as root:
            record = root / "changes" / "example"
            record.mkdir()
            for name in ("summary.md", "spec.md", "tasks.md"):
                (record / name).write_text(f"{name}\n", encoding="utf-8")
            (record / "spec.md").write_text("", encoding="utf-8")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("FILE_EMPTY", "changes/example/spec.md"), pairs)

        with copied_harness() as root:
            record = root / "changes" / "example"
            record.mkdir()
            for name in ("summary.md", "tasks.md"):
                (record / name).write_text(f"{name}\n", encoding="utf-8")
            (record / "spec.md").mkdir()
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("PATH_TYPE_INVALID", "changes/example/spec.md"), pairs)

    def test_required_file_symlink_escape(self):
        with copied_harness() as root:
            outside = root.parent / "outside-template.md"
            outside.write_text("secret\n", encoding="utf-8")
            target = root / "templates" / "change" / "spec.md"
            target.unlink()
            try:
                target.symlink_to(outside)
            except OSError:
                self.skipTest("platform denied symlink creation")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("PATH_ESCAPE", "templates/change/spec.md"), pairs)

        with copied_harness() as root:
            outside = root.parent / "outside-record.md"
            outside.write_text("secret\n", encoding="utf-8")
            record = root / "changes" / "example"
            record.mkdir()
            for name in ("summary.md", "tasks.md"):
                (record / name).write_text(f"{name}\n", encoding="utf-8")
            link = record / "spec.md"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("platform denied symlink creation")
            result = run_validator(root=root, output_format="json")
            self.assertEqual(1, result.returncode)
            _, pairs = error_pairs(result)
            self.assertIn(("PATH_ESCAPE", "changes/example/spec.md"), pairs)


class BoundaryTests(unittest.TestCase):
    def test_validation_is_read_only(self):
        with copied_harness() as root:
            before = tree_fingerprint(root)
            result = run_validator(root=root)
            after = tree_fingerprint(root)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertEqual(before, after)

    def test_copied_validator_without_root(self):
        with copied_harness() as root:
            result = subprocess.run(
                [sys.executable, str(root / "bin" / "validate.py")],
                cwd=root.parent,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertEqual("Harness contract is valid.\n", result.stdout)

    def test_error_sort_matches_text_and_json(self):
        with copied_harness() as root:
            write_manifest(root, {})
            text_result = run_validator(root=root, output_format="text")
            json_result = run_validator(root=root, output_format="json")
        self.assertEqual(1, text_result.returncode)
        self.assertEqual(1, json_result.returncode)
        payload = json.loads(json_result.stdout)
        json_lines = [
            f"[{item['code']}] {item['path']}: {item['message']}\n"
            for item in payload["errors"]
        ]
        self.assertEqual("".join(json_lines), text_result.stdout)
        codes = [item["code"] for item in payload["errors"]]
        paths = [item["path"] for item in payload["errors"]]
        messages = [item["message"] for item in payload["errors"]]
        self.assertEqual(
            sorted(zip(codes, paths, messages)),
            list(zip(codes, paths, messages)),
        )

    def test_missing_root_is_unreadable(self):
        missing = REPO_ROOT / "tmp-missing-harness-root"
        result = run_validator(root=missing, output_format="text")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("[ROOT_UNREADABLE] .:", result.stderr)

    def test_nondirectory_root_is_unreadable(self):
        with tempfile.NamedTemporaryFile() as handle:
            result = run_validator(root=Path(handle.name), output_format="text")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("[ROOT_UNREADABLE] .:", result.stderr)

    def test_invalid_format_argument(self):
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--root",
                str(SOURCE_HARNESS),
                "--format",
                "xml",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("[ARGUMENT_INVALID] .:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_utf8_is_internal_error(self):
        with copied_harness() as root:
            (root / "manifest.json").write_bytes(b'{"schema_version": 1, "bad": "\xff"}')
            result = run_validator(root=root, output_format="text")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("[INTERNAL_ERROR] .:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class ReviewRegressionTests(unittest.TestCase):
    def test_empty_extension_kind_unsupported(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"][0]["kind"] = "x-"
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        _, pairs = error_pairs(result)
        self.assertIn(
            ("COMPONENT_KIND_UNSUPPORTED", "manifest.json#/components/0/kind"),
            pairs,
        )

    def test_nonfinite_json_constants_rejected(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with copied_harness() as root:
                    manifest = read_manifest(root)
                    text = json.dumps(manifest, ensure_ascii=False, indent=2)
                    text = text[:-2] + f',\n  "x-number": {constant}\n}}\n'
                    (root / "manifest.json").write_text(text, encoding="utf-8")
                    result = run_validator(root=root, output_format="json")
                self.assertEqual(1, result.returncode, result.stderr or result.stdout)
                payload, pairs = error_pairs(result)
                self.assertFalse(payload["valid"])
                self.assertIn(("MANIFEST_JSON_INVALID", "manifest.json"), pairs)
                self.assertEqual("", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_nul_in_component_path_is_syntax_invalid(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"][0]["path"] = "agents/evil\u0000.md"
            write_manifest(root, manifest)
            result = run_validator(root=root, output_format="json")
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        _, pairs = error_pairs(result)
        self.assertIn(
            ("PATH_SYNTAX_INVALID", "manifest.json#/components/0/path"),
            pairs,
        )


    def _assert_single_line_text_errors(self, result):
        self.assertEqual(1, result.returncode, result.stderr or result.stdout)
        self.assertEqual("", result.stderr)
        lines = result.stdout.splitlines()
        self.assertGreaterEqual(len(lines), 1)
        self.assertEqual(len(lines), result.stdout.count("\n"))
        for line in lines:
            self.assertNotRegex(line, r"[\x00-\x1f\x7f\u0085\u2028\u2029]")
            self.assertRegex(line, r"^\[([A-Z0-9_]+)\] .+: .+$")

    def test_text_escapes_control_chars_in_component_path(self):
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["components"][0]["path"] = "agents/missing\nsecond-line.md"
            write_manifest(root, manifest)
            text_result = run_validator(root=root, output_format="text")
            json_result = run_validator(root=root, output_format="json")
        self._assert_single_line_text_errors(text_result)
        self.assertIn("agents/missing\\u000asecond-line.md", text_result.stdout)
        self.assertNotIn("\nsecond-line", text_result.stdout.replace("\\u000a", ""))
        payload = json.loads(json_result.stdout)
        self.assertEqual(1, json_result.returncode)
        self.assertEqual(
            "agents/missing\nsecond-line.md",
            payload["errors"][0]["path"],
        )

    def test_text_escapes_unicode_line_separators_in_component_path(self):
        separators = {
            "\u0085": "\\u0085",
            "\u2028": "\\u2028",
            "\u2029": "\\u2029",
        }
        for separator, escaped in separators.items():
            with self.subTest(separator=hex(ord(separator))):
                with copied_harness() as root:
                    manifest = read_manifest(root)
                    manifest["components"][0]["path"] = (
                        f"agents/missing{separator}second-line.md"
                    )
                    write_manifest(root, manifest)
                    text_result = run_validator(root=root, output_format="text")
                    json_result = run_validator(root=root, output_format="json")
                self._assert_single_line_text_errors(text_result)
                self.assertEqual(1, len(text_result.stdout.splitlines()))
                self.assertIn(
                    f"agents/missing{escaped}second-line.md",
                    text_result.stdout,
                )
                payload = json.loads(json_result.stdout)
                self.assertEqual(1, json_result.returncode)
                self.assertEqual(
                    f"agents/missing{separator}second-line.md",
                    payload["errors"][0]["path"],
                )

    def test_text_escapes_control_chars_in_manifest_field_and_id(self):
        duplicate_id = "coord\tinator"
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["bad\rfield"] = True
            manifest["components"][0]["id"] = duplicate_id
            manifest["components"].append(dict(manifest["components"][0]))
            write_manifest(root, manifest)
            text_result = run_validator(root=root, output_format="text")
            json_result = run_validator(root=root, output_format="json")
        self._assert_single_line_text_errors(text_result)
        self.assertIn("manifest.json#/bad\\u000dfield", text_result.stdout)
        expected_message = f"duplicate component id {duplicate_id!r}"
        self.assertIn(expected_message, text_result.stdout)
        payload = json.loads(json_result.stdout)
        self.assertEqual(1, json_result.returncode)
        paths = [item["path"] for item in payload["errors"]]
        messages = [item["message"] for item in payload["errors"]]
        self.assertTrue(any("bad\rfield" in path for path in paths))
        self.assertIn(expected_message, messages)

    def test_unpaired_surrogate_is_manifest_json_invalid(self):
        placements = {
            "unknown-field-name": lambda manifest, char: manifest.update({char: 1}),
            "extension-field-value": lambda manifest, char: manifest.update(
                {"x-value": char}
            ),
        }
        surrogates = {"high": "\ud800", "low": "\udfff"}
        for placement, mutate in placements.items():
            for kind, char in surrogates.items():
                for output_format in ("text", "json"):
                    with self.subTest(
                        placement=placement, surrogate=kind, format=output_format
                    ):
                        with copied_harness() as root:
                            manifest = read_manifest(root)
                            mutate(manifest, char)
                            # ensure_ascii keeps the file itself pure ASCII, so the
                            # surrogate only appears after json.loads decodes it.
                            (root / "manifest.json").write_text(
                                json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
                                encoding="ascii",
                            )
                            result = run_validator(root=root, output_format=output_format)
                        self.assertEqual(1, result.returncode, result.stderr)
                        self.assertEqual("", result.stderr)
                        self.assertNotIn("Traceback", result.stderr + result.stdout)
                        # stdout must be encodable as UTF-8, which is what failed before.
                        result.stdout.encode("utf-8")
                        if output_format == "json":
                            payload = json.loads(result.stdout)
                            self.assertFalse(payload["valid"])
                            self.assertIsNone(payload["schema_version"])
                            self.assertEqual(
                                [("MANIFEST_JSON_INVALID", "manifest.json")],
                                [(i["code"], i["path"]) for i in payload["errors"]],
                            )
                        else:
                            self._assert_single_line_text_errors(result)
                            self.assertIn("[MANIFEST_JSON_INVALID] manifest.json:", result.stdout)

    def test_valid_surrogate_pair_is_not_rejected(self):
        # U+1F600 is written to disk as the escaped pair 😀; json.loads
        # combines it into one scalar, so it must not trip the surrogate check.
        with copied_harness() as root:
            manifest = read_manifest(root)
            manifest["x-emoji"] = "\U0001f600"
            (root / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
                encoding="ascii",
            )
            raw = (root / "manifest.json").read_text(encoding="ascii")
            result = run_validator(root=root, output_format="json")
        self.assertIn("\\ud83d\\ude00", raw)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertEqual("", result.stderr)
        payload, pairs = error_pairs(result)
        self.assertTrue(payload["valid"])
        self.assertEqual([], pairs)
