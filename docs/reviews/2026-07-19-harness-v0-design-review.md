# Harness v0 设计与实施计划审阅

- 审阅日期：2026-07-19
- 审阅范围：`origin/main...codex/harness-v0-design`
- 固定点：`a003853ce364c8ecfbaf4fa4af1889d99225f512`
- 最终审阅提交：`30634dc`
- 审阅角色：规划者之外的 Standards Reviewer 与 Spec Reviewer
- 结论：Approve，允许合入

## 审阅依据

- 仓库 README 所声明的通用 AI Coding Harness 目标。
- `docs/design/harness-v0.md` 中已批准的 Portable Harness v0 设计。
- `docs/adr/0001-portable-harness-contract.md` 中的可移植契约决策。
- 用户批准的范围：先头脑风暴、设计保持通用、设计可追溯、开发由外部 Grok 4.5 执行、Codex 负责规划/审阅/合入。

## 第一轮结论

第一轮独立审阅为 Request changes，共发现四项意见，其中路径问题被两路审阅同时识别：

1. POSIX 路径设计未明确拒绝反斜杠和 Windows 盘符前缀，也缺少稳定错误映射与跨平台负例。
2. Change Template 与实际 Change Record 的测试没有覆盖空文件、目录冒充文件和符号链接逃逸。
3. 只读验证只哈希普通文件，不能证明目录、空目录、节点类型与符号链接目标未发生变化。

## 修订

提交 `30634dc` 完成以下修订：

- 设计、ADR 与计划统一规定反斜杠及 Windows 盘符前缀非法。
- 增加稳定错误码 `PATH_SYNTAX_INVALID`，并要求 POSIX/Windows 错误映射一致。
- 为 Change Template 和实际记录补充空文件、错误节点类型、符号链接逃逸测试。
- 将普通文件内容哈希升级为完整文件树指纹，覆盖相对路径、空目录、节点类型、符号链接目标和普通文件内容。

## 第二轮门禁

- Standards Review：0 findings，Approve。
- Spec Review：0 findings，Approve。
- `git diff --check origin/main...HEAD`：通过。
- 工作区范围：仅包含本设计、ADR、实施计划及本审阅记录，不包含实现代码或分发资产。

## 合入意见

本分支满足当前“设计与实施计划”交付范围。契约保持项目无关、工具无关和领域无关，且通过自包含分发目录、Manifest 相对路径、扩展命名空间、标准库校验器与生产者/消费者资产分离保证可移植性。

允许合入 `main`。后续由开发者按照 `docs/plans/harness-v0-implementation.md` 实施；实现 PR 必须重新经过独立 Standards / Spec 审阅与完整测试，不得沿用本次文档审阅结论替代实现验收。
