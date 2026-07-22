# PR #3：Branch Hygiene workflow 审阅

## 结论

**Request changes。** 当前存在 1 个阻塞 P2。本结论仅适用于 `ci/detect-stale-merged-branches@76d9b9773a06c9495a27d6882a100d11c0ba52c6`，基线为 `main@83cff0e072af8d956b5f122c36f71a183e176812`。任何新增提交都必须重新审阅。

- PR：[PR #3 — ci: detect remote branches left merged into main](https://github.com/StevenG3/scaffold/pull/3)
- 变更范围：仅 `.github/workflows/branch-hygiene.yml`，`+40/-0`
- Standards：1 个 P2，Request changes
- Spec：1 个 P2，Request changes
- 合入状态：`OPEN / DRAFT / MERGEABLE / CLEAN`；不得合入

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
