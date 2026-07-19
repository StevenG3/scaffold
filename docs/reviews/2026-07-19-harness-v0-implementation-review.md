# Harness v0 实现审阅

- 审阅日期：2026-07-19
- PR：[PR #1 — feat: implement portable Harness v0 vertical slice](https://github.com/StevenG3/scaffold/pull/1)
- 固定点：`323cd1d7e8afaf223cb118eec16c5438bbc638bc`
- 最新已审阅提交：`eb4b1a52bc9103eea7999921143f011ccaa44738`
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

## 第二轮复审

- 复审提交：`df1b07ed5683a4de845d06950a303c6c090128a6`
- 新增提交：`fix: close harness v0 review boundary gaps`
- Standards：0 findings，Approve。
- Spec：1 个 P2，Request changes。
- 本地完整测试：46 项全部通过。
- 上轮三个 P2 定向回归：3 项全部通过。
- GitHub Actions run `29654504735`：validator、tests、whitespace 均为 success。

上轮的三个 P2 与一个 P3 均已关闭：空 `x-` kind 被拒绝，非有限 JSON 常量被拒绝，NUL 路径不再产生 traceback，路径安全逻辑已收敛到共享 helper。

### [P2] Text 错误输出可被控制字符破坏

位置：`template/.harness/bin/validate.py:49,294`

`render_text` 直接拼接用户可控的 `code`、`path` 和 `message`；路径语法只拒绝 NUL、反斜杠和盘符前缀。合法 JSON 字符串中的 CR、LF 或其他控制字符会进入 Text 输出。

已复现组件路径 `agents/missing\nsecond-line.md`：校验器以 `1` 退出，但单个错误被渲染为两行：

```text
[PATH_MISSING] agents/missing
second-line.md: referenced path does not exist
```

这违反设计中“Text 每行一项错误”及固定 `[CODE] path: message` 格式，也会造成日志注入和机器按行解析歧义。

要求：

1. 在 Text 渲染边界统一转义 CR、LF、TAB、其他 C0 控制字符及 DEL，不能只修复 Component path；JSON Pointer、未知字段名、重复 ID 和错误消息同样可能包含用户输入。
2. 保持可打印 Unicode 可读，并定义确定性的转义表示。
3. 增加至少覆盖 Component path 和 Manifest 字段名/ID 的回归测试，断言每个错误严格占一行、无原始控制字符且退出码仍为 `1`。
4. 保持 JSON 输出语义不变。

### 第二轮合入意见

当前 PR 仍不应合入。修复上述 P2 并补齐回归测试后，需要对新的 HEAD 再执行 Standards / Spec 双路复审；第二轮对 `df1b07e` 的审阅结论不能自动批准后续提交。

## 第三轮复审

- 复审提交：`50c8db3a714e341f08e57f246799ba7f200b389d`
- 新增提交：`fix: escape control characters in text errors`
- Standards：1 个 P2，Request changes。
- Spec：2 个 P2，Request changes。
- 去重后阻塞问题：2 个 P2。
- 本地完整测试：48 项全部通过。
- GitHub Actions run `29679703626`：success。
- `git diff --check 323cd1d...50c8db3`：通过。

上一轮针对 CR、LF、TAB、其他 C0 控制字符及 DEL 的 Text 转义已实现，但复审发现 Unicode 行分隔符仍能破坏单行契约，并且修复意外改变了 JSON 错误消息语义。

### [P2] Unicode 行分隔符仍能拆分 Text 错误

位置：`template/.harness/bin/validate.py:49`

`escape_text_field()` 只转义 C0 和 DEL，保留 `U+0085`（NEL）、`U+2028`（Line Separator）和 `U+2029`（Paragraph Separator）。这三个字符都会被 Python `splitlines()` 识别为行边界；终端和日志处理器也可能按行解释。

独立探针确认三个输入均从一个字段拆成两行，因此仍违反“Text 每行一项错误”及固定格式契约。

要求：

1. 在 Text 渲染边界额外转义 `U+0085`、`U+2028`、`U+2029`，使用确定性的可见表示。
2. 为三个 Unicode 行分隔符增加回归测试，断言一个错误严格占一个物理行。
3. 保持普通可打印 Unicode 可读，保持 JSON 输出不变。

### [P2] 重复 ID 的 JSON 错误消息语义发生变化

位置：`template/.harness/bin/validate.py:205`、`tests/test_validate.py:674`

实现把重复 ID 消息从 `f"duplicate component id {component_id!r}"` 改成 `f"duplicate component id {component_id}"`。相同的 `coord\tinator` 输入在 `df1b07e` 中为带引号且由 repr 表示的消息，当前 HEAD 则变成包含原始 TAB 的裸值。

这违反第二轮任务“保持 JSON 输出语义不变”。Text 安全应只由 `escape_text_field()` 在渲染边界实现，不应改动结构化 `ContractError.message`。

要求：

1. 恢复 `{component_id!r}` 的原始消息构造。
2. 调整测试，分别断言 JSON message 保持旧语义、Text 输出仍为单行可见表示。
3. 不改变其他稳定错误 code、path 或 message。

### 第三轮合入意见

当前 PR 仍不应合入。修复以上两个 P2 并补充回归测试后，对新 HEAD 执行第四轮 Standards / Spec 复审。现有绿色测试与 CI 没有覆盖这两个边界，不能替代契约验收。

## 第四轮复审

- 复审提交：`eb4b1a52bc9103eea7999921143f011ccaa44738`
- 新增提交：`fix: harden text escaping and restore duplicate-id JSON message`
- Standards：1 个 P2，Request changes。
- Spec：1 个 P2，Request changes。
- 本地完整测试：49 项全部通过。
- 官方 Text / JSON 校验：均退出 `0`。
- Python 3.9 语法解析：通过。
- GitHub Actions run `29680038842`：validator、tests、whitespace 均为 success。

第三轮的两个 P2 均已关闭：Text 渲染覆盖 Python `splitlines()` 识别的全部行边界字符，重复 Component ID 的结构化 JSON message 也恢复为与 `df1b07e` 逐字一致。

### [P2] 完整验证序列污染 Git 工作区

位置：`.gitignore:1`、`docs/plans/harness-v0-implementation.md:790-800`

在真实 Git 工作区按计划原样执行：

```bash
python3 template/.harness/bin/validate.py
python3 template/.harness/bin/validate.py --format json
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

测试虽然全部通过，但会生成未跟踪的 `tests/__pycache__/*.pyc`；导入 validator 的验证方式还可能生成 `template/.harness/bin/__pycache__/*.pyc`。当前 `.gitignore` 未覆盖 Python 字节码，因此最终 `git status --short` 非空，直接违反实施计划的 clean-worktree 验收结果。

要求：

1. 在生产者侧 `.gitignore` 增加通用 `__pycache__/` 和 `*.py[cod]` 规则。
2. 清理已生成的缓存，并在真实 Git checkout 中重新执行完整验证序列。
3. 最终 `git status --short` 必须为空。
4. 不修改 Harness 外部契约、设计、ADR 或实施计划。

实施计划 Task 8 原本把允许改动范围限定为 workflow、README、`template/.harness/` 和 `tests/`。本审阅记录作为规划者/Reviewer 的明确批准，为修复该生产者侧验收缺口增加唯一范围例外：允许修改根目录 `.gitignore`，仅加入上述通用 Python 缓存规则；不得借此扩大其他范围。

### 第四轮合入意见

当前 PR 仍不应合入。本地集成验证中创建的合并提交未推送远端 `main`。开发者完成 `.gitignore` 修复并推送新 HEAD 后，需要执行第五轮复审和合并结果验证。
