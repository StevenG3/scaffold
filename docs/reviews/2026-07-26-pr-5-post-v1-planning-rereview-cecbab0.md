# PR #5 Post-v1 Planning 第三轮整改复审

- 复审日期：2026-07-26
- PR：#5 `Post-v1: process codification, v2 planning draft, and B0 customization record`
- 基线：`main@b1fcda4b82450138cfcbdbad71803896c6881368`
- 上轮复审 HEAD：`b344f4bbb05117b13e4d314127b512b935e22d65`
- 固定复审 HEAD：`cecbab042ad8edd633eb320eee45ce03ba108c61`
- 整改提交：
  - `cecbab0` `docs: enumerate asset commits individually in the evidence rule`
- 复审方式：Standards / Spec 双路独立复审、R3 整改报告核对、全量测试、范围语义清除扫描、机器契约与 bundle 文件集差异及远端 CI 核对
- 当前结论：**Approve，可以合入**

本结论只绑定上述精确复审 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次批准。

## 上轮合入要求复核

| 合入要求 | 复核结果 | 说明 |
| --- | --- | --- |
| 多个 asset commits 不使用 Git 范围 | 已关闭 | `summary.md` 必须逐个列出每个 asset commit；规则明文禁止 range notation。 |
| 提交无需连续且不得夹入无关提交 | 已关闭 | 证据集合由显式 SHA 清单构成，不再依赖提交图范围。 |
| 单提交示例 | 已关闭 | 使用单个 id，并采用 `asset commit` / `that diff` 单数语义。 |
| 多提交示例 | 已关闭 | 使用两个独立 id，并采用 `asset commits` / `those diffs` 复数语义。 |
| asset → audit 顺序与无自引用 | 保持关闭 | `summary.md` 只引用已经存在的 asset commits，Change Record 仍在后续 audit commit 落地。 |

## Findings

**无 Critical、Important 或 Minor correctness finding。**

一个非阻断说明：规则允许使用完整 id 或“当前唯一可解析”的缩写 id。缩写未来可能随仓库增长而失去唯一性；但这是上一轮明确允许的验收方案，当前示例为占位值，不在本轮移动验收标准。若未来追求永久自包含证据，可另行将规则强化为完整 OID。

## Standards 复审

- PASS。
- `template/.harness/skills/harness-bootstrap/SKILL.md:92-96` 的证据规则已改为逐提交枚举。
- `template/.harness/skills/harness-bootstrap/SKILL.md:110-116` 的单提交与多提交示例逐字符合规则。
- 相对 `b344f4b`，流程文档、v2 草案、Manifest、CLI、Schema、测试和其他 Skill 均无变化。
- 未发现 smell-baseline 判断项。

## Spec 复审

- PASS。
- 上轮唯一 Important 已完整关闭。
- R3 整改报告与实际 diff 一致。
- 未发现 missing、partial、错误或 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 4/4 | 逐 SHA 规则、禁用范围和单/多提交示例完整满足整改要求。 |
| B. 事实准确性 | 4/4 | 文档表述与 Git 证据语义一致。 |
| C. 通用性 | 4/4 | 支持单个、多个及非连续 asset commits，不依赖提交图形状。 |
| D. 可维护性 | 4/4 | 规则局部明确，示例与证据顺序可直接执行。 |
| E. 验证充分性 | 4/4 | 全量门禁、语义扫描、差异边界和远端 CI 均已独立核验。 |
| F. 可追溯性 | 3/4 | 当前唯一可解析短 id 符合验收要求；完整 OID 的长期稳定性更强，但不构成本轮 finding。 |

总分：**23/24**。所有维度均达到合入门槛，无 correctness finding。

## 独立验证证据

隔离 worktree：

```text
/Users/shiliwei/.config/superpowers/worktrees/scaffold/pr5-rereview-cecbab0
detached HEAD cecbab042ad8edd633eb320eee45ce03ba108c61
```

变更边界：

```text
$ git diff --stat b344f4bbb05117b13e4d314127b512b935e22d65..cecbab042ad8edd633eb320eee45ce03ba108c61
template/.harness/skills/harness-bootstrap/SKILL.md | 10 +++++++---
1 file changed, 7 insertions(+), 3 deletions(-)
```

本地门禁：

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 168 tests in 10.665s
OK (skipped=2)

$ git diff --check b1fcda4b82450138cfcbdbad71803896c6881368...cecbab042ad8edd633eb320eee45ce03ba108c61
无输出，exit 0
```

- 两项 skip 与此前相同：当前文件系统拒绝非 UTF-8 文件名；与本次 prose-only 整改无关。
- `template/.harness/skills/harness-bootstrap/SKILL.md` 中不存在 `commit range` 或 SHA `A..B` 形式。
- 规则明确包含 `lists every asset commit individually`、`Range notation is never used` 和单/多提交证据示例。
- 相对上轮 HEAD，机器契约路径没有变化，bundle 文件集合没有变化。
- 分发 bundle 新增文本不含生产者专属 token 或日期。
- 实现方 R3 整改报告已完整读取：`.superpowers/sdd/pr5-r3-fix-report.md`。

远端证据：

- PR #5 当前 head OID：`cecbab042ad8edd633eb320eee45ce03ba108c61`
- GitHub Actions run：`30187135874`
- `validate`：SUCCESS
- PR 状态：`OPEN / Draft / MERGEABLE`

## 合入意见

**批准合入固定 HEAD `cecbab042ad8edd633eb320eee45ce03ba108c61`。**

合入前仍须执行机械重锁：

1. PR head OID 仍等于本记录固定 HEAD；
2. required check 仍为 SUCCESS；
3. PR 从 Draft 转为 Ready 后保持 mergeable；
4. 若 head 发生任何变化，立即作废本批准并重新审阅。

本记录不批准任何后续 HEAD。

## 合入结果

- 合入时间：2026-07-26
- 合入方式：Squash merge
- 已批准 PR HEAD：`cecbab042ad8edd633eb320eee45ce03ba108c61`
- main 合入提交：`d0c7bab58c457f45e23aea82a5b6402ab1f9aa44`
- PR 状态：MERGED
- 远端功能分支：`docs/post-v1-planning` 已删除

合入前已再次确认 PR head OID 与本记录固定 HEAD 一致，required check 为 SUCCESS，
PR 为 Ready / MERGEABLE。合入后门禁与 main 远端状态见本记录入库提交及本轮最终回报。
