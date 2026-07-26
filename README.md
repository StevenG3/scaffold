# Scaffold — 通用 AI Coding Harness

本仓库用于沉淀并维护一套**通用的 Harness Engineering 脚手架**：围绕 AI Coding Agent，提供可复用的约束机制、反馈回路、工作流编排与持续改进闭环，让 Agent 在真实工程中稳定、可审计地交付代码。

## 背景

AI Coding 正从 Prompt Engineering、Context Engineering 走向 **Harness Engineering**。模型能力已足够强，但在企业级存量代码库中，「能写代码」与「可信赖地交付」之间仍有鸿沟——业务隐性知识未系统化、质量门禁不可机械化执行、跨会话缺少结构化流程。

本项目的目标，是把行业实践（尤其是 Anthropic / OpenAI 的 Harness 思路，以及公开实践文章中的经验归纳）沉淀为一套**可复制、可演进、与具体业务解耦**的通用 Harness。

## 本仓库做什么

- 提供通用 Harness 的目录结构、Agent 角色、Rules / Skills / Changes 约定与流程模板
- 用 Git 版本化管理上述资产，便于团队复用与持续迭代
- 将设计参考与演进决策留在仓库内，保证「发现一次 Agent 错误 → 工程化消除同类错误」可追溯

> 分发包契约由 v0 奠基，v1 已扩展至 Manifest Schema v2 与自安装 CLI（见下文「设计与决策」）；后续演进（v2 分层等）按公开规划与真实接入反馈推进。

## 参考资料

- [Harness Engineering 阅读摘要](docs/reference/Harness-Engineering.md) — 本仓库维护者撰写的阅读摘要（转述与归纳），附原文链接；**不含**第三方文章全文
- 原文：[微信公众平台](https://mp.weixin.qq.com/s?__biz=MzIzOTU0NTQ0MA==&mid=2247559842&idx=1&sn=71ee08bf0421ad2f1aa4dd7a58901c5f)（版权归原权利方）

## 第三方内容与许可

- 仓库内 `docs/reference/` 下对外部文章仅保留**摘要与链接**，不进行全文再分发。
- 本仓库自身代码与文档以 **MIT 许可证**开源（见 [LICENSE](LICENSE)）；该许可证**不**授予对第三方原文全文的转载或再分发权利。

## 状态

Harness v1 已交付并合入：自安装单文件 CLI（`init` / `adapt` / `validate`）、Manifest Schema v2、平台投影（CLAUDE.md 与 AGENTS.md 以受管区块更新，区块外的用户内容逐字节保留；Cursor 规则文件 `.cursor/rules/harness.mdc` 由工具整文件生成并拥有，每次投影整体重建）、带定制记录的 harness-bootstrap Skill，以及 169 个测试与配套 CI 门禁；[不变式闭包设计法](docs/process/invariant-closure-design.md)（docs/process/）已作为正式流程生效，v2 分层能力的规划（[docs/design/harness-v2-planning.md](docs/design/harness-v2-planning.md)）以真实使用反馈为准入门槛，反馈到位后再启动。

## 设计与决策

- [Harness v0 设计规格](docs/design/harness-v0.md)
- [ADR-0001：可移植 Harness 契约](docs/adr/0001-portable-harness-contract.md)
- [Harness v0 实施计划](docs/plans/harness-v0-implementation.md)
- [Harness v1 设计规格](docs/design/harness-v1.md)
- [ADR-0002：实例化与适配投影](docs/adr/0002-instantiation-and-adapter-projection.md)
- [Harness v1 实施计划](docs/plans/harness-v1-implementation.md)

审阅记录（「发现一次 Agent 错误 → 工程化消除同类错误」的可追溯依据）：

- [Harness v0 设计审阅](docs/reviews/2026-07-19-harness-v0-design-review.md)
- [Harness v0 实现审阅](docs/reviews/2026-07-19-harness-v0-implementation-review.md) — 六轮 Standards / Spec 双路复审，逐轮记录 P2 边界缺陷与对应回归测试

## 快速验证

运行 `python3 template/.harness/bin/validate.py` 验证分发契约，运行 `python3 -m unittest discover -s tests -v` 执行完整测试。向目标项目实例化 Harness 只需一条命令：`python3 template/.harness/bin/harness.py init --target <目标项目>`（自安装 + 平台投影 + 校验；随后在目标项目中运行 harness-bootstrap Skill 完成定制）。分发包要求 Python 3.9 或更高版本。

## License

MIT（见 [LICENSE](LICENSE)；第三方内容例外见上文「第三方内容与许可」）。
