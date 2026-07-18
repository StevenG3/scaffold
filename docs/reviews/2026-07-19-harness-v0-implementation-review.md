# Harness v0 实现审阅

- 审阅日期：2026-07-19
- PR：[PR #1 — feat: implement portable Harness v0 vertical slice](https://github.com/StevenG3/scaffold/pull/1)
- 固定点：`323cd1d7e8afaf223cb118eec16c5438bbc638bc`
- 已审阅提交：`07aab673afbdf12b3f86fee140bf032605769ba7`
- 审阅方式：Standards / Spec 双路独立审阅，加本地最小输入复现
- 结论：Request changes，暂不合入

## 验证证据

- `python3 -m unittest discover -s tests -v`：43 项全部通过。
- Python 3.9 语法解析：通过。
- `git diff --check 323cd1d...07aab67`：通过。
- GitHub Actions run `29653482060`：success。
- 额外边界探针稳定复现以下三个 P2 问题。

## Standards Findings

### [P2] 空扩展 kind 被错误接受

位置：`template/.harness/bin/validate.py:190`

`kind.startswith("x-")` 会把 `x-` 当成合法 kind；实测 `validate_manifest_structure(...)` 返回空错误列表。实施计划要求允许内置 kind 或非空 `x-*` kind。

要求：`x-` 前缀后至少包含一个字符；增加 `kind: "x-"` 返回 `COMPONENT_KIND_UNSUPPORTED` 的回归测试。

### [P3] 路径安全逻辑重复

位置：`template/.harness/bin/validate.py:287,450,467`

`resolve_safe_path`、`_valid_directory`、`_check_required_path_syntax` 分别实现路径语法、解析和 containment，未落实实施计划要求的 shared safe-path helper。这是 Duplicated Code judgement call，容易造成错误映射或检查顺序漂移。

建议：提取单一路径解析核心，仅参数化期望节点类型、允许基目录和缺失错误码。

## Spec Findings

### [P2] 接受 JSON 标准禁止的非有限常量

位置：`template/.harness/bin/validate.py:609`

Python `json.loads` 默认接受 `NaN`、`Infinity` 和 `-Infinity`。实测在 Manifest 加入 `"x-number": NaN` 后，校验器仍返回 exit `0` 和 `"valid": true`。

要求：禁用非有限常量，稳定映射为 `MANIFEST_JSON_INVALID` / exit `1`，并覆盖三个常量的回归测试。

### [P2] NUL 路径导致 traceback

位置：`template/.harness/bin/validate.py:294,327,647-650`

组件路径 `agents/evil\u0000.md` 会让 `Path.resolve()` 抛出未捕获的 `ValueError`，打印 traceback 并以 `1` 退出，违反稳定 Text/JSON 输出及无 traceback 契约。

要求：在触碰文件系统前把 NUL 映射为 `PATH_SYNTAX_INVALID`；增加错误码、退出码及无 traceback 的回归测试。

## 合入意见

当前 PR 不应合入。现有测试与 CI 为绿色，但没有覆盖上述契约边界，不能替代规格验收。

开发者需要：

1. 修复全部三个 P2，并添加能够先失败、修复后通过的回归测试。
2. 建议同时收敛 P3 重复路径逻辑，避免三套实现继续漂移。
3. 保持 PR 为 Draft，推送新提交并提供完整验证结果。
4. 新 HEAD 必须重新执行 Standards / Spec 双路独立审阅；本记录不构成对后续提交的批准。
