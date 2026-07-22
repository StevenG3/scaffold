import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = REPO_ROOT / "template" / ".harness"


class TemplateContractTests(unittest.TestCase):
    def test_bundle_contains_declared_runtime_assets(self):
        expected = {
            "README.md",
            "agents/coordinator.md",
            "bin/validate.py",
            "changes/README.md",
            "manifest.json",
            "rules/delivery.md",
            "skills/change-delivery/SKILL.md",
            "templates/change/spec.md",
            "templates/change/summary.md",
            "templates/change/tasks.md",
        }
        actual = {
            path.relative_to(HARNESS_ROOT).as_posix()
            for path in HARNESS_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(expected, actual)

    def test_manifest_declares_generic_contract(self):
        manifest = json.loads((HARNESS_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(1, manifest["schema_version"])
        self.assertEqual("README.md", manifest["entrypoint"])
        self.assertEqual(
            ["coordinator", "delivery-rule", "change-delivery"],
            [component["id"] for component in manifest["components"]],
        )
        self.assertEqual(
            ["summary.md", "spec.md", "tasks.md"],
            manifest["change_management"]["required_files"],
        )

    def test_bundle_contains_no_producer_history(self):
        forbidden = ("StevenG3", "2026-07-19", "scaffold", "codex/harness-v0-design")
        for path in HARNESS_ROOT.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, text, f"{token!r} leaked into {path}")
