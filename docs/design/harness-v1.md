# Harness v1 设计规格 — 接入体验纵切片

- 状态：Approved
- 起草日期：2026-07-23
- 批准日期：2026-07-23（含审阅整改修订：§7.1 错误渲染、§7.2 缓存排除、§8.1 字节级语义、§8.3 节点安全）
- 目标版本：Schema v2
- 对应决策：[ADR-0002：实例化与适配投影](../adr/0002-instantiation-and-adapter-projection.md)
- 前置版本：[Harness v0 设计规格](harness-v0.md)、[ADR-0001](../adr/0001-portable-harness-contract.md)

## 1. 背景

v0 交付了可移植分发包 `template/.harness/` 与契约校验器，但接入方式仍是「手动复制目录」，且复制后如何定制成项目专属 Harness 没有任何机械支撑。本仓库的长期愿景是**开源的跨项目 Harness 模板化工具**，完整蓝图分三步：

1. **接入体验**：新项目低成本实例化并定制（本设计，v1）。
2. **分层模板**：通用层 / 技术栈层 / 项目层可组合（未来 v2，依赖 v1 的真实接入反馈）。
3. **演进同步**：模板升级回流到已接入项目、项目资产回流上游（未来 v3，依赖存量接入项目）。

v1 只做第一步，但在契约中为后两步预留锚点（`origin` 元数据），不预实现其逻辑。

## 2. 头脑风暴结论

与用户对齐的关键意图决策：

- **目标用户**：开源社区，通用性、文档、兼容性按最高标准。
- **平台策略**：`.harness/` 保持平台中立作为单一事实源；工具生成各 Agent 平台（Claude Code、Codex、Cursor）的**适配投影**。拒绝了「只押注单平台」（绑定风险）与「纯中立不适配」（接入体验差）。
- **实现语言**：Python 3.9+ 标准库，延续 v0 校验器路线，零第三方依赖。拒绝了 Go/Rust 单二进制（需重写校验器、双实现维护）与 Node/TS（引入运行时依赖）。
- **实例化分工**：CLI 只做确定性机械操作（复制、投影、校验）；定制环节由内置 bootstrap Skill 引导 Agent 完成。拒绝了「CLI 内置问答向导」（只能浅层定制）与「全交给 Agent」（不可重复、不可审计）。
- **好用性硬要求**：bootstrap 引导问答必须「先侦察后提问、每题带选项、标注推荐与理由、写明各选项代价」，让不清楚自己需要什么的用户全程选推荐项也能得到合理的 Harness。
- **路线切法**：先做接入体验纵切片（方案 A），拒绝了先做分层（在零接入反馈下过早固化合并语义）与先做升级（无服务对象）。

## 3. 目标

v1 必须满足以下结果：

- 一个新项目从拿到 scaffold 到拥有已定制、已校验、已接入所在 Agent 平台的 `.harness/`，全程有机械工具与 Skill 支撑，无需照文章手工搭建。
- 单文件 CLI `bin/harness.py` 提供 `init`、`adapt`、`validate` 三个子命令，随分发包一起分发，自身零第三方依赖。
- `init` 将分发包自安装到目标项目，写入 `origin` 来源元数据，并自动完成首次投影与校验。
- `adapt` 以**受管块**方式生成或更新平台投影文件，幂等、确定性、不破坏用户已有内容，并提供 `--check` 模式供 CI 检测投影过期。
- `harness-bootstrap` Skill 引导 Agent 完成项目定制，问答格式满足好用性硬要求。
- Manifest 升级到 Schema v2（v1 的严格超集），校验器同时接受 v1 与 v2；v0 的 `validate.py` 命令契约（输出格式、退出码）保持不变。
- 分发包保持自包含、平台中立、不含 scaffold 生产者历史。

## 4. 非目标

v1 不实现以下内容：

- `upgrade` 子命令、模板与项目间任何形式的合并或同步（v3 范围；v1 只写入 `origin` 锚点）。
- 分层模板、技术栈层内容、层合并语义（v2 范围）。
- 通过网络下载模板（v1 的 `init` 从本地 scaffold 副本运行）。
- pip / npx / Homebrew 等包管理分发（v1 以 git clone / 下载压缩包获取）。
- 除 Claude Code、Codex、Cursor 之外的内置适配器（扩展交给 `x-*` 命名空间）。
- 由 CLI 生成任何自然语言内容（项目规则、Wiki 正文均由 Agent 在 bootstrap 中产出）。
- 多 Agent 调度、流水线编排、MCP 集成（沿用 v0 非目标）。
- 修改 v0 已固定的 `validate.py` 独立命令契约。

## 5. 分层架构

### 5.1 分发包增量

```text
template/.harness/
├── manifest.json              # 升级到 schema_version 2
├── README.md                  # 更新：加入 CLI 与 bootstrap 使用说明
├── agents/coordinator.md      # 不变
├── rules/delivery.md          # 不变
├── skills/
│   ├── change-delivery/SKILL.md      # 不变
│   └── harness-bootstrap/SKILL.md    # 新增：定制引导 Skill
├── templates/change/          # 不变
├── changes/                   # 不变
├── wiki/
│   └── README.md              # 新增：项目知识落点（占位说明，非机器契约）
└── bin/
    ├── validate.py            # 保留：v0 契约不变，内部升级支持 schema v2
    └── harness.py             # 新增：单文件 CLI（init / adapt / validate）
```

要点：

- `harness.py` 与 `validate.py` 同处 `bin/`，随分发包分发。`harness.py validate` 直接 `import` 复用 `validate.py` 的校验逻辑，不复制实现。
- `wiki/` 仅是约定目录加说明文件，不进入 Manifest 机器契约；bootstrap Skill 将项目知识写入其中。
- 分发包内不出现 scaffold 专属名称、日期与历史（沿用 v0 验收标准）。

### 5.2 生产者侧增量

```text
docs/design/harness-v1.md                                # 本设计
docs/adr/0002-instantiation-and-adapter-projection.md    # 本轮决策
docs/plans/harness-v1-implementation.md                  # 待撰写的实施计划
tests/test_harness_cli.py                                # 新增：CLI 行为测试
tests/test_adapters.py                                   # 新增：投影生成测试
tests/test_validate.py                                   # 扩展：schema v2 用例
tests/test_template_contract.py                          # 扩展：新增文件契约
```

## 6. Manifest Schema v2

### 6.1 设计原则

v2 是 v1 的**严格超集**：v1 合法的 Manifest 在 v2 语义下仍然合法（除 `schema_version` 数值本身）。校验器同时接受 `schema_version` 为 `1` 或 `2`；`1` 按 v0 规则校验，新增字段仅在 `2` 下合法。

### 6.2 v2 示例

```json
{
  "schema_version": 2,
  "template_version": "1.0.0",
  "entrypoint": "README.md",
  "components": [
    { "id": "coordinator", "kind": "agent", "path": "agents/coordinator.md" },
    { "id": "delivery-rule", "kind": "rule", "path": "rules/delivery.md" },
    { "id": "change-delivery", "kind": "skill", "path": "skills/change-delivery/SKILL.md" },
    { "id": "harness-bootstrap", "kind": "skill", "path": "skills/harness-bootstrap/SKILL.md" }
  ],
  "change_management": {
    "template": "templates/change",
    "records": "changes",
    "required_files": ["summary.md", "spec.md", "tasks.md"]
  },
  "adapters": ["claude-code", "codex", "cursor"],
  "origin": null
}
```

### 6.3 新增字段规则

- `template_version`：可选字符串；出现时必须匹配语义化版本 `X.Y.Z`（三段非负整数，不带前缀）。模板仓库中维护，供 `init` 复制到 `origin`。
- `adapters`：可选数组；成员为非空字符串且不得重复。内置值为 `claude-code`、`codex`、`cursor`；其他值必须以 `x-` 开头。缺省视为空数组（`adapt` 无事可做并明确提示）。
- `origin`：可选；值为 `null` 或对象。模板仓库中保持 `null`；`init` 在目标项目副本中写入对象：

```json
"origin": {
  "template_name": "scaffold-harness",
  "template_version": "1.0.0",
  "initialized_at_schema": 2
}
```

  - `origin.template_name`：必填非空字符串。
  - `origin.template_version`：必填，规则同 `template_version`。
  - `origin.initialized_at_schema`：必填整数，记录初始化时的 schema 版本。
  - `origin` 对象内未定义字段仅允许 `x-*`。
- v2 下顶层未定义字段的处理规则与 v0 相同：仅允许 `x-*`。
- `origin` 是为 v3 升级预留的锚点，校验器只验证其结构。v1 中它唯一的读取场景：`adapt` 以 `origin` 是否为 `null` 区分模板本体与已接入副本（见 7.3 与第 13 节）。

## 7. CLI 契约：`bin/harness.py`

### 7.1 总体约定

- 单文件、Python 3.9+ 标准库、无第三方依赖；`python3 bin/harness.py <subcommand>` 方式调用。
- 全部子命令支持 `--format text|json`（默认 `text`），输出与退出码语义与 v0 校验器对齐：
  - `0`：成功。
  - `1`：契约或状态违规（校验失败、投影过期、目标已存在等可预期失败）。
  - `2`：命令参数错误、路径不可访问或工具自身非预期错误。
- Text 错误格式沿用 `[CODE] path: message`；JSON 输出固定包含 `ok`（布尔）、`command`、`errors`（数组，元素含 `code`、`path`、`message`）、`notices`（数组，结构同 `errors`，承载不构成失败的提示，如 `ADAPTER_EXTERNAL`、`ADAPT_SKIPPED_TEMPLATE`）与各子命令附加字段。
- 所有子命令确定性输出：相同输入产生逐字节相同的输出与文件产物（不写时间戳、随机值、绝对路径进产物）。
- 命令级错误（退出码 `2`，发生在参数解析成功之后）同样遵守 `--format`：`json` 下向 stdout 输出完整 envelope（`ok: false`、`command`、`errors`、`notices` 及该子命令的附加字段）后以 `2` 退出；`text` 下向 stderr 输出 `[CODE] path: message` 行。本条覆盖两类：可预期参数/环境错误（非法 `--adapters` 成员 `ARGUMENT_INVALID`、根目录不可读 `ROOT_UNREADABLE`），以及节点安全核验通过后仍发生的运行时 I/O 故障（读取失败、写入/替换失败，code `PROJECTION_IO_ERROR`）——后者归类退出 `2` 但不得逃逸到裸 `INTERNAL_ERROR` 文本。节点布局类契约错误（§8.3）始终是退出 `1`，不得混入本类。命令级错误的 Text 渲染必须与 `emit` 相同地对 code/path/message 做控制字符转义（覆盖 C0、DEL、NEL、U+2028、U+2029），保证一个错误恰占一个物理行。参数解析本身失败（未知子命令、未知选项，此时 `--format` 不可知）仍走 stderr 文本，且同样经上述转义——解析器错误消息中由输入注入的控制字符不得拆行。
- **JSON 输出必须始终是合法 UTF-8**。POSIX 下 argv 经 `surrogateescape` 可能携带无法编码为 UTF-8 的代理字符：任何 argv 值含此类字节时，在进入子命令逻辑前稳定拒绝——报 `ARGUMENT_INVALID`、退出 `2`、经转义的单行 stderr 文本（该场景不产生 JSON envelope：非法字节使 envelope 本身无法成为合法 UTF-8）。
- **错误 envelope 必须如实报告进度**：`adapt` / `init` 不是跨文件事务；失败发生时，envelope 的 `written` / `projected_files` 必须列出截至失败点已实际提交到磁盘的投影文件，不得报告空列表。`validate.py` 独立命令保持其既有行为不变；`harness.py validate` 的正常校验输出仍与 `validate.py` 逐字节一致，仅命令级错误路径按本条统一渲染。

### 7.2 `init` — 自安装到目标项目

```bash
python3 <scaffold>/template/.harness/bin/harness.py init --target <project-dir> \
  [--adapters claude-code,codex] [--format text|json]
```

行为（按序）：

1. 源目录 = `harness.py` 所在 `bin/` 的父目录（即所在 `.harness/`）。先对源目录运行完整校验，失败则退出 `1`（不复制损坏模板）。
2. `--target` 必须是已存在的目录；`<target>/.harness` 这一目录项**只要存在即拒绝**（以 `lstat`/`lexists` 判定：普通文件、目录、符号链接——包括悬空符号链接——一律计为已存在），报 `INIT_TARGET_EXISTS`、退出 `1`，且不得进入复制流程（v1 无升级能力，绝不覆盖）。不提供 `--force`。
3. 完整复制 `.harness/` 到 `<target>/.harness/`（含 `bin/` 自身，使目标项目可独立运行后续命令）。复制排除的缓存产物为确定清单：`__pycache__`、`*.pyc`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`.DS_Store`。复制阶段与其后 `origin` 写入阶段（步骤 4 的 manifest 读取/写回）的 I/O 失败（`shutil.Error` / `OSError`，如源内坏节点、目标磁盘故障）是命令级错误：报 `INIT_IO_ERROR`、退出 `2`、按 §7.1 规则渲染（json 下输出完整 init envelope）；若目标 `.harness/` 已被（部分）创建，必须附带 `INIT_CLEANUP_HINT` notice 指明清理路径。
4. 在目标副本的 `manifest.json` 中写入 `origin` 对象（来源名称与 `template_version`）；若给出 `--adapters` 则覆盖 `adapters` 数组（成员校验同 6.3）。这是 `init` 唯一允许修改的被复制文件。
5. 对目标副本执行 `adapt`（见 7.3）。
6. 对目标副本执行校验；成功后输出下一步指引（运行 bootstrap Skill 的提示）。任何步骤失败即停止并报告，已复制内容保留供用户检查，同时明确提示清理方式。

JSON 附加字段：`target`（目标 `.harness/` 的规范化绝对路径）、`projected_files`（本次生成的投影文件相对目标项目根的路径列表）。

### 7.3 `adapt` — 生成/更新平台投影

```bash
python3 .harness/bin/harness.py adapt [--root <harness-dir>] [--check] [--format text|json]
```

- 无 `--root` 时以 `harness.py` 所在目录的父目录为 Harness 根；投影文件写入 Harness 根的**父目录**（即项目根）。
- 当 Manifest `origin` 为 `null`（模板本体，尚未接入任何项目）时，`adapt` 与 `adapt --check` 输出提示并以 `0` 退出，不生成也不检查投影——模板仓库自身不是被接入项目，不应出现投影文件。
- 读取 Manifest `adapters` 数组，对每个内置适配器生成对应投影（见第 8 节）；`x-*` 适配器不内置实现，逐个输出提示（code `ADAPTER_EXTERNAL`）且不视为错误。
- `--check`：不写任何文件；若任一投影文件缺失或其受管块内容与期望不一致，列出差异文件并退出 `1`。供 CI 与 `validate` 之外的门禁使用。
- 幂等：连续两次 `adapt` 的第二次必须零改动。

JSON 附加字段：`written`（本次实际写入的文件列表）、`unchanged`、`stale`（仅 `--check` 下）。

### 7.4 `validate` — 契约校验

```bash
python3 .harness/bin/harness.py validate [--root <harness-dir>] [--format text|json]
```

- 语义与 `validate.py` 完全一致（内部复用其实现），仅作为统一入口提供。
- `validate.py` 作为独立命令继续存在且契约不变；文档以 `harness.py validate` 为推荐入口。

## 8. 适配投影机制

### 8.1 受管块（managed block）

每个投影文件中，工具只拥有一段由标记包围的**受管块**，块外内容完全属于用户：

```markdown
<!-- BEGIN HARNESS MANAGED BLOCK (harness adapt) -->
…由工具生成的内容，禁止手工编辑，重跑 adapt 会覆盖…
<!-- END HARNESS MANAGED BLOCK -->
```

规则（**全部在字节层执行**：以二进制读写投影文件，标记为 ASCII 字节串，不做任何换行转换；块外用户字节在任何操作下逐字节保留，包括 CRLF、END 标记后的空行、无末尾换行与非 ASCII 内容）：

- 目标文件不存在或为零字节：写入受管块（工具生成内容统一使用 LF）。
- 目标文件存在但无标记：在文件**末尾追加**——保留原字节序列不动，若末字节非 `\n` 先补一个 `\n`，再加一个空行与受管块；补充的字节属于追加内容，不构成对用户字节的修改。
- 目标文件存在且恰有一对顺序正确的标记：**受管区间** = 从 `BEGIN` 标记首字节起，到 `END` 标记末字节止，再并入紧随其后的一个 `\n`（若存在）。仅以重新渲染的块（含终止 `\n`，若原区间未含终止 `\n` 且位于文件末尾则同样不含）替换该区间；区间外前缀与后缀逐字节原样拼回。该规则保证重复执行逐字节幂等。
- 标记不成对、重复或顺序颠倒（对 `mode: "block"` 与 `mode: "file"` 一视同仁）：报错退出 `1`（code `PROJECTION_MARKER_BROKEN`），拒绝写入，绝不猜测修复。
- 受管块内容由 Manifest 确定性推导：Harness 入口路径、组件清单（id / kind / path）、最小使用指令（读 README → 按任务加载组件 → 变更走 Change Record → 交付前跑 validate）。不复制组件正文，只做索引与指路，保持「单一事实源在 `.harness/`」。

### 8.2 内置适配器

| 适配器 | 投影文件（相对项目根） | 形态 |
| --- | --- | --- |
| `claude-code` | `CLAUDE.md` | 受管块，指向 `.harness/` 入口与组件索引 |
| `codex` | `AGENTS.md` | 同上 |
| `cursor` | `.cursor/rules/harness.mdc` | 整文件生成（Cursor 规则文件为工具专属格式，仍带标记以便 `--check` 与破损检测） |

`mode: "file"`（Cursor）的整文件所有权**不豁免标记完整性检查**：写入或 `--check` 前必须先按 §8.1 检查既有文件的标记；破损即 `PROJECTION_MARKER_BROKEN` / 退出 `1`，不得静默覆盖。标记完好或文件不存在时，才以完整渲染结果比较/覆盖。

三个投影的信息内容一致，仅按平台惯例调整文件位置与头部格式。适配器实现为 `harness.py` 内部的表驱动结构（文件路径 + 渲染函数），新增内置适配器只需注册一项——这是 v2 分层与社区扩展的接缝。

### 8.3 投影目标的节点安全规则

投影写入的信任边界是**项目根目录内的真实文件树**。对每个投影目标路径：

- 从项目根到目标的**每一段路径**都以 `lstat` 检查：任何一段是符号链接即拒绝，报 `PROJECTION_PATH_UNSAFE`、退出 `1`。
- 中间段必须是真实目录；目标本身只允许「不存在」或「普通文件」两种状态。目标为目录、FIFO、设备、socket 等非普通节点时报 `PROJECTION_TARGET_INVALID`、退出 `1`，且**不得读取**该节点（避免在 FIFO 等节点上阻塞）。
- 以上属于可预期契约错误：稳定错误码、一次性收集、退出 `1`；不得落入 `INTERNAL_ERROR` / 退出 `2`。
- `--check` 与写路径执行相同的节点检查，且 `--check` 保持零写入。
- 写入前在同一调用内重新核验目标节点状态（尽力缓解检查-使用竞态；在支持 `O_NOFOLLOW` 的平台以 no-follow 语义打开）。本规则防护的是意外与常见恶意布局，不承诺抵御与写入并发的本地攻击者——该边界记录于此，不再扩大。
- **失败原子性**：正式目标文件在一次完整成功的写入落定之前不得发生任何变化。写入流程为：在目标同目录创建安全的临时普通文件 → 循环写入直至全部字节完成（`os.write` 的短写必须续写，零进展视为失败）→ flush 并 fsync → 重新执行节点安全核验 → 以原子替换（`os.replace`）提交。任一环节失败——**包括文件描述符关闭失败**——：原目标逐字节不变、尽力关闭描述符并清理本次临时文件、该目标不得进入 `written`，错误按 §7.1 以 `PROJECTION_IO_ERROR` 渲染。临时文件属于该目标的声明写集，命名确定性（如 `<name>.harness-tmp`）。
- `init` 复制产生的 `.harness/` 内容来自模板自身，沿用 v0 的 Manifest 路径安全规则（§6.2 / ADR-0001），不受本节约束。

## 9. `harness-bootstrap` Skill

### 9.1 定位

`init` 完成后，项目获得的是**通用**Harness。bootstrap Skill 引导 Agent 把它定制成**项目专属** Harness。产出全部为自然语言资产，由 Agent 生成、用户确认，CLI 不参与。

### 9.2 流程

1. **侦察（先于一切提问）**：Agent 读取项目代码库——技术栈、构建与测试命令、目录结构、既有规范文件（lint 配置、CONTRIBUTING、CI 配置）、既有 Agent 配置（已有的 CLAUDE.md / AGENTS.md 用户内容）。能从代码库确定的事实**禁止**拿去提问。
2. **访谈**：就侦察无法确定、必须由人拍板的决策逐题提问（见 9.3 格式规范）。最少覆盖：项目一句话定位、质量门禁命令（测试/lint/构建中哪些是交付必跑）、变更审批约定、Harness 语言（正文用中文/英文/双语）。
3. **产出**：
   - `rules/` 下新增项目规则文件（如 `rules/project.md`），并注册进 Manifest `components`。
   - `wiki/` 下建立知识骨架：至少「系统概览」「关键约定」两篇的初稿，标注待补充位置。
   - 首条 Change Record：本次 bootstrap 本身按 `change-delivery` Skill 走完整记录，作为项目的第一条审计轨迹与示范。
4. **验证**：运行 `harness.py validate` 与 `harness.py adapt --check`，证据记入该 Change Record 的 `summary.md`。

### 9.3 访谈格式规范（好用性硬要求）

Skill 文本中以「必须遵守」措辞写死以下规则，并附正反示例对照：

- **一次只问一个问题。**
- **每题必须给出 2–4 个枚举选项**；禁止无选项的开放式提问。开放信息（如项目定位一句话）也须先给出 Agent 基于侦察起草的候选供确认或修改。
- **每题必须标注推荐项**并给出基于侦察证据的理由（「我看到你们 CI 里已经跑 `pytest`，推荐将其设为交付门禁」）。
- **每个选项必须写明代价**，不只写好处。
- **允许用户始终选择推荐项**：全程接受默认推荐所得到的 Harness 必须是自洽可用的。
- 反例（写入 Skill 作对照）：「你们的代码规范是什么？」「还有什么要补充的吗？」——凡是把发现成本转嫁给用户的提问都属违规。

### 9.4 机械边界（诚实声明）

访谈质量属自然语言行为，`validate.py` 不校验（沿用 ADR-0001 第 4 条原则）。保障手段为：Skill 内嵌格式模板与正反示例、bootstrap 产物必须走 Change Record 留痕、投影与结构由 CLI 机械把关。

## 10. 数据流

```text
获取 scaffold（git clone / 下载）
→ python3 …/harness.py init --target <项目>     # 机械：复制 + origin + 投影 + 校验
→ Agent 按投影入口发现 .harness/，加载 harness-bootstrap Skill
→ 侦察 → 访谈（选项/推荐/代价）→ 产出项目规则与 Wiki 骨架 → 首条 Change Record
→ python3 .harness/bin/harness.py validate && adapt --check
→ 此后日常交付沿 v0 数据流（README → Manifest → 组件 → Change Record → validate）
```

## 11. 错误处理

- 所有可预期失败（目标已存在、标记破损、投影过期、Manifest 违规）走退出码 `1` 并使用稳定错误码；错误码新增 `INIT_*`、`ADAPTER_*`、`PROJECTION_*` 前缀族，命名与 v0 错误码风格一致，一次性收集、稳定排序。
- `init` 不做部分回滚（保持工具无状态、可预测），失败时保留现场并输出明确的清理指引。
- 任何命令都不得修改受管块之外的用户内容；`init` 之外的命令不得创建 `.harness/` 内文件。

## 12. 测试设计

沿用 v0 的 `unittest` + `tempfile` 零依赖策略。测试矩阵至少覆盖：

1. Schema v2 全字段合法/非法用例（`template_version` 格式、`adapters` 重复与非法名、`origin` 结构），以及 v1 Manifest 继续通过。
2. `init`：成功路径产物完整；源模板损坏拒绝复制；目标已存在拒绝；`origin` 正确写入；`--adapters` 覆盖生效；复制后的目标可独立运行三个子命令（可移植性）。
3. `adapt`：三种投影内容正确；文件不存在/存在无标记/存在有标记三分支；标记破损报错；幂等（二次运行零改动）；`--check` 对缺失与过期的检测；确定性（两次全新生成逐字节一致）。
4. 受管块外用户内容在任何操作下保持逐字节不变（v0 只读性测试的写入版：**声明式写集**——除明确声明的产物文件外，项目文件树指纹不变）。
5. 退出码与 text/JSON 输出稳定性（含错误排序）。
6. `harness.py validate` 与 `validate.py` 对同一夹具输出一致。
7. 分发包契约扩展：新增文件（`harness.py`、bootstrap SKILL、`wiki/README.md`）存在且非空，bootstrap SKILL frontmatter 合规。

## 13. CI 门禁

`validate.yml` 在既有两条命令外追加：

```bash
python3 template/.harness/bin/harness.py validate
python3 template/.harness/bin/harness.py adapt --check --root template/.harness
```

模板 Manifest 的 `adapters` 保持声明（`["claude-code", "codex", "cursor"]`，供接入副本使用），但按 7.3 规则，模板本体（`origin: null`）上的 `adapt --check` 是提示性无操作并以 `0` 退出——CI 借此验证该分支行为，同时保证模板仓库内不出现投影文件。接入副本上的完整投影行为由测试矩阵第 2、3 条在临时目录中覆盖。

## 14. 验收标准

- 在全新临时目录中：`init` → 目标项目获得完整 `.harness/` + 三个投影文件 + `origin` 元数据，`validate` 与 `adapt --check` 均退出 `0`。
- 对已有 `CLAUDE.md`（含用户内容）的项目执行 `init`/`adapt`，用户内容逐字节保留。
- 全部单元测试通过；CI 通过；`git diff --check` 无错误。
- v0 契约回归：既有 `validate.py` 全部测试不修改而继续通过（schema v1 Manifest 仍被接受）。
- 分发包无 scaffold 专属名称、日期、历史；`harness.py` 在 Python 3.9 环境可运行。
- bootstrap SKILL 包含 9.3 全部硬性规则与正反示例。
- 未实现任何第 4 节非目标。

## 15. 可追溯链

```text
docs/design/harness-v1.md
→ docs/adr/0002-instantiation-and-adapter-projection.md
→ docs/plans/harness-v1-implementation.md
→ 实现 PR → docs/reviews/ 审阅记录 → 合入提交
```

## 16. 实施边界

开发者可自由调整 `harness.py` 内部模块划分、渲染函数组织与测试夹具结构。以下变化必须先回到设计/ADR 重新批准：

- 修改子命令名称、参数、退出码语义或 JSON 顶层字段。
- 修改受管块标记文本或三分支处理规则。
- 修改 Schema v2 字段定义或 v1 兼容语义。
- 新增/删除内置适配器。
- 引入第三方运行时依赖或网络访问。
- 让 CLI 生成自然语言定制内容。
- 扩大到第 4 节非目标范围。
