# PR #3：Branch Hygiene workflow 审阅

## 当前结论

**Approve，建议合入。** 本结论仅适用于 `ci/detect-stale-merged-branches@321a405f8fc90e6122f9b790582c9686a16067fd`，审阅时远端主干为 `main@affb21dd9f27fe6961df38bbee3d8cbb90e08397`，共同基线为 `83cff0e072af8d956b5f122c36f71a183e176812`。任何新增提交都使批准失效。

- PR：[PR #3 — ci: detect remote branches left merged into main](https://github.com/StevenG3/scaffold/pull/3)
- 变更范围：仅 `.github/workflows/branch-hygiene.yml`，`+49/-0`
- Standards：0 findings，Approve
- Spec：0 findings，Approve
- 合入状态：`OPEN / DRAFT / MERGEABLE / CLEAN`

## 第一轮审阅（`76d9b97`，已关闭）

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | push 到 main 的路径正确，但非 main 的手动运行违反“只判断已合入 main”的核心语义。 |
| B. 事实准确性 | 2/4 | 输出宣称以 main 为基准，实际在 `workflow_dispatch` 下使用被选择 ref 的 SHA。 |
| C. 通用性 | 4/4 | 使用标准 Git 与 GitHub Actions，且没有把生产者侧 VCS 策略写入可移植分发包。 |
| D. 可维护性 | 3/4 | 单 job、最小权限和完整 refname 过滤清晰，但事件相关基准隐含在环境变量中。 |
| E. 验证充分性 | 2/4 | PR 前无法真实运行该 workflow；现有绿色 CI 只覆盖 Validate Harness，且原探针遗漏非 main dispatch。 |
| F. 可追溯性 | 4/4 | 触发器、失败输出、精确 HEAD 和独立探针均可定位复现。 |

总分：**17/24**。A、B、E 为 2 分，触发 fail-fast 合入门禁。

## Standards findings

### [P2] 手动运行使用了错误的主干基准

位置：`.github/workflows/branch-hygiene.yml:7`、`.github/workflows/branch-hygiene.yml:27`

workflow 声明支持 `workflow_dispatch`，但 `git merge-base --is-ancestor "$ref" "$GITHUB_SHA"` 把事件 SHA 当成 main。GitHub 对手动运行允许选择 branch 或 tag；此时 `GITHUB_SHA` 是该选择 ref 的最后提交，而不是默认分支提交。实现因此与 job 名称及错误文案中的 “merged into main” 不一致。

独立复现：以本 PR HEAD `76d9b97` 模拟手动选择该分支，原样脚本 exit `1` 并列出 `origin/ci/detect-stale-merged-branches`；但该提交不是 `origin/main@83cff0e` 的祖先，属于未合入的在途工作。

整改要求：比较基准必须固定为已 fetch 的 `refs/remotes/origin/main`，或显式拒绝非 main 的手动运行；重新提交后必须增加非 main dispatch 探针并对新 HEAD 完整复审。

## Spec findings

### [P2] 未合入分支在 workflow_dispatch 场景被误报

需求要求“存在未合入的远端分支时 exit 0，不得误报在途工作”。当前实现从非 main ref 手动运行会把触发分支自身判为祖先并报残留，直接违反该验收条件。该问题不会被 PR 上的 Validate Harness 检查发现。

## 范围裁定

裁定：**Harness v0 实施计划已随 v0 交付而关闭，不再约束后续变更。**

Standards 独立审阅最初将新 workflow 路径列为 P2；经本任务要求的 planner 裁定，该项不成立，故不计入最终 findings。

`docs/plans/harness-v0-implementation.md:806` 是 Harness v0 开发分支的交接范围门禁；v0 已通过 PR #1 合入。本 PR 是 planner 明确授权的后续生产者侧仓库治理任务，因此新增 `.github/workflows/branch-hygiene.yml` 不构成该计划下的越界，也无需伪装成 `validate.yml` 修改。

范围声明成立：精确 diff 仅包含 `.github/workflows/branch-hygiene.yml`，`template/.harness/` 没有变化。设计 §7.3 要求分发规则保持语言、框架和业务无关，Coordinator 也不假设 CI provider；远端分支清理属于 scaffold 生产者的 GitHub 流程，不应进入可移植 bundle。

## 设计取舍

批准“发现残留分支时 exit 1 并把 main 标红”的策略。该行为正是把重复发生、弱提示无法消除的流程遗漏转为机械门禁；降级为只警告会削弱本 PR 的目标，不构成 finding。

## 验证证据

- 从 YAML 解析并抽取 `jobs.stale-merged-branches.steps[1].run`；抽取脚本 SHA-256：`2294db1b4551f4bc120e201f9f1676105b41e2d2d91ea045ca19a8c736b5b7b6`。
- 临时 bare remote + fresh clone：已合入残留分支 exit `1` 且只列出该分支；干净仓库 exit `0`；仅有未合入分支 exit `0`；`origin/HEAD` 未误报；全部通过。
- 额外非 main dispatch 探针：exit `1` 并误报 PR 分支，确认本轮 P2。
- `actions/checkout@v4` 的 `fetch-depth: 0` 按官方契约获取所有 branches/tags，足以支持完整远端分支遍历。
- `python3 template/.harness/bin/validate.py`：exit `0`。
- `python3 template/.harness/bin/validate.py --format json`：`valid: true`。
- `python3 -m unittest discover -s tests -v`：51/51 通过。
- `git diff --check 83cff0e...76d9b97`：exit `0`。
- 审阅目标工作区 `git status --short`：空。
- GitHub Actions run `29902650312`：SUCCESS，精确对应 `76d9b97`；该 run 仅执行现有 Validate Harness，不验证新增 workflow。

## 合入建议

当前不得合入。开发者修复 `$GITHUB_SHA` 基准问题并推送新 HEAD 后，重新执行 Standards / Spec 双路审阅、五类脚本探针、完整仓库门禁，并确认精确 HEAD 的 CI。批准只能绑定新的精确 HEAD；本记录不自动批准任何后续提交。

## 第二轮复审（`321a405`）

上一轮 P2 已关闭：workflow 固定使用 `refs/remotes/origin/main`，先验证该 ref 存在，再以它作为所有 `merge-base --is-ancestor` 判断的唯一基准。`workflow_dispatch` 从非 main branch 或 tag 运行时，不再使用事件 `$GITHUB_SHA`，因此不会误报在途分支。

### 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 4/4 | push 与手动运行均只判断“已合入 main”，全部验收场景通过。 |
| B. 事实准确性 | 4/4 | 判断基准、job 名称和错误文案统一指向远端 main。 |
| C. 通用性 | 4/4 | 仅依赖标准 Git 与 GitHub Actions，不污染可移植 Harness bundle。 |
| D. 可维护性 | 4/4 | 主干 ref 显式命名并 fail closed，完整 refname 过滤和严格 Bash 清晰。 |
| E. 验证充分性 | 4/4 | 原样抽取脚本覆盖正常、对抗和缺失主干 ref 场景；仓库门禁及精确 HEAD CI 全绿。 |
| F. 可追溯性 | 4/4 | 上轮 finding、修复提交、探针输出和批准 HEAD 均在同一记录中闭环。 |

总分：**24/24**。无低于 3 分的维度。

### Standards findings

0 findings，Approve。

- `contents: read` 保持最小权限；`actions/checkout@v4` 配合 `fetch-depth: 0` 获取判断所需历史和远端分支。
- `main_ref` 存在性检查、case 变量模式、process substitution、条件命令退出码和确定性输出均正确。
- 范围仍仅包含生产者侧 workflow；已记录的范围裁定保持有效。
- Fowler smell baseline 未发现可定位问题。

### Spec findings

0 findings，Approve。

- 已合入单分支或多分支：exit `1` 并逐项列出。
- 干净远端：exit `0`。
- 仅有未合入分支：exit `0`，不误报。
- `origin/HEAD`：不误报。
- 非 main branch/tag 的 `workflow_dispatch`：仍固定比较 `origin/main`，exit 与主干事实一致。
- 缺失 `origin/main`：明确写 stderr 并 exit `1`，不产生假绿。

### 验证证据

- 从新 YAML 原样抽取 `jobs.stale-merged-branches.steps[1].run`；脚本 SHA-256：`6152dfd31266ecc13961a645a1193a605f98af36ace4bae699acddd82a741b6f`。
- 临时 bare remote + fresh clone：clean、unmerged、non-main dispatch、multiple stale、`origin/HEAD`、cleaned-again、missing-main-ref 全部符合预期。
- 真实仓库以 `GITHUB_SHA=321a405` 模拟非 main dispatch：exit `0`，输出 `No merged branches left behind.`。
- `bash -n` 与 YAML 结构抽取通过。
- Validator Text / JSON 均通过。
- `python3 -m unittest discover -s tests -v`：51/51 通过。
- `git diff --check affb21d...321a405`：exit `0`；审阅目标工作区干净。
- GitHub Actions run `29908340478`：SUCCESS，精确对应 `321a405`；该 run 仍只覆盖 Validate Harness。

### 合入前验证空白处理

新增 workflow 在进入默认分支前无法通过 `workflow_dispatch` 真实执行，因此批准依据是：从精确 HEAD 的 YAML 解析原始 run block、在 fresh clone 中执行完整探针、并验证现有 required check。合入后必须等待 `push: main` 产生的 Branch Hygiene 首次真实 run；只有该 run 和 Validate Harness 都成功，才算完成合入。

### 第二轮合入建议

允许将精确 HEAD `321a405f8fc90e6122f9b790582c9686a16067fd` 合入 `main`。推送必须同时删除所有已合入的远端分支，包括 `ci/detect-stale-merged-branches`；本地合入完成后删除对应开发分支及 `codex/pr-3-review`，避免新门禁首次运行即被残留分支触发。
