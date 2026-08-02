# 定制记录 — 接入 #1（bootstrap 首次真实执行）

本文件按 `skills/harness-bootstrap/SKILL.md` 的「Customization record」契约编写，覆盖本次 bootstrap 触碰的**每一个目标资产**。本 Change Record 自身的审计元数据（`summary.md`、`spec.md`、`tasks.md`、本文件）按契约不入表。

`.github/workflows/validate.yml` 也不入表：它是本仓库的 CI 配置，不是 Harness 资产，不用于配置或治理 Harness 本身。该改动的证据在资产提交 `2b8100bd60b0000d20a79ae4a9b77b412aeb33a7`。

## 表

| Asset | Action | Reason | Reusability guess |
| ----- | ------ | ------ | ----------------- |
| `rules/project.md` | `added` | 访谈裁定了项目目的、7 条交付门禁、三方审批约定、消费者副本同步规则与行文语言，这些在随包发行的 `rules/delivery.md` 里没有落点。 | `project` |
| `manifest.json` (`project-rules`) | `added` | 注册 `rules/project.md`，使校验器与三个平台投影都能看到它。 | `project` |
| `wiki/overview.md` | `added` | 侦察查明了生产者/消费者双身份的目录职责、技术栈与 v0–v3 路线，需要一个入口页承载。 | `project` |
| `wiki/conventions.md` | `added` | 侦察查明强制流程、角色分工、审阅记录抬头契约与回灌禁令，并记录本次实测出的 v3 `upgrade` 需求证据。 | `project` |
| `CLAUDE.md`（投影，非 bundle 内） | `modified` | 注册 `project-rules` 后由 `harness.py adapt` 重生成受管块，使组件清单包含本项目的项目规则。 | `project` |
| `AGENTS.md`（投影，非 bundle 内） | `modified` | 同上，Codex 平台入口；变更内容同样是本项目的 `project-rules` 注册。 | `project` |
| `.cursor/rules/harness.mdc`（投影，非 bundle 内） | `modified` | 变更内容是本项目的 `project-rules` 注册。该文件按 v1 设计为工具整文件拥有、每次投影整体重建；但整文件所有权是写入机制，不等于内容谱系——本次实际保留了全部 26 行原有内容并新增 1 行。 | `project` |

## 契约留白上报（流程 §3「契约留白上报」）

Skill 规定 Asset 列写「bundle-relative path」，但上表后三行的三个平台投影文件位于**分发包之外**（仓库根与 `.cursor/`），没有 bundle 相对路径可写。它们确实是「为配置或治理项目而存在的 Harness 资产」，且确实被本次 bootstrap 触碰（`adapt` 重生成），而 Skill 明确要求「难以归类的目标资产仍须成行，绝不省略」。

本次处理：**成行**，路径按仓库根相对写出并标注「投影，非 bundle 内」。这是接入 #1 发现的 Skill 契约留白，提请设计方裁定投影文件的归属与路径写法；在裁定前，本记录以「宁可多行且显式标注」的方式保证不漏。

## 上游分层提示

标记 `stack` 或 `generic` 的行是上游模板分层的候选证据，将来向上游共享本记录时应逐字保留。

补充观察（供 v2 §2 反馈使用）：按 PR #7 审阅 F1 的裁定改判后，7 行**全部**为 `project`，没有任何 `stack` 或 `generic` 行——因为每一行的实际变更内容都是本项目特有的 `project-rules` 注册或本项目的项目层资产，而不是投影机制本身的通用性。

这一改判本身就是层边界的证据：**资产的复用性要按本次变更的内容判定，不能按写入它的机制判定**。三个投影文件的生成机制对任何项目都通用，但它们本次被写进去的内容只对本项目成立。

同时，`wiki/overview.md` §3「技术栈」的内容（Python 3.9+、仅标准库、stdlib `unittest`、无 linter）实质上是**栈级**材料，只是彼时被写在项目层页面里——这正是 v2 分层要解决的现象：栈级知识没有归属层，只能塞进项目层。它没有单独成行，是因为它不是独立资产，而是某个 `project` 资产内部的一节；这说明按文件粒度的复用性标注无法表达「一个文件内混有多层内容」，是 v2 分层设计需要处理的粒度问题。若将来抽取为 Python 栈层资产，须先去除全部项目上下文并译为英文（回灌禁令见 `rules/project.md` §6）。
