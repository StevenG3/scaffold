# PR #5 Post-v1 Planning 整改复审

- 复审日期：2026-07-26
- PR：#5 `Post-v1: process codification, v2 planning draft, and B0 customization record`
- 基线：`main@b1fcda4b82450138cfcbdbad71803896c6881368`
- 被退回 HEAD：`51c15a03b9fadd6fdb8df9131712fe99aa6ebc56`
- 固定复审 HEAD：`7f11bd55bd6d9d9111873ac980153c0f106d1e2f`
- 整改提交：
  - `79b7533` `docs: approve invariant-closure process and bind stage obligations`
  - `7f11bd5` `docs: make the bootstrap customization record decidable`
- 复审方式：Standards / Spec 双路独立复审、整改报告核对、全量测试、机器契约与 bundle 文件集差异、针对性语义探针及远端 CI 核对
- 当前结论：**Request changes，仍不得合入**

本结论只绑定上述精确复审 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## 上轮四项合入要求复核

| 合入要求 | 复核结果 | 说明 |
| --- | --- | --- |
| 流程批准状态、生效阶段和 Draft 义务的唯一语义 | 部分关闭 | `Approved`、批准日期、生效点和阶段义务已写明，但 Draft 禁止派发实现与 v2 的 B0 派发条款直接冲突。 |
| v2 草案满足或明确退出当前强制适用范围 | 未关闭 | 文档已声明规划阶段及 B1 完备交付点，但同一 Draft 仍直接派发 B0 实现。 |
| customization record 的资产范围、Action 规则和证据载体 | 部分关闭 | 范围、四种 Action 与两类载体已有定义，但“全部资产无豁免”与提交号证据形成自引用，当前契约不可完成。 |
| 修订后的示例与验证证据 | 部分关闭 | 已增加六行示例和双载体句子，但 Manifest 示例把 path 写成了 component id。机器验证证据成立。 |

## Findings

### [Important] Draft 禁止派发实现与 v2 B0 的永久派发条款冲突

位置：

- `docs/process/invariant-closure-design.md:27-31`
- `docs/design/harness-v2-planning.md:69-82`

新流程规定：

> 规划阶段文档不得据此派发实现。

但 v2 Draft 仍规定：

> B0（可立即做）

以及：

> 实施 B0（观察工具化），由实现方按本规划派发。

本 PR 又实际交付了 B0 的 bootstrap Skill 修改。即使把流程的生效点解释为“合入 main”，合入后的永久文档仍会同时保留“Draft 不得派发实现”和“按本 Draft 派发 B0”两种相反规则，因此阶段义务并非唯一语义。

整改要求：

1. 若 B0 是允许在规划阶段实施的观察性例外，在流程阶段表中明确例外的范围、批准条件和不得触碰的契约边界，并让 v2 文档引用该例外。
2. 若不存在例外，删除 Draft 中的 B0 实施派发条款；先按流程形成满足正式设计阶段义务的 B0 设计，再派发实现。
3. 不得仅用“流程此前尚未生效”解释历史动作，因为冲突条款会随本 PR 一同进入 main。

### [Important] 全资产记录与 VCS 提交证据形成不可满足的自引用

位置：

- `template/.harness/skills/harness-bootstrap/SKILL.md:47-63`
- `template/.harness/skills/harness-bootstrap/SKILL.md:86-91`
- `template/.harness/skills/harness-bootstrap/SKILL.md:93-110`
- `template/.harness/manifest.json:27-34`

Skill 要求记录 bootstrap 触碰的 **every Harness asset, with no exemptions**。bootstrap 同时创建 Change Record 的 `summary.md`、`spec.md`、`tasks.md` 和 `customization-record.md`；这些文件位于 Manifest 声明的 Harness Change Record 目录中，也是 bootstrap 触碰的 Harness 资产。

VCS 路径又要求所有资产改动落入可引用提交，并由 `summary.md` 写入该提交号。若 `summary.md` 本身属于“无豁免”的资产集合，它必须在自身内容里记录包含自身最终内容的 commit id；写入该 id 会改变 commit id，因而无法得到满足当前文字契约的最终提交。Worked example 也没有列出这些由 bootstrap 创建的 Change Record 资产，和“无豁免”范围不一致。

整改要求：

1. 明确区分“被定制的 Harness 目标资产”和“承载审计证据的 Change Record 元数据”。
2. 若 Change Record 元数据不属于记录范围，必须显式排除，而不是保留 “no exemptions”。
3. 规定可完成的 VCS 顺序，例如先提交目标资产，再由后续审计提交的 `summary.md` 引用前一目标提交或明确的提交范围；不得要求文件引用包含其最终内容的自身 commit id。
4. 同步修订 worked example，使其覆盖最终定义的完整范围。

### [Important] Manifest worked example 把 component path 当成 component id

位置：

- `template/.harness/skills/harness-bootstrap/SKILL.md:72`
- `template/.harness/skills/harness-bootstrap/SKILL.md:95-102`
- `template/.harness/manifest.json:5-25`

列定义要求 Manifest 注册行写为“manifest path followed by the component id in parentheses”，但示例写成：

```text
manifest.json (rules/project.md)
```

`rules/project.md` 是 component path，不是 component id。现有 Manifest 明确区分二者，例如 `delivery-rule -> rules/delivery.md`。该示例是用于保证不同 Agent 机械一致执行的核心例子，却没有遵守自己的字段定义。

整改要求：

1. 示例括号中使用明确的组件 id，例如 `manifest.json (project-rules)`，并在 Reason 中说明其 path 为 `rules/project.md`；或
2. 若真实意图是使用 component path，则修改列定义并统一所有示例与说明。

二者只能选择一种唯一语义。

## Standards 复审

- 3 项 Important 均属于新增规范的内部一致性或可执行性阻断。
- 未发现独立的 smell-baseline 问题。
- 整改 diff 与完整 PR diff 的格式检查均通过。

## Spec 复审

- 原 Important #1 的状态标记问题已关闭，但阶段合规问题因 B0 派发冲突仍未关闭。
- 原 Important #2 已补充大量必要细节，但证据载体的提交自引用使契约仍不可完成。
- 示例要求已交付，但 Manifest 行使用了错误的标识维度。
- 未发现与四项整改要求无关的 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 四项要求均有响应，但阶段合规、证据闭包与示例仍存在阻断。 |
| B. 事实准确性 | 2/4 | 文档同时禁止和派发 Draft 实现，示例又混淆 Manifest id/path。 |
| C. 通用性 | 2/4 | VCS 证据路径存在自引用，无法作为任意项目可完成的通用流程。 |
| D. 可维护性 | 3/4 | 分节、Action 定义和示例改善明显，但元数据边界需要收敛。 |
| E. 验证充分性 | 4/4 | 机器门禁、测试、文件集、格式和远端 CI 均有精确 HEAD 证据。 |
| F. 可追溯性 | 4/4 | 整改简报、报告、两提交、精确 HEAD 与 CI 绑定完整。 |

总分：**17/24**。存在 3 项 Important 合入阻断，当前不得合入。

## 独立验证证据

隔离 worktree：

```text
/Users/shiliwei/.config/superpowers/worktrees/scaffold/pr5-rereview-7f11bd5
detached HEAD 7f11bd55bd6d9d9111873ac980153c0f106d1e2f
```

本地门禁：

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 168 tests in 10.236s
OK (skipped=2)

$ git diff --check b1fcda4b82450138cfcbdbad71803896c6881368...7f11bd55bd6d9d9111873ac980153c0f106d1e2f
无输出，exit 0
```

- 两项 skip 与上一轮相同：当前文件系统拒绝非 UTF-8 文件名；与本次 prose-only 整改无关。
- 相对被退回 HEAD，`template/.harness/manifest.json`、CLI、Schema 和测试没有变化。
- `template/.harness/` 文件集合没有变化。
- 分发 bundle 新增文本不含生产者专属 token 或日期。
- Manifest 探针确认现有 component id/path 分离；示例括号内容 `rules/project.md` 不是现有 id 形式。
- 实现方整改简报与报告已完整读取，报告路径：
  - `.superpowers/sdd/pr5-r1-brief.md`
  - `.superpowers/sdd/pr5-r1-fix-report.md`

远端证据：

- PR #5 当前 head OID：`7f11bd55bd6d9d9111873ac980153c0f106d1e2f`
- GitHub Actions run：`30184846646`
- `validate`：SUCCESS
- PR 状态：`OPEN / Draft / MERGEABLE`

## 合入意见

**不得合入当前 HEAD。**

实现方需关闭上述 3 项 Important，并在下一轮整改报告中逐项说明：

1. Draft 阶段 B0 是否为正式例外；若是，给出唯一且受限的流程规则，否则移除 Draft 派发。
2. customization record 的目标资产与证据元数据边界。
3. 不产生 commit-id 自引用的 VCS 证据提交顺序。
4. Manifest registration 行究竟使用 component id 还是 path，并修正示例。
5. 更新 worked example 与验证证据，使其与最终规则逐字一致。

推送新 HEAD 后，重新执行 Standards / Spec 双路审阅、全量门禁和远端 CI 核对。本记录不构成对任何后续提交的批准。
