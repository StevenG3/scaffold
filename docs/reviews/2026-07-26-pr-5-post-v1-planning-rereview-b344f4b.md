# PR #5 Post-v1 Planning 第二轮整改复审

- 复审日期：2026-07-26
- PR：#5 `Post-v1: process codification, v2 planning draft, and B0 customization record`
- 基线：`main@b1fcda4b82450138cfcbdbad71803896c6881368`
- 上轮复审 HEAD：`7f11bd55bd6d9d9111873ac980153c0f106d1e2f`
- 固定复审 HEAD：`b344f4bbb05117b13e4d314127b512b935e22d65`
- 整改提交：
  - `6434954` `docs: scope planning-stage dispatch to an observational exception`
  - `b344f4b` `docs: bound the customization record scope and its evidence order`
- 复审方式：Standards / Spec 双路独立复审、R2 简报与整改报告核对、全量测试、机器契约与 bundle 文件集差异、真实 Git 范围语义探针及远端 CI 核对
- 当前结论：**Request changes，仍不得合入**

本结论只绑定上述精确复审 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## 上轮五项合入要求复核

| 合入要求 | 复核结果 | 说明 |
| --- | --- | --- |
| Draft 阶段 B0 的正式例外与唯一受限流程 | 已关闭 | 流程用 (a)–(d) 四个合取条件定义唯一的观察性实施例外，并再次排除例外外的规划实施。 |
| v2 对例外的引用与逐项满足 | 已关闭 | B0 条目及近期行动均引用同一例外，声明本次派发如何满足四项条件。 |
| 目标资产与 Change Record 审计元数据边界 | 已关闭 | `customized target asset` 已定义；五类审计元数据显式排除，“无豁免”仅约束目标资产。 |
| 无 commit-id 自引用的两段提交顺序 | 部分关闭 | asset commit → audit commit 的顺序可完成且消除了自引用，但多提交的范围表示会漏掉首提交。 |
| Manifest id/path 与 worked example 一致性 | 已关闭 | 示例使用 component id `project-rules`，Reason 单独说明 path `rules/project.md`。 |

## Finding

### [Important] Worked example 的 Git 两点范围漏掉首个 asset commit

位置：

- `template/.harness/skills/harness-bootstrap/SKILL.md:92-97`
- `template/.harness/skills/harness-bootstrap/SKILL.md:110-112`

Skill 规定多个 target asset 提交时，`summary.md` 记录“commit range”，并给出：

```text
a1b2c3d..e4f5a6b
```

作为“全部 bootstrap target asset changes”的证据。但 Git 的标准两点范围 `A..B`：

- 作为 revision set 时，包含从 `B` 可达但从 `A` 不可达的提交，排除 `A` 本身；
- 作为 `git diff A..B` 时，比较 `A` 与 `B` 的树，同样不包含 `A` 这个提交相对其父提交引入的改动。

因此，如果 `A` 是第一个 asset commit，示例无法证明 `A` 中的资产变更，与 “every target asset change” 和 “exact rewritten content” 的承诺冲突。当前文字也没有要求 asset commits 必须连续；即使改用普通范围，仍可能把非资产提交混入证据集合。

独立真实探针：

```text
$ git rev-list --oneline 6434954..b344f4b
b344f4b docs: bound the customization record scope and its evidence order

$ git diff --name-only 6434954..b344f4b
template/.harness/skills/harness-bootstrap/SKILL.md

$ git rev-list --oneline 6434954^..b344f4b
b344f4b docs: bound the customization record scope and its evidence order
6434954 docs: scope planning-stage dispatch to an observational exception
```

第一整改提交修改的两个流程文档被 `6434954..b344f4b` 排除，证明该示例确实遗漏范围起点。

整改要求：

1. 推荐让 `summary.md` 逐个列出每个 asset commit 的完整或唯一可解析 SHA；这不要求提交连续，也不会夹入其他提交。
2. 若必须使用范围，需规定 asset commits 连续，并使用包含首提交的明确语义，例如 `<first>^..<last>`，同时写明验证命令。
3. 修订 worked example，使单提交、多提交的记录格式都与最终规则逐字一致。

## Standards 复审

- 1 项 Important：示例的 Git 范围语义无法满足其声明的完整证据标准。
- 观察性实施例外、v2 引用、目标/元数据边界、两段提交结构和 Manifest id/path 均通过。
- 未发现独立 smell-baseline 问题。

## Spec 复审

- 五项整改要求中的四项已完全关闭。
- 两段提交结构本身可完成，但其多提交证据表示仍部分失败。
- 未发现无关 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 3/4 | 五项要求中的四项关闭，仅多提交证据格式未满足完整性。 |
| B. 事实准确性 | 2/4 | 示例对 Git `A..B` 的实际范围语义描述错误。 |
| C. 通用性 | 3/4 | 两段顺序可用于任意 VCS 项目，但范围表达尚不能覆盖非连续提交。 |
| D. 可维护性 | 4/4 | 边界与阶段规则已明显收敛，剩余修订局部明确。 |
| E. 验证充分性 | 4/4 | 全量门禁、机器文件差异、链接、真实 Git 语义及远端 CI 均已核验。 |
| F. 可追溯性 | 4/4 | R2 简报、报告、提交、精确 HEAD 与 CI 绑定完整。 |

总分：**20/24**。存在 1 项 Important 合入阻断，当前不得合入。

## 独立验证证据

隔离 worktree：

```text
/Users/shiliwei/.config/superpowers/worktrees/scaffold/pr5-rereview-b344f4b
detached HEAD b344f4bbb05117b13e4d314127b512b935e22d65
```

本地门禁：

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 168 tests in 18.400s
OK (skipped=2)

$ git diff --check b1fcda4b82450138cfcbdbad71803896c6881368...b344f4bbb05117b13e4d314127b512b935e22d65
无输出，exit 0
```

- 两项 skip 与前几轮相同：当前文件系统拒绝非 UTF-8 文件名；与本次 prose-only 整改无关。
- 相对上轮 HEAD，`template/.harness/manifest.json`、CLI、Schema 和测试没有变化。
- `template/.harness/` 文件集合没有变化。
- 新增文档相对链接检查通过。
- 实现方 R2 简报与报告已完整读取：
  - `.superpowers/sdd/pr5-r2-brief.md`
  - `.superpowers/sdd/pr5-r2-fix-report.md`

远端证据：

- PR #5 当前 head OID：`b344f4bbb05117b13e4d314127b512b935e22d65`
- GitHub Actions run：`30186053923`
- `validate`：SUCCESS
- PR 状态：`OPEN / Draft / MERGEABLE`

## 合入意见

**不得合入当前 HEAD。**

实现方只需关闭这一项 Important：

1. 选择逐 SHA 清单，或定义包含首提交且不夹入无关提交的唯一范围语义；
2. 同步修改 Evidence carrier 规则、version-control 示例句和 R3 整改报告；
3. 用至少两个真实连续 asset commits 演示首尾提交均被证据集合覆盖。

推送新 HEAD 后，重新执行 Standards / Spec 双路审阅、全量门禁和远端 CI 核对。本记录不构成对任何后续提交的批准。
