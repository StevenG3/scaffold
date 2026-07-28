# 协议执行记录（可复现审阅协议的历次运行）

本文件把**协议运行的观察值落进仓库**。此前会话 C 的完整运行只在对话中披露、
从未入库——外部审阅第 10 轮把这记为 I3：**未入库的证据等于不存在**，
与「扫描表留在被 git 忽略的临时目录」是同一类错误。

记录约定：

- **历史条目**绑定其运行时的精确 HEAD，事后不修改；
- **当前条目**的约定（**去镜像**，本轮由外部第 11 轮 I2 定案）：

  **不记录任何 Git 或命令可以事后自行导出的统计量。** 差异统计、文件数、
  `rev-list` 计数写进记录，就必然与它所在的那个提交互相追逐——
  这是同一缺陷的第三次复发（记录 4 文件 `+42/-8`，真实 5 文件 `+60/-27`）。
  它们一律**替换为命令**，由复核者当场执行：

  ```sh
  # 本记录所在提交的增量与边界（复核者执行，勿抄录结果）
  git show --stat HEAD
  git diff --name-status <前驱>..HEAD
  git rev-list --count <前驱>..HEAD
  git diff --exit-code <base>...HEAD -- template/     # 零回灌
  ```

  当前条目**只保留两类事实**：

  1. **机器生成产物本身**（脚本、生成表）——它们是被描述的对象，不是对提交的描述；
  2. **最小不变量**：脚本 SHA-256 与结果摘要。这两个值描述的是**产物内容**，
     不随「哪个提交包含它们」而变，因此不存在自指追逐。

  其余一切（时间、角色、结论）作为**带时点的历史**记录。
  提交后的 SHA / `rev-list` / CI run id 由 **PR 正文指针**给出，
  并在每次 push 后的**指针刷新步骤**中更新为 exact-head 的 run id。

---

## 历史条目：会话 C 全机械协议运行

- 运行时间：2026-07-28
- 绑定 HEAD：`30f95e639a3e696d25d5737ddd3c11049ce93251`
- 角色：会话 C（合并 + 机械步骤）
- 结论：**READY**（六维 23/24）

| 步骤 | 观察值 |
| --- | --- |
| 第 1 步 远端锁定 | `headRefOid=30f95e63`，`MERGEABLE` / `CLEAN`，`Validate Harness` = SUCCESS，run `30326614745` |
| 第 2 步 增量与边界 | 单个 audit commit，零回灌（**当轮历史记述**；差异统计已按去镜像约定移除，复核请执行上文命令） |
| 第 5 步 绿灯电池 | 全绿；digest `837bab63…`；collector `297`；脚本 SHA `e734a5ac…` |
| 第 6 步 变异探针 | 两个探针均达到 post-fix 预期 |
| 第 7 步 七条门禁 | 7/7 通过，分流字节数 `27/0, 27/0, 99/0, 0/23861, 0/0, 27/0, 10/0` |
| 第 8 步 复锁 | clean |
| A/B 反例 | 全部关闭 |

---

## 当前条目：最终内容态的机械终检（实现方自跑，C 式）

- 运行时间：2026-07-28
- 角色：实现方在最终内容态自跑 C 式机械终检（外部第 11 轮 I3 要求落库）
- 前驱 HEAD（第 1 步锁定对象）：`351c70aa7670e416decf1b77c1a9903290cd9a28`
- 绑定：**本记录随其所在提交生效**；该提交的 SHA、`rev-list` 计数与 CI run id 见 PR 正文指针

> **本节两次犯过它要防的病**：先是逐字沿用前一提交的数值，再是记录了一份
> 与 Git 不符的差异统计（记 4 文件 `+42/-8`，真实 5 文件 `+60/-27`）。
> 根因不是粗心，而是**把可导出的统计量抄进记录**——记录与它所在的提交互相追逐，
> 永远差一步。**去镜像**之后这一类缺陷在结构上不再可能：记录里没有这些数字了。

### 复核者应执行的命令（本记录不抄录其输出）

```sh
git show --stat HEAD
git diff --name-status 351c70aa7670e416decf1b77c1a9903290cd9a28..HEAD
git rev-list --count 351c70aa7670e416decf1b77c1a9903290cd9a28..HEAD
git diff --exit-code e338db8936a07b2f102df6fbd0bfa900577545b7...HEAD -- template/
gh pr view 7 --repo StevenG3/scaffold \
  --json state,isDraft,baseRefOid,headRefOid,mergeable,mergeStateStatus,statusCheckRollup
```

### 机械步骤的观察值（只保留产物不变量与退出语义）

| 步骤 | 观察值 |
| --- | --- |
| 第 1 步 远端锁定 | 锁定前驱 HEAD：`state=OPEN` `draft=true` `mergeable=MERGEABLE` `mergeState=CLEAN`（当次实测） |
| 第 2 步 增量与边界 | **按去镜像约定不抄录统计量**；`git diff main -- template/` 实测为空（零回灌） |
| 第 5 步 绿灯电池 | `default 0` / `--baseline 0` / `--help 0` / `--emit-markdown PATH 0`；生成物与入库表 `cmp` 逐字节一致；非 ASCII 字节 **0**；定向 **75/0**；红基线 `directed cases: 75, failures: 30` |
| 第 5 步 产物不变量 | 脚本 SHA-256 `f4ffcb94994488bedd312e3099d9be81a479cf353a736bcde325cbb02e8bf24b`；结果摘要 `20ad0f5005822570f955e0542e7446b21f962b187c630b08d75d5f1d7f4a6b6d` |
| 第 6 步 变异探针 | 穷举投毒：`--emit-markdown` `rc=1`；`--emit-markdown PATH` `rc=1` 且**正式文件逐字节未变**；横幅为首行。未抽中输入探针 `digest_changed=False`（与收窄后的检测范围声明一致，非缺陷） |
| 第 6 步 结构攻击（本轮新增） | 审阅方反例（end 哨兵前移至 marker 之后、FAIL 行之前）**被拒**；premature end / late begin / 空视图 / 仅 marker / 缺 layer / 缺 attestation 六种形状全部**被拒**；真实非零层在**两个出口**仍 fail closed |
| 第 7 步 七条门禁 | 7/7 exit 0（分流字节数按去镜像约定不抄录；复核请用 `capture_gate` 包装器实测） |
| 第 8 步 复锁 | 提交并推送后由 PR 正文指针给出 exact-head 的 SHA 与 CI run id |

### 落地核对清单（本提交声称的每一处修复）

| 声称的修复 | 核对命令（对已提交树） | 期望 |
| --- | --- | --- |
| I1 视图结构完整性校验 | `git show HEAD:<evidence>/carrier_sweep.py \| grep -c "_layer_rows\|_attested_classes"` | ≥ 1 |
| I1 六种结构攻击回归 | `python3 <evidence>/carrier_sweep.py \| grep -c "refused *PASS"` | 6 |
| I2 去镜像（记录内无差异统计） | `grep -c "文件 \`+" <evidence>/protocol-runs.md` | 0（仅在说明病灶处以历史口吻出现） |
| I3 终检与清单入库 | 本节存在于 `protocol-runs.md` | 存在 |
| Minor 起始哨兵定向用例 | `python3 <evidence>/carrier_sweep.py \| grep -c "begin sentinel literal"` | 1 |
