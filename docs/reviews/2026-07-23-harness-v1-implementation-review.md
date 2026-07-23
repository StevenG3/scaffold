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
