import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = REPO_ROOT / "template" / ".harness"

FORBIDDEN_PRODUCER_TOKENS = ("StevenG3", "2026-07-19", "scaffold", "codex/harness-v0-design")

# Designer ruling (harness-v1.md §5.1): in the bundled LICENSE, and only there,
# exactly one verbatim copyright line is lawful notice rather than producer
# history. Nothing else in LICENSE is relaxed.
LAWFUL_COPYRIGHT_LINE = "Copyright (c) 2026 StevenG3"

# SHA-256 of the audited MIT notice (the reviewed root LICENSE text, verified
# against the OSI/SPDX MIT template after substituting year and holder). The
# bundle LICENSE is pinned to this hash so the notice chain is
# authoritative text -> bundle -> installed.
AUDITED_MIT_NOTICE_SHA256 = "c76ac50199f94e4d75cb6f6ca4dd53d92bd7752bdb7e1911599a71448ad12a70"

# The three substantive segments of the MIT notice: the grant, the
# notice-retention condition, and the warranty disclaimer. Matched against
# whitespace-normalised text because the audited file hard-wraps them.
MIT_REQUIRED_SEGMENTS = (
    "Permission is hereby granted",
    "shall be included in all copies or substantial portions",
    'THE SOFTWARE IS PROVIDED "AS IS"',
)


def find_mit_notice_problems(data: bytes) -> list:
    """Return every reason ``data`` is not the substantive MIT notice."""
    problems = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        return [f"LICENSE is not valid UTF-8: {error}"]
    normalised = " ".join(text.split())
    for segment in MIT_REQUIRED_SEGMENTS:
        if segment not in normalised:
            problems.append(f"MIT notice is missing the segment {segment!r}")
    occurrences = [line for line in text.split("\n") if line == LAWFUL_COPYRIGHT_LINE]
    if len(occurrences) != 1:
        problems.append(
            f"expected exactly one {LAWFUL_COPYRIGHT_LINE!r} line, found {len(occurrences)}"
        )
    return problems


def assert_valid_mit_notice(data: bytes) -> None:
    """Raise ``AssertionError`` unless ``data`` is a valid MIT notice."""
    problems = find_mit_notice_problems(data)
    if problems:
        raise AssertionError("; ".join(problems))


def find_producer_history_violations(harness_root: Path) -> list:
    """Scan a bundle tree for producer-history leaks.

    Every file gets the full forbidden-token scan. For ``LICENSE`` only, the
    single verbatim lawful copyright line must appear exactly once and is
    removed whole from the scanned text; every remaining LICENSE line is then
    scanned with the full token set, ``StevenG3`` included.
    """
    problems = []
    for path in sorted(harness_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(harness_root).as_posix()
        text = path.read_text(encoding="utf-8")
        if relative == "LICENSE":
            lines = text.split("\n")
            occurrences = [line for line in lines if line == LAWFUL_COPYRIGHT_LINE]
            if len(occurrences) != 1:
                problems.append(
                    f"LICENSE must contain exactly one {LAWFUL_COPYRIGHT_LINE!r} line, "
                    f"found {len(occurrences)}"
                )
            text = "\n".join(line for line in lines if line != LAWFUL_COPYRIGHT_LINE)
        for token in FORBIDDEN_PRODUCER_TOKENS:
            if token in text:
                problems.append(f"{token!r} leaked into {relative}")
    return problems


class _MutatedBundle:
    """Copy of the bundle tree whose LICENSE can be tampered with."""

    def __init__(self, license_bytes: bytes):
        self._license_bytes = license_bytes
        self._temp = None

    def __enter__(self) -> Path:
        self._temp = tempfile.mkdtemp(prefix="harness-license-mutation-")
        root = Path(self._temp) / ".harness"
        shutil.copytree(HARNESS_ROOT, root)
        (root / "LICENSE").write_bytes(self._license_bytes)
        return root

    def __exit__(self, *exc_info) -> None:
        shutil.rmtree(self._temp, ignore_errors=True)


class TemplateContractTests(unittest.TestCase):
    def test_bundle_contains_declared_runtime_assets(self):
        expected = {
            "LICENSE",
            "README.md",
            "agents/coordinator.md",
            "bin/harness.py",
            "bin/validate.py",
            "changes/README.md",
            "manifest.json",
            "rules/delivery.md",
            "skills/change-delivery/SKILL.md",
            "skills/harness-bootstrap/SKILL.md",
            "wiki/README.md",
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
        self.assertEqual(2, manifest["schema_version"])
        self.assertEqual("1.0.0", manifest["template_version"])
        self.assertEqual("README.md", manifest["entrypoint"])
        self.assertEqual(
            ["coordinator", "delivery-rule", "change-delivery", "harness-bootstrap"],
            [component["id"] for component in manifest["components"]],
        )
        self.assertEqual(
            ["summary.md", "spec.md", "tasks.md"],
            manifest["change_management"]["required_files"],
        )
        self.assertEqual(["claude-code", "codex", "cursor"], manifest["adapters"])
        self.assertIsNone(manifest["origin"])

    def test_bundle_contains_no_producer_history(self):
        self.assertEqual([], find_producer_history_violations(HARNESS_ROOT))


class LicenseNoticeChainTests(unittest.TestCase):
    """Anchor authoritative notice text -> bundle -> (installed, in the CLI tests)."""

    def test_bundle_license_is_the_audited_root_notice(self):
        bundle = (HARNESS_ROOT / "LICENSE").read_bytes()
        self.assertEqual((REPO_ROOT / "LICENSE").read_bytes(), bundle)
        self.assertEqual(AUDITED_MIT_NOTICE_SHA256, hashlib.sha256(bundle).hexdigest())
        assert_valid_mit_notice(bundle)

    def test_tampering_with_any_substantive_segment_fails(self):
        pristine = (HARNESS_ROOT / "LICENSE").read_text(encoding="utf-8")
        for segment, replacement in (
            ("Permission is hereby granted", "No permission is granted"),
            ("shall be included in all", "may be omitted from"),
            ('THE SOFTWARE IS PROVIDED "AS IS"', "THE SOFTWARE IS FULLY WARRANTED"),
        ):
            with self.subTest(segment=segment):
                self.assertIn(segment, pristine)
                tampered = pristine.replace(segment, replacement)
                self.assertTrue(find_mit_notice_problems(tampered.encode("utf-8")))
                deleted = pristine.replace(segment, "")
                self.assertTrue(find_mit_notice_problems(deleted.encode("utf-8")))

    def test_missing_or_duplicated_copyright_line_fails(self):
        pristine = (HARNESS_ROOT / "LICENSE").read_text(encoding="utf-8")
        without = pristine.replace(LAWFUL_COPYRIGHT_LINE + "\n", "")
        self.assertTrue(find_mit_notice_problems(without.encode("utf-8")))
        doubled = pristine.replace(
            LAWFUL_COPYRIGHT_LINE, LAWFUL_COPYRIGHT_LINE + "\n" + LAWFUL_COPYRIGHT_LINE
        )
        self.assertTrue(find_mit_notice_problems(doubled.encode("utf-8")))

    def test_holder_token_outside_the_copyright_line_fails(self):
        pristine = (HARNESS_ROOT / "LICENSE").read_text(encoding="utf-8")
        leaked = pristine + "StevenG3 internal producer-history note outside the copyright line\n"
        with _MutatedBundle(leaked.encode("utf-8")) as root:
            self.assertTrue(find_producer_history_violations(root))

    def test_other_forbidden_tokens_inside_license_still_fail(self):
        pristine = (HARNESS_ROOT / "LICENSE").read_text(encoding="utf-8")
        for token in ("2026-07-19", "scaffold", "codex/harness-v0-design"):
            with self.subTest(token=token):
                with _MutatedBundle((pristine + token + "\n").encode("utf-8")) as root:
                    self.assertTrue(find_producer_history_violations(root))

    def test_pristine_bundle_copy_passes_the_same_scan(self):
        pristine = (HARNESS_ROOT / "LICENSE").read_bytes()
        with _MutatedBundle(pristine) as root:
            self.assertEqual([], find_producer_history_violations(root))
