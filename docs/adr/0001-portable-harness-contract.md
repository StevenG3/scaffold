# ADR-0001：可移植 Harness 契约

- 状态：Accepted
- 日期：2026-07-19
- 关联设计：[Harness v0 设计规格](../design/harness-v0.md)

## Context

本仓库需要让 Harness 能直接落地到不同语言、框架和组织方式的项目。早期方案把校验脚本放在目标项目根目录、把 Application Owner 固化为单一字段、依赖固定英文 Markdown 标题，并计划把 scaffold 自身的 Change 历史放进待复制目录。这些做法会把生产者的结构和历史强加给消费者。

同时，只有文档而没有机械校验无法形成有效质量门禁；一次性实现完整流水线又会在缺乏使用反馈时过早固化设计。

## Decision

### 1. 使用单目录可移植分发包

所有目标项目运行资产放在 `template/.harness/` 内。目标项目只需复制该目录。测试、CI、设计、ADR、计划和审阅记录留在 scaffold 仓库，不进入分发包。

### 2. 使用相对 Manifest 和通用 Component 列表

Manifest 中的路径相对自身解析。组件通过 `id`、`kind`、`path` 描述，不提供强制的 Owner 字段，也不把示例 Coordinator 设为 Schema 保留角色。内置类型保持最小，扩展使用 `x-*` 命名空间。

### 3. 使用 Python 标准库参考校验器

分发包包含只使用 Python 3.9 及以上版本标准库的 `bin/validate.py`。它提供确定性 Text/JSON 输出和稳定退出码，不修改目标文件。Python 3.9+ 是 v0 唯一明确的运行前置条件；未来可以在保持 Manifest 契约与输出语义的前提下增加其他语言实现。

### 4. 机械校验结构，不校验自然语言

校验器验证 Manifest、路径安全、文件存在性、最小 Skill frontmatter 和 Change 文件集合，不依赖 Markdown 标题或正文语言。自然语言质量由项目规则和 Reviewer 判断。

## Consequences

正面影响：

- 分发包可以独立复制，不污染目标项目根目录。
- 目标项目可以替换角色、语言和正文结构。
- 严格字段加 `x-*` 扩展同时提供拼写保护和演进空间。
- 生产者侧审计历史不会泄漏到消费者项目。
- 无第三方包降低首次接入成本。

代价与限制：

- 目标环境必须具备 Python 3.9 或更高版本。
- 最小 frontmatter 检查不等价于完整 YAML 验证。
- v0 不提供安装、合并或升级已有 Harness 的能力。
- 不验证自然语言内容是否高质量或业务正确。

## Alternatives Considered

### 只提供文档

拒绝。无法机械验证结构，Agent 和项目会随时间漂移。

### 把 `.harness/` 直接作为本仓库自身实例

拒绝。复制时会混入 scaffold 的 Change 历史和生产者上下文。

### 固定 Application Owner 和十阶段流程

拒绝。不同项目的角色、交付流程和风险等级差异过大。

### 使用固定 Markdown 标题作为契约

拒绝。对语言、团队文档规范和未来模板调整过于敏感。

### 引入 JSON Schema 或 YAML 第三方库

v0 暂不采用。它们能减少手写校验代码，但会增加目标项目首次运行前的依赖安装步骤。若未来契约复杂度显著提升，应通过新 ADR 重新评估。
