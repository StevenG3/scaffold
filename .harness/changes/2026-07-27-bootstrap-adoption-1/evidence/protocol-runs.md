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
> 永远差一步。**去镜像**把这一类缺陷的入口收窄到一个**显式白名单**：记录中除机器生成产物外不得出现现刻数字断言，由 `check_current_numbers.py` 机械核查；**其域、词表、豁免、自检形态与冻结条款一律以 `run-manifest.md` 的「检查器现状（SSOT）」节为准**，本处不复述。第 11 轮删的是 **Git 可导出**的一类，第 12 轮补上 **脚本可导出**的一类。**此处不再声称「结构上不再可能」**——会话 C 用 `run-manifest.md:49` 的残值证伪过那个无界说法；能声称的只是「白名单之外的数字会被核查命令抓住」。

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
| 第 5 步 产物不变量 | 脚本 SHA-256 `1020c231b9b5e11b43d0febb2e05e8e25ed9e6e092f4e222f2c3a5a0f90c8fd3`；结果摘要 `20ad0f5005822570f955e0542e7446b21f962b187c630b08d75d5f1d7f4a6b6d` |
| 第 6 步 变异探针 | 穷举投毒：`--emit-markdown` `rc=1`；`--emit-markdown PATH` `rc=1` 且**正式文件逐字节未变**；横幅为首行。未抽中输入探针 `digest_changed=False`（与收窄后的检测范围声明一致，非缺陷） |
| 第 6 步 结构攻击（本轮新增） | 审阅方反例（end 哨兵前移至 marker 之后、FAIL 行之前）**被拒**；premature end / late begin / 空视图 / 仅 marker / 缺 layer / 缺 attestation 六种形状全部**被拒**；真实非零层在**两个出口**仍 fail closed |
| 第 7 步 七条门禁 | **全部**门禁 exit 0（门禁条目见 `rules/project.md` §2；分流字节数与条目数按去镜像约定不抄录，复核请用 `capture_gate` 包装器实测） |
| 第 8 步 复锁 | 提交并推送后由 PR 正文指针给出 exact-head 的 SHA 与 CI run id |

### 清单纪律：被取代的行必须同提交删除

**清单的不变量是「每一行当下可复跑且期望成立」，而不是「只增不删的历史」。**
第八次复发就发生在这里：上一轮用新行取代了两条旧行，却把旧行留在表里，
于是它们继续断言「每文件单变体轮换」与「`.md` 全域」——两句都已被同一提交证伪。
**新行取代旧行时，旧行必须在同一提交中删除**；需要保留的历史叙述写进整改记录，不留在清单里。

### 修复纪律：finding 必须按内容寻址

审阅给出的行号**只是起点**。同一个错误字符串往往在记录里出现多次——
R13 按 C 给的行号修了 `run-manifest.md`，却没有对同一字符串做全目录检索，
于是 `summary.md` 里逐字相同的一处原样留存，成为**同一缺陷的第六次复发**。

因此本轮起：**收到 finding 后，先对其字符串/模式在整个 Change Record 目录做
`grep -rn`，拿到全部命中，逐一处置；行号仅用于定位第一处。**
落地自核清单必须给出每个原违规字符串的**全目录终态**（0 命中，或全部转为历史绑定行）。

### 内容寻址扫描记录（**每轮必填**，空表即视为未执行）

内容寻址纪律写在文档里两轮之后仍被违反——**第九次复发与第六次完全同形**：
删了两行清单行，却没有对**这两行的断言字符串**做全库 `grep`，于是它们的原文
继续活在叙事段里，而同一份记录在另一处已把其中一句定性为缺陷。

结论：**纪律必须变成清单里的格子，否则不会被执行。** 本节自 R17 起为固定小节，
每轮列出：finding 涉及的**字符串/模式**与**机制关键词** × 全库命中数 × 逐处处置终态。

**查找必须做到「断言级」**：只搜字面串会漏掉**同一断言的转述**——第十次复发即如此（两条被废止断言的四处活体转述未被绑定，因为它们的措辞与被删行不同字）。因此除字面串外，还须对该 finding 的**机制关键词**逐词全库 `grep`，每个命中归类为：**SSOT 内** / **指针** / **节级历史域内** / **违规→处置**。

| 字符串 / 模式 | 全库命中 | 逐处处置终态 |
| --- | --- | --- |
| `每个被扫文件各注入一次` | 记录正文已清零；仅剩本小节自身的两处引用（本表一行 + 下方核查命令一行） | 叙事段原句改写为历史绑定表述（`历史@c399394`），并注明已被后续轮次两次取代。**核查命令因此排除本文件**——把自己的引用算进命中，就是又一个自指 |
| `三种记法` | 未绑定命中 0（`summary.md` 的该句已在 R17 改写为不含此串的表述；`tasks.md` 一处带 `历史@c399394`） | 叙事段改写 + 历史绑定；**本格首次填写时写成「summary 一处」，实为 0——填表本身也要复跑，不能凭印象** |
| `整个 Change Record 目录全部 .md 全文` | 剩余命中全部带 `历史@` 绑定 | 域自 R15 起含 `.py` 注释与 docstring；原句改为当轮历史 + 指向轴表 |
| 无界句「…只存在于机器生成产物中」（PR 正文复活） | PR 正文一处 | 改为缩面表述：机器保证仅及轴表覆盖域，其余为命令 / 白名单 / 历史绑定 |
| 单行 docstring 未被扫描（C2） | 实现缺陷，无字符串命中 | 已修复并加自检变体；**形态与覆盖范围以 `run-manifest.md`「检查器现状（SSOT）」节为准**，此处不复述 |

### 机制关键词归类（断言级扫描，R18 起随扫描记录一并提交）

对机制关键词逐词全库 `grep`，每个命中归入四类之一。**未归类即视为违规。**

| 关键词 | 命中归类 |
| --- | --- |
| 全文域 / 句式禁令 / 检查域 / 被扫文件 | SSOT 节内、指针、或节级历史域内 |
| 叉积 / 变异验证 / 逐文件 / 逐记法 | 同上 |
| 冻结 | SSOT 节（含豁免条款）或节级历史域 |
| prose_lines / 单行 docstring | 代码实现、SSOT、指针或节级历史域 |

归类统计**不在此抄录**（它是脚本可导出的现刻数字）——复跑上述归类命令即得，
唯一必须成立的条件是：**「违规→需处置」一类为空**。

> **归类口径**：SSOT = `run-manifest.md`「检查器现状（SSOT）」节内；
> 指针 = 行内明确指向 SSOT；节级历史域 = 位于带「本节为该轮历史（历史@…）」声明的小节内；
> 其余为代码标识符、扫描记录小节自身引用，或**违规**。

核查命令（可复跑）：

```sh
D=.harness/changes/2026-07-27-bootstrap-adoption-1
# 节级排除：只排除「内容寻址扫描记录」小节自身（它必须引用这些串），
# 不再整文件排除——文件级排除会把同文件其他位置的真违规一并掩掉。
scan_only() {   # 打印除扫描记录小节之外的全部命中
  grep -rn "$1" $D | grep -v "$(printf 'protocol-runs.md:%s' "$(awk '/^### 内容寻址扫描记录/{s=NR} /^### 落地核对清单/{e=NR} END{printf "(%d|%d)", s, e}' $D/evidence/protocol-runs.md)")"
}

# 更简单且稳定的等价做法：把扫描记录小节从文件中切掉后再搜
sed '/^### 内容寻址扫描记录/,/^### 落地核对清单/d' $D/evidence/protocol-runs.md > /tmp/pr-noscan.md
grep -rn "每个被扫文件各注入一次" $D --include=*.md | grep -v "evidence/protocol-runs.md" | wc -l   # 期望 0
grep -n "每个被扫文件各注入一次" /tmp/pr-noscan.md | wc -l                                          # 期望 0
grep -rn "三种记法" $D | grep -v "历史@" | grep -v "evidence/protocol-runs.md" | wc -l              # 期望 0
grep -n "三种记法" /tmp/pr-noscan.md | grep -v "历史@" | wc -l                                      # 期望 0
```

### 落地核对清单（本提交声称的每一处修复）

命令可直接运行（路径为仓库根相对路径）；期望值写的是**真实期望**，不是「越少越好」。

| 声称的修复 | 核对命令 | 期望 |
| --- | --- | --- |
| 视图结构完整性校验存在 | `grep -c "_layer_rows\|_attested_classes" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py` | ≥ 2 |
| 结构攻击回归全绿 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -cE "(premature end\|late begin\|removed begin\|empty view\|marker-only\|missing layer row\|missing attestation).*PASS"` | 7 |
| 去镜像：记录中无现刻数字断言 | `sed -n '/^## 结果/,/^### 红基线/p' .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/run-manifest.md \| grep -cE "定向用例数 \|分支 \(a\) 命中"` | 0 |
| 去镜像：Git 统计量仅在病灶引述中出现 | `grep -rn "+42/-8\|+60/-27" .harness/changes/2026-07-27-bootstrap-adoption-1 | grep -v "内容寻址\|落地核对"` | 剩余命中**全部落在描述该病灶的叙述句内**（句中含「差异统计」或「与 Git 不符」等上下文串），无任何现刻断言；**期望以内容锚给出，不再用行号坐标**——行号会随任何编辑漂移 |
| umask 韧性 | `( umask 177; python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py >/dev/null 2>&1; echo $? )` 与 `grep -c Traceback` | exit 1 且 traceback 计数 0 |
| 起始哨兵定向用例 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -c "begin sentinel literal"` | 1 |
| 核查的参数域 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --bogus` | exit 2 |
| 历史豁免形态 | `grep -c "历史@" .harness/changes/2026-07-27-bootstrap-adoption-1/summary.md` | 非零——历史行已迁移到**显式绑定记号** `历史@<hex>`；旧式「散落 hex + 历史」不再豁免 |
| 旧式豁免逃逸 | 上条自检中的两个逃逸样本 | 均 `caught=True`（终验给出的原文：引用 commit id 走私现刻数字） |
| 生成表可字节再生 | `g=$(mktemp); python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py --emit-markdown "$g"; cmp "$g" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/boundary-cases.md` | `cmp` 无输出且 exit 0——入库表与当场再生的字节完全一致 |
| 现刻数字断言：覆盖域终态 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py` | exit 0，并打印扫描到的文件数与域说明；**声称仅限载体自由度表标记为覆盖的轴**，开放轴见该表 |
| 变异验证：文件 × 记法叉积 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --self-test` | 每个文件 × 每个变体全部 `caught=True`（**变体集合与自检形态见 SSOT 节**），打印句与实现一致；变体含裸数字、逗号格式、反引号包裹、两条历史豁免逃逸样本、英文注释形态 |
| 单行 docstring 覆盖（C2） | `grep -A 14 "^SELF_TEST_VARIANTS" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py \| grep -c '"""'` | 非零——变体集合含单行 docstring 形态（**覆盖声称见 SSOT 节**）。轴表声称「`.py` 注释与 docstring = 覆盖」，而此前该形态从未被扫（三引号同行成对，旧解析只认奇数个），属**已声称覆盖域内的实现缺陷**，已补齐 |
| 核查器的源码编码 | `python3 -c "import pathlib;print(sum(1 for b in pathlib.Path('.harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py').read_bytes() if b>0x7e))"` | **非零**——该文件不是纯 ASCII，因为它要在定义处逐字列出被禁的中文标记词；纯 ASCII 纪律只约束被哈希存证的 `carrier_sweep.py`，已在其 docstring 中明示 |
| 无非预期未完成任务 | `grep -c "^- \[ \]" .harness/changes/2026-07-27-bootstrap-adoption-1/tasks.md` | 1（仅剩预期中的后续项） |
