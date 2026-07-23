# ADR-0002：实例化与适配投影

- 状态：Accepted
- 日期：2026-07-23（接受日期同日；实现审阅后修订受管块为字节级语义并补充投影节点安全规则，见关联设计 §8.1 / §8.3）
- 关联设计：[Harness v1 设计规格](../design/harness-v1.md)
- 前置决策：[ADR-0001：可移植 Harness 契约](0001-portable-harness-contract.md)

## Context

v0 的接入方式是手动复制目录，无定制支撑、无平台接入。项目愿景是开源的跨项目 Harness 模板化工具，完整蓝图为三步：接入体验 → 分层模板 → 演进同步。各 Agent 平台入口约定互不相同（Claude Code：`CLAUDE.md` / `.claude/`；Codex：`AGENTS.md`；Cursor：`.cursor/rules/`），而 `.harness/` 是平台中立约定，两者之间存在接入鸿沟。

同时，定制一个项目专属 Harness 需要理解代码库与业务——这超出机械工具能力；而完全交给 Agent 自由发挥又不可重复、不可审计。目标用户（开源社区）中很多人并不清楚自己需要什么样的 Harness 配置。

## Decision

### 1. 中立核心 + 适配投影

`.harness/` 保持平台中立的单一事实源。工具按 Manifest `adapters` 声明生成各平台投影文件（`CLAUDE.md`、`AGENTS.md`、`.cursor/rules/harness.mdc`），投影只做索引与指路，不复制组件正文。

### 2. 受管块写入策略

投影文件中工具只拥有一对标记之间的受管块：无文件则创建、有文件无标记则末尾追加、有标记则只替换块内、标记破损则报错拒改。用户内容在任何操作下逐字节保留。

### 3. 自安装单文件 CLI

新增 `bin/harness.py`（Python 3.9+ 标准库、单文件、随分发包分发），子命令 `init` / `adapt` / `validate`。`init` 将 CLI 所在的 `.harness/` 自身复制到目标项目，因此接入后的项目无需 scaffold 仓库即可继续运行全部命令。`validate.py` 独立命令契约不变，`harness.py validate` 复用其实现。

### 4. Schema v2：超集演进 + origin 锚点

`schema_version: 2` 为 v1 严格超集，新增可选 `template_version`、`adapters`、`origin`。校验器同时接受 1 与 2。`origin` 由 `init` 写入接入副本，记录模板名称与版本，为未来升级（v3）预留锚点；v1 中它唯一被读取的场景是区分模板本体（`origin: null`，`adapt` 不生成投影）与接入副本。

### 5. 机械与智能分工：CLI + bootstrap Skill

CLI 只做确定性操作（复制、写 origin、投影、校验）。项目定制由分发包内置的 `harness-bootstrap` Skill 引导 Agent 完成，且访谈格式为硬性规范：先侦察代码库、能自答的不许问用户；一次一问；每题 2–4 个枚举选项；必须标注推荐项与基于证据的理由；必须写明各选项代价；全程选推荐项须能得到自洽可用的 Harness。bootstrap 过程本身走 Change Record 留痕。

## Consequences

正面影响：

- 一套 `.harness/` 同时服务多个 Agent 平台，无供应商绑定；投影可随时重建，事实源唯一。
- 受管块使工具可以安全进入已有 `CLAUDE.md` / `AGENTS.md` 的存量项目。
- 自安装设计让接入项目脱离 scaffold 仓库独立存活，符合 ADR-0001 的自包含原则。
- 超集式 Schema 演进保护 v0 存量：旧 Manifest 与旧校验命令均不破坏。
- 侦察优先 + 选项/推荐/代价的访谈规范，把「用户不知道自己要什么」变成可走默认路径的引导过程。

代价与限制：

- 适配层需随各平台约定演变而维护；内置适配器每增一个都是长期承诺，故 v1 仅收录三个，其余走 `x-*` 扩展。
- 受管块无法阻止用户手工编辑块内内容导致的漂移，只能靠 `adapt --check` 在 CI 中拦截。
- 访谈质量属自然语言行为，校验器不背书（沿 ADR-0001 第 4 条），靠 Skill 内嵌模板、正反示例与 Change Record 审计约束。
- `origin` 只是锚点；真正的升级/合并语义推迟到 v3，届时可能需要新的决策。

## Alternatives Considered

### 只押注 Claude Code 原生机制

拒绝。集成最深但单平台绑定，与开源通用定位冲突。

### 纯中立、不做适配层

拒绝。接入体验差，等于把适配成本转嫁给每个接入项目。

### Go / Rust 单二进制或 Node CLI

拒绝（v1）。单二进制需重写或双维护校验逻辑；Node 引入运行时依赖。Python 3.9+ 已是 ADR-0001 确立的唯一运行前置，沿用之。若未来分发体验成为主要摩擦，可另立 ADR 评估。

### CLI 内置交互问答完成定制

拒绝。机械问答只能填浅层变量，写不出有价值的项目规则；理解代码库是 Agent 的比较优势。

### 定制全交 Agent、不提供 CLI

拒绝。复制、投影、校验是确定性操作，交给 Agent 不可重复、不可审计，违背 v0 已确立的机械化门禁原则。

### 投影采用符号链接或整文件覆盖

拒绝。符号链接跨平台行为不一致且多数 Agent 平台按普通文件读取；整文件覆盖会摧毁存量项目的已有用户内容。
