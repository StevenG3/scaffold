# 系统概览 — scaffold

> 骨架页。由 `harness-bootstrap` 在接入 #1 中依据代码库侦察生成；标注「待补充」的位置需要在后续交付中随事实补齐。

## 1. 定位

维护一套通用、可复制、与业务解耦的 AI Coding Harness 分发包与实例化工具链，让 Agent 在真实工程中稳定、可审计地交付代码。

## 2. 仓库结构

| 路径 | 角色 |
| --- | --- |
| `template/.harness/` | **分发包**（生产者资产）。对外分发的唯一单元；`init` 只复制这棵树。内容保持英文与项目中立。 |
| `.harness/` | **消费者实例**（本仓库自用）。由 `init` 从分发包安装，仅 `manifest.json` 的 `origin` 印章与项目层资产不同。 |
| `template/.harness/bin/harness.py` | 单文件 CLI，子命令 `init` / `adapt` / `validate`；随分发包一起分发，使接入项目脱离本仓库独立存活。 |
| `template/.harness/bin/validate.py` | 契约校验器，独立命令契约；`harness.py validate` 复用其实现。 |
| `tests/` | stdlib `unittest` 套件，全部扫描根固定在 `template/.harness`。 |
| `docs/design/` `docs/adr/` `docs/plans/` | 设计规格、架构决策记录、实施计划。 |
| `docs/process/` | 强制流程（不变式闭包设计法）。 |
| `docs/reviews/` | 独立审阅记录，绑定精确 HEAD。 |
| `.github/workflows/` | CI 门禁：`validate.yml`（契约 + 测试 + 空白 + 消费者副本）、`branch-hygiene.yml`（已合入分支清理）。 |
| `.superpowers/sdd/` | 过程档案（任务简报、整改报告、外审原文），整体 git-ignored。 |

## 3. 技术栈

- Python 3.9+，**仅标准库**，无第三方依赖（ADR-0001 的既定取舍：降低目标项目首次接入成本）。
- 测试框架为 stdlib `unittest`；仓库无 linter / formatter 配置。
- Manifest Schema v2（v1 的严格超集），字段见 `docs/design/harness-v1.md` §6。

## 4. 演进路线

1. **v0**：可移植分发包 + 契约校验器（已交付）。
2. **v1**：接入体验纵切片——自安装 CLI、平台投影、`harness-bootstrap` Skill（已交付合入）。
3. **v2**：分层模板（通用层 / 技术栈层 / 项目层），状态 Draft，定型前置条件为 ≥2 个不同技术栈的真实接入反馈；本次接入是第 1 个。见 `docs/design/harness-v2-planning.md`。
4. **v3**：演进同步（模板升级回流、项目资产回流上游），尚未启动。

## 5. 待补充

- 分发包各组件（`agents/` / `rules/` / `skills/`）在真实项目中的使用频次与取舍证据——需要日常交付积累后补。
- 第 2 个接入项目（不同技术栈）的对照记录，v2 定型的另一半前置条件。
- 消费者副本项目层资产的稳定形态：哪些内容将来会上抬为栈层（Python 栈）资产。
