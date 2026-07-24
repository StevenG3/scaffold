# Harness v1 实现审阅

- 审阅日期：2026-07-23
- 审阅对象：`feature/harness-v1`
- 基线：`main@a06c0571a7978a5439d1bc3fc3273c2c5d898149`
- 固定 HEAD：`370fbb87dd67b20a3f9d88d27cccc7b1d71f6709`
- 变更规模：13 个提交，16 个文件，`+3244/-15`
- 审阅方式：Standards / Spec 双路独立审阅，加本地最小输入与对抗输入复现
- 结论：**Request changes，禁止合入**

本结论仅适用于上述精确 HEAD。远端在审阅时只有
`main@a06c0571a7978a5439d1bc3fc3273c2c5d898149`，没有
`feature/harness-v1`，因此不存在可与 `370fbb8` 绑定的远端 CI 运行；本轮结论以本地锁定提交上的独立验证为依据。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 1/4 | 核心命令与 88 项测试已交付，但写集安全、块外字节保全、Cursor 破损检测和 JSON 输出契约均未满足。 |
| B. 事实准确性 | 2/4 | 文档宣称所有可预期状态走稳定 exit 1、所有 JSON 输出有固定 envelope，实测目录目标走 exit 2，非法 adapter 输出 Text stderr。 |
| C. 通用性 | 2/4 | 标准库与平台中立方向成立，但 symlink、CRLF、特殊节点和隐藏缓存边界不适合直接落地到任意存量项目。 |
| D. 可维护性 | 3/4 | 单文件 CLI 与表驱动适配器结构清晰；文件状态判断和文本往返没有集中成安全写入边界。 |
| E. 验证充分性 | 2/4 | 88 项测试全绿，但未覆盖会越界写、损坏用户字节和破坏输出契约的验收边界。 |
| F. 可追溯性 | 2/4 | 设计、ADR、计划和提交链齐全，但设计仍为 Draft、ADR 仍为 Proposed，且精确 HEAD 未同步远端、无对应 CI。 |

总分：**12/24**。存在 Critical finding，且 A、B、C、E、F 均不高于 2 分，不能合入。

## Standards findings

### [Critical] 投影路径可借 symlink 写出项目边界

位置：`template/.harness/bin/harness.py:201-203,241-242`

`target.is_file()`、`read_text()` 与 `write_text()` 都跟随符号链接。独立夹具令
`project/CLAUDE.md` 指向项目外 `outside.md`，执行 `adapt` 得到：

```text
SYMLINK rc= 0 outside_changed= True
written: CLAUDE.md
adapt: ok
```

这违反设计 §8.1、§11、§12 及计划 Global Constraints 的声明式写集和用户内容边界。父目录 symlink 同样可逃逸；目录目标实测变成
`INTERNAL_ERROR` / exit 2，FIFO 等非普通节点还可能产生阻塞。

整改要求：

1. 在读写前以 `lstat` 检查从项目根到目标的每一段，拒绝 symlink；现有目标只能是普通文件，父节点只能是真实目录。
2. 所有这些可预期状态以稳定的 `PROJECTION_*` 错误和 exit 1 返回；`--check` 保持零写。
3. 写入前重新核验目标，避免检查后替换造成的明显竞态；在支持的平台使用 no-follow 语义。
4. 增加目标 symlink、父目录 symlink、目录和至少一种非普通节点的回归测试，断言项目外字节不变且命令不会阻塞。

### [Important] 受管块外用户字节被修改

位置：`template/.harness/bin/harness.py:91-110,203,242`

`lstrip("\n")` 会删除 END 标记后的用户空行；`read_text()` / `write_text()` 的通用换行转换还会把 CRLF 改为 LF。独立结果：

```text
SUFFIX rc= 0 before_tail= b'\n\n\nUSER-SUFFIX\n' after_tail= b'\nUSER-SUFFIX\n'
CRLF rc= 0 prefix_after= b'USER\nNOTES\n\n<!-- BEG'
```

这直接违反 ADR-0002 §2、设计 §8.1、§12.4 和验收标准 §14 的“块外逐字节保留”。

整改要求：以 bytes 或禁用换行转换的等价实现定位 ASCII marker，仅替换 marker 所有区间；前缀、后缀必须原样拼回。补 LF/CRLF、无末尾换行、END 后 0/1/多空行及非 ASCII 用户内容的逐字节断言。

### [Important] Cursor 破损 marker 被静默覆盖

位置：`template/.harness/bin/harness.py:204-205`

整文件模式直接生成期望内容，没有检查既有 marker。对只含 BEGIN 的
`.cursor/rules/harness.mdc`，实测 exit 0 且原文件被覆盖：

```text
CURSOR_BROKEN rc= 0 overwritten= True
written: .cursor/rules/harness.mdc
adapt: ok
```

设计 §8.2 虽授权工具拥有 Cursor 整文件，但同时明确保留 marker 用于
`--check` 与破损检测；§8.1 规定不成对时必须
`PROJECTION_MARKER_BROKEN` / exit 1 且拒绝修改。需对 file 模式执行相同的 marker 完整性检查，并补 BEGIN-only、END-only、倒序和重复 marker 测试。

### [Important] `--format json` 的参数错误不返回 JSON 契约

位置：`template/.harness/bin/harness.py:323-331`

独立执行
`harness.py init --target /tmp --adapters vscode --format json`：

```text
rc=2
stdout=''
stderr="[ARGUMENT_INVALID] vscode: adapter names must be built-in or start with 'x-' and be unique\n"
```

设计 §7.1 要求全部子命令支持 JSON，并固定包含 `ok`、`command`、
`errors`、`notices` 和子命令字段。当前路径绕过 `emit()`，输出 Text stderr。
需统一参数错误渲染，并为每个子命令至少覆盖一个 JSON 参数错误，断言字段、流向和 exit 2。

## Spec findings

### [Important] 设计没有定义投影目标的文件系统节点安全规则

设计 §8 与 §11 声明安全写集和用户内容保全，却未明确 symlink、父目录
symlink、目录、FIFO/device/socket 等节点的处理。这是设计缺陷，不只是实现遗漏。

设计方需补充：允许的节点类型、symlink 策略、稳定错误码/退出码、`--check`
行为及竞态边界；实施与测试按修订后的规则对齐。不得只在实现中加临时判断而让公开契约继续留白。

### [Minor] `init` 未排除“隐藏缓存”

位置：`template/.harness/bin/harness.py:387-389`

设计 §7.2 明确复制排除 `__pycache__` 与隐藏缓存，实现仅忽略
`__pycache__` 和 `*.pyc`。在源 bundle 加入 `.pytest_cache/marker` 后，实测
`init` exit 0 且该文件被复制。需定义“隐藏缓存”的确定范围并至少覆盖
`.pytest_cache`、`.mypy_cache` 等约定项；若真实意图只是 Python bytecode，
则应先修订设计，不能保留过度承诺。

### [Minor] bootstrap 合规示例自身未完全合规

位置：`template/.harness/skills/harness-bootstrap/SKILL.md:27-33,55-57`

“C. Other” 没有说明代价，违反同文件第 24 行和设计 §9.3 的“每个选项必须写明代价”。验证命令写作 `python3 bin/harness.py ...`，在通常的项目根工作目录不可运行；应写成项目根可直接执行的 `.harness/bin/harness.py`，或明确先进入 `.harness/`。

### [Minor] 设计决策状态未闭环

位置：`docs/design/harness-v1.md:3`、`docs/adr/0002-instantiation-and-adapter-projection.md:3`

实现已完成并请求合入，但设计仍标为 `Draft（待批准）`，ADR 仍为
`Proposed`。这与 v0 的 `Approved` / `Accepted` 治理方式不一致。设计方应记录批准日期并将状态更新为 `Approved` / `Accepted`；该修改必须由设计所有者提交，不能由实现方自行宣告批准。

## 四个既有 Minor 的独立裁定

| 实现方内部结论 | 独立裁定 | 理由 |
| --- | --- | --- |
| `origin.template_version` 非字符串报 `FIELD_TYPE_INVALID` | **接受，不构成 finding** | 类型不符归类为 type error 合理；实测会稳定拒绝，未改变 v0 契约。 |
| adapt 的 Manifest 无效与根不可读缺专属测试 | **维持 Minor，要求补测** | 代码复用 validator 路径降低逻辑风险，但 CLI 自己负责 envelope 与 exit code；本轮已证明未测输出路径会漂移。修订时补两条专属测试。 |
| init 失败路径的 `target` 未 resolve | **接受，不构成 finding** | 设计只明确规定成功响应中的 `target` 为规范化绝对路径，失败响应没有该要求。 |
| Cursor 整文件工具所有、每次重生成 | **部分推翻，升级为 Important** | 整文件所有权成立，但设计 §8.2 明确要求 marker 参与破损检测；所有权不授权覆盖破损 marker。 |

## 验证证据

### 规定门禁

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与上一命令 stdout/stderr 逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 88 tests in 8.639s
OK

$ git diff --check
无输出，exit 0

$ git diff --check a06c057...370fbb8
无输出，exit 0
```

端到端冒烟通过：已有 `CLAUDE.md` 首行为 `user notes`，`init` 后首行不变，
受管块追加在后；副本执行 `adapt --check` 为 `adapt: ok` / exit 0。

### 兼容、只读和纯净性

- 从 `a06c057` 提取原始 schema v1 bundle；旧 validator、当前
  `validate.py` 和 `harness.py validate` 在 Text 与 JSON 下均 exit 0，
  stdout/stderr 逐字节一致。
- 对官方 bundle 连续执行直接 validate、CLI validate、`adapt --check`：
  文件树 SHA-256 前后均为
  `87d03e078bd77cfb5688beeccc000e0fffae7ff6434e1efd3fb5b939616d35e4`。
- Python 3.9 grammar parse 通过 `harness.py` 与 `validate.py`。
- 独立扫描未发现禁用 token、日期、网络访问、第三方依赖或第 4 节非目标实现。
- `tests/test_validate.py` 相对基线恰好只有计划批准的三处样例事实修改：
  schema 成功断言 1→2、不支持版本 2→3、重复组件指针 3→4。
- 远端实时状态：只有 `main@a06c057`；没有精确 HEAD 的远端 branch 或 CI，
  因此绿色 CI 证据为空，不能用其他提交的运行替代。

## 合入建议

**不得合入 `370fbb87dd67b20a3f9d88d27cccc7b1d71f6709`。**

开发侧需完成全部 Critical / Important 整改及回归测试；同时处理上列 Minor，
或由设计方明确修订相应承诺。推送新 HEAD 后必须重新执行：

1. Standards / Spec 双路独立审阅；
2. 本记录中的 symlink、特殊节点、LF/CRLF、suffix、Cursor marker 和 JSON envelope 探针；
3. 88 项既有测试及新增测试、v0 Text/JSON 字节兼容、只读文件树指纹、Python 3.9 grammar、`git diff --check`；
4. 与新精确 HEAD 绑定的远端 CI。

本记录不构成对任何后续提交的批准。

## 第二轮复审（2026-07-24，`77602e6`）

- 复审 HEAD：`77602e6cd97242e283006a62d49807863cf00390`
- 相对上轮 HEAD：4 个实现方提交
  - `f2902fe`：修订设计与 ADR
  - `5c8d81b`：字节级受管块与投影节点安全
  - `39f9e60`：命令级 JSON error envelope
  - `77602e6`：缓存排除与 bootstrap 指引
- 审阅方式：重新执行 Standards / Spec 双路独立审阅、上轮全部探针、全量门禁及新增故障注入
- 结论：**Request changes，仍不得合入**

上轮全部 Critical / Important 行为缺陷均已关闭，但写入实现仍可能破坏用户文件并错误报告成功；另发现初始化 dangling symlink 与错误渲染边界缺陷。本结论仅绑定上述精确 HEAD，任何新增提交均须重新复审。

### 第二轮六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 上轮验收边界均已整改，但短写假成功、失败写破坏用户字节及 dangling `.harness` 仍违反核心契约。 |
| B. 事实准确性 | 2/4 | `os.write` 只写部分字节时仍报告 `written` / exit 0；JSON 模式的投影读取错误仍输出 Text stderr。 |
| C. 通用性 | 2/4 | symlink、非普通节点、CRLF 与缓存策略已通用化，但底层写可靠性与错误渲染仍不足以安全落地到任意项目。 |
| D. 可维护性 | 3/4 | 节点检查和字节块处理已形成明确边界；正式文件直接 `O_TRUNC` 且错误渲染重复，仍需收敛。 |
| E. 验证充分性 | 2/4 | 104 项测试全绿并新增大量边界测试，但没有覆盖短写、写异常、dangling `.harness` 和命令错误控制字符。 |
| F. 可追溯性 | 3/4 | 设计已 Approved、ADR 已 Accepted，修订与提交清晰；精确 HEAD 仍未同步远端，没有可绑定 CI。 |

总分：**14/24**。A、B、C、E 均为 2 分，触发合入门禁。

### 上轮 findings 关闭情况

| 上轮 finding | 独立复现结果 | 状态 |
| --- | --- | --- |
| 投影目标 symlink 越界 | exit 1 / `PROJECTION_PATH_UNSAFE`；外部文件保持 `b'OUTSIDE'` | 已关闭 |
| 父目录 symlink 越界 | exit 1 / `PROJECTION_PATH_UNSAFE`；外部目录为空 | 已关闭 |
| 目录/FIFO 目标 | 均 exit 1 / `PROJECTION_TARGET_INVALID`；FIFO 探针未阻塞 | 已关闭 |
| END 后空行丢失 | `b'\n\n\nUSER-SUFFIX\n'` 前后逐字节一致 | 已关闭 |
| CRLF 被归一化 | `b'USER\r\nNOTES\r\n'` 前缀逐字节保留 | 已关闭 |
| Cursor 破损 marker 被覆盖 | exit 1 / `PROJECTION_MARKER_BROKEN`；文件未变化 | 已关闭 |
| JSON adapter 参数错误无 envelope | exit 2；stderr 空；stdout 含完整 init envelope | 已关闭 |
| 隐藏缓存未排除 | 设计列出的 6 类缓存全部未进入目标 bundle | 已关闭 |
| bootstrap 示例与命令路径 | 选项 C 已补代价；命令改为项目根下 `.harness/bin/harness.py` | 已关闭 |
| 设计与 ADR 状态未闭环 | 设计 `Approved`，ADR-0002 `Accepted` | 已关闭 |

### 设计修订核对

设计修订覆盖了上轮提出的 Spec findings：

- §7.1 明确参数解析后的 exit 2 命令错误必须遵守 `--format`。
- §7.2 把“隐藏缓存”收敛成 6 项确定清单。
- §8.1 明确使用 bytes、受管区间边界及 CRLF/空行/无末尾换行语义。
- §8.2 明确 Cursor 整文件所有权不豁免 marker 完整性检查。
- §8.3 明确逐段 `lstat`、symlink/非普通节点错误码、`--check` 同检查及竞态边界。
- 状态由 Draft/Proposed 闭环为 Approved/Accepted。

新增设计缺口：§8.1 的“任何操作下块外字节逐字节保留”尚未落成失败原子性规则。当前正式文件直接 `O_TRUNC`，真实写故障会破坏块外内容。下一轮应在设计中明确“完整临时写成功前原文件不得变化”，再由实现与测试落实。

### Standards findings

#### [Important] 部分写或写异常会破坏用户文件

位置：`template/.harness/bin/harness.py:329-347`

实现以 `O_TRUNC` 直接打开正式投影文件，只调用一次 `os.write`，且忽略其返回的实际字节数。

独立故障注入：

```text
SHORT_WRITE returned True errors [] bytes b'EXP'
MID_WRITE exception 'simulated mid-write failure' errors [] bytes b'EX'
```

短写时 `_write_projection` 返回成功，上层会把文件列入 `written` 并 exit 0；异常时原有用户文件已被截断。两种结果均违反 ADR-0002 §2 与设计 §8.1 的用户字节保全。

整改要求：

1. 在目标同目录创建安全临时普通文件，循环写入直至全部字节完成；零进展或异常必须失败。
2. 完整写入并按需要 flush/fsync 后，重新执行节点安全核验，再以安全替换提交。
3. 任一失败必须保留原目标逐字节不变并清理临时文件；成功后才报告 `written`。
4. 增加短写、零字节写、写异常和替换异常的故障注入回归测试。

#### [Important] 投影 I/O 错误绕过 JSON envelope

位置：`template/.harness/bin/harness.py:299-301,343-346,641-646`

成功 `lstat` 后的 `read_bytes()` 错误，以及写入/关闭错误，直接逃逸到最外层
`INTERNAL_ERROR` handler。不可读的普通 `CLAUDE.md` 实测：

```text
READ_FAILURE_JSON rc 2
stdout ''
stderr "[INTERNAL_ERROR] .: [Errno 13] Permission denied: '.../CLAUDE.md'\n"
```

exit 2 分类合理，但修订后的 §7.1 要求参数解析后的命令错误遵守 `--format`。
`adapt --format json` 应在 stdout 返回完整 envelope，不能退化为 Text stderr。

整改要求：在 `cmd_adapt` / 投影边界捕获这类 OSError，以 exit 2 返回；JSON
使用完整 adapt envelope，Text 使用安全的单行错误格式。不得把节点布局错误
错误分类为 exit 2。

#### [Minor] Text 命令错误仍可被控制字符拆行

位置：`template/.harness/bin/harness.py:114-116`

`emit_command_error` 没有像 `emit` 一样调用 `validate.escape_text_field`。独立输入 adapter
名 `"bad\nname"`：

```text
rc 2
stderr "[ARGUMENT_INVALID] bad\nname: ...\n"
physical_lines 2
```

需统一转义 code/path/message，并覆盖 CR、LF、C0、DEL、NEL、U+2028 与
U+2029，保证一个错误只占一个物理行。

### Spec findings

#### [Important] 短写被误判为完整投影成功

位置：`template/.harness/bin/harness.py:343-347`

POSIX `os.write` 允许返回小于输入长度的正数。当前实现忽略返回值，因此产生截断文件仍报告成功，违反设计 §7.3 的正确投影与幂等、§8.1 的确定性字节产物及 §14 验收要求。此 finding 与 Standards 的数据安全 finding 分属两个审阅轴，整改要求相同。

#### [Important] dangling `.harness` 未按“目标已存在”稳定拒绝

位置：`template/.harness/bin/harness.py:552-577`

`Path.exists()` 对悬空 symlink 返回 false。项目内预置
`.harness -> missing-target` 后执行 init：

```text
DANGLING_HARNESS rc 2
stdout ''
stderr "[INTERNAL_ERROR] .: [Errno 17] File exists: '.../project/.harness'\n"
still_symlink True
```

设计 §7.2 要求 `<target>/.harness` 已存在时稳定拒绝并 exit 1。目录项无论是否悬空都已占用目标名称。需使用 `lstat` / `lexists` 判断并返回
`INIT_TARGET_EXISTS` / exit 1；补 dangling symlink 回归测试，断言不进入
`copytree` 且链接不变。

### 已知残留的独立裁定

- **`lstat` 成功后读取失败：exit 2 合理。** 这属于路径在检查后不可访问或发生环境竞态，不是 Manifest/投影状态违规。
- **真实写中途 OSError：exit 2 合理。** 它是运行时 I/O 故障，不应伪装成 exit 1 的契约错误。
- **实现方关于“因此可直接落入全局 INTERNAL_ERROR”的结论不成立。** 合理的是 exit 2 分类；参数已经解析且 format 已知时，仍须按 §7.1 返回对应 Text/JSON 格式。
- **写故障的破坏性副作用不被 exit 2 豁免。** 原文件被 `O_TRUNC` 截断违反用户内容保全；需以失败原子写保证失败时原文件不变。

### 第二轮验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与 validate.py stdout/stderr 逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 104 tests in 8.063s
OK

$ git diff --check
无输出，exit 0

$ git diff --check e2c2e23...77602e6
无输出，exit 0
```

其他证据：

- Python 3.9 grammar parse：2 个 CLI 文件通过。
- v0 schema v1 bundle：旧 validator、当前 `validate.py`、当前
  `harness.py validate` 在 Text/JSON 下返回码与 stdout/stderr 逐字节一致。
- 只读指纹：三条只读命令执行前后均为
  `d5c07b82cdfa233a924fa7a684de70705fd7a8912dd51d1b70fc43a9e40a5fb6`。
- E2E：CRLF 用户前缀保留，三个投影均生成，副本 `adapt --check` exit 0。
- bundle 禁用 token、日期、第三方依赖、网络访问与第 4 节非目标扫描无发现。
- `tests/test_validate.py` 仍严格只有批准的三处样例事实修改。
- 审阅后 `git status --short` 为空。
- 远端实时仅有 `main@e2c2e23`；新 HEAD `77602e6` 未在远端，因而没有可绑定的 CI 运行。

### 第二轮合入建议

**不得合入 `77602e6cd97242e283006a62d49807863cf00390`。**

开发侧需修复本轮全部 Important，并补齐对应故障注入测试；Text 控制字符
Minor 也应在同一轮关闭。新 HEAD 必须重新执行 Standards / Spec 双路审阅、
本记录全部旧探针及新增短写/异常写/dangling symlink/错误格式探针、全量测试、
v0 兼容、只读指纹、diff check 与精确 HEAD CI。本记录不批准任何后续提交。

## 第三轮复审（2026-07-24，`87cea4f`）

- 复审 HEAD：`87cea4f9f9e794649035eb25337af9c646869971`
- 上轮 HEAD：`77602e6cd97242e283006a62d49807863cf00390`
- 新增提交：`fca4cbb`（设计修订）、`2f8db11`、`315474a`、`87cea4f`
- 审阅方式：Standards / Spec 双路独立审阅、第二轮全部故障注入、第一轮旧探针、全量门禁、v0 字节兼容与只读指纹
- 结论：**Request changes，仍不得合入**

第二轮要求的主要修复成立；短写、零进展写、写中异常、替换异常、不可读文件
JSON、dangling `.harness` 和 adapter 控制字符探针均已 fail closed，且原文件
逐字节不变。但独立扩展故障注入发现关闭失败仍绕过错误信封并遗留临时文件；
初始化复制阶段 I/O 也绕过 JSON envelope 与 cleanup hint；部分成功后的
`written` 谎报为空；POSIX 非 UTF-8 argv 可产生非法 JSON。以上均阻塞合入。
本结论只绑定上述精确 HEAD。

### 第三轮六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 指定边界已关闭，但 close fault 和 init 复制失败仍违反失败原子性及命令错误契约。 |
| B. 事实准确性 | 2/4 | 已写入投影时仍报告 `written: []`；非 UTF-8 argv 可产生无效 JSON 字节流。 |
| C. 通用性 | 3/4 | 临时写、`lexists`、节点安全和转义方向通用；剩余问题集中在底层 I/O 与 POSIX argv。 |
| D. 可维护性 | 3/4 | 安全写已集中；关闭、复制和 parser error 仍绕过统一错误边界。 |
| E. 验证充分性 | 2/4 | 112 项全绿，但未覆盖 close fault、复制 I/O、部分进度和非法 argv 字节。 |
| F. 可追溯性 | 3/4 | 设计与实现提交对应清晰；精确 feature HEAD 未推送远端，无绑定 CI。 |

总分：**15/24**。A、B、E 为 2 分，且存在 Important findings，不能合入。

### 第二轮 findings 与旧探针回归

| finding / 探针 | 独立复现结果 | 状态 |
| --- | --- | --- |
| 短写 | 循环完成全部字节；目标等于期望产物，无临时文件 | 已关闭 |
| 零进展写 | `PROJECTION_IO_ERROR`；原文件逐字节不变，无临时文件 | 已关闭 |
| 写中异常 | `PROJECTION_IO_ERROR`；原文件逐字节不变，无临时文件 | 已关闭 |
| 替换异常 | `PROJECTION_IO_ERROR`；原文件逐字节不变，无临时文件 | 已关闭 |
| 不可读普通文件 / JSON | exit 2；stderr 空；stdout 为 adapt JSON envelope，原文件不变 | 已关闭 |
| dangling `.harness` | exit 1 / `INIT_TARGET_EXISTS`；链接保持不变 | 已关闭 |
| adapter 控制字符 / Text | CR、LF、TAB、NEL、U+2028、U+2029 均转义；一个物理行 | 已关闭 |
| 目标 / 父目录 symlink | exit 1 / `PROJECTION_PATH_UNSAFE`；边界外无变化 | 回归通过 |
| 目录 / FIFO 目标 | exit 1 / `PROJECTION_TARGET_INVALID`；FIFO 不阻塞 | 回归通过 |
| END 后空行 / CRLF | 块外前后缀逐字节一致 | 回归通过 |
| Cursor 破损 marker | exit 1 / `PROJECTION_MARKER_BROKEN`；文件不变 | 回归通过 |

### 设计修订核对

第二轮要求已写入设计：

- §8.3 明确同目录临时文件、短写循环、零进展失败、`fsync`、重新核验后替换，
  且任一失败须保持原目标不变、清理临时文件、不计入 `written`。
- §7.1 明确运行时投影 I/O 使用 `PROJECTION_IO_ERROR` / exit 2，Text
  控制字符转义，JSON 继续使用命令 envelope。
- §7.2 使用 `lexists` 语义判断 `.harness` 的任意目录项，包括 dangling
  symlink。

新增设计缺口：`init` 在复制 bundle 阶段发生 I/O 失败时，§7.1 / §7.2
没有定义稳定错误码、JSON envelope 与部分目标 cleanup hint。该阶段同样发生
在参数解析后，且可能已创建部分 `.harness`；设计应补充例如
`INIT_IO_ERROR` 的契约，再由实现与测试对齐。

### Standards findings

#### [Important] 临时文件关闭失败绕过错误信封并遗留节点

位置：`template/.harness/bin/harness.py:403-413`

写入和 `fsync` 被异常处理包围，`os.close(descriptor)` 却在处理边界之外。
让真实 close 完成后再抛 `OSError` 的独立故障注入结果：

```text
CLOSE_ERROR exception=OSError
error_code=None
target_unchanged=True
temp_exists=True
```

错误未转成 `PROJECTION_IO_ERROR`，且 `.harness-tmp` 未清理，违反 §7.1
和 §8.3。应把 close 纳入统一异常与 cleanup 边界；所有打开后的失败都应尽力
关闭描述符、清理本次临时文件并抛 `ProjectionIOError`。补 close fault 测试，
断言稳定 envelope、原目标不变、临时文件不存在。

#### [Important] POSIX 非 UTF-8 argv 可生成非法 JSON

位置：`template/.harness/bin/harness.py:126-136`

以包含字节 `0xff` 的 argv 调用 JSON 模式，Python 的 surrogateescape 与当前
`ensure_ascii=False` 组合会把原始 `0xff` 写入 stdout：

```text
rc=2
stderr=b''
stdout_utf8_valid=False
```

这违反 §7.1 的机器可读输出契约。应在渲染前稳定拒绝或安全规范化
surrogateescape，保证 stdout 始终是 UTF-8 且可被标准 JSON 解析器解析；
补 bytes argv 子进程测试。

### Spec findings

#### [Important] init 复制 I/O 绕过 envelope 与清理提示

位置：`template/.harness/bin/harness.py:657-673`

`shutil.copytree` 在命令级异常处理和 `cleanup_hint` 建立之前执行。向源 bundle
加入 dangling symlink 后：

```text
COPY_FAILURE rc=2
stdout=b''
stderr='[INTERNAL_ERROR] ...'
destination_exists=True
copied_entries=23
```

JSON 模式无 envelope，目标已部分创建却无 cleanup hint。应先补设计契约，再
捕获 `shutil.Error` / `OSError`，以稳定 init 错误码和所选格式返回；目标存在
时给出准确清理提示。补复制中断/坏源节点测试。

#### [Important] 部分投影已提交时 `written` 谎报为空

位置：`template/.harness/bin/harness.py:493,534-542,687-700`

令 `CLAUDE.md` 成功替换、随后 `AGENTS.md` 替换失败：

```text
rc=2
errors=['PROJECTION_IO_ERROR']
payload_written=[]
CLAUDE.md exists=True
AGENTS.md exists=False
```

`adapt` / `init` 不是跨文件事务，错误 envelope 必须报告已提交文件。实现方
将其列为 Minor，但空列表是错误的外部事实，会误导恢复与自动化，独立裁定为
**Important**。应在异常中携带截至失败点的提交列表，或以等价结构将真实进度
传给 renderer，并补第二个投影失败测试。

#### [Minor] 参数解析 Text 路径仍可被控制字符拆行

位置：`template/.harness/bin/harness.py:728-733`

adapter 校验错误已转义，但 argparse 顶层错误仍直接插入 `str(error)`。未知
参数 `"--bad\nname"` 会产生两个物理行。§7.1 允许解析失败使用 Text stderr，
但固定单行错误格式仍不应允许输入注入新行。应复用同一转义函数并补
parser-level 测试。

### 三个披露 Minor 的独立裁定

| 实现方披露 | 独立裁定 | 理由 |
| --- | --- | --- |
| 预存 `.harness-tmp` 时 fail closed、无自愈 | **接受，不构成 finding** | `O_EXCL` 稳定拒绝，原目标和预存节点不变；无法证明节点归工具所有，自动删除反而可能破坏数据。 |
| I/O 失败时 `written` 少报 | **推翻 Minor，升级 Important** | 首个文件可能已提交且不会回滚；空列表是错误事实，会误导恢复和自动化。 |
| 转义覆盖依赖共享函数 | **接受，不构成 finding** | 复用集中转义函数合理，现有测试覆盖 C0、DEL、NEL、U+2028、U+2029；argparse 未调用它是另一条 Minor。 |

### 第三轮验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与 validate.py stdout/stderr 逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 112 tests in 28.173s
OK

$ git diff --check
无输出，exit 0

$ git diff --check 8d0c8ac...87cea4f
无输出，exit 0
```

其他证据：

- v0 schema v1 bundle：旧 validator、当前 `validate.py`、当前
  `harness.py validate` 在 Text / JSON 下均 exit 0，stdout/stderr
  分别逐字节一致。
- 三条只读命令前后文件树指纹均为
  `472f46c19f6ef229426352fb52120669766620528fb50913802e61a7cfb0e50e`。
- Python 3.9 grammar：两个 CLI 文件均通过。
- E2E init / adapt check：init exit 0、check exit 0，CRLF 用户前缀逐字节保留，
  三个声明投影均存在。
- bundle 禁用 token、日期、网络、第三方依赖和 §4 非目标扫描无发现。
- `tests/test_validate.py` 仍严格只有获批的三处样例事实修正。
- 执行全部探针后 feature worktree `git status --short` 为空。
- 远端只有 `main@8d0c8ac`，没有 `feature/harness-v1`；不存在与
  `87cea4f` 精确绑定的远端 CI。

### 第三轮合入建议

**不得合入 `87cea4f9f9e794649035eb25337af9c646869971`。**

开发侧至少需要：

1. 修复 close fault 的统一 envelope 与临时文件清理并补故障测试；
2. 补齐 init copy I/O 的设计契约、envelope、cleanup hint 与测试；
3. 部分成功后如实报告 `written` / `projected_files`；
4. 保证所有 JSON 输出为合法 UTF-8，并补非 UTF-8 argv 测试；
5. 修复 parser-level Text 控制字符拆行。

新 HEAD 需重新执行双路审阅、本文三轮全部探针、全量测试、v0 字节兼容、只读
指纹、Python 3.9 grammar、`git diff --check` 与精确 HEAD CI。本记录不批准
任何后续提交。

## 第四轮复审（2026-07-24，`bbec6c9`）

- 复审 HEAD：`bbec6c928530f9c426ccf858a357bc6a8f798ecc`
- 上轮 HEAD：`87cea4f9f9e794649035eb25337af9c646869971`
- 新增提交：`18b13f1`、`ce3459f`、`9bbb83b`、`b3e5b3c`、`9e7b3c5`、`bbec6c9`
- 审阅方式：Standards / Spec 双路独立审阅、第三轮全部探针、manifest
  stamp 故障、全部历史探针和相邻阶段故障注入
- 结论：**Request changes，仍不得合入**

第三轮五个 finding 及本轮披露的 manifest stamp 故障均已按要求关闭，118 项
测试和全部既有门禁通过。但“全阶段 I/O envelope”仍未闭环：源 Manifest
校验后的再次读取、init 最终校验、adapt 校验后的 Manifest 重读都可裸抛
`OSError`。此外，init 的 exit 1 部分成功仍把 `projected_files` 谎报为空。
本结论只绑定上述精确 HEAD。

### 第四轮六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 指定修复成立，但 init 全生命周期 I/O 和所有失败类型的真实进度仍未覆盖。 |
| B. 事实准确性 | 2/4 | exit 1 前已写入两个投影时，JSON 仍报告 `projected_files: []`。 |
| C. 通用性 | 3/4 | POSIX argv、节点安全和失败原子写已通用化；阶段边界仍依赖局部 try/except。 |
| D. 可维护性 | 3/4 | 进度随 `ProjectionIOError` 传递清晰，但 init/adapt 的读取和验证错误处理分散。 |
| E. 验证充分性 | 2/4 | 118 项全绿，却遗漏三个相邻 I/O 缝隙、exit 1 部分进度和 pre-close FD 生命周期。 |
| F. 可追溯性 | 3/4 | 两次设计修订与四次修复对应清晰；精确 feature HEAD 未在远端，无绑定 CI。 |

总分：**15/24**。A、B、E 为 2 分，且存在 Important findings，不能合入。

### 第三轮 findings 与新增披露项关闭情况

| 探针 | 独立结果 | 状态 |
| --- | --- | --- |
| close-after-real-close 故障 | `PROJECTION_IO_ERROR`；原目标不变；临时文件清理 | 已关闭 |
| init copytree 故障 | exit 2 / `INIT_IO_ERROR`；JSON envelope + `INIT_CLEANUP_HINT` | 已关闭 |
| 第二个投影 I/O 失败 | `written: ["CLAUDE.md"]` 与磁盘实际一致 | 已关闭 |
| argv 字节 `0xff` | exit 2；stdout 空；stderr 为合法 UTF-8 单行且无原始 `0xff` | 已关闭 |
| parser 换行注入 | `\n` 转义为 `\u000a`；单一物理行 | 已关闭 |
| manifest stamp 写入故障 | exit 2 / `INIT_IO_ERROR` + `INIT_CLEANUP_HINT`，非 `INTERNAL_ERROR` | 已关闭 |

短写、零进展写、写中异常、替换异常、不可读普通文件 JSON、dangling
`.harness`、adapter 控制字符、目标/父目录 symlink、目录/FIFO、END 后空行、
CRLF 和 Cursor 破损 marker 全部回归通过。所有失败原子写探针中，原目标均
逐字节不变且本次临时文件被清理；短写成功产物等于完整期望字节。

### 设计修订核对

- §7.1 已增加 parser 控制字符转义、非法 UTF-8 argv 的稳定拒绝，以及错误
  envelope 必须如实报告 `written` / `projected_files` 三条规则。
- §7.2 已明确 copytree 与 origin Manifest 读取/写回的 I/O 错误使用
  `INIT_IO_ERROR` / exit 2，并在目标已创建时附 `INIT_CLEANUP_HINT`。
- §8.3 已把文件描述符关闭失败纳入 `PROJECTION_IO_ERROR` 和失败原子边界。

但“§7.2 `INIT_IO_ERROR` 全阶段覆盖”并未真正写成完整契约：当前文字只点名
copytree 与 origin stamp，没有覆盖源 Manifest 校验后的再次读取、最终
`validate_harness(destination)`，也未明确 adapt 后 exit 1 的部分投影进度。
§7.1 的一般规则足以判定当前实现不合规，但 §7.2 仍应把这些 init 阶段及
cleanup/progress 字段明确列出，避免下一轮继续出现局部补丁。

### Standards findings

#### [Important] close-before-consume 故障仍可泄漏描述符

位置：`template/.harness/bin/harness.py:420-447`

实现先把 `descriptor = None`，再调用 `os.close(close_fd)`。若 close 在真正
消费描述符前抛错，`finally` 无法再次处理该 fd。独立注入结果：

```text
PRECLOSE_FAULT exc=ProjectionIOError code=PROJECTION_IO_ERROR
target_intact=True temp=False fd_open=True
```

错误码、目标字节与临时文件均正确，但描述符仍开放，与 §8.3“尽力关闭描述符”
不一致。需明确跨平台 close 失败的所有权语义并实现安全的 best-effort 收口，
避免盲目重试关闭已被消费或复用的 fd；补“抛错发生在实际 close 之前”的测试，
而不只覆盖当前的 close-then-raise 夹具。

非阻塞维护性观察：`_escape_argv_field` 直接读取 `validate` 的下划线私有常量与
helper，形成轻微 Feature Envy / 紧耦合。当前两个模块随同一单文件分发包发布，
本轮不单独阻塞；后续可把公共转义边界公开化以降低漂移。

### Spec findings

#### [Important] init 仍有两个裸 I/O 缝隙

位置：`template/.harness/bin/harness.py:657,793`

独立注入：

```text
SOURCE_MANIFEST_REREAD rc=None exc=OSError stdout='' stderr='' dest=False
FINAL_VALIDATE_IO rc=None exc=OSError stdout='' stderr=''
dest=True projections=['CLAUDE.md', 'AGENTS.md', '.cursor/rules/harness.mdc']
```

第一处是源校验成功后再次 `read_text/json.loads`；第二处是复制、stamp 和投影
完成后的最终 `validate_harness`。两者均逃出 `cmd_init`，脚本入口会降级成
Text-only `INTERNAL_ERROR`，即使请求 JSON。最终校验故障时目标与三个投影已
落盘，却没有 `INIT_CLEANUP_HINT` 或真实 `projected_files`。这违反 §7.1 的
post-parse envelope，以及 §7.2“任何步骤失败即停止、明确清理方式”。

整改要求：把源二次读取和最终校验纳入 init 命令错误边界；运行时 I/O 使用
稳定 `INIT_IO_ERROR` / exit 2，按格式渲染；目标已创建时附 cleanup hint，
并在最终阶段报告已提交投影。补两条故障注入测试。

#### [Important] adapt 校验后的 Manifest 重读仍绕过 envelope

位置：`template/.harness/bin/harness.py:534-554`

`validate_harness(root)` 成功后，line 554 再次读取 Manifest，未纳入
`ProjectionIOError` 或命令级异常边界。独立令该次读取抛 `OSError`：

```text
ADAPT_MANIFEST_REREAD rc=None exc=OSError stdout='' stderr=''
```

脚本入口同样会输出裸 `INTERNAL_ERROR`，违反 §7.1“参数解析成功后的命令级
错误遵守 `--format`”。应避免重复读取或捕获读取/解析竞态，以
`PROJECTION_IO_ERROR`（或设计明确的稳定 code）返回完整 adapt envelope。

#### [Important] init 的 exit 1 部分成功仍少报进度

位置：`template/.harness/bin/harness.py:612-620,788-800`

在目标项目预置 `AGENTS.md` 目录，init 会先成功写入 `CLAUDE.md`，遇到
`AGENTS.md` 节点错误后继续成功写入 Cursor 投影。独立结果：

```text
INIT_EXIT1_PROGRESS rc=1
codes=['PROJECTION_TARGET_INVALID']
reported=[]
actual_files=['CLAUDE.md', '.cursor/rules/harness.mdc']
cleanup=['INIT_CLEANUP_HINT']
```

§7.1 的新规没有限定 exit 2；任何错误 envelope 都必须报告截至失败点已实际
提交的投影。`_init_failure` 固定 `projected_files: []`，导致 exit 1 和最终
校验失败路径继续谎报。应允许 `_init_failure` 接收真实进度，并在
`run_adapt` 返回 errors 及 final validation failure 时传入 `written` /
`unchanged` 的适当集合；补部分写入后契约错误的回归测试。

### 第四轮验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与独立命令逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 118 tests in 11.557s
OK

$ git diff --check
无输出，exit 0

$ git diff --check 08359a7...bbec6c9
无输出，exit 0
```

其他门禁：

- v0 schema v1：旧 validator、当前 validator、当前 CLI 在 Text/JSON 下均
  exit 0，stdout/stderr 逐字节一致。
- 三条只读命令执行前后 bundle 指纹均为
  `e47aca5d8ad876f9315a83fb422fbd569c6bd99f4bab93d7184f95ae89e59af2`。
- Python 3.9 grammar：`harness.py`、`validate.py` 均通过。
- E2E init / adapt check：均 exit 0，CRLF 用户前缀逐字节保留，三个投影存在。
- 禁用 token、日期、网络访问与第三方依赖扫描无发现。
- `tests/test_validate.py` 相对 v0 仍恰好只有获批的三处样例事实修正。
- 全部验证后 `git status --short` 为空，HEAD 仍为
  `bbec6c928530f9c426ccf858a357bc6a8f798ecc`。
- 远端只有 `main@08359a7`，没有 `feature/harness-v1` 或开放 PR；不存在与
  `bbec6c9` 精确绑定的 CI。

### 第四轮合入建议

**不得合入 `bbec6c928530f9c426ccf858a357bc6a8f798ecc`。**

下一轮至少应：

1. 设计并实现 init 源 Manifest 二次读取与最终校验的 `INIT_IO_ERROR`
   envelope、cleanup hint 和真实进度；
2. 收口 adapt 校验后 Manifest 重读的运行时 I/O envelope；
3. 让 init 的 exit 1 / 最终校验失败如实报告已提交投影；
4. 明确并测试 close-before-consume 时的安全描述符所有权。

新 HEAD 必须重跑四轮全部探针、全量测试和既有门禁。本记录不批准后续提交。

## 第五轮复审（2026-07-24，`93aee76`）

- 复审 HEAD：`93aee7626fd0ead6f1da146a810aa04a76d181ed`
- 上轮 HEAD：`bbec6c928530f9c426ccf858a357bc6a8f798ecc`
- 新增提交：`11de76f`、`91c09be`、`a64a6da`、`93aee76`
- 审阅方式：Standards / Spec 双路独立审阅、第四轮全部探针、本轮三项主动
  收口、全部历史探针、全量门禁及相邻生命周期故障注入
- 结论：**Request changes，仍不得合入**

第四轮五个 findings 及本轮主动披露的三项收口均按指定行为通过；125 项测试、
历史探针和门禁也全部通过。但设计宣称的“全生命周期”仍存在未覆盖的异常类型与
阶段：`UnicodeDecodeError`、统一入口 `validate` 的裸 `OSError`、成功响应前
的目标路径解析仍会逃逸。此外，`projected_files = written + unchanged` 与
“本次实际提交/生成”的公开定义冲突。本结论仅绑定上述精确 HEAD。

### 第五轮六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 点名修复通过，但“所有读取/全生命周期”仍漏 Unicode 解码、validate 和成功 resolve。 |
| B. 事实准确性 | 2/4 | 未修改的 byte-identical 文件被列入“本次实际提交”的 `projected_files`。 |
| C. 通用性 | 3/4 | POSIX fd 所有权已明确；解码错误和路径解析边界仍不足以跨环境稳定落地。 |
| D. 可维护性 | 3/4 | init/adapt 阶段注释与错误边界清楚，但相同异常分类仍以多个局部 catch 拼接。 |
| E. 验证充分性 | 2/4 | 125 项全绿，却未覆盖非法 UTF-8、validate 对称边界、最终 resolve 和 unchanged 语义。 |
| F. 可追溯性 | 3/4 | 设计与实现提交对应清晰；精确 feature HEAD 未推送远端，无绑定 CI。 |

总分：**15/24**。A、B、E 为 2 分，且存在 Important findings，不能合入。

### 第四轮 findings 与主动收口验证

| 探针 | 独立结果 | 状态 |
| --- | --- | --- |
| `SOURCE_MANIFEST_REREAD` | exit 2 / `INIT_IO_ERROR` JSON；目标未创建，无 cleanup hint | 已关闭 |
| `FINAL_VALIDATE_IO` | exit 2 / `INIT_IO_ERROR` + cleanup hint；报告三个实际投影 | 已关闭 |
| `ADAPT_MANIFEST_REREAD` | exit 2 / `PROJECTION_IO_ERROR` 完整 adapt envelope | 已关闭 |
| `INIT_EXIT1_PROGRESS` | exit 1；报告 `CLAUDE.md` 与 Cursor，和磁盘一致 | 已关闭 |
| `PRECLOSE_FAULT` | `PROJECTION_IO_ERROR`；原目标不变、temp 清理、close 恰调用一次 | 按修订契约关闭 |
| 源校验裸 `OSError` | exit 2 / `INIT_IO_ERROR`；target null、进度空、无 cleanup hint | 已关闭 |
| adapt 校验裸 `OSError` | exit 2 / `PROJECTION_IO_ERROR`；三个进度字段为空 | 已关闭 |
| ProjectionIOError 的 `written + unchanged` | 返回 `["CLAUDE.md", "AGENTS.md"]`，与当前实现规则一致 | 行为通过；语义见 finding |

短写、零进展写、写中异常、替换异常、close-after-real-close、symlink、父目录
symlink、目录/FIFO、END 后空行、CRLF、Cursor 破损 marker、不可读目标 JSON、
dangling `.harness`、adapter/parser 控制字符、copytree、manifest stamp、
`0xff` argv 均回归通过。

### 设计修订核对

- §7.2 已从局部阶段扩展为 init 生命周期枚举，覆盖源校验、源 Manifest 重读、
  copy、origin stamp、投影和最终 validate，并明确 cleanup/progress。
- §7.3 已明确 adapt 校验后 Manifest 重读的对称错误 envelope。
- §8.3 已明确 fd 恰好 close 一次；close 抛错后视为已消费、不重试，病理性的
  pre-close 泄漏由短生命周期进程退出回收。实现与该取舍一致。

然而“不得局部补丁”尚未闭环：

1. §7.2 写“所有运行时 I/O 失败”，实现与测试却只覆盖
   `OSError/json.JSONDecodeError`，遗漏 `read_text(encoding="utf-8")`
   实际会抛的 `UnicodeDecodeError`。
2. §7.1 对统一 CLI 的命令级错误仍适用于 `harness.py validate`，但 §7.4
   没有对称写清其运行时读取边界，实现也未覆盖。
3. init 成功响应前仍执行一次未保护的 `destination.resolve()`。
4. §7.1/§7.2 的“已实际提交”与 §7.2 JSON 字段“本次生成”排除 unchanged，
   而实现方指定 `written + unchanged`。设计必须先统一字段含义。

### Standards findings

#### [Important] Unicode 解码竞态仍逃逸全生命周期 envelope

位置：`template/.harness/bin/harness.py:548-599,692-746,829-857,896-914`

这些边界捕获 `OSError` / `json.JSONDecodeError`，但 UTF-8 解码发生在
`Path.read_text`，失败类型是 `UnicodeDecodeError`。真实非法 UTF-8 Manifest：

```text
INIT_BAD_UTF8     rc=2 stdout=b'' stderr=[INTERNAL_ERROR]
ADAPT_BAD_UTF8    rc=2 stdout=b'' stderr=[INTERNAL_ERROR]
VALIDATE_BAD_UTF8 rc=2 stdout=b'' stderr=[INTERNAL_ERROR]
```

校验成功后令第二次读取抛 `UnicodeDecodeError`，`cmd_init` 与 `cmd_adapt`
也直接抛出，stdout 为空。这违反 §7.1、§7.2 和 §7.3。

整改要求：在 init/adapt 的验证与每个读取边界明确捕获 `UnicodeError`
（或更窄的 `UnicodeDecodeError`），分别映射为 `INIT_IO_ERROR` /
`PROJECTION_IO_ERROR`；补真实非法字节和 post-validate decode race 测试。

#### [Important] `projected_files` 把 unchanged 误报为本次提交

位置：`template/.harness/bin/harness.py:863-875,883-888,909-923`

预置 byte-identical `CLAUDE.md`，让随后 `AGENTS.md` 写失败：

```text
UNCHANGED_PROGRESS rc=2
reported=['CLAUDE.md']
CLAUDE inode_same=True bytes_same=True
```

该文件本次没有写入或提交，却被计入 §7.1 所称“截至失败点已实际提交”和字段
定义所称“本次生成”。若产品语义确实要报告“失败时已存在且有效的投影”，应先
修订 §7.1、§7.2 和字段名称/定义；若维持“本次提交/生成”，错误路径只能报告
`written`。这是设计与实现的事实语义冲突，不可仅用测试固定当前行为。

非阻塞维护性观察：五个并行进度列表与多处 envelope 拼装形成轻微 Data Clumps /
Duplicated Code；当前规模尚可，不单独阻塞。

### Spec findings

#### [Important] 统一 `validate` 仍缺少对称运行时错误 envelope

位置：`template/.harness/bin/harness.py:263-277`

独立让 `validate.validate_harness` 抛 `OSError`：

```text
VALIDATE_IO_SEAM rc=None exc=OSError stdout='' stderr=''
```

脚本入口会退化为裸 `INTERNAL_ERROR`。§7.1 已明确 `harness.py validate`
正常输出与独立 validator 一致，但命令级错误路径按统一 CLI 契约渲染。因此
init/adapt 的新 catch 不能替代 validate 对称边界。应以稳定 code、exit 2 和
所选格式返回；独立 `validate.py` 的 v0 行为保持不变。

#### [Important] 成功响应前的目标 resolve 仍是裸 I/O 缝隙

位置：`template/.harness/bin/harness.py:926-935`

final validation 成功后，success envelope 仍调用未保护的
`destination.resolve()`。让该次 resolve 抛 `OSError`：

```text
SUCCESS_TARGET_RESOLVE calls=2 rc=None exc=OSError
stdout='' stderr='' dest=True
```

此时 Harness 与三个投影已经落盘，但没有 `INIT_IO_ERROR`、cleanup hint 或
真实进度，违反 §7.2“参数解析后直至命令返回”的全生命周期定义。应在复制前
安全解析并缓存规范化目标，或把最终 resolve 纳入 init 错误边界；补故障测试。

### 第五轮验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与独立命令逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 125 tests in 9.495s
OK

$ git diff --check
无输出，exit 0

$ git diff --check 9a5fb58...93aee76
无输出，exit 0
```

其他门禁：

- v0 schema v1：旧 validator、当前 validator、当前 CLI 在 Text/JSON 下均
  exit 0，stdout/stderr 逐字节一致。
- 三条只读命令前后 bundle 指纹均为
  `398a6fd556eb2159181231e98f473173f383efe644d8f41238dee97494ddb48b`。
- Python 3.9 grammar：两个 CLI 文件均通过。
- E2E init / adapt check 均 exit 0，CRLF 用户前缀逐字节不变，三个投影存在。
- 禁用 token、日期、网络和第三方依赖扫描无发现。
- `tests/test_validate.py` 仍只有获批的三处样例事实修正。
- 全部验证后工作区干净，HEAD 仍为
  `93aee7626fd0ead6f1da146a810aa04a76d181ed`。
- 远端只有 `main@9a5fb58`，没有 feature 分支或开放 PR，故无精确 HEAD CI。

### 第五轮合入建议

**不得合入 `93aee7626fd0ead6f1da146a810aa04a76d181ed`。**

下一轮至少应：

1. 统一捕获并渲染 init/adapt/统一 validate 的 Unicode 解码失败；
2. 收口 init 最终 success target resolve 的 I/O 边界；
3. 明确 `projected_files` 是“本次写入”还是“当前有效”，再统一设计、实现和测试；
4. 为以上真实字节和相邻生命周期边界增加回归测试。

新 HEAD 必须重跑五轮全部探针、全量测试与既有门禁。本记录不批准后续提交。

## 第六轮复审（2026-07-24，`76a4523`）

### 结论

**Request changes，不得合入。**

本轮结论仅绑定
`76a4523b2c91cb10249f968ed44795bb57656180`。设计修订
`f7b5f88` 先于实现修复 `e826c7b` 与测试 `76a4523`，且正确补充了 Unicode
读取、统一 `validate`、init 全生命周期、预解析目标以及
`projected_files` 语义 A。第五轮的三个直接 finding 均已关闭，140 项测试与
全部既有门禁也通过。

但相邻 I/O 缝隙扫描独立发现三个 Important：init 的 target 检查仍不在错误
边界内；已缓存的规范化绝对目标没有用于失败响应；命令级 JSON 错误消息含
POSIX `surrogateescape` 字符时会产生非法 UTF-8。这三项都直接违反本轮修订后
的 §7.1/§7.2，故不能批准。

### 六维评分

| 维度 | 得分 | 独立裁定 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 第五轮指定整改已覆盖，但 init 全生命周期和合法 UTF-8 envelope 仍未闭环。 |
| B. 事实准确性 | 2/4 | “失败 envelope 复用缓存”“JSON 始终合法 UTF-8”与实际实现不符。 |
| C. 通用性 | 3/4 | 标准库、平台中立与语义 A 成立；POSIX 路径字节和不可访问路径仍有通用性缺口。 |
| D. 可维护性 | 2/4 | 生命周期逻辑分散，缓存值与原始值并存，新增契约未形成单一出口。 |
| E. 验证充分性 | 2/4 | 140 项测试与真实非法 Manifest 很充分，但漏掉 target 检查错误、失败路径绝对值和异常消息代理字符。 |
| F. 可追溯性 | 3/4 | 设计、实现、测试分提交且顺序正确；分支未推送，无精确 HEAD CI。 |

**总分：14/24。** A、B、D、E 未达到合入门槛。

### 第五轮 findings 与指定探针

| finding / 探针 | 本轮独立结果 | 状态 |
| --- | --- | --- |
| init / adapt / 统一 validate 读取真实非法 UTF-8 Manifest | 分别 exit 2，JSON 可严格解析，stderr 空，错误码依次为 `INIT_IO_ERROR` / `PROJECTION_IO_ERROR` / `VALIDATE_IO_ERROR`，无裸 `INTERNAL_ERROR` | 已关闭 |
| 独立 `validate.py` 非法 UTF-8 | 保持 v0：exit 2，stdout 空，stderr 裸 `INTERNAL_ERROR` | 兼容通过 |
| 源 Manifest 二读 / adapt 二读解码竞态 | 分别稳定映射 `INIT_IO_ERROR` / `PROJECTION_IO_ERROR` | 已关闭 |
| stamp 读取 / final validate 解码竞态 | 均为 `INIT_IO_ERROR`、exit 2，带 cleanup hint 和真实进度 | 已关闭 |
| 成功前 `resolve()` 故障 | `INIT_IO_ERROR`、无 cleanup hint、无目标副本 | 已关闭 |
| 语义 A：byte-identical `CLAUDE.md` 后续失败 | `projected_files=[]`，原 inode 与全字节均不变 | 已关闭 |
| written + unchanged + failure 三态 | `written=['AGENTS.md']`、`unchanged=['CLAUDE.md']`、失败项不混入 | 已关闭 |

历史 SHORT / ZERO / MID / REPLACE / CLOSE_AFTER / PRECLOSE_FAULT /
SOURCE_MANIFEST_REREAD / FINAL_VALIDATE_IO / ADAPT_MANIFEST_REREAD /
INIT_EXIT1_PROGRESS / SOURCE_VALIDATE_OSERROR / ADAPT_VALIDATE_OSERROR /
copytree / stamp / unreadable projection / target symlink / parent symlink /
目录 / FIFO / END suffix / CRLF / Cursor broken marker / dangling `.harness` /
adapter controls / parser newline / argv `0xff` 探针全部重新执行，均保持前五轮
已裁定的 fail-closed、失败原子性、准确进度和块外字节保全结果。

### Standards findings

#### Important — target 路径检查吞掉 I/O 错误并错误降级为 exit 1

位置：`template/.harness/bin/harness.py:795-810`

`Path.is_dir()` 会把路径查询的 `OSError` 当作 `False`，而随后的
`os.path.lexists()` 也在保护边界外。真实自环符号链接探针：

```text
TARGET_LOOP rc=1 errors=['INIT_TARGET_MISSING'] target=None stderr_empty=True
```

该路径不是“目标不存在”的可预期状态；设计 §7.2 已把 target 路径检查和失败
状态构造纳入 init 全生命周期，并要求运行时路径故障映射
`INIT_IO_ERROR` / exit 2。注入 `is_dir` / `lexists` 的 `OSError` 还会直接逃逸
到统一裸内部错误。

最低整改：用显式 `stat` / `lstat` 结果区分“不存在或不是目录”（exit 1）与
“查询失败”（`INIT_IO_ERROR` / exit 2）；将 target、`.harness` 目录项检查及
cleanup 状态查询置于同一个明确边界。增加真实不可访问/循环路径与故障注入的
Text/JSON 回归。

#### Important — 缓存的绝对 target 未用于失败 envelope

位置：`template/.harness/bin/harness.py:833-987`

代码在复制前得到 `resolved_target`，但 cleanup hint 和复制、stamp、投影、
final validate 的全部失败返回仍使用 `str(destination)`。从临时 cwd 以相对
target 注入复制故障：

```text
RELATIVE_COPY_FAILURE rc=2
target='project/.harness' absolute=False
codes=['INIT_IO_ERROR'] hint_path='project/.harness'
```

这违反 §7.2“成功与失败 envelope 复用缓存”和 §7.2 JSON 字段的规范化绝对
路径定义，也使 cleanup 指引依赖调用者当前目录。

最低整改：预解析成功后，所有成功与失败 envelope、错误 path 与
`INIT_CLEANUP_HINT` 均只使用同一缓存绝对路径；预解析失败阶段保持无复制、无
cleanup hint。补相对 target 在 copy/stamp/projection/final-validation/exit-1
失败路径上的字段断言。

#### Important — JSON 错误 envelope 可能不是合法 UTF-8

位置：`template/.harness/bin/harness.py:135-155`

`emit_command_error()` 以 `ensure_ascii=False` 原样渲染异常消息。POSIX 文件
系统错误可以经 `surrogateescape` 带入代理字符；stdout 默认也使用
`surrogateescape`。给 `copytree` 注入包含 `\udcff` 的 `shutil.Error` 并捕获
原始 stdout 字节：

```text
SURROGATE_ERROR_JSON rc=2 exc=None utf8_valid=False raw_ff=True
```

即命令返回了 envelope，但其字节流不能以严格 UTF-8 解码，与 §7.1
“JSON 输出必须始终是合法 UTF-8”“path/message 经转义”直接冲突。

最低整改：在 JSON 渲染边界对所有字符串做可逆安全转义，最小方案可使用
ASCII-safe JSON 编码；不得只处理 argv。增加以 `TextIOWrapper(errors=
"surrogateescape")` 捕获原始字节、再严格 `decode("utf-8")` 和
`json.loads()` 的测试，错误 path 与 message 都应覆盖。

### Spec findings 与设计核对

- `f7b5f88` 独立修改 `docs/design/harness-v1.md`，位于实现提交之前，满足
  设计所有权与提交顺序要求。
- §7.1 已枚举 `OSError`、`JSONDecodeError`、`UnicodeError` 并规定三类阶段
  错误码；§7.3 与 §7.4 已补 adapt / validate 对称边界。
- §7.2 已枚举九个 init 生命周期阶段，并将 resolve 明确为复制前阶段；§7.1、
  §7.2 及 JSON 字段对语义 A 的表述一致，未发现 “written + unchanged” 残留。
- 设计文本本身足以覆盖第五轮 Spec findings；本轮阻断是实现没有落实其中
  target 检查、失败 envelope 缓存复用和合法 UTF-8 三项，不需要再放宽设计。
- `copytree` 保留 `(shutil.Error, OSError)` 是可接受的显式边界；未复用读取
  异常元组不构成 finding。

### 第六轮验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（与独立命令逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 140 tests in 8.787s
OK

$ git diff --check
无输出，exit 0

$ git diff --check d8bb2cc...76a4523
无输出，exit 0
```

其他门禁：

- v0 schema v1：旧 validator、当前 `validate.py`、当前 `harness.py validate`
  在 Text/JSON 下 stdout/stderr 逐字节一致。
- 三条只读命令前后 bundle 指纹均为
  `79f98d158401d77c6504a1997d90a379e6ccebe7ce375dfa2bcf56d8e2d050aa`。
- Python 3.9 grammar：两个 CLI 文件均通过。
- E2E init / adapt check：均 exit 0，CRLF 用户前缀逐字节保留，三个投影存在。
- 禁用 token、日期、网络访问和第三方依赖扫描无发现。
- `tests/test_validate.py` 相对 v0 仍恰好只有批准的三处样例事实修正。
- 全部验证后 feature worktree 干净，HEAD 仍为
  `76a4523b2c91cb10249f968ed44795bb57656180`。
- feature 分支未推送，GitHub 无开放 PR 或绑定精确 HEAD 的 CI；本轮不能声称
  具备远端 CI 证据。静态/探针阻断已足够拒绝，未要求为失败版本补跑 CI。

### 第六轮合入建议

**不得合入 `76a4523b2c91cb10249f968ed44795bb57656180`。**

下一轮必须至少关闭：

1. target 与 `.harness` 目录项检查的 init I/O 边界；
2. 规范化绝对 target 在全部 post-resolve 响应和 cleanup hint 中的复用；
3. 文件系统异常含代理字符时 JSON envelope 的严格 UTF-8 合法性。

新 HEAD 必须重新执行本文六轮全部探针、140 项以上测试、v0 字节兼容、只读
指纹、Python 3.9 grammar、E2E 与 diff check。本记录不批准任何后续提交。

## 第七轮复审（2026-07-24，`a270b1d`）

### 结论

**Request changes，PR #4 保持 Draft，不得合入。**

本轮结论仅绑定
`a270b1d8dcc3f17f8a5dd2e716af8acb68ac304a`。相对第六轮
`76a4523b2c91cb10249f968ed44795bb57656180` 仅增加实现提交
`cf49eb7` 和测试提交 `a270b1d`，没有设计文件修改。第六轮三个 Important
均已独立复现关闭，157 项测试、六轮历史回归和全部既有门禁通过，远端精确
HEAD CI 也为 SUCCESS。

但相邻 JSON 出口扫描发现一个新的 Important：统一入口
`harness.py validate --format json` 的 exit-1 校验结果不经过本轮改成
ASCII-safe 的 `emit` / `emit_command_error`，仍直接调用 v0
`validate.render_json(ensure_ascii=False)`。校验结果 path/message 含 POSIX
`surrogateescape` 字符时，stdout 会写出裸 `0xff`，不能严格按 UTF-8
解码，也不能作为 UTF-8 JSON 消费。这违反 §7.1“JSON 输出始终合法 UTF-8”。

同时，§7.4 要求统一入口正常校验结果与独立 `validate.py` 逐字节一致，而
独立 renderer 在同一边界也会输出非法 UTF-8。因此“本轮无需设计提交”的判断
只对第六轮三个直接 finding 成立，不能覆盖新发现的契约冲突；设计方必须先
裁定这一边界，不能由实现方静默选择优先级。

### 六维评分

| 维度 | 得分 | 独立裁定 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 三项指定整改已完成，但统一 validate 仍违反全局合法 UTF-8 要求。 |
| B. 事实准确性 | 2/4 | “全部字符串字段严格 UTF-8”不涵盖 exit-1 validation result。 |
| C. 通用性 | 3/4 | init 路径与 JSON envelope 已跨平台收口；POSIX 非 UTF-8 文件名仍会破坏统一入口。 |
| D. 可维护性 | 3/4 | target 三态和单一绝对缓存清晰；JSON 存在两个渲染边界且契约不同步。 |
| E. 验证充分性 | 2/4 | 157 项与 13 个 red-first 成立，但 surrogate 测试只覆盖 `emit*`，漏掉 `cmd_validate`。 |
| F. 可追溯性 | 4/4 | 分支、Draft PR、精确 HEAD CI、提交顺序和本记录均可追溯。 |

**总分：16/24。** A、B、E 未达到合入门槛。

### 第六轮 findings 逐项关闭

| 第六轮 finding | 第七轮独立证据 | 状态 |
| --- | --- | --- |
| target 检查吞掉 I/O 错误 | 真实自环 symlink 在 Text/JSON 均 exit 2 / `INIT_IO_ERROR`、`target=null`、零复制；missing/普通文件仍 exit 1；目标 `stat` 与 leaf `lstat` 故障均进入 envelope | 已关闭 |
| 失败响应未复用绝对 target | 相对 `--target` 下独立注入 copy、stamp、ProjectionIOError、exit-1、final validate I/O、final invalid，并验证 success 与外指 leaf symlink；全部 post-resolve target、INIT error path、cleanup hint 使用同一 `parent.resolve()/.harness`，leaf 未跟随 | 已关闭 |
| command envelope 可输出非法 UTF-8 | 对 `emit` / `emit_command_error` 分别注入 path/message `\udcff`，原始 stdout 可严格 UTF-8 解码并 `json.loads()`，且只含 ASCII 字节 | 已关闭，但发现相邻 `cmd_validate` 出口 |

本轮新增的 17 项测试连同修改后的 R5 resolve 测试在第六轮实现上重新执行：
12 项新测试失败/报错，修改后的 R5 测试另有 1 项失败，共 **13 项 red-first**；
在本轮实现上全部通过。该主张已独立证实。

### Standards findings

#### Important — `cmd_validate` exit-1 JSON 仍可能输出非法 UTF-8

位置：

- `template/.harness/bin/harness.py:307-340`
- `template/.harness/bin/validate.py:123-130`

`cmd_validate` 成功取得 `ValidationResult` 后直接调用
`validate.render_json()`；后者保持 `ensure_ascii=False`。这条路径绕过本轮
修改的两个 renderer。用等价于 POSIX 非 UTF-8 Change Record 目录名的
`ContractError.path="changes/bad\udcff/summary.md"` 驱动真实
`cmd_validate`，并通过 `TextIOWrapper(errors="surrogateescape")` 捕获底层
字节：

```text
DECODE_ERROR 'utf-8' codec can't decode byte 0xff in position 94
CMD_VALIDATE_SURROGATE rc=1 strict_utf8=False json=False raw_ff=True bytes=216
```

这是可返回的契约校验失败，不是 argv 解析错误或运行时读取异常，因此不会被
`emit_command_error` 捕获。现有 R6 JSON 测试只覆盖 init 的两个 renderer，
无法发现该分支。

最低整改：先由设计方裁定 §7.1 合法 UTF-8 与 §7.4/v0 字节一致性在
surrogate validation result 上的优先级；随后建立单一安全 JSON 出口。测试
必须从 `cmd_validate` 驱动 exit-1 `ValidationResult`，捕获原始 stdout，
严格 `decode("utf-8")` 后再 `json.loads()`，同时覆盖 surrogate path 与
message。不得只测试 `json.dumps()` 返回的 Python 字符串。

### Spec findings

#### Important — §7.1 与 §7.4 在 surrogate 校验结果上存在未裁定冲突

- `docs/design/harness-v1.md:159` 要求所有 JSON 输出始终是合法 UTF-8。
- `docs/design/harness-v1.md:202-204` 要求统一入口的正常校验结果与独立
  `validate.py` 逐字节一致，并保持独立 v0 行为。
- v0 `validate.render_json(ensure_ascii=False)` 对含 surrogate 的
  `ValidationResult` 本身不能产生合法 UTF-8 字节流。

因此不能同时无条件满足“同一结果逐字节一致”“独立 v0 输出不变”和“统一
入口始终合法 UTF-8”。本轮无设计提交并非完全成立：第六轮三个 finding 无需
改设计，但这个相邻边界需要设计所有者明确选择，例如：

1. 将无效 UTF-8 JSON 视为 v0 缺陷，批准独立与统一 renderer 同步加固，并
   明确兼容性只保护原本可编码的结果；或
2. 仅加固统一入口，并明确 surrogate 边界是 §7.4 字节一致性的例外。

不得通过放宽 §7.1、忽略该输入或让 stdout 继续依赖
`surrogateescape` 解决。

本轮两提交仅修改 `harness.py` 与 `test_harness_cli.py`，未发现其他 scope
creep。`stat/lstat` 三态、安全父目录缓存、八类 post-resolve 响应与
ASCII-safe command envelope 均符合既有 §7.1–§7.2。

### 六轮历史探针与验证证据

六轮 SHORT / ZERO / MID / REPLACE / CLOSE_AFTER / PRECLOSE_FAULT /
SOURCE_MANIFEST_REREAD / FINAL_VALIDATE_IO / ADAPT_MANIFEST_REREAD /
INIT_EXIT1_PROGRESS / SOURCE_VALIDATE_OSERROR / ADAPT_VALIDATE_OSERROR /
copytree / stamp / unreadable projection / target symlink / parent symlink /
目录 / FIFO / END suffix / CRLF / Cursor broken marker / dangling `.harness` /
adapter controls / parser newline / argv `0xff` / invalid UTF-8 / resolve /
written-vs-unchanged 探针均通过；原文件保全、失败原子性、准确进度和只读语义
无回退。

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.
exit 0

$ python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit 0（当前有效 bundle 与独立命令逐字节一致）

$ python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit 0

$ python3 -m unittest discover -s tests -v
Ran 157 tests in 9.018s
OK

$ git diff --check
无输出，exit 0

$ git diff --check fff9650...a270b1d
无输出，exit 0
```

其他门禁：

- v0 schema v1：旧 validator、当前 `validate.py`、当前 `harness.py validate`
  在正常 Text/JSON 夹具下 stdout/stderr 逐字节一致。
- 三条只读命令前后 bundle 指纹均为
  `b90c8eef7fc1d2c2db13c2821bd10a7b616d03e7ea28d1e5e7467ce948c91511`。
- Python 3.9 grammar：两个 CLI 文件均通过。
- E2E init / adapt check：均 exit 0，CRLF 用户前缀逐字节保留，三个投影存在。
- 禁用 token、日期、网络访问与第三方依赖扫描无发现。
- `tests/test_validate.py` 相对 v0 仍恰好只有获批三处样例事实修正。
- feature 审阅检出干净，HEAD 仍为
  `a270b1d8dcc3f17f8a5dd2e716af8acb68ac304a`。
- `origin/feature/harness-v1` 精确匹配该 HEAD；PR #4 为 OPEN / Draft /
  MERGEABLE / CLEAN。
- GitHub Actions `Validate Harness` run `30068116586` 绑定该 HEAD，
  conclusion `SUCCESS`。绿色 CI 未覆盖上述 surrogate validation-result
  边界，不能覆盖静态与独立字节探针阻断。

### 第七轮合入建议

**不得合入 `a270b1d8dcc3f17f8a5dd2e716af8acb68ac304a`；PR #4 保持 Draft。**

下一轮必须先由设计提交明确 surrogate 校验结果下的合法 UTF-8 与 v0/统一入口
兼容关系，再以独立实现提交和真实原始字节测试关闭 `cmd_validate` 出口。新
HEAD 必须重新执行七轮全部探针、157 项以上测试和既有门禁，并提供绑定新
HEAD 的远端 CI。本记录不批准任何后续提交。
