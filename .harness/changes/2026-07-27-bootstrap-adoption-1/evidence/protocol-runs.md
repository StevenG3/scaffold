# 协议执行记录（可复现审阅协议的历次运行）

本文件把**协议运行的观察值落进仓库**。此前会话 C 的完整运行只在对话中披露、
从未入库——外部审阅第 10 轮把这记为 I3：**未入库的证据等于不存在**，
与「扫描表留在被 git 忽略的临时目录」是同一类错误。

记录约定：

- **历史条目**绑定其运行时的精确 HEAD，事后不修改；
- **现刻条目**的约定（**去镜像**，由外部第 11 轮 I2 定案）：

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
> 永远差一步。**去镜像**把这一类缺陷的入口收窄到一个**显式白名单**：记录中除机器生成产物外不得出现现刻数字断言，由 `check_current_numbers.py` 对整个 Change Record 全文机械核查（该命令已做逐文件、逐记法的变异验证，能失败）。第 11 轮删的是 **Git 可导出**的一类，第 12 轮补上 **脚本可导出**的一类。**此处不再声称「结构上不再可能」**——会话 C 用 `run-manifest.md:49` 的残值证伪过那个无界说法；能声称的只是「白名单之外的数字会被核查命令抓住」。

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
| 第 5 步 绿灯电池 | `default 0` / `--baseline 0` / `--help 0` / `--emit-markdown PATH 0`；生成物与入库表 `cmp` 逐字节一致；源码**无**非 ASCII 字节（`grep -c '[^ -~]'` 输出为空）。**定向数、失败数、红基线数字按去镜像约定不抄录**——运行上述命令，或读机器生成的 `boundary-cases.md` |
| 第 5 步 产物不变量 | 脚本 SHA-256 `edd1e762a905e006c796d73d4210df0f4cd6ed1d170045a5a3d120926e6261ee`；结果摘要 `20ad0f5005822570f955e0542e7446b21f962b187c630b08d75d5f1d7f4a6b6d` |
| 第 6 步 变异探针 | 穷举投毒：`--emit-markdown` `rc=1`；`--emit-markdown PATH` `rc=1` 且**正式文件逐字节未变**；横幅为首行。未抽中输入探针 `digest_changed=False`（与收窄后的检测范围声明一致，非缺陷） |
| 第 6 步 结构攻击（本轮新增） | 审阅方反例（end 哨兵前移至 marker 之后、FAIL 行之前）**被拒**；premature end / late begin / 空视图 / 仅 marker / 缺 layer / 缺 attestation 六种形状全部**被拒**；真实非零层在**两个出口**仍 fail closed |
| 第 7 步 七条门禁 | **全部**门禁 exit 0（门禁条目见 `rules/project.md` §2；分流字节数与条目数按去镜像约定不抄录，复核请用 `capture_gate` 包装器实测） |
| 第 8 步 复锁 | 提交并推送后由 PR 正文指针给出 exact-head 的 SHA 与 CI run id |

### 修复纪律：finding 必须按内容寻址

审阅给出的行号**只是起点**。同一个错误字符串往往在记录里出现多次——
R13 按 C 给的行号修了 `run-manifest.md`，却没有对同一字符串做全目录检索，
于是 `summary.md` 里逐字相同的一处原样留存，成为**同一缺陷的第六次复发**。

因此本轮起：**收到 finding 后，先对其字符串/模式在整个 Change Record 目录做
`grep -rn`，拿到全部命中，逐一处置；行号仅用于定位第一处。**
落地自核清单必须给出每个原违规字符串的**全目录终态**（0 命中，或全部转为历史绑定行）。

### 落地核对清单（本提交声称的每一处修复）

命令可直接运行（路径为仓库根相对路径）；期望值写的是**真实期望**，不是「越少越好」。

| 声称的修复 | 核对命令 | 期望 |
| --- | --- | --- |
| 视图结构完整性校验存在 | `grep -c "_layer_rows\|_attested_classes" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py` | ≥ 2 |
| 结构攻击回归全绿 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -cE "(premature end\|late begin\|removed begin\|empty view\|marker-only\|missing layer row\|missing attestation).*PASS"` | 7 |
| 去镜像：记录中无现刻数字断言 | `sed -n '/^## 结果/,/^### 红基线/p' .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/run-manifest.md \| grep -cE "定向用例数 \|分支 \(a\) 命中"` | 0 |
| 去镜像：Git 统计量仅在病灶引述中出现 | `grep -n "+42/-8\|+60/-27" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/protocol-runs.md \| grep -v '^[0-9]*:|'` | 恰 **2** 行：第 14 行（第 11 轮 I2 的病灶描述）与第 64 行（现刻条目的引述）。`grep -v '^[0-9]*:|'` 排除本清单自身那一行——**核对命令若把自己算进去，就是又一个自指**。 |
| umask 韧性 | `( umask 177; python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py >/dev/null 2>&1; echo $? )` 与 `grep -c Traceback` | exit 1 且 traceback 计数 0 |
| 起始哨兵定向用例 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -c "begin sentinel literal"` | 1 |
| **现刻数字断言核查（全文域）** | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py` | exit 0，且打印「scanned N markdown file(s) in full」——域是整个 Change Record 的全部 `.md`（生成表除外），**无行号窗口、无反引号置盲** |
| **该核查的变异验证** | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --self-test` | **每个被扫文件各注入一次**，三种记法（裸数字 / 逗号格式 / 反引号包裹）轮换，全部 `caught=True` 才过；注入仅在内存中，**不修改任何文件** |
| 核查的参数域 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --bogus` | exit 2 |
| 原违规字符串的全目录终态 | `grep -rn "当前定向用例为" .harness/changes/2026-07-27-bootstrap-adoption-1` | 仅剩两类命中，均合法：本清单自身引用该模式的行，以及 `summary.md` 中**历史绑定**的 finding 描述（含「历史」与当轮 HEAD）。**无任何现刻断言**——由 `check_current_numbers.py` exit 0 兜底 |
| 原违规字符串的全目录终态 | `grep -rn "当前为" .harness/changes/2026-07-27-bootstrap-adoption-1` | 仅剩本清单自身引用该模式的行 |
| 死指针的全目录终态 | `grep -rn "「当前结果」" .harness/changes/2026-07-27-bootstrap-adoption-1` | 仅剩本清单自身引用该模式的行；记录正文中的死指针已全部改指机器生成的 `boundary-cases.md` |
| 核查器的源码编码 | `python3 -c "import pathlib;print(sum(1 for b in pathlib.Path('.harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py').read_bytes() if b>0x7e))"` | **非零**——该文件不是纯 ASCII，因为它要在定义处逐字列出被禁的中文标记词；纯 ASCII 纪律只约束被哈希存证的 `carrier_sweep.py`，已在其 docstring 中明示 |
| 无非预期未完成任务 | `grep -c "^- \[ \]" .harness/changes/2026-07-27-bootstrap-adoption-1/tasks.md` | 1（仅剩预期中的后续项） |
