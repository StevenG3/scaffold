# Harness Engineering 阅读摘要

> **性质说明**：本文档是本仓库维护者撰写的**阅读摘要**（转述与归纳），仅作设计参考。<br>
> **不是**原作者文章的全文转载、存档或摘录汇编。第三方原文的版权归原权利方所有；本仓库不主张对原文的再分发权。阅读全文请走下方原文链接。

## 原文信息

| 项 | 内容 |
| --- | --- |
| 标题 | Harness Engineering：耗时一周，我是如何将应用的 AI Coding 率提升至 90% 的 |
| 作者标注 | 阿里云开发者 |
| 发布 | 2026年5月7日 |
| 原文链接 | [微信公众平台原文](https://mp.weixin.qq.com/s?__biz=MzIzOTU0NTQ0MA==&mid=2247559842&idx=1&sn=71ee08bf0421ad2f1aa4dd7a58901c5f) |

阅读完整论述、数据图表与细节，请以原文链接为准。

## 摘要在说什么

AI Coding 正经历三次范式跃迁：Prompt Engineering → Context Engineering → **Harness Engineering**。模型能力已足够强，但在企业级存量代码库中，Agent 产出常「语法正确、业务语义有隐患」。差距来自隐性知识未系统化，以及缺少外部约束与反馈。

**Harness Engineering** 的操作性定义（综合文中对 Anthropic / Mitchell Hashimoto / OpenAI 实践的归纳）：围绕 AI Coding Agent，设计约束机制、反馈回路、工作流编排与持续改进闭环；每发现一次 Agent 错误，就工程化地消除同类错误再次发生的可能。

## 关键论点（维护者整理）

### 为何不能只靠模型

文中归纳 Agent 四类失败模式：一步到位挤爆上下文、过早宣布完成、缺少端到端验证、冷启动无跨会话记忆。共同根因是缺少结构化约束与反馈；且 Agent 难以准确自评产出质量，需要外部化质量体系。

### 四根支柱

1. **上下文架构**：刚好够用；索引/地图式入口，分层按需加载，避免百科全书式 `AGENTS.md`。
2. **Agent 专业化**：规划 / 实现 / 评判分离；受限工具集优于全能通用 Agent。
3. **持久化记忆**：进度落在文件系统，而非仅靠上下文窗口。
4. **结构化执行**：先理解与书面计划，再编码；用可机械化验证的质量门禁替代纯自然语言「建议」。

### 企业侧挑战（文中归纳）

- 大型存量库的认知负担与隐性知识
- 质量控制跟不上 Agent 产出速度
- 「熵」累积（次优 pattern 被反复模仿）
- 开发者角色转向：工作环境设计、规范编写、任务编排与验收

### 文中实战骨架（供本仓库后续设计对照）

文中在约 10 万行 Java 企业应用上落地的四要素：

| 要素 | 作用 |
| --- | --- |
| Rules | 稳定约束（结构、规范、分层） |
| Skills | 可复用 SOP（分析、编码、评审、测试、部署等） |
| Wiki | 业务与系统知识 |
| Changes | 变更全过程审计轨迹 |

物理载体为 `.harness/`（agents / rules / skills / changes / mcp 等），并以 Application Owner Agent 编排约 **10 阶段**流水线（需求分析 → … → 用户确认），含质量门禁、失败回退、评审轮次上限与 Human-in-the-Loop 确认点。上下文分常驻 / 阶段触发 / 按需查询三层。

### 经验与效果（文中主张，非本仓库实测）

- Harness 需 Dry Run；门禁须可程序化验证；执行与评判分离；流程一致性优先于「小改动走捷径」；规范是对应历史失败的活文档。
- 文中给出项目维度 AI 代码率约 **24.86% → 90.54%** 的前后对比，并强调高 AI 率须建立在质量门禁之上。
- 更深层收益被描述为：返工减少、交付可预期、知识沉淀成「活的项目开发手册」。

## 对本仓库的用途

本摘要仅作 **设计输入与术语对齐**，不构成对本仓库最终目录布局、流程阶段或 Skill 清单的承诺。具体 Harness 形态以本仓库后续决策与实现为准。

## 文中引用的外部资料（便于溯源）

- Anthropic — Effective harnesses for long-running agents：https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic — Harness design for long-running application development：https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic — 2026 Agentic Coding Trends Report：https://resources.anthropic.com/2026-agentic-coding-trends-report
- OpenAI — Harness engineering: leveraging Codex in an agent-first world：https://openai.com/index/harness-engineering/
