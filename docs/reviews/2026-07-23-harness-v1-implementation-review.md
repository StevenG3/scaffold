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
