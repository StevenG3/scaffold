# Harness v1 实施计划 — 接入体验纵切片

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现设计规格 [harness-v1.md](../design/harness-v1.md)：单文件 CLI `template/.harness/bin/harness.py`（`init` / `adapt` / `validate`）、Schema v2 校验、受管块投影、`harness-bootstrap` Skill、`wiki/` 占位与测试/CI 扩展。

**Architecture:** `.harness/` 平台中立事实源；`harness.py` 复用 `validate.py` 的校验实现与错误类型；投影用受管块写入项目根的 `CLAUDE.md` / `AGENTS.md` / `.cursor/rules/harness.mdc`；定制交给 bootstrap Skill（纯文档交付物）。

**Tech Stack:** Python 3.9+ 标准库（`argparse` / `json` / `shutil` / `pathlib`）、`unittest` + `tempfile`、GitHub Actions。

## Global Constraints

- 仅 Python 3.9+ 标准库；禁止第三方依赖与网络访问（设计 §16）。
- `template/.harness/` 内任何文件禁止出现 token：`StevenG3`、`2026-07-19`、`scaffold`、`codex/harness-v0-design`（由 `tests/test_template_contract.py::test_bundle_contains_no_producer_history` 机械强制）。因此模板名常量取 `portable-harness`；分发包内不得写入任何日期。
- `validate.py` 独立命令契约（参数、输出、退出码）不得改变；只允许内部扩展 Schema v2 支持。既有 `tests/test_validate.py` 的测试**不修改**且必须持续通过。例外（设计方裁决，2026-07-23，仅限以下三处「样例事实」修正，测试意图不变）：(a) `test_unsupported_schema_version` 的样例值 `schema_version = 2` 改为 `3`（意图：不支持的版本被拒绝）；(b) `test_json_success_contract` 对官方模板 `schema_version` 的断言由 `1` 改为 `2`（意图：JSON 成功输出契约稳定）；(c) `test_duplicate_component_id` 期望的指针由 `components/3/id` 改为 `components/4/id`（意图：重复 id 被定位报告；模板组件数由 3 变 4 所致）。除此三处外 `tests/test_validate.py` 不得修改。
- 退出码语义全 CLI 统一：`0` 成功；`1` 契约/状态违规；`2` 参数错误、根不可读或内部错误。
- 所有命令确定性输出：产物与 stdout 不含时间戳、随机值；产物文件不含绝对路径。
- 受管块外的用户内容在任何操作下逐字节保留；`init` 之外的命令不得在 `.harness/` 内创建文件。
- 分发包内英文行文（与既有模板一致）；生产者侧文档中文。
- 实现分支：从设计分支 `design/harness-v1` 切出 `feature/harness-v1`，每个 Task 至少一次提交。

## 文件结构总览

| 文件 | 动作 | 职责 |
| --- | --- | --- |
| `template/.harness/bin/validate.py` | 修改 | 增加 Schema v2 字段校验（v1 行为不变） |
| `template/.harness/bin/harness.py` | 新建 | 单文件 CLI：init / adapt / validate |
| `template/.harness/skills/harness-bootstrap/SKILL.md` | 新建 | 定制引导 Skill（含访谈硬规范与正反示例） |
| `template/.harness/wiki/README.md` | 新建 | 项目知识落点说明（非机器契约） |
| `template/.harness/manifest.json` | 修改 | 升级 Schema v2，注册 bootstrap，声明 adapters |
| `template/.harness/README.md` | 修改 | 加入 CLI 与 bootstrap 使用说明 |
| `tests/test_schema_v2.py` | 新建 | Schema v2 校验矩阵 |
| `tests/test_adapters.py` | 新建 | 受管块引擎 + adapt 行为矩阵 |
| `tests/test_harness_cli.py` | 新建 | validate 一致性 + init 行为矩阵 |
| `tests/test_template_contract.py` | 修改 | 扩充分发包文件清单与 Manifest 断言 |
| `.github/workflows/validate.yml` | 修改 | 追加 harness.py 门禁 |
| `README.md` | 修改 | 「设计与决策」补 v1 链接 |

---

### Task 1: validate.py 支持 Schema v2

**Files:**
- Modify: `template/.harness/bin/validate.py`
- Test: `tests/test_schema_v2.py`（新建）

**Interfaces:**
- Consumes: 现有 `validate.py` 的 `ContractError`、`require_field`、`reject_unknown_fields`、`json_pointer`、`validate_manifest_structure`。
- Produces（后续 Task 依赖，名称必须一字不差）：模块级常量 `BUILTIN_ADAPTER_NAMES = ("claude-code", "codex", "cursor")`、`SUPPORTED_SCHEMA_VERSIONS = (1, 2)`；新错误码 `FIELD_VALUE_INVALID`。

- [ ] **Step 1: 写失败测试**

新建 `tests/test_schema_v2.py`（帮助函数直接复用 `test_validate.py`，`unittest discover` 会把 `tests/` 加入 `sys.path`）：

```python
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
```

- [ ] **Step 2: 确认失败**

Run: `python3 -m unittest tests.test_schema_v2 -v`（在仓库根执行，下同）
Expected: `SchemaV2AcceptanceTests` 全部 FAIL（v2 被 `SCHEMA_VERSION_UNSUPPORTED` 拒绝）。

- [ ] **Step 3: 实现 validate.py 扩展**

在 `template/.harness/bin/validate.py` 顶部常量区（`BUILTIN_KINDS` 附近）追加：

```python
SUPPORTED_SCHEMA_VERSIONS = (1, 2)
BUILTIN_ADAPTER_NAMES = ("claude-code", "codex", "cursor")
TOP_LEVEL_FIELDS_V2 = TOP_LEVEL_FIELDS | {"template_version", "adapters", "origin"}
ORIGIN_FIELDS = {"template_name", "template_version", "initialized_at_schema"}
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
```

`validate_manifest_structure` 中，把原来的

```python
    reject_unknown_fields(manifest, TOP_LEVEL_FIELDS, (), errors)

    schema_version = require_field(manifest, "schema_version", int, (), errors)
    if schema_version is not None and schema_version != 1:
```

替换为（先读版本，再按版本选 allowed 集；版本缺失或非法时按 v1 集处理）：

```python
    schema_version = require_field(manifest, "schema_version", int, (), errors)
    if schema_version is not None and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            ContractError(
                "SCHEMA_VERSION_UNSUPPORTED",
                json_pointer("schema_version"),
                f"schema_version {schema_version!r} is unsupported",
            )
        )

    allowed_top = TOP_LEVEL_FIELDS_V2 if schema_version == 2 else TOP_LEVEL_FIELDS
    reject_unknown_fields(manifest, allowed_top, (), errors)
    if schema_version == 2:
        _validate_v2_fields(manifest, errors)
```

（原 `if schema_version is not None and schema_version != 1:` 整段错误追加逻辑被上面吸收，勿重复。）在 `_is_supported_kind` 之前新增：

```python
def _validate_semver(value, pointer, errors, field_name):
    if type(value) is not str or not _SEMVER_RE.match(value):
        errors.append(
            ContractError(
                "FIELD_VALUE_INVALID",
                pointer,
                f"field {field_name!r} must be a semantic version like '1.2.3'",
            )
        )
        return False
    return True


def _validate_v2_fields(manifest, errors):
    if "template_version" in manifest:
        _validate_semver(
            manifest["template_version"],
            json_pointer("template_version"),
            errors,
            "template_version",
        )

    if "adapters" in manifest:
        adapters = manifest["adapters"]
        if type(adapters) is not list:
            errors.append(
                ContractError(
                    "FIELD_TYPE_INVALID",
                    json_pointer("adapters"),
                    "field 'adapters' must be list",
                )
            )
        else:
            seen = set()
            for index, name in enumerate(adapters):
                pointer = json_pointer("adapters", index)
                if type(name) is not str or name == "":
                    errors.append(
                        ContractError(
                            "FIELD_TYPE_INVALID",
                            pointer,
                            "adapter name must be a non-empty string",
                        )
                    )
                    continue
                if name not in BUILTIN_ADAPTER_NAMES and not (
                    name.startswith("x-") and len(name) > 2
                ):
                    errors.append(
                        ContractError(
                            "FIELD_VALUE_INVALID",
                            pointer,
                            f"unsupported adapter {name!r}",
                        )
                    )
                if name in seen:
                    errors.append(
                        ContractError(
                            "FIELD_VALUE_INVALID",
                            pointer,
                            f"duplicate adapter {name!r}",
                        )
                    )
                seen.add(name)

    origin = manifest.get("origin")
    if "origin" in manifest and origin is not None:
        location = ("origin",)
        if type(origin) is not dict:
            errors.append(
                ContractError(
                    "FIELD_TYPE_INVALID",
                    json_pointer("origin"),
                    "field 'origin' must be null or an object",
                )
            )
        else:
            reject_unknown_fields(origin, ORIGIN_FIELDS, location, errors)
            require_field(origin, "template_name", str, location, errors)
            version = require_field(origin, "template_version", str, location, errors)
            if version is not None:
                _validate_semver(
                    version,
                    json_pointer("origin", "template_version"),
                    errors,
                    "template_version",
                )
            initialized = require_field(
                origin, "initialized_at_schema", int, location, errors
            )
            if initialized is not None and initialized not in SUPPORTED_SCHEMA_VERSIONS:
                errors.append(
                    ContractError(
                        "FIELD_VALUE_INVALID",
                        json_pointer("origin", "initialized_at_schema"),
                        f"initialized_at_schema {initialized!r} is unsupported",
                    )
                )
```

- [ ] **Step 4: 确认通过（含回归）**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全部 PASS（既有 `test_validate.py` 未改动且通过）。

- [ ] **Step 5: Commit**

```bash
git add template/.harness/bin/validate.py tests/test_schema_v2.py
git commit -m "feat: accept manifest schema v2 in validator"
```

---

### Task 2: bootstrap Skill、wiki 占位与 Manifest v2 升级

**Files:**
- Create: `template/.harness/skills/harness-bootstrap/SKILL.md`
- Create: `template/.harness/wiki/README.md`
- Modify: `template/.harness/manifest.json`
- Modify: `tests/test_template_contract.py`

**Interfaces:**
- Consumes: Task 1 的 Schema v2 校验。
- Produces: 模板 Manifest 声明 `template_version: "1.0.0"`、`adapters: ["claude-code", "codex", "cursor"]`、`origin: null`、组件 `harness-bootstrap`；Task 3-6 的 CLI 依赖这些字段。

- [ ] **Step 1: 更新契约测试（先失败）**

`tests/test_template_contract.py` 中，`test_bundle_contains_declared_runtime_assets` 的 `expected` 集合追加两项（`bin/harness.py` 在 Task 3 加入，此处勿加）：

```python
            "skills/harness-bootstrap/SKILL.md",
            "wiki/README.md",
```

`test_manifest_declares_generic_contract` 整体替换为：

```python
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
```

Run: `python3 -m unittest tests.test_template_contract -v` → Expected: FAIL。

- [ ] **Step 2: 新建 SKILL.md**

`template/.harness/skills/harness-bootstrap/SKILL.md` 全文：

```markdown
---
name: harness-bootstrap
description: Customize a freshly installed Harness into a project-specific Harness through evidence-based interviews and recorded outputs.
---

# Harness Bootstrap

## When to use

Run once after `harness.py init` installs this Harness into a project, or whenever project-level customization must be rebuilt.

## Inputs

- The target project's codebase.
- The installed Harness directory.
- A human partner able to approve project decisions.

## Non-negotiable interview rules

1. **Scout before asking.** First read the codebase: languages, build and test commands, directory layout, lint and CI configuration, existing agent instruction files. Never ask the user anything the codebase can answer.
2. **One question per message.**
3. **Every question offers 2-4 enumerated options.** Open questions must present drafted candidates based on scouting, for confirmation or edit.
4. **Every question marks a recommended option**, with a reason grounded in scouting evidence.
5. **Every option states its trade-off**, not only its benefit.
6. **The default path must work.** A user who accepts every recommendation must end with a coherent, usable Harness.

### Example - compliant

> Which command set is the delivery quality gate? I found `pytest` in CI and a `lint` script in the build file.
>
> - A. `pytest` only - fastest gate, but style drift goes uncaught. (recommended: CI already enforces it)
> - B. `pytest` plus `lint` - stricter, slower on large changes.
> - C. Other - tell me the exact commands.

### Example - violations

> "What are your coding standards?" (transfers discovery cost to the user)
>
> "Anything else to add?" (no options, no recommendation)

## Steps

1. Scout the codebase and record findings.
2. Interview the user following the rules above. Cover at least: one-line project purpose, delivery quality-gate commands, change approval convention, Harness prose language.
3. Write project rules into `rules/` (for example `rules/project.md`) and register each new file in `manifest.json` under `components`.
4. Draft `wiki/overview.md` and `wiki/conventions.md` skeletons from scouting findings, marking gaps explicitly.
5. Record this bootstrap itself as the first Change Record using the change-delivery skill.

## Outputs

- Project rules registered in the manifest.
- Wiki skeleton under `wiki/`.
- A complete first Change Record.

## Verification

Run `python3 bin/harness.py validate` and `python3 bin/harness.py adapt --check`; store the exact output in the Change Record summary.
```

- [ ] **Step 3: 新建 wiki/README.md**

```markdown
# Project Wiki

Project-specific knowledge lives here: system overview, key conventions, and domain notes. The harness-bootstrap skill drafts the initial skeleton; keep pages current as the project evolves. This directory is not part of the machine contract.
```

- [ ] **Step 4: 升级 manifest.json**

`template/.harness/manifest.json` 全文替换：

```json
{
  "schema_version": 2,
  "template_version": "1.0.0",
  "entrypoint": "README.md",
  "components": [
    {
      "id": "coordinator",
      "kind": "agent",
      "path": "agents/coordinator.md"
    },
    {
      "id": "delivery-rule",
      "kind": "rule",
      "path": "rules/delivery.md"
    },
    {
      "id": "change-delivery",
      "kind": "skill",
      "path": "skills/change-delivery/SKILL.md"
    },
    {
      "id": "harness-bootstrap",
      "kind": "skill",
      "path": "skills/harness-bootstrap/SKILL.md"
    }
  ],
  "change_management": {
    "template": "templates/change",
    "records": "changes",
    "required_files": [
      "summary.md",
      "spec.md",
      "tasks.md"
    ]
  },
  "adapters": [
    "claude-code",
    "codex",
    "cursor"
  ],
  "origin": null
}
```

- [ ] **Step 5: 验证并提交**

Run: `python3 template/.harness/bin/validate.py && python3 -m unittest discover -s tests -v`
Expected: 校验输出 `Harness contract is valid.`，测试全 PASS。

```bash
git add template/.harness/skills/harness-bootstrap/SKILL.md template/.harness/wiki/README.md template/.harness/manifest.json tests/test_template_contract.py
git commit -m "feat: add bootstrap skill, wiki stub, and schema v2 manifest"
```

---

### Task 3: harness.py 骨架与 validate 子命令

**Files:**
- Create: `template/.harness/bin/harness.py`
- Modify: `tests/test_template_contract.py`（expected 集合加 `bin/harness.py`）
- Test: `tests/test_harness_cli.py`（新建）

**Interfaces:**
- Consumes: `validate.validate_harness(root)`、`validate.render_text` / `render_json`、`validate.RootUnreadableError`、`validate.ContractError`、`validate.escape_text_field`。
- Produces（Task 4-6 依赖）：`parse_args(argv)`、`emit(fmt, command, ok, errors, notices, extra) -> int`（返回退出码 0/1）、`cmd_validate(root, fmt) -> int`、`main(argv=None) -> int`、常量 `TEMPLATE_NAME = "portable-harness"`、`BIN_DIR`。

- [ ] **Step 1: 写失败测试**

新建 `tests/test_harness_cli.py`：

```python
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
```

同时给 `tests/test_template_contract.py` 的 `expected` 集合追加 `"bin/harness.py"`。

Run: `python3 -m unittest tests.test_harness_cli tests.test_template_contract -v` → Expected: FAIL（文件不存在）。

- [ ] **Step 2: 实现骨架**

新建 `template/.harness/bin/harness.py`：

```python
#!/usr/bin/env python3
"""Portable Harness CLI: install, project, and validate the bundle."""
import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path, PurePosixPath

BIN_DIR = Path(__file__).resolve().parent
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))
import validate  # noqa: E402

TEMPLATE_NAME = "portable-harness"
MARKER_BEGIN = "<!-- BEGIN HARNESS MANAGED BLOCK (harness adapt) -->"
MARKER_END = "<!-- END HARNESS MANAGED BLOCK -->"


class MarkerBrokenError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parse_args(argv=None):
    parser = _ArgumentParser(description="Portable Harness CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", description="Install this Harness into a target project."
    )
    init_parser.add_argument("--target", type=Path, required=True)
    init_parser.add_argument("--adapters", default=None)
    init_parser.add_argument("--format", choices=("text", "json"), default="text")

    adapt_parser = subparsers.add_parser(
        "adapt", description="Generate platform projection files."
    )
    adapt_parser.add_argument("--root", type=Path, default=BIN_DIR.parent)
    adapt_parser.add_argument("--check", action="store_true")
    adapt_parser.add_argument("--format", choices=("text", "json"), default="text")

    validate_parser = subparsers.add_parser(
        "validate", description="Validate the Harness contract."
    )
    validate_parser.add_argument("--root", type=Path, default=BIN_DIR.parent)
    validate_parser.add_argument("--format", choices=("text", "json"), default="text")

    return parser.parse_args(argv)


def emit(fmt, command, ok, errors, notices, extra):
    """Render one command result. Returns the exit code (0 ok, 1 violation)."""
    errors = sorted(errors)
    notices = sorted(notices)
    if fmt == "json":
        payload = {
            "ok": ok,
            "command": command,
            "errors": [asdict(item) for item in errors],
            "notices": [asdict(item) for item in notices],
        }
        payload.update(extra)
        sys.stdout.write(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    else:
        for item in errors + notices:
            sys.stdout.write(
                f"[{validate.escape_text_field(item.code)}] "
                f"{validate.escape_text_field(item.path)}: "
                f"{validate.escape_text_field(item.message)}\n"
            )
        for path in extra.get("written", ()):
            sys.stdout.write(f"written: {path}\n")
        if ok:
            sys.stdout.write(f"{command}: ok\n")
    return 0 if ok else 1


def cmd_validate(root, fmt):
    try:
        result = validate.validate_harness(root)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    rendered = (
        validate.render_json(result) if fmt == "json" else validate.render_text(result)
    )
    sys.stdout.write(rendered)
    return 0 if result.valid else 1


def main(argv=None):
    try:
        args = parse_args(argv)
    except ValueError as error:
        sys.stderr.write(f"[ARGUMENT_INVALID] .: {error}\n")
        return 2
    if args.command == "validate":
        return cmd_validate(args.root, args.format)
    if args.command == "adapt":
        return cmd_adapt(args.root, args.check, args.format)
    if args.command == "init":
        return cmd_init(args.target, args.adapters, args.format)
    raise RuntimeError(f"unsupported command {args.command!r}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as error:
        sys.stderr.write(f"[INTERNAL_ERROR] .: {error}\n")
        raise SystemExit(2)
```

`cmd_adapt` / `cmd_init` 本 Task 先占位（保证 `validate` 与参数解析可测）：

```python
def cmd_adapt(root, check, fmt):
    raise RuntimeError("adapt is implemented in a later task")


def cmd_init(target, adapters_raw, fmt):
    raise RuntimeError("init is implemented in a later task")
```

（把这两个占位函数放在 `main` 之前；Task 4/6 会整体替换它们。）

- [ ] **Step 3: 确认通过**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全 PASS。

- [ ] **Step 4: Commit**

```bash
git add template/.harness/bin/harness.py tests/test_harness_cli.py tests/test_template_contract.py
git commit -m "feat: add harness CLI skeleton with validate subcommand"
```

---

### Task 4: 受管块引擎与投影渲染

**Files:**
- Modify: `template/.harness/bin/harness.py`
- Test: `tests/test_adapters.py`（新建）

**Interfaces:**
- Consumes: Task 3 的 `MARKER_BEGIN` / `MARKER_END` / `MarkerBrokenError`。
- Produces（Task 5 依赖）：`render_block_body(manifest) -> str`、`apply_managed_block(existing_text, body) -> str`（`existing_text` 为 `None` 或 str；标记破损抛 `MarkerBrokenError`）、`render_cursor_file(manifest) -> str`、表 `ADAPTERS = {"claude-code": {"path": "CLAUDE.md", "mode": "block"}, "codex": {"path": "AGENTS.md", "mode": "block"}, "cursor": {"path": ".cursor/rules/harness.mdc", "mode": "file"}}`。

- [ ] **Step 1: 写失败测试**

新建 `tests/test_adapters.py`（顶部 fixture 供本 Task 与 Task 5 共用）：

```python
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
```

Run: `python3 -m unittest tests.test_adapters -v` → Expected: FAIL（函数不存在）。

- [ ] **Step 2: 实现引擎与渲染**

在 `harness.py` 中 `emit` 之后追加：

```python
def apply_managed_block(existing_text, body):
    """Insert or refresh the managed block; user text outside it is untouched."""
    block = MARKER_BEGIN + "\n" + body + "\n" + MARKER_END + "\n"
    if existing_text is None:
        return block
    begins = existing_text.count(MARKER_BEGIN)
    ends = existing_text.count(MARKER_END)
    if begins == 0 and ends == 0:
        prefix = existing_text
        if not prefix.endswith("\n"):
            prefix += "\n"
        return prefix + "\n" + block
    if begins != 1 or ends != 1:
        raise MarkerBrokenError("managed block markers are broken")
    begin_index = existing_text.index(MARKER_BEGIN)
    end_index = existing_text.index(MARKER_END)
    if end_index < begin_index:
        raise MarkerBrokenError("managed block markers are broken")
    suffix = existing_text[end_index + len(MARKER_END):].lstrip("\n")
    return existing_text[:begin_index] + block + suffix


def render_block_body(manifest):
    entrypoint = manifest["entrypoint"]
    template_dir = manifest["change_management"]["template"]
    lines = [
        "This project uses a portable AI coding harness stored in `.harness/`.",
        "",
        f"- Entrypoint: `.harness/{entrypoint}`",
        "- Manifest: `.harness/manifest.json`",
        "",
        "Components:",
        "",
    ]
    for component in manifest["components"]:
        lines.append(
            f"- {component['id']} ({component['kind']}): `.harness/{component['path']}`"
        )
    lines.extend(
        [
            "",
            "Workflow:",
            "",
            "1. Read the entrypoint, then load only the components needed for the current task.",
            f"2. Deliver changes through a Change Record started from `.harness/{template_dir}/`.",
            "3. Run `python3 .harness/bin/harness.py validate` before delivery.",
            "",
            "Do not edit this block by hand. Regenerate it with `python3 .harness/bin/harness.py adapt`.",
        ]
    )
    return "\n".join(lines)


CURSOR_FRONTMATTER = (
    "---\n"
    "description: Portable AI coding harness entrypoint\n"
    "alwaysApply: true\n"
    "---\n"
    "\n"
)


def render_cursor_file(manifest):
    return (
        CURSOR_FRONTMATTER
        + MARKER_BEGIN
        + "\n"
        + render_block_body(manifest)
        + "\n"
        + MARKER_END
        + "\n"
    )


ADAPTERS = {
    "claude-code": {"path": "CLAUDE.md", "mode": "block"},
    "codex": {"path": "AGENTS.md", "mode": "block"},
    "cursor": {"path": ".cursor/rules/harness.mdc", "mode": "file"},
}
```

- [ ] **Step 3: 确认通过**

Run: `python3 -m unittest tests.test_adapters -v` → Expected: PASS（`ManagedBlockTests`、`RenderTests` 全绿）。

- [ ] **Step 4: Commit**

```bash
git add template/.harness/bin/harness.py tests/test_adapters.py
git commit -m "feat: add managed-block engine and projection renderers"
```

---

### Task 5: adapt 子命令（含 --check 与模板本体跳过）

**Files:**
- Modify: `template/.harness/bin/harness.py`（替换 `cmd_adapt` 占位）
- Test: `tests/test_adapters.py`（追加子进程测试类）

**Interfaces:**
- Consumes: Task 4 全部产出、Task 3 `emit`。
- Produces（Task 6 依赖）：`run_adapt(root, manifest, check) -> tuple` 返回 `(errors, notices, written, unchanged, stale)`（`errors`/`notices` 为 `validate.ContractError` 列表，其余为 POSIX 相对路径字符串列表）；`cmd_adapt(root, check, fmt) -> int`。

- [ ] **Step 1: 写失败测试**

`tests/test_adapters.py` 追加：

```python
class AdaptCommandTests(unittest.TestCase):
    def test_creates_all_three_projections(self):
        with instantiated_project() as (project, root):
            result = run_instance_cli(root, "adapt")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc"):
                self.assertTrue((project / name).is_file(), name)
            self.assertIn("adapt: ok", result.stdout)

    def test_preserves_existing_user_content(self):
        with instantiated_project() as (project, root):
            (project / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
            run_instance_cli(root, "adapt")
            text = (project / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("my own notes\n"))
            self.assertIn(harness.MARKER_BEGIN, text)

    def test_adapt_is_idempotent(self):
        with instantiated_project() as (project, root):
            run_instance_cli(root, "adapt")
            snapshot = {
                name: (project / name).read_bytes()
                for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc")
            }
            second = run_instance_cli(root, "adapt", "--format", "json")
            payload = json.loads(second.stdout)
            self.assertEqual([], payload["written"])
            self.assertEqual(3, len(payload["unchanged"]))
            for name, content in snapshot.items():
                self.assertEqual(content, (project / name).read_bytes(), name)

    def test_broken_markers_fail(self):
        with instantiated_project() as (project, root):
            (project / "CLAUDE.md").write_text(
                harness.MARKER_BEGIN + "\nno end\n", encoding="utf-8"
            )
            result = run_instance_cli(root, "adapt")
            self.assertEqual(1, result.returncode)
            self.assertIn("[PROJECTION_MARKER_BROKEN] CLAUDE.md", result.stdout)

    def test_check_reports_missing_and_stale(self):
        with instantiated_project() as (project, root):
            result = run_instance_cli(root, "adapt", "--check", "--format", "json")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(3, len(payload["stale"]))
            self.assertIn("PROJECTION_MISSING", [e["code"] for e in payload["errors"]])

            run_instance_cli(root, "adapt")
            ok = run_instance_cli(root, "adapt", "--check")
            self.assertEqual(0, ok.returncode, ok.stdout)

            claude = project / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8").replace("Workflow", "Werkflow"),
                encoding="utf-8",
            )
            stale = run_instance_cli(root, "adapt", "--check", "--format", "json")
            self.assertEqual(1, stale.returncode)
            self.assertIn(
                "PROJECTION_STALE",
                [e["code"] for e in json.loads(stale.stdout)["errors"]],
            )

    def test_check_never_writes(self):
        with instantiated_project() as (project, root):
            run_instance_cli(root, "adapt", "--check")
            for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc"):
                self.assertFalse((project / name).exists(), name)

    def test_template_origin_null_skips_projection(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE_HARNESS / "bin" / "harness.py"),
                "adapt",
                "--check",
                "--root",
                str(SOURCE_HARNESS),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[ADAPT_SKIPPED_TEMPLATE]", result.stdout)

    def test_external_adapter_is_notice_not_error(self):
        with instantiated_project() as (project, root):
            manifest = read_manifest(root)
            manifest["adapters"] = ["claude-code", "x-corp"]
            write_manifest(root, manifest)
            result = run_instance_cli(root, "adapt")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("[ADAPTER_EXTERNAL] x-corp", result.stdout)

    def test_output_is_deterministic(self):
        outputs = []
        for _ in range(2):
            with instantiated_project() as (project, root):
                run_instance_cli(root, "adapt")
                outputs.append(
                    tuple(
                        (project / name).read_bytes()
                        for name in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/harness.mdc")
                    )
                )
        self.assertEqual(outputs[0], outputs[1])
```

Run: `python3 -m unittest tests.test_adapters -v` → Expected: `AdaptCommandTests` FAIL（占位 RuntimeError → 退出码 2）。

- [ ] **Step 2: 实现 adapt**

用以下内容**整体替换** `harness.py` 中的 `cmd_adapt` 占位：

```python
def run_adapt(root, manifest, check):
    """Project the manifest into platform files. Root must already be validated."""
    project_root = root.parent
    errors, notices, written, unchanged, stale = [], [], [], [], []
    for name in manifest.get("adapters", []):
        if name not in ADAPTERS:
            notices.append(
                validate.ContractError(
                    "ADAPTER_EXTERNAL",
                    name,
                    "external adapter is not generated by this tool",
                )
            )
            continue
        spec = ADAPTERS[name]
        rel = PurePosixPath(spec["path"])
        target = project_root.joinpath(*rel.parts)
        display = rel.as_posix()
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        if spec["mode"] == "file":
            expected = render_cursor_file(manifest)
        else:
            try:
                expected = apply_managed_block(existing, render_block_body(manifest))
            except MarkerBrokenError:
                errors.append(
                    validate.ContractError(
                        "PROJECTION_MARKER_BROKEN",
                        display,
                        "managed block markers are missing their pair or out of order",
                    )
                )
                continue
        if check:
            if existing is None:
                stale.append(display)
                errors.append(
                    validate.ContractError(
                        "PROJECTION_MISSING", display, "projection file does not exist"
                    )
                )
            elif existing != expected:
                stale.append(display)
                errors.append(
                    validate.ContractError(
                        "PROJECTION_STALE",
                        display,
                        "projection is out of date; run adapt",
                    )
                )
            else:
                unchanged.append(display)
        else:
            if existing == expected:
                unchanged.append(display)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(expected, encoding="utf-8")
                written.append(display)
    return errors, notices, written, unchanged, stale


def cmd_adapt(root, check, fmt):
    try:
        result = validate.validate_harness(root)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    if not result.valid:
        return emit(
            fmt,
            "adapt",
            False,
            list(result.errors),
            [],
            {"written": [], "unchanged": [], "stale": []},
        )
    root = result.root
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("origin") is None:
        notices = [
            validate.ContractError(
                "ADAPT_SKIPPED_TEMPLATE",
                ".",
                "origin is null; template bundles do not generate projections",
            )
        ]
        return emit(
            fmt,
            "adapt",
            True,
            [],
            notices,
            {"written": [], "unchanged": [], "stale": []},
        )
    errors, notices, written, unchanged, stale = run_adapt(root, manifest, check)
    return emit(
        fmt,
        "adapt",
        not errors,
        errors,
        notices,
        {"written": written, "unchanged": unchanged, "stale": stale},
    )
```

- [ ] **Step 3: 确认通过**

Run: `python3 -m unittest discover -s tests -v` → Expected: 全 PASS。

- [ ] **Step 4: Commit**

```bash
git add template/.harness/bin/harness.py tests/test_adapters.py
git commit -m "feat: add adapt subcommand with managed-block projections"
```

---

### Task 6: init 子命令

**Files:**
- Modify: `template/.harness/bin/harness.py`（替换 `cmd_init` 占位）
- Test: `tests/test_harness_cli.py`（追加测试类）

**Interfaces:**
- Consumes: Task 5 `run_adapt`、Task 3 `emit` / `TEMPLATE_NAME` / `BIN_DIR`。
- Produces: `cmd_init(target, adapters_raw, fmt) -> int`；成功时 JSON 附加 `target`（绝对路径字符串）与 `projected_files`（相对项目根 POSIX 路径列表）。

- [ ] **Step 1: 写失败测试**

`tests/test_harness_cli.py` 追加（同文件顶部已 import 的基础上补 `hashlib`、`os`、`shutil`、`stat`、`tempfile`、`contextmanager`）：

```python
import hashlib
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager

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
```

Run: `python3 -m unittest tests.test_harness_cli -v` → Expected: `InitCommandTests` FAIL。

- [ ] **Step 2: 实现 init**

用以下内容**整体替换** `harness.py` 中的 `cmd_init` 占位：

```python
def _parse_adapters_argument(raw, errors):
    names = [item.strip() for item in raw.split(",") if item.strip()]
    seen = set()
    for name in names:
        is_builtin = name in ADAPTERS
        is_extension = name.startswith("x-") and len(name) > 2
        if not (is_builtin or is_extension) or name in seen:
            errors.append(
                validate.ContractError(
                    "ARGUMENT_INVALID",
                    name,
                    "adapter names must be built-in or start with 'x-' and be unique",
                )
            )
        seen.add(name)
    return names


def _init_failure(fmt, errors, notices=(), target=None):
    return emit(
        fmt,
        "init",
        False,
        errors,
        list(notices),
        {"target": target, "projected_files": []},
    )


def cmd_init(target, adapters_raw, fmt):
    source = BIN_DIR.parent
    adapters_override = None
    if adapters_raw is not None:
        argument_errors = []
        adapters_override = _parse_adapters_argument(adapters_raw, argument_errors)
        if argument_errors:
            for item in sorted(argument_errors):
                sys.stderr.write(
                    f"[{item.code}] {item.path}: {item.message}\n"
                )
            return 2

    try:
        source_result = validate.validate_harness(source)
    except validate.RootUnreadableError as error:
        sys.stderr.write(f"[ROOT_UNREADABLE] .: {error}\n")
        return 2
    if not source_result.valid:
        errors = list(source_result.errors)
        errors.append(
            validate.ContractError(
                "INIT_SOURCE_INVALID",
                ".",
                "source template failed validation; refusing to copy",
            )
        )
        return _init_failure(fmt, errors)

    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if "template_version" not in source_manifest:
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_SOURCE_INVALID",
                    "manifest.json",
                    "template_version is required to initialize a project",
                )
            ],
        )

    if not target.is_dir():
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_TARGET_MISSING",
                    str(target),
                    "target must be an existing directory",
                )
            ],
        )
    destination = target / ".harness"
    if destination.exists():
        return _init_failure(
            fmt,
            [
                validate.ContractError(
                    "INIT_TARGET_EXISTS",
                    str(destination),
                    "a .harness directory already exists; refusing to overwrite",
                )
            ],
            target=str(destination),
        )

    shutil.copytree(
        source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    cleanup_hint = validate.ContractError(
        "INIT_CLEANUP_HINT",
        str(destination),
        "initialization failed after copying; remove this directory to retry",
    )

    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    manifest["origin"] = {
        "template_name": TEMPLATE_NAME,
        "template_version": source_manifest["template_version"],
        "initialized_at_schema": manifest["schema_version"],
    }
    if adapters_override is not None:
        manifest["adapters"] = adapters_override
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    errors, notices, written, unchanged, stale = run_adapt(
        destination, manifest, check=False
    )
    if errors:
        return _init_failure(
            fmt, errors, notices=[cleanup_hint] + notices, target=str(destination)
        )

    final_result = validate.validate_harness(destination)
    if not final_result.valid:
        return _init_failure(
            fmt,
            list(final_result.errors),
            notices=[cleanup_hint],
            target=str(destination),
        )

    return emit(
        fmt,
        "init",
        True,
        [],
        notices,
        {
            "target": str(destination.resolve()),
            "projected_files": written + unchanged,
        },
    )
```

- [ ] **Step 3: 确认通过**

Run: `python3 -m unittest discover -s tests -v` → Expected: 全 PASS。

- [ ] **Step 4: Commit**

```bash
git add template/.harness/bin/harness.py tests/test_harness_cli.py
git commit -m "feat: add init subcommand with origin stamping"
```

---

### Task 7: 文档与 CI 门禁

**Files:**
- Modify: `template/.harness/README.md`
- Modify: `README.md`
- Modify: `.github/workflows/validate.yml`

**Interfaces:**
- Consumes: Task 1-6 全部交付。
- Produces: 无代码接口；对外文档与 CI 契约。

- [ ] **Step 1: 更新分发包 README**

`template/.harness/README.md` 全文替换：

```markdown
# Portable AI Coding Harness

This directory is a self-contained, project-neutral Harness. Teams may translate or replace its prose while preserving `manifest.json` and the declared file contract.

## Install into a project

From a local copy of the template, run:

    python3 <template>/.harness/bin/harness.py init --target <project-dir>

`init` copies the bundle, stamps its origin, generates platform projection files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/harness.mdc`), and validates the result. Then open your agent and run the `harness-bootstrap` skill to customize the Harness for the project.

## Start (installed projects)

1. Read `manifest.json`.
2. Load only components needed for the current task.
3. Create a Change Record from `templates/change/` before implementation.
4. Record verification evidence in the Change Record.
5. Run `python3 bin/harness.py validate` before delivery.

## Components

- `agents/`: replaceable role definitions.
- `rules/`: stable project constraints.
- `skills/`: reusable workflows, including `harness-bootstrap` for first-time customization.
- `templates/change/`: required Change Record shape.
- `changes/`: project-local delivery history.
- `wiki/`: project knowledge base (not part of the machine contract).

## Commands

- `python3 bin/harness.py validate` - check the Harness contract (read-only).
- `python3 bin/harness.py adapt` - regenerate platform projection files; only managed blocks are touched.
- `python3 bin/harness.py adapt --check` - fail if projections are stale; useful in CI.

All commands require Python 3.9 or newer and use only the standard library.
```

- [ ] **Step 2: 更新仓库 README 与 CI**

`README.md`「设计与决策」清单追加三行（放在 v0 三行之后）：

```markdown
- [Harness v1 设计规格](docs/design/harness-v1.md)
- [ADR-0002：实例化与适配投影](docs/adr/0002-instantiation-and-adapter-projection.md)
- [Harness v1 实施计划](docs/plans/harness-v1-implementation.md)
```

`.github/workflows/validate.yml` 在 `Validate distributable Harness` 步骤后插入：

```yaml
      - name: Validate via harness CLI
        run: python3 template/.harness/bin/harness.py validate
      - name: Check template projections are skipped
        run: python3 template/.harness/bin/harness.py adapt --check --root template/.harness
```

- [ ] **Step 3: 验证并提交**

Run: `python3 template/.harness/bin/harness.py validate && python3 template/.harness/bin/harness.py adapt --check --root template/.harness && python3 -m unittest discover -s tests -v`
Expected: 校验 `Harness contract is valid.`；adapt 输出含 `[ADAPT_SKIPPED_TEMPLATE]` 且退出 0；测试全 PASS。

```bash
git add template/.harness/README.md README.md .github/workflows/validate.yml
git commit -m "docs: document harness CLI and wire CI gates"
```

---

### Task 8: 验收清单

**Files:** 无新改动；只运行验证。

- [ ] **Step 1: 设计验收标准逐条核对**（设计 §14）

```bash
python3 template/.harness/bin/validate.py
python3 template/.harness/bin/harness.py validate
python3 template/.harness/bin/harness.py adapt --check --root template/.harness
python3 -m unittest discover -s tests -v
git diff --check
```

Expected: 前三条退出 0；测试全 PASS；`git diff --check` 无输出。

- [ ] **Step 2: 端到端手工冒烟**

```bash
DEMO=$(mktemp -d) && mkdir "$DEMO/demo-app" && printf 'existing notes\n' > "$DEMO/demo-app/CLAUDE.md"
python3 template/.harness/bin/harness.py init --target "$DEMO/demo-app"
head -3 "$DEMO/demo-app/CLAUDE.md"
python3 "$DEMO/demo-app/.harness/bin/harness.py" adapt --check
rm -rf "$DEMO"
```

Expected: `init` 输出 `init: ok`；`head` 首行是 `existing notes`；`adapt --check` 退出 0。

- [ ] **Step 3: 提交收尾**

若上述任何一步失败：回到对应 Task 修复后重跑本 Task。全部通过后，按仓库流程发起 PR（PR 审阅与 `docs/reviews/` 记录由审阅者完成，不属于本计划）。
