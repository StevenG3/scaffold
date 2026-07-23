import importlib.util
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
    )


BODY = "example body"
BLOCK = f"{harness.MARKER_BEGIN}\n{BODY}\n{harness.MARKER_END}\n"


class ManagedBlockTests(unittest.TestCase):
    def test_create_when_file_absent(self):
        self.assertEqual(BLOCK, harness.apply_managed_block(None, BODY))

    def test_append_when_no_markers(self):
        result = harness.apply_managed_block("user text\n", BODY)
        self.assertEqual("user text\n\n" + BLOCK, result)
        result = harness.apply_managed_block("no trailing newline", BODY)
        self.assertEqual("no trailing newline\n\n" + BLOCK, result)

    def test_replace_between_markers_preserves_user_text(self):
        existing = "before\n" + f"{harness.MARKER_BEGIN}\nold\n{harness.MARKER_END}\n" + "after\n"
        result = harness.apply_managed_block(existing, BODY)
        self.assertEqual("before\n" + BLOCK + "after\n", result)

    def test_apply_is_idempotent(self):
        once = harness.apply_managed_block("user text\n", BODY)
        twice = harness.apply_managed_block(once, BODY)
        self.assertEqual(once, twice)

    def test_broken_markers_raise(self):
        for text in (
            f"{harness.MARKER_BEGIN}\nno end\n",
            f"no begin\n{harness.MARKER_END}\n",
            f"{harness.MARKER_END}\nswapped\n{harness.MARKER_BEGIN}\n",
            f"{harness.MARKER_BEGIN}\n{harness.MARKER_BEGIN}\n{harness.MARKER_END}\n",
        ):
            with self.assertRaises(harness.MarkerBrokenError):
                harness.apply_managed_block(text, BODY)


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


if __name__ == "__main__":
    unittest.main()
