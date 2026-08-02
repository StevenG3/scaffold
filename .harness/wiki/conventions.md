# 关键约定 — scaffold

> 骨架页。由 `harness-bootstrap` 在接入 #1 中依据代码库侦察生成；标注「待补充」的位置需要在后续交付中随事实补齐。约束性条款以 [`rules/project.md`](../rules/project.md) 为准，本页只做展开与背景说明。

## 1. 强制流程：不变式闭包设计法

`docs/process/invariant-closure-design.md`（状态 Approved，自合入 main 起对 v2 及后续设计强制生效）。要点：

- **设计方**：正式设计进入实现派发前，必须交付全称不变式、逐条闭包枚举表（操作点 × 异常类别 × 错误码 × 退出码 × 测试义务）、对抗输入域全集、兼容性承诺的精确边界；缺一不得派发实现。
- **实现方**：修类不修实例（每个 finding 附同类缝隙自查表）；红测先行（回归测试必须先在被退回 HEAD 上真实见红）；探针主动扩展；契约留白上报（遇设计未定义的输入域，停止并上报裁定，不按直觉处理）。
- **协调方**：交外部审阅前完成闭包表全表扫描，产出扫描表而非「已检查」断言。
- **规划阶段**文档不得派发实现，唯一例外是「观察性实施」（(a) 只动自然语言资产、机器契约零触碰；(b) 只为采集决策门反馈；(c) 逐次经设计方批准留档；(d) 仍须独立审阅方可合入）。

该流程的立项依据是 v1 的复盘数据：8 轮整改约 28 个 Critical/Important 中约 21 个是 3 个不变式的重复实例，根因是「审阅方用全称命题检查、设计方按存在命题交付」的方法不对称。

## 2. 角色分工

| 角色 | 拥有 | 禁止 |
| --- | --- | --- |
| 设计方 | 契约与裁决权；契约修订独立成 docs 提交，先于实现 | — |
| 实现方 | 实现、测试、提交 | 修改审阅记录、自评通过、执行合并 |
| 审阅方 | 独立复现、独立裁定；唯一的合入决定者 | 结论外推到其他 HEAD |

## 3. 审阅记录惯例

- 位置：`docs/reviews/`。
- 命名：初审 `YYYY-MM-DD-<主题>-review.md`；复审 `YYYY-MM-DD-<主题>-rereview-<短 HEAD>.md`。
- 抬头固定字段：审阅日期、PR、基线、**固定 HEAD**、本轮 fixed point（复审）、本轮提交、本轮范围、变更规模、审阅方式、当前结论。
- 抬头后紧跟一句显式声明：本结论只绑定该精确 HEAD，任何新提交都必须重新锁定 HEAD 并执行新的独立审阅。
- 结论取值：**Request changes，禁止合入** / **Approve，可以合入**。
- 正文分节：`## Findings`（无问题时写「无。」）、`## 上轮阻断关闭情况`（复审）。
- Finding 以 `### [Critical|Important] <标题>` 开头，附「位置」文件行号清单与真实执行输出。

## 4. 提交与分支

- 提交信息：英文 Conventional Commits（`feat:` / `fix:` / `docs:` / `chore:`），带 `Co-Authored-By` trailer。
- 分支：专用分支 + GitHub PR；合入后残留的已合并远端分支由 `branch-hygiene.yml` 检出并要求删除。
- 过程档案（任务简报、整改报告、外审原文、diff）落 `.superpowers/sdd/`，该目录被 `.gitignore` 整体忽略，不进版本库。

## 5. 禁令：项目层内容永不回灌分发包

`tests/test_template_contract.py` 的 `FORBIDDEN_PRODUCER_TOKENS` 禁止 `template/.harness/` 内出现生产者上下文 token，其中包括字面量 `scaffold`；唯一豁免是 bundled `LICENSE` 中的一行版权声明。

因此消费者副本 `.harness/` 下的 `rules/project.md`、`wiki/*`、`changes/*` **永不**流入 `template/.harness/`。两棵树的物理分离是 ADR-0001 的明确裁决（拒绝「把 `.harness/` 直接作为本仓库自身实例」，理由是复制时会混入生产者上下文）。

若某条项目层内容被判定为**栈级可复用**（对任何 Python 项目都成立），它的去向是 v2 的技术栈层，而不是直接回灌分发包；上抬前须去除全部项目上下文并译为英文。

## 6. v3 `upgrade` 需求证据（接入 #1 实测）

本项目被迫采用**删除重装**的手工同步，证据与代价如下：

- v1 CLI 只有 `init` / `adapt` / `validate`，无 `upgrade`（`python3 .harness/bin/harness.py --help` 实测）。
- `init` 在目标已存在 `.harness/` 时以稳定错误码 `INIT_TARGET_EXISTS`（"a .harness directory already exists; refusing to overwrite"）拒绝，无 `--force`、无合并能力（`template/.harness/bin/harness.py:929-931`）。
- 因此分发包每次演进，消费者副本的同步流程是：备份项目层资产 → 删除 `.harness/` → `init --target .` → 放回项目层资产 → **重新在 `manifest.json` 注册项目层组件** → 重跑 7 条门禁。

代价（v3 应消除的）：

1. **定制资产保全靠人工**。备份/放回全凭交付者记忆，漏一个文件就静默丢失项目层定制。
2. **manifest 注册必然丢失，且丢失后门禁静默放行**。`init` 写入的是分发包原版 manifest，`project-rules` 组件注册每次都要手工重加。实测（重装后放回 `rules/project.md` 但忘记重新注册）：

   ```text
   $ python3 .harness/bin/harness.py validate
   Harness contract is valid.
   validate=0
   $ python3 .harness/bin/harness.py adapt --check
   adapt: ok
   adaptcheck=0
   $ grep -c project-rules CLAUDE.md
   0
   ```

   两条消费者门禁全绿，而三个投影文件里已经没有 `project-rules` —— Agent 从此看不到项目规则。原因是 `init` 会按新 manifest 重新生成投影，manifest 与投影**一致地**都少了这个组件；校验器只检查已注册项的一致性，无从知道曾经注册过什么，未注册的多余文件也不构成契约违规。这是当前机制下**最危险的一处静默失败**。（对照：若只删注册而不重装，旧投影仍列着该组件，`adapt --check` 会以 `PROJECTION_STALE` 报错——保护恰好在最需要它的重装路径上失效。）
3. **Change Record 历史随目录删除**，必须一并备份，否则交付历史丢失。
4. **无法回答「我落后了什么」**。没有版本差异视图，只能靠 `diff -r template/.harness .harness` 人工比对，而该比对会把项目层资产也报成差异（噪声）。

结论：v3 的升级能力至少需要「保留项目层资产的三方合并」与「manifest 组件注册的持久化/再注册」两项，否则手工同步的静默失败面无法收敛。本节为 `docs/design/harness-v2-planning.md` §2 要求的接入反馈之一。

## 7. 待补充

- 日常交付中真实用到的 Change Record 粒度惯例（一个 PR 一条？一个任务一条？）——需积累若干次交付后归纳。
- 消费者 Change Record（`.harness/changes/`）与 `docs/plans/` + `docs/reviews/` 的职责边界，目前是「Change Record 记交付证据、docs/reviews 记独立审阅结论」的初步分工，待实践验证。
