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

## 当前条目：R23 最终内容态的机械终检（实现方自跑，C 式）

> **重跑惯例（R19 起，R22 起有红命令背书）**：本节**每轮必须整体重跑并重写**，
> 不得沿用上一轮的观察值。节标题带轮次、条目内绑定**当轮**前驱 HEAD。
>
> **这条惯例自己刚刚证明了 R19 的教训**：它写成散文义务却没有清单格子，
> 于是 R20、R21 两轮都没重跑，标题停在 R19、前驱停在 历史@6507a986，
> 外审按下方命令跑 `rev-list` 得到的是三，不是一——
> **「纪律必须变成清单格子才会被执行」这句话，在写下它的那一节上第二次应验。**
> 现已配落地清单的**前驱守护行**：本节记录的前驱必须等于 `git rev-parse --short=8 HEAD^`。
> 该行一红，就说明本节没跟着这轮重跑；而轮次标签与前驱同处一节，
> 因此重写本节时标签必然一起更新——**用一个可执行的等式，守住一整节的新鲜度。**

- 运行时间：2026-07-29
- 角色：实现方在最终内容态自跑 C 式机械终检（外部第 11 轮 I3 要求落库）
- 前驱 HEAD（第 1 步锁定对象）：`c7aa54c1`
- 绑定：**本记录随其所在提交生效**；该提交的 SHA、`rev-list` 计数与 CI run id 见 PR 正文指针

> **本节两次犯过它要防的病**：先是逐字沿用前一提交的数值，再是记录了一份
> 与 Git 不符的差异统计（记 4 文件 `+42/-8`，真实 5 文件 `+60/-27`）。
> 根因不是粗心，而是**把可导出的统计量抄进记录**——记录与它所在的提交互相追逐，
> 永远差一步。**去镜像**把这一类缺陷的入口收窄到一个**显式的豁免集合**（其构成见 SSOT 节；旧称「白名单」的框架已撤回）：记录中除机器生成产物外不得出现现刻数字断言，由 `check_current_numbers.py` 机械核查；**其域、词表、豁免、自检形态与冻结条款一律以 `run-manifest.md` 的「检查器现状（SSOT）」节为准**，本处不复述。第 11 轮删的是 **Git 可导出**的一类，第 12 轮补上 **脚本可导出**的一类。**此处不再声称「结构上不再可能」**——会话 C 用 `run-manifest.md:49` 的残值证伪过那个无界说法；能声称的只是「豁免集合之外的数字会被核查命令抓住」。

### 复核者应执行的命令（本记录不抄录其输出）

```sh
git show --stat HEAD
git diff --name-status c7aa54c1..HEAD
git rev-list --count c7aa54c1..HEAD        # 在交付 HEAD 上应为一
git diff --exit-code e338db8936a07b2f102df6fbd0bfa900577545b7...HEAD -- template/
gh pr view 7 --repo StevenG3/scaffold \
  --json state,isDraft,baseRefOid,headRefOid,mergeable,mergeStateStatus,statusCheckRollup
```

### 机械步骤的观察值（只保留产物不变量与退出语义）

| 步骤 | 观察值 |
| --- | --- |
| 第 1 步 远端锁定 | 锁定前驱 HEAD：`state=OPEN` `draft=true` `mergeable=MERGEABLE` `mergeState=CLEAN`（当次实测） |
| 第 2 步 增量与边界 | **按去镜像约定不抄录统计量**；`git diff main -- template/` 实测为空（零回灌） |
| 第 5 步 绿灯电池 | `default 0` / `--baseline 0` / `--help 0` / `--emit-markdown PATH 0`；生成物与入库表 `cmp` 逐字节一致；源码**无**非 ASCII 字节（`grep -c '[^ -~]'` 输出为零，与落地清单对应行同口径）。**定向数、失败数、红基线数字按去镜像约定不抄录**——运行上述命令，或读机器生成的 `boundary-cases.md` |
| 第 5 步 产物不变量 | 脚本 SHA-256 与结果摘要**见 `run-manifest.md` 的「本节保留的唯一两个不变量」小节**（R20 起全库唯一抄本，此处不复制）；R22、R23 两轮均未触碰该脚本，两值不变，由清单的两条守护行当场核对 |
| 第 6 步 变异探针 | 穷举投毒：`--emit-markdown` `rc=1`；`--emit-markdown PATH` `rc=1` 且**正式文件逐字节未变**；横幅为首行。未抽中输入探针 `digest_changed=False`（与收窄后的检测范围声明一致，非缺陷） |
| 第 6 步 结构攻击（R14 新增，此后每轮复跑） | 审阅方反例（end 哨兵前移至 marker 之后、FAIL 行之前）**被拒**；premature end / late begin / 空视图 / 仅 marker / 缺 layer / 缺 attestation 六种形状全部**被拒**；真实非零层在**两个出口**仍 fail closed |
| 第 6 步 过滤器变异（R22 新增，R23 按实测改写并入库为可复跑样本） | `dehist.awk` 锚定修正后，对 `protocol-runs.md` 不再致盲（旧写法会把该节与落地清单整段抹掉却仍打印零——新旧两版对跑实测）。`cells.awk` 改以分隔行定基准后，三个构造样本的新旧对照为：**缺分隔行**由**零报告**变为报错（这是旧版真正的静默洞）；**坏表头**旧版报错但**归因错行**（以坏表头为基准，反判分隔行与正文行），新版定位到表头行本身；**坏正文行**两版一致 |
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

| 字符串 / 模式（含英文） | 域外命中 | 逐处处置终态 |
| --- | --- | --- |
| `每个被扫文件各注入一次` | 0 | R17 已改写为历史绑定表述 |
| `三种记法` | 0 | 仅存于轮次历史节内的引用，按域定义不计 |
| `整个 Change Record 目录全部` | 0 | R17 已改写并指向 SSOT |
| `exactly two`（英文） | 0 | 检查器 docstring 已指针化，不再自报豁免族数 |
| `every other .md`（英文） | 0 | 域的描述只留在 SSOT |
| `1020c231`（旧脚本 SHA 前缀） | 0 | R20 单点化：全库不再有旧抄本 |
| `第 13 轮`（错误轮次标签） | 0 | 已改回第 12 轮；PR 正文轮次表补轨道列与切换说明 |
| `6507a986`（陈旧前驱 HEAD，排除 `历史@` 绑定） | 0 | 该节已重跑，前驱改绑 R22；叙述该缺陷的一处已用 `历史@` 显式绑定 |
| `R19 最终内容态`（陈旧节标题） | 0 | 该节标题已改为 R22 |
| `pure ASCII`（英文，排除 `.py` 源码自述） | 0 | 两处源码自述属实现层，其余仅存于历史节内 |
| `静默放行`（R22 的假机理措辞） | 0 | 三处已按新旧对照改写；仅存于 R23 历史节内，且是「旧版**并非**静默放行」的否定式表述 |

**结构性核查（同一 shell 块，与上表一并复跑）**：

| 核查 | 期望 |
| --- | --- |
| `sed` 排除后终止行仍在 | 恰一处 |
| `dehist.awk` 用于 `protocol-runs.md` 后该节仍在 | 恰一处（F4 致盲反例） |
| `dehist.awk` 用于 `protocol-runs.md` 后「落地核对清单」仍在 | 恰一处（同上） |
| `cells.awk` 全库表格行格数 | `anomalous rows: 0` |
| `cells.awk` 三个构造样本 | 坏表头报**表头行本身**；缺分隔行报 `table has no separator row`；坏正文行报正文行 |
| 前驱守护 `guard.sh` | 在**交付 HEAD** 上 `guard exit=0`；提交前跑必红（前驱要到提交存在后才成立） |
| 叙事节作用域声明无遗漏 | `grep '^live'` 只剩结构节（`Status` / `Result` / `Verification evidence` / `Exceptions` / `Decision` / `Phase A` / `Phase B` 三节） |

> **域的定义（R21 起，R22 如实化）**：
> 字面串扫描的域 = 全语料 − 下列排除项：
> **(a)** `protocol-runs.md` 上由 `sed` 切掉的**两个子节**（本扫描记录小节 + 机制关键词归类小节）；
> **(b)** `summary.md` 与 `tasks.md` 上由 `dehist.awk` 抹空的**历史节**——现存历史节**只在此二文件**，
> 故过滤器也**只应用于**它们。两条排除不是同一机制，也不互相替代。
>
> 轮次历史节内引用 finding 字符串是**构造良性**的：节头已声明历史作用域，
> 节内的引用按定义就是历史引用。需要审计这些引用时，用不带排除的原始 `grep -rn`——那是另一件事。
>
> **为什么必须这样定义域**：R20 那张表所填值低于外审当场执行的输出，差额正是那次提交
> **自己的整改叙事**——修复某个字符串，就必然要引用该字符串。旧域下这是个**不稳定不动点**：
> 填表→写整改记录→计数又变了，每轮重踩。语义化之后期望统一为 0，**不动点消失**。
>
> **过滤器自身也要被验证**：R21 的锚定按**任意行**匹配，于是任何**讨论**这条纪律的散文
> 都会把它所在的整节抹掉。上表的两条致盲反例就是为此而设——
> **一个会致盲自己的过滤器，比没有过滤器更危险：它让八个格子照样打印零。**
>
> **填表纪律**：格值 = 当场执行输出；域 = 上述定义；
> **填表必须是提交前的最后一步**——填完之后若再改动任何**非历史节**文字，必须重跑全表。

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

**节级排除的正确做法**——把「内容寻址扫描记录」小节从文件中切掉后再搜。
上一版交付的 `scan_only` 用 `awk` 生成 `(a|b)` 再喂给基本正则 `grep -v`，
括号与竖线都被当字面量，**过滤实际零匹配**；同时 `--include=*.md` 让字面串扫描
对域的 `.py` 半边**结构性失明**——而第十一次复发恰恰住在 `.py` 里。两处都已修正。

```sh
D=.harness/changes/2026-07-27-bootstrap-adoption-1
PR=$D/evidence/protocol-runs.md

# 1) 在 protocol-runs.md 上，用 sed 切掉**两个子节**：本扫描记录小节，
#    以及紧随其后的「机制关键词归类」小节——终止行是「### 落地核对清单」。
#    范围内的否定 `/^### 落地核对清单/!d` 保住终止行；朴素的 `/start/,/end/d`
#    会连下一节标题一起删掉，扫描就对整节半盲。
#    （`;}` 不可省：BSD sed 不接受紧挨的 `d}`，会报 extra characters。）
sed '/^### 内容寻址扫描记录/,/^### 落地核对清单/{/^### 落地核对清单/!d;}' "$PR" > /tmp/pr-noscan.md
grep -c '^### 落地核对清单' /tmp/pr-noscan.md      # 期望 1：终止行必须保留

# 2) 在 summary.md 与 tasks.md 上，把**带历史作用域声明的整节**抹成空行
#    （保留行号，不移位）。历史节目前只存在于这两个文件；protocol-runs.md
#    的排除走上面的 sed，两者不是同一机制，也不互相替代。
#
#    锚定很关键：只有 `^## ` 节头之后**紧邻的首个非空行**匹配历史声明，
#    才算该节是历史节。R21 的写法按**任意行**匹配，于是任何**讨论**这条纪律
#    的散文都会把它所在的整节抹掉——把它用到 protocol-runs.md 上，
#    当前条目与落地清单会被整段致盲，而八个格子照样打印零。
cat > /tmp/dehist.awk <<'AWK'
/^## /            { if (buf != "") printf "%s", (hist ? blank : buf)
                    buf=""; blank=""; hist=0; want=1 }
want && !/^## / && NF { hist = ($0 ~ /^> \*\*本节为该轮历史/); want=0 }
                  { buf = buf $0 "\n"; blank = blank "\n" }
END               { if (buf != "") printf "%s", (hist ? blank : buf) }
AWK
awk -f /tmp/dehist.awk $D/summary.md > /tmp/summary-nohist.md
awk -f /tmp/dehist.awk $D/tasks.md   > /tmp/tasks-nohist.md

# 2b) 锚定的反例验证：把过滤器用到 protocol-runs.md 上，它必须**不**致盲。
awk -f /tmp/dehist.awk $PR > /tmp/pr-dehist.md
grep -c '^## 当前条目'      /tmp/pr-dehist.md   # 期望：恰一处（该节必须存活）
grep -c '^### 落地核对清单' /tmp/pr-dehist.md   # 期望：恰一处（同上）

# 3) 在**去历史节语料**（.md + .py）里搜字面串
scan_corpus() {           # $1 = 字面串
  grep -rn --include='*.md' --include='*.py' "$1" "$D" \
    | grep -Ev '(protocol-runs|summary|tasks)\.md:'
  grep -n "$1" /tmp/pr-noscan.md      | sed 's|^|evidence/protocol-runs.md(noscan):|'
  grep -n "$1" /tmp/summary-nohist.md | sed 's|^|summary.md(nohist):|'
  grep -n "$1" /tmp/tasks-nohist.md   | sed 's|^|tasks.md(nohist):|'
}

# 新域下**每一格的期望都是 0**：域外命中即违规，历史域内引用不计。
# 需要审计历史引用时，用不带排除的原始 grep -rn 即可，那是另一件事。
scan_corpus "每个被扫文件各注入一次" | wc -l
scan_corpus "三种记法" | wc -l
scan_corpus "整个 Change Record 目录全部" | wc -l
scan_corpus "exactly two" | wc -l
scan_corpus "every other .md" | wc -l
scan_corpus "1020c231" | wc -l
scan_corpus "第 13 轮" | wc -l
scan_corpus "6507a986" | grep -v '历史@' | wc -l   # 显式绑定的引用按既有惯例豁免
scan_corpus "R19 最终内容态" | wc -l
scan_corpus "pure ASCII" | grep -v '\.py:' | wc -l
scan_corpus "静默放行" | wc -l

# 4) 表格行格数一致性。基准列数**从分隔行**（`| --- | --- |`）推导——
#    它不可能含代码段里的竖线；R21 用块首行定基准，于是表头行自己坏掉时
#    整张表以坏表头为基准，反把分隔行和正文行判成异常（归因错行）；
#    而**缺分隔行**的表在旧写法下零报告——那才是真正的静默洞。
#    转义过的 `\|` 不计入列数。
cat > /tmp/cells.awk <<'AWK'
function cells(s,   k,m) { k=gsub(/\\\|/,"&",s); m=gsub(/\|/,"&",s); return m-k-1 }
function flush(   i,e) {
  if (n==0) return
  e=-1
  for (i=1; i<=n; i++) if (L[i] ~ /^\|[ :|-]+\|[ \t]*$/) { e=cells(L[i]); break }
  if (e<0) { print F[1]":"R[1]" table has no separator row"; b++ }
  else for (i=1; i<=n; i++) if (cells(L[i]) != e) { print F[i]":"R[i]" expected "e" cells, got "cells(L[i]); b++ }
  n=0
}
FNR==1  { flush() }
!/^\|/  { flush(); next }
        { n++; L[n]=$0; F[n]=FILENAME; R[n]=FNR }
END     { flush(); print "anomalous rows: " b+0 }
AWK
awk -f /tmp/cells.awk $(find $D -name '*.md' | sort)   # 期望 anomalous rows: 0

# 4b) 检测器自身的变异验证：三个构造样本，证明它能红、且归因正确。
printf '| a | b | c |\n| --- | --- |\n| x | y |\n'  > /tmp/m_header.md   # 坏表头
printf '| a | b |\n| x | y | z |\n'                  > /tmp/m_nosep.md    # 缺分隔行
printf '| a | b |\n| --- | --- |\n| x | y | z |\n'  > /tmp/m_body.md     # 坏正文行
awk -f /tmp/cells.awk /tmp/m_header.md   # 期望：报第一行（表头行本身）
awk -f /tmp/cells.awk /tmp/m_nosep.md    # 期望：报 table has no separator row
awk -f /tmp/cells.awk /tmp/m_body.md     # 期望：报第三行

# 末段：前驱守护。本文件「当前条目」一节记录的前驱，必须等于交付提交的父提交。
#    在**交付 HEAD** 上执行；提交前跑必红，因为前驱要到提交存在后才成立。
#    命令住在栅栏块而非表格单元格——单元格的转义往返会改坏它（R21 的教训）。
cat > /tmp/guard.sh <<'SH'
D=.harness/changes/2026-07-27-bootstrap-adoption-1
# 锚到带标签的那一行，而不是「前驱 HEAD」这个词——该词在同节的惯例说明里也出现，
# 只是恰好不含十六进制串。靠「恰好」成立的提取，等于没有锚。
rec=$(sed -n '/^## 当前条目/,/^### /p' "$D/evidence/protocol-runs.md" \
      | grep '前驱 HEAD（第 1 步锁定对象）' | grep -oE '[0-9a-f]{8}')
par=$(git rev-parse --short=8 HEAD^)
# 两侧都必须非空：根提交无父，空=空 会假绿。理论上不可达（本记录不可能位于根提交），
# 但守护行的正确性不该依赖「不可达」这种论证。
test -n "$rec" && test -n "$par" && test "$rec" = "$par"
echo "guard exit=$?  recorded=$rec  parent=$par"
SH
sh /tmp/guard.sh          # 期望 guard exit=0
```


### 落地核对清单（本提交声称的每一处修复）

命令可直接运行（路径为仓库根相对路径）；期望值写的是**真实期望**，不是「越少越好」。

| 声称的修复 | 核对命令 | 期望 |
| --- | --- | --- |
| 视图结构完整性校验存在 | `grep -c "_layer_rows\|_attested_classes" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py` | ≥ 2 |
| 结构攻击回归全绿 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -cE "(premature end\|late begin\|removed begin\|empty view\|marker-only\|missing layer row\|missing attestation).*PASS"` | 7 |
| 去镜像：记录中无现刻数字断言 | `sed -n '/^## 结果/,/^### 红基线/p' .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/run-manifest.md \| grep -cE "定向用例数 \|分支 \(a\) 命中"` | 0 |
| 去镜像：Git 统计量仅在病灶引述中出现 | `grep -rn "+42/-8\\|+60/-27" .harness/changes/2026-07-27-bootstrap-adoption-1 \| grep -v "内容寻址\|落地核对"` | 剩余命中**全部落在描述该病灶的叙述句内**（句中含「差异统计」或「与 Git 不符」等上下文串），无任何现刻断言；**期望以内容锚给出，不再用行号坐标**——行号会随任何编辑漂移 |
| umask 韧性 | `( umask 177; python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py >/dev/null 2>&1; echo $? )` 与 `grep -c Traceback` | exit 1 且 traceback 计数 0 |
| 起始哨兵定向用例 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -c "begin sentinel literal"` | 1 |
| 核查的参数域 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --bogus` | exit 2 |
| 历史豁免形态 | `grep -c "历史@" .harness/changes/2026-07-27-bootstrap-adoption-1/summary.md` | 非零——历史行已迁移到**显式绑定记号** `历史@<hex>`；旧式「散落 hex + 历史」不再豁免 |
| 旧式豁免逃逸 | 上条自检中的两个逃逸样本 | 均 `caught=True`（终验给出的原文：引用 commit id 走私现刻数字） |
| 生成表可字节再生 | `g=$(mktemp); python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py --emit-markdown "$g"; cmp "$g" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/boundary-cases.md` | `cmp` 无输出且 exit 0——入库表与当场再生的字节完全一致 |
| 现刻数字断言：覆盖域终态 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py` | exit 0，并打印扫描到的文件数与域说明；**声称仅限载体自由度表标记为覆盖的轴**，开放轴见该表 |
| 变异验证：文件 × 记法叉积 | `python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py --self-test` | 每个文件 × 每个变体全部 `caught=True`（**变体集合与自检形态见 SSOT 节**），打印句与实现一致；变体含裸数字、逗号格式、反引号包裹、两条历史豁免逃逸样本、英文注释形态 |
| 单行 docstring 覆盖（C2） | `grep -A 14 "^SELF_TEST_VARIANTS" .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py \| grep -c '"""'` | 非零——变体集合含单行 docstring 形态（**覆盖声称见 SSOT 节**）。轴表声称「`.py` 注释与 docstring = 覆盖」，而此前该形态从未被扫（三引号同行成对，旧解析只认奇数个），属**已声称覆盖域内的实现缺陷**，已补齐 |
| **表格行格数一致（R21 起有命令背书）** | 见本文件「内容寻址扫描记录」小节 shell 块末尾的 `cells.awk`（连同其调用一并入库，可整段复制执行） | **anomalous rows: 0**。表头行的格数即该表期望，随后每行必须相等；未转义的竖线多切一格，本行立即变红。R20 曾声称「全表格行改用 cell-count 核对」而只转义了一处、且**无任何已提交命令背书**——外审用独立解析器一跑就找出三行（`run-manifest.md:261`、`summary.md:508`、`summary.md:597`），均已转义。**命令放在栅栏块而不是表格单元格里**：R21 先把它写进单元格，转义往返把 awk 正则改坏，逐字取出后误报十余行——**能被格式转义改写的命令，不算已交付的命令。** |
| **当前条目的前驱绑定（R22 起，R23 移入栅栏块）** | 见本文件「内容寻址扫描记录」小节 shell 块末尾的 `guard.sh`（整段复制即可执行） | **0**（在**交付 HEAD** 上运行；提交前跑必红，因为前驱要到提交存在后才成立）。本节记录的前驱必须等于交付提交的父提交——这一行一红，就说明「当前条目」没跟着这轮重跑。R20、R21 两轮漏跑正是因为该惯例只是**散文义务**：标题停在 R19、前驱停在 历史@6507a986，外审跑 `rev-list` 得到的是三不是一。轮次标签与前驱同处一节，重写本节时必然一起更新，故这一个等式同时守住轮次标签的新鲜度。**「纪律必须变成清单格子」在写下它的那一节上第二次应验。** |
| **历史节过滤器的锚定（F4 反例）** | `awk -f /tmp/dehist.awk .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/protocol-runs.md \| grep -c '^## 当前条目'`（`/tmp/dehist.awk` 由扫描小节 shell 块生成） | **恰一处**。过滤器只认「`^## ` 节头后紧邻首个非空行」的历史声明；按任意行匹配的旧写法用在本文件上，会把当前条目与落地清单整段抹掉而八个格子照样打印零——**一个会致盲自己的过滤器，比没有过滤器更危险**。 |
| **外审轮次口径** | `ls docs/reviews/ \| grep -c pr-7` | **11**（= R1–R11，故下一轮外审为**第 12 轮**）。**口径限定**：`docs/reviews/` 是**审阅方所有物**，有意**不纳入版本控制**；因此该命令只在审阅方落盘的工作区里有意义，**fresh clone 上得 0 属预期**，不构成本行变红。此处记录的是口径而非可移植计数。 |
| **叙事节的作用域声明无遗漏（R23 起）** | `awk '/^## /{h=$0; want=1; next} want && NF {print (($0 ~ /^> \\*\\*本节为该轮历史/) ? "HIST" : "live"), h; want=0}' .harness/changes/2026-07-27-bootstrap-adoption-1/summary.md .harness/changes/2026-07-27-bootstrap-adoption-1/tasks.md \| grep '^live'` | 只应剩**结构节**（`Status` / `Result` / `Verification evidence` / `Exceptions` / `Decision` / `Phase A` / `Phase B` 三节）；**任何叙事节落进这份输出即为违规**。R1 两节此前正是漏了声明，使「历史节内引用构造良性」这句全称对它们不真——**失败方向是假红，安全，但全称句只要有一个反例就不成立**，补声明比缩声称更一致。 |
| **被存证脚本的纯 ASCII 不变式** | `grep -c '[^ -~]' .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py` | **0**。该构造保证在记录中被声称十一轮，却从未有清单守护——第十一次复发正是它被打破（历史标签把非 ASCII 字节写进了被哈希存证的脚本）。**声称了却没有清单行的不变式，等于没有守护。** |
| **手抄不变量：脚本 SHA 与实际字节一致** | `test "$(shasum -a 256 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| cut -d' ' -f1)" = "$(grep '脚本 SHA-256' .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/run-manifest.md \| grep -oE '[0-9a-f]{64}')"; echo $?` | **0**。不变量节记录的 SHA 与当场计算的字节哈希必须相等；脚本一改而抄本未同步，本行立即变红。 |
| **手抄不变量：SHA 抄本数** | `grep -rn --exclude-dir=__pycache__ "$(shasum -a 256 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| cut -d' ' -f1)" .harness/changes/2026-07-27-bootstrap-adoption-1 \| wc -l` | **恰 1**——即 `run-manifest.md` 的「本节保留的唯一两个不变量」小节。R19 的 Critical 正是同一个值散落三处而只同步了一处；把「有几处抄本」写成可执行期望值，是手抄值唯一可行的守护。 |
| **手抄不变量：结果摘要抄本数** | `grep -rln --exclude-dir=__pycache__ "$(python3 .harness/changes/2026-07-27-bootstrap-adoption-1/evidence/carrier_sweep.py \| grep -oE '[0-9a-f]{64}' \| head -1)" .harness/changes/2026-07-27-bootstrap-adoption-1 \| sort` | **恰三个文件，逐一具名**：`evidence/run-manifest.md`（唯一手抄本）、`evidence/boundary-cases.md`（`--emit-markdown` 机器生成）、`summary.md`（逐字粘贴的运行输出）。后两者是**产物**不是手抄，故不计入单点化约束——但它们必须逐一具名，否则「恰 N 处」这个期望值本身又成了没人核对的数字。 |
| 核查器的源码编码 | `python3 -c "import pathlib;print(sum(1 for b in pathlib.Path('.harness/changes/2026-07-27-bootstrap-adoption-1/evidence/check_current_numbers.py').read_bytes() if b>0x7e))"` | **非零**——该文件不是纯 ASCII，因为它要在定义处逐字列出被禁的中文标记词；纯 ASCII 纪律只约束被哈希存证的 `carrier_sweep.py`，已在其 docstring 中明示 |
| 无非预期未完成任务 | `grep -c "^- \[ \]" .harness/changes/2026-07-27-bootstrap-adoption-1/tasks.md` | 1（仅剩预期中的后续项） |
