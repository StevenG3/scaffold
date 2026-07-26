# PR #5 Post-v1 Planning 独立审阅

- 审阅日期：2026-07-26
- PR：#5 `Post-v1: process codification, v2 planning draft, and B0 customization record`
- 基线：`main@b1fcda4b82450138cfcbdbad71803896c6881368`
- 固定 HEAD：`51c15a03b9fadd6fdb8df9131712fe99aa6ebc56`
- 审阅范围：3 个提交，3 个文件，`+177/-0`
- 审阅方式：Standards / Spec 双路独立审阅、本地全量测试、Manifest 与 bundle 文件集差异、Markdown 链接及远端 CI 核对
- 当前结论：**Request changes，禁止合入**

本结论只绑定上述精确 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## Findings

### [Important] 强制规范的效力与适用阶段自相矛盾

位置：

- `docs/process/invariant-closure-design.md:1-3,22-49`
- `docs/design/harness-v2-planning.md:3,6,53-65`

PR 正文、不变式流程标题和 v2 草案都把“不变式闭包设计法”描述为 v2 及后续设计的强制流程，但流程自身仍标为 `Proposed`。合入后无法机械判断该规范是否已经获得批准并正式生效。

同时，流程要求“任何新设计”必须包含全称不变式、逐条闭包枚举表和完整对抗输入域；v2 草案自称该流程的首个强制适用对象，却把闭包表和输入域展开推迟到“定稿时”。流程没有定义 Draft 阶段豁免，因此首个适用对象在同一 PR 内违反了新流程。

整改要求：

1. 明确流程的审批状态和生效点：若本 PR 使其正式生效，应记录已批准状态；否则不得将其描述为已强制适用。
2. 明确定义 Draft、正式设计、批准和实施各阶段的最低交付义务。
3. 按上述裁决修订 v2 文档：要么当前补齐闭包表和输入全集，要么将其明确降格为不受该条款约束的路线图，并说明何时转为受控设计。

### [Important] B0 定制记录不足以稳定形成路线图要求的接入证据

位置：

- `docs/design/harness-v2-planning.md:24-28,67-80`
- `template/.harness/skills/harness-bootstrap/SKILL.md:43-64,68-73`

路线图要求收集每个项目的项目层资产清单，以及用户实际推翻或改写模板内容的记录。Skill 当前只要求为 “template asset the bootstrap touched” 建表：

- 没有明确该范围是否包含 bootstrap 新增的 `rules/` 与 `wiki/` 项目资产；
- `modified` 与 `replaced` 只有可选值，没有可判定的语义边界；
- 没有说明实际改写证据由表格、Change Record 内其他文件还是 Git diff 承载；
- 因而不同 Agent 可能对相同定制生成不同范围和分类的记录，削弱跨项目比较能力。

整改要求：

1. 将记录范围定义为所有新增、修改、替换或删除的 Harness 资产，并明确是否覆盖 `rules/`、`wiki/`、Manifest 注册和其他 bootstrap 产物。
2. 为四种 `Action` 给出互斥、可判定的定义。
3. 明确保存实际改写证据的载体及最小内容；若依赖 Git diff，需写入 Skill 契约并说明无 Git 环境的替代方式。
4. 增加至少一个完整示例，证明新增项目资产、模板改写和层级猜测能被一致记录。

## Standards 审阅

- 两项 Important 均属于文档治理与内部一致性的硬性违反。
- 判断项：`modified` / `replaced` 是含义不清的领域名称，会令证据分类漂移。
- 未发现其他 Standards 违反；文档链接和 diff 格式检查通过。

## Spec 审阅

- “v2+ 强制流程”没有形成明确生效且自洽的规范，核心承诺部分实现。
- B0 虽增加了 `customization-record.md`，但其覆盖范围和证据载体不足以确定性满足 v2 路线图所列反馈集。
- 未发现与 PR 三项承诺无关的 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 三项产物均已添加，但 mandatory 流程与 B0 证据契约存在核心缺口。 |
| B. 事实准确性 | 2/4 | `Proposed` 与“强制适用”并存，无法形成唯一当前状态。 |
| C. 通用性 | 3/4 | 方向具有跨项目价值，但定制记录分类尚不能保证跨 Agent、跨项目一致。 |
| D. 可维护性 | 3/4 | 文档结构清晰；流程阶段和 Action 语义需进一步收敛。 |
| E. 验证充分性 | 4/4 | 机器门禁、本地测试、链接、文件集和远端 CI 均已独立核验。 |
| F. 可追溯性 | 3/4 | PR、提交与路线图关联清晰，但拟议流程缺少正式生效记录。 |

总分：**17/24**。存在 Important 合入阻断，当前不得合入。

## 独立验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -v
Ran 168 tests in 10.373s
OK (skipped=2)

$ git diff --check origin/main...51c15a03b9fadd6fdb8df9131712fe99aa6ebc56
无输出，exit 0
```

- 两项跳过均因当前文件系统拒绝非 UTF-8 文件名，不涉及本 PR 的 prose-only 变更。
- 本地 Markdown 相对链接检查通过。
- `template/.harness/manifest.json`、CLI、Schema、测试及 bundle 文件集合相对基线均未改变。
- 远端 `validate` workflow 在固定 HEAD 上成功。
- 审阅结束前重新核对：本地 HEAD、`origin/docs/post-v1-planning` 和 PR #5 head OID 均为 `51c15a03b9fadd6fdb8df9131712fe99aa6ebc56`。
- PR 状态为 `OPEN / Draft / MERGEABLE`，尚无可继承的批准结论。

## 合入意见

**不得合入当前 HEAD。**

实现方需关闭上述两项 Important，并在整改报告中逐项说明：

1. 流程批准状态、生效阶段和 Draft 义务的唯一语义；
2. v2 草案如何满足或明确退出当前强制适用范围；
3. customization record 的完整资产范围、Action 判定规则和实际改写证据载体；
4. 修订后的示例与验证证据。

推送新 HEAD 后，重新执行 Standards / Spec 双路审阅、全量门禁和远端 CI 核对。本记录不构成对任何后续提交的批准。
