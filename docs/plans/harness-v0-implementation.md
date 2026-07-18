# Portable Harness v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained `template/.harness/` bundle with a versioned manifest, minimal reusable components, Change templates, and a deterministic standard-library validator.

**Architecture:** Every target-project runtime asset lives under `template/.harness/`; producer-side tests, CI, design and review evidence remain outside it. `manifest.json` is the machine interface, Markdown components are replaceable guidance, and `bin/validate.py` is a single-file deep module that validates structure without interpreting prose.

**Tech Stack:** Python 3.9+ standard library, JSON, Markdown, `unittest`, GitHub Actions.

---

## Execution contract

Before editing, read:

- `docs/design/harness-v0.md`
- `docs/adr/0001-portable-harness-contract.md`
- `README.md`

Start from the commit containing this plan on `main`, then create `feat/harness-v0`. Do not edit the design, ADR or this plan. If an external contract must change, stop and return the proposal to the planner.

The developer owns implementation commits only. The planner/reviewer owns review records, approval and merge.

## Stable validator contract

The validator must use these error codes exactly:

```text
ARGUMENT_INVALID
ROOT_UNREADABLE
MANIFEST_MISSING
MANIFEST_JSON_INVALID
FIELD_MISSING
FIELD_TYPE_INVALID
FIELD_UNKNOWN
SCHEMA_VERSION_UNSUPPORTED
COMPONENT_ID_DUPLICATE
COMPONENT_KIND_UNSUPPORTED
PATH_ABSOLUTE
PATH_SYNTAX_INVALID
PATH_TRAVERSAL
PATH_ESCAPE
PATH_MISSING
PATH_TYPE_INVALID
FILE_EMPTY
SKILL_FRONTMATTER_INVALID
CHANGE_REQUIRED_FILE_MISSING
INTERNAL_ERROR
```

Errors sort by `(code, path, message)`. Text uses `[CODE] path: message`. JSON uses:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "PATH_MISSING",
      "path": "agents/coordinator.md",
      "message": "referenced component file does not exist"
    }
  ],
  "root": "/absolute/path/to/.harness",
  "schema_version": 1
}
```

## File map

| Path | Responsibility |
| --- | --- |
| `template/.harness/manifest.json` | Versioned machine contract |
| `template/.harness/README.md` | Portable entrypoint and component map |
| `template/.harness/agents/coordinator.md` | Replaceable example role |
| `template/.harness/rules/delivery.md` | Framework-neutral delivery rule |
| `template/.harness/skills/change-delivery/SKILL.md` | Minimal delivery workflow |
| `template/.harness/templates/change/*.md` | Required Change Record files |
| `template/.harness/changes/README.md` | Records-directory guidance |
| `template/.harness/bin/validate.py` | CLI and validation deep module |
| `tests/test_template_contract.py` | Static distribution tests |
| `tests/test_validate.py` | Behavioral and boundary tests |
| `.github/workflows/validate.yml` | Producer-side quality gate |
| `README.md` | Repository status and quickstart |

### Task 1: Add the portable static bundle

**Files:**

- Create: `tests/test_template_contract.py`
- Create: `template/.harness/manifest.json`
- Create: `template/.harness/README.md`
- Create: `template/.harness/agents/coordinator.md`
- Create: `template/.harness/rules/delivery.md`
- Create: `template/.harness/skills/change-delivery/SKILL.md`
- Create: `template/.harness/templates/change/{summary,spec,tasks}.md`
- Create: `template/.harness/changes/README.md`

- [ ] **Step 1: Write the failing static contract test**

Create `tests/test_template_contract.py`:

```python
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
```

- [ ] **Step 2: Verify the red state**

Run `python3 -m unittest tests.test_template_contract -v`.

Expected: non-zero exit because `template/.harness/` does not exist.

- [ ] **Step 3: Create the exact Manifest**

Create `template/.harness/manifest.json` using the complete JSON in section 6 of `docs/design/harness-v0.md`. Preserve component IDs, kinds and paths exactly. Preserve required-file order `summary.md`, `spec.md`, `tasks.md`.

- [ ] **Step 4: Create generic guidance files**

Create `template/.harness/README.md`:

```markdown
# Portable AI Coding Harness

This directory is a self-contained, project-neutral Harness. Teams may translate or replace its prose while preserving `manifest.json` and the declared file contract.

## Start

1. Read `manifest.json`.
2. Load only components needed for the current task.
3. Create a Change Record from `templates/change/` before implementation.
4. Record verification evidence in the Change Record.
5. Run `python3 bin/validate.py` before delivery.

## Components

- `agents/`: replaceable role definitions.
- `rules/`: stable project constraints.
- `skills/`: reusable workflows.
- `templates/change/`: required Change Record shape.
- `changes/`: project-local delivery history.

## Validation

Run `python3 bin/validate.py`. The validator is read-only and requires Python 3.9 or newer.
```

Create `template/.harness/agents/coordinator.md`:

```markdown
# Coordinator

Coordinate delivery without assuming a language, framework, issue tracker or CI provider.

## Responsibilities

- Read the Harness entrypoint and manifest.
- Load only components relevant to the current task.
- Require a Change Record before implementation.
- Require reproducible verification evidence before delivery.

## Boundaries

- Do not invent project-specific requirements.
- Do not mark work complete without external evidence.
- Do not replace the project's human approval rules.
```

Create `template/.harness/rules/delivery.md`:

```markdown
# Evidence-Based Delivery

Every change follows four states: understand, plan, execute, verify.

- Understanding identifies the requested outcome and constraints.
- Planning names files, steps and acceptance evidence.
- Execution stays within approved scope.
- Verification runs reproducible checks and records results.

Work is not complete when evidence is missing or a required check fails.
```

Create `template/.harness/skills/change-delivery/SKILL.md`:

```markdown
---
name: change-delivery
description: Deliver a repository change through an explicit record, scoped execution, and reproducible verification.
---

# Change Delivery

## When to use

Use for any repository change that must be reviewed or audited.

## Inputs

- Requested outcome and constraints.
- Project-specific rules and context.
- Verification commands available in the target repository.

## Steps

1. Copy `templates/change/` into a new directory under `changes/`.
2. Complete `spec.md` and obtain project-required approval.
3. Break work into verifiable items in `tasks.md`.
4. Execute only approved scope.
5. Run declared checks and record exact evidence in `summary.md`.

## Outputs

- Complete Change Record.
- Scoped repository change.
- Reproducible verification evidence.

## Verification

Run `python3 bin/validate.py` and the target repository's own quality gates.
```

- [ ] **Step 5: Create the three Change templates**

Create `templates/change/spec.md` with Goal, Scope, Non-goals and Acceptance criteria sections. Create `tasks.md` with four unchecked items: record the approved specification, implement scoped slices, run declared checks, and record evidence/exceptions. Create `summary.md` with Status, Result, Verification evidence, Exceptions and Decision sections. Each empty section contains one direct instruction sentence rather than a placeholder token. Create `changes/README.md` stating that every non-hidden record directory must retain every file declared by `change_management.required_files`.

Use these exact bodies:

```markdown
<!-- templates/change/spec.md -->
# Change Specification

## Goal
State one observable outcome.

## Scope
List what this change may modify.

## Non-goals
List adjacent work explicitly excluded.

## Acceptance criteria
List mechanically verifiable conditions and required human decisions.
```

```markdown
<!-- templates/change/tasks.md -->
# Change Tasks

- [ ] Record the approved specification.
- [ ] Implement one scoped, verifiable slice at a time.
- [ ] Run the declared checks.
- [ ] Record evidence and unresolved exceptions.
```

```markdown
<!-- templates/change/summary.md -->
# Change Summary

## Status
Record the current delivery state.

## Result
Describe the observable outcome.

## Verification evidence
Record exact commands, exit status and relevant output.

## Exceptions
Record unresolved risks or state `None`.

## Decision
Record the final approval or rejection and its owner.
```

```markdown
<!-- changes/README.md -->
# Change Records

Create one non-hidden subdirectory per repository change by copying every file from `../templates/change/`. The directory name is project-defined. Each record must retain all files declared by `change_management.required_files` in `manifest.json`.
```

- [ ] **Step 6: Verify and commit**

Run `python3 -m unittest tests.test_template_contract -v`.

Expected: exit `0`; three tests report `ok`.

```bash
git add template/.harness tests/test_template_contract.py
git commit -m "feat: add portable harness template"
```

### Task 2: Add the validator CLI and success path

**Files:**

- Create: `tests/test_validate.py`
- Create: `template/.harness/bin/validate.py`
- Modify: `tests/test_template_contract.py`

- [ ] **Step 1: Add `bin/validate.py` to the static expected set**

The static test must now expect ten runtime files.

- [ ] **Step 2: Write failing CLI tests**

Create `tests/test_validate.py`:

```python
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
```

- [ ] **Step 3: Verify the red state**

Run `python3 -m unittest tests.test_validate -v`.

Expected: non-zero exit because `bin/validate.py` is missing.

- [ ] **Step 4: Implement CLI result types and rendering**

Create `template/.harness/bin/validate.py` with:

```python
#!/usr/bin/env python3
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class ContractError:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    root: Path
    schema_version: object
    errors: tuple

    @property
    def valid(self):
        return not self.errors


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Validate a portable Harness contract.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def render_text(result):
    if result.valid:
        return "Harness contract is valid.\n"
    return "".join(
        f"[{item.code}] {item.path}: {item.message}\n"
        for item in sorted(result.errors)
    )


def render_json(result):
    payload = {
        "valid": result.valid,
        "errors": [asdict(item) for item in sorted(result.errors)],
        "root": str(result.root),
        "schema_version": result.schema_version,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
```

Implement `validate_harness(root)` to resolve root and read `manifest.json`. A missing file returns `MANIFEST_MISSING` with path `manifest.json` and message `manifest file does not exist`; invalid JSON returns `MANIFEST_JSON_INVALID` with path `manifest.json` and message built by `f"invalid JSON at line {error.lineno} column {error.colno}"`. A parsed object returns its `schema_version` and no errors at this stage. Implement `main(argv=None)` to render the selected format and return `0` for valid or `1` for contract errors. The module entrypoint must convert unexpected `OSError`, `UnicodeError` or `RuntimeError` to an `INTERNAL_ERROR` line on stderr and exit `2` without traceback.

- [ ] **Step 5: Verify and commit**

Run `python3 -m unittest tests.test_template_contract tests.test_validate -v`.

Expected: exit `0`; all tests report `ok`.

```bash
git add template/.harness/bin/validate.py tests/test_template_contract.py tests/test_validate.py
git commit -m "feat: add harness validator CLI"
```

### Task 3: Validate Manifest structure and extensions

**Files:**

- Modify: `tests/test_validate.py`
- Modify: `template/.harness/bin/validate.py`

- [ ] **Step 1: Add failing structural tests**

Add tests for:

- missing Manifest → `MANIFEST_MISSING` and `schema_version: null`;
- invalid JSON → `MANIFEST_JSON_INVALID` and `schema_version: null`;
- missing required top-level fields → `FIELD_MISSING`;
- wrong field types, including boolean `schema_version` → `FIELD_TYPE_INVALID`;
- schema version `2` → `SCHEMA_VERSION_UNSUPPORTED`;
- duplicate component ID → `COMPONENT_ID_DUPLICATE`;
- kind `service` → `COMPONENT_KIND_UNSUPPORTED`;
- kind `x-service` → accepted;
- unknown field `custom` at the top level, component level and Change level → `FIELD_UNKNOWN`;
- unknown field `x-custom` at each of those levels → accepted;
- empty or duplicate `required_files` → `FIELD_TYPE_INVALID`.

Every assertion must check exit `1`, exact code and exact `manifest.json#/...` path. Run the new methods and confirm they fail because the CLI currently accepts invalid structures.

- [ ] **Step 2: Implement strict schema helpers**

Add these constants:

```python
BUILTIN_KINDS = {"agent", "rule", "skill"}
TOP_LEVEL_FIELDS = {"schema_version", "entrypoint", "components", "change_management"}
COMPONENT_FIELDS = {"id", "kind", "path"}
CHANGE_FIELDS = {"template", "records", "required_files"}
```

Add `json_pointer(*parts)`, `reject_unknown_fields(value, allowed, location, errors)` and `require_field(value, field, expected_type, location, errors)`. JSON Pointer segments must escape `~` as `~0` and `/` as `~1`. `validate_manifest_structure(manifest)` must aggregate all independent errors, validate every object level, require non-empty strings and lists, enforce unique IDs and required files, and allow only built-in kinds or non-empty `x-*` kinds.

Do not run path validation for a field whose type failed. Do not stop at the first error.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m unittest discover -s tests -v
```

Expected: exit `0`; final result `OK`.

```bash
git add template/.harness/bin/validate.py tests/test_validate.py
git commit -m "feat: validate harness manifest schema"
```

### Task 4: Validate safe paths, files and Skill frontmatter

**Files:**

- Modify: `tests/test_validate.py`
- Modify: `template/.harness/bin/validate.py`

- [ ] **Step 1: Add failing path tests**

Test component paths `/tmp/outside.md`, `../outside.md`, `agents\coordinator.md`, `C:/outside.md`, and `agents/missing.md`; expect `PATH_ABSOLUTE`, `PATH_TRAVERSAL`, `PATH_SYNTAX_INVALID`, `PATH_SYNTAX_INVALID`, and `PATH_MISSING`. Also test a directory where a file is required (`PATH_TYPE_INVALID`), an empty component (`FILE_EMPTY`), and a symlink escaping the Harness root (`PATH_ESCAPE`; skip only if the platform denies symlink creation).

For the Skill, separately remove the opening delimiter, closing delimiter, `name:` and `description:`; expect `SKILL_FRONTMATTER_INVALID` at `skills/change-delivery/SKILL.md`.

- [ ] **Step 2: Implement POSIX path resolution**

Use `PurePosixPath` for Manifest syntax, but first reject `\\` and Windows drive prefixes matching `^[A-Za-z]:` with `PATH_SYNTAX_INVALID`. Reject absolute paths with `PATH_ABSOLUTE` and any `..` part with `PATH_TRAVERSAL` before touching the filesystem. Convert POSIX parts with `root.joinpath(*pure.parts)`, resolve strictly, require the resolved result to remain under resolved root, then require the declared file/directory type. This ordering and error mapping must be identical on POSIX and Windows.

Implement:

```python
def validate_nonempty_file(path, display_path, errors):
    if not path.read_bytes():
        errors.append(ContractError("FILE_EMPTY", display_path, "referenced file is empty"))
```

Implement `validate_skill_frontmatter(path, display_path, errors)` using line-based detection only: first line and closing delimiter are `---`; between them, non-empty top-level `name:` and `description:` lines must exist. Do not parse full YAML.

Apply safe-path checks to the entrypoint, every component, Change template and records directory. Task 5 owns required Change files so it can emit the more specific `CHANGE_REQUIRED_FILE_MISSING` code. Apply frontmatter only to `kind: skill` after its file passes.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m unittest discover -s tests -v
```

Expected: exit `0`; final result `OK`.

```bash
git add template/.harness/bin/validate.py tests/test_validate.py
git commit -m "feat: validate harness component paths"
```

### Task 5: Validate Change templates and records

**Files:**

- Modify: `tests/test_validate.py`
- Modify: `template/.harness/bin/validate.py`

- [ ] **Step 1: Add failing Change tests**

Add tests that:

1. Delete `templates/change/spec.md` and expect `CHANGE_REQUIRED_FILE_MISSING` at `templates/change/spec.md`.
2. Create `changes/example/` containing only `summary.md` and expect sorted missing-file errors for `spec.md` and `tasks.md`.
3. Add both missing files and expect exit `0`.
4. Add hidden incomplete directory `changes/.draft/` and expect exit `0`.
5. Set a required file to an absolute path and then `../outside.md`; expect `PATH_ABSOLUTE` and `PATH_TRAVERSAL`.
6. Replace a required template file first with an empty file and then a directory; expect `FILE_EMPTY` and `PATH_TYPE_INVALID` at its template-relative path.
7. Replace a required record file first with an empty file and then a directory; expect `FILE_EMPTY` and `PATH_TYPE_INVALID` at its Harness-root-relative record path.
8. Replace required template and record files, one at a time, with symlinks escaping their respective allowed roots; expect `PATH_ESCAPE` (skip only if the platform denies symlink creation).

Run the new methods directly. Expected: non-zero exit because Change validation is not implemented.

- [ ] **Step 2: Implement Change validation**

Implement `validate_change_management(root, config, errors)` with these exact behaviors:

- Resolve `template` and `records` through the shared safe-path helper.
- For each `required_files` POSIX path, reject backslashes, Windows drive prefixes, absolute paths, `..` and resolved root escape using the shared safety rules; require a non-empty regular file under the template, but map an absent file to `CHANGE_REQUIRED_FILE_MISSING` instead of generic `PATH_MISSING`.
- For each sorted, non-hidden immediate child directory under records, require the same non-empty file set.
- Apply the same path-syntax, containment, regular-file and non-empty checks to template files and actual record files. A required file may not escape either its template/record base or the Harness root through a symlink.
- Emit one `CHANGE_REQUIRED_FILE_MISSING` per absent file.
- Ignore hidden child directories and ordinary files directly under records.
- Never inspect Markdown headings or prose.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m unittest discover -s tests -v
```

Expected: exit `0`; final result `OK`.

```bash
git add template/.harness/bin/validate.py tests/test_validate.py
git commit -m "feat: validate harness change records"
```

### Task 6: Lock output, portability and read-only behavior

**Files:**

- Modify: `tests/test_validate.py`
- Modify: `template/.harness/bin/validate.py`

- [ ] **Step 1: Add the complete tree fingerprint helper**

```python
import hashlib
import os
import stat


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
```

- [ ] **Step 2: Add failing boundary tests**

Test that:

- complete tree fingerprint is identical before and after validation, including paths, empty directories, node types, symlink targets and regular-file contents;
- a copied Harness validates with its copied `bin/validate.py` and no `--root`;
- multiple errors sort identically in Text and JSON by `(code, path, message)`;
- missing or non-directory root exits `2`, writes no stdout and writes `[ROOT_UNREADABLE] .:` to stderr;
- `--format xml` exits `2`, writes `[ARGUMENT_INVALID] .:` to stderr and emits no traceback;
- malformed UTF-8 or an unexpected read error exits `2` with `INTERNAL_ERROR` and no traceback.

Run these methods directly and confirm at least the root-error contract fails before implementation.

- [ ] **Step 3: Finish command-level handling**

Before Manifest loading, classify missing, non-directory or unreadable roots as `ROOT_UNREADABLE`. Subclass `argparse.ArgumentParser`, override `error(message)` to raise `ValueError(message)`, and render that exception with prefix `[ARGUMENT_INVALID] .:` and exit `2`. Catch unexpected `OSError`, `UnicodeError` and `RuntimeError` at the entrypoint and render `INTERNAL_ERROR`.

The completed CLI mapping is:

```text
valid contract             -> exit 0, stdout only
contract violations        -> exit 1, stdout only
invocation/environment bug -> exit 2, stderr only
```

- [ ] **Step 4: Verify direct interfaces**

```bash
python3 template/.harness/bin/validate.py
python3 template/.harness/bin/validate.py --format json
python3 -m unittest discover -s tests -v
```

Expected: all commands exit `0`; Text says `Harness contract is valid.`; JSON contains `"valid": true`; unittest ends with `OK`.

- [ ] **Step 5: Commit boundary guarantees**

```bash
git add template/.harness/bin/validate.py tests/test_validate.py
git commit -m "test: lock harness validator boundaries"
```

### Task 7: Add producer CI and repository quickstart

**Files:**

- Create: `.github/workflows/validate.yml`
- Modify: `README.md`

- [ ] **Step 1: Create GitHub Actions workflow**

```yaml
name: Validate Harness

on:
  pull_request:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.9"
      - name: Validate distributable Harness
        run: python3 template/.harness/bin/validate.py
      - name: Run tests
        run: python3 -m unittest discover -s tests -v
      - name: Check whitespace
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}
        run: git diff --check "$BASE_SHA" HEAD
```

- [ ] **Step 2: Update repository README**

Replace the Status paragraph with:

```markdown
仓库已交付 Harness v0 可移植垂直切片：包含自包含分发包、版本化 Manifest、最小 Agent / Rule / Skill / Change Template、标准库校验器及 CI 门禁。完整流水线、MCP 和安装器不在 v0 范围内。
```

Add before License:

```markdown
## 快速验证

运行 `python3 template/.harness/bin/validate.py` 验证分发契约，运行 `python3 -m unittest discover -s tests -v` 执行完整测试。将 `template/.harness/` 复制到目标项目即可开始项目级定制；分发包要求 Python 3.9 或更高版本。
```

- [ ] **Step 3: Run final local gates**

```bash
python3 template/.harness/bin/validate.py
python3 -m unittest discover -s tests -v
git diff --check
```

Expected: validator exits `0`; unittest ends with `OK`; whitespace check has no output and exits `0`.

- [ ] **Step 4: Commit CI and documentation**

```bash
git add .github/workflows/validate.yml README.md
git commit -m "ci: validate portable harness bundle"
```

### Task 8: Produce developer handoff evidence

**Files:** No changes unless verification exposes a defect.

- [ ] **Step 1: Run clean verification**

```bash
python3 template/.harness/bin/validate.py
python3 template/.harness/bin/validate.py --format json
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected: valid Text and JSON results, unittest `OK`, no whitespace output, clean worktree.

- [ ] **Step 2: Confirm scope**

Run `git diff --name-only main...HEAD`.

Every path must be one of `.github/workflows/validate.yml`, `README.md`, a file below `template/.harness/`, or a file below `tests/`. The developer must not create review records, modify approved design/ADR/plan files, add dependencies, or add MCP, full-pipeline or installer behavior.

- [ ] **Step 3: Hand off for independent review**

Provide:

- branch name and exact HEAD SHA;
- commits since `main`;
- validator Text and JSON results;
- complete unittest summary;
- CI run URL after opening the PR;
- deviations and unresolved risks, explicitly `None` when absent.

Do not merge, squash, amend reviewed commits or mark the task accepted. The independent planner/reviewer/merger owns those actions.
