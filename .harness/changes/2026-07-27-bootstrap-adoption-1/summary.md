# Change Summary — 接入 #1：scaffold 自身接入 Harness

## Status

实现方已完成交付，等待独立审阅。实现方不自评通过、不执行合并（`rules/project.md` §3）。

## Result

本仓库现同时是 Harness 的生产者与消费者：

- 仓库根安装了消费者副本 `.harness/`，并生成三个平台投影 `CLAUDE.md`、`AGENTS.md`、`.cursor/rules/harness.mdc`。**在 `init` 刚完成、尚未经 bootstrap 定制的那一时点**，消费者副本与分发包 `template/.harness/` 的唯一差异是 `init` 写入的 `origin` 印章；该陈述只描述那个时点，不描述本 Change Record 所在的最终状态（最终状态见下方「最终状态的实际差异」）；
- bootstrap 依据代码库侦察 + 所有者访谈裁决，产出项目层资产 `rules/project.md`、`wiki/overview.md`、`wiki/conventions.md`，并注册 `project-rules` 组件；
- CI 追加两条消费者副本门禁，消除「投影静默过期」缺口；
- 分发包 `template/.harness/` 零改动，零内容回灌。

访谈五题的裁决（所有者全部采纳推荐项，Q4 取 A+C 叠加）：Q1 项目层中文、随包英文原样；Q2 门禁 7 条（CI 5 条 + 消费者 2 条）；Q3 本次即把消费者副本纳入 CI；Q4 删除重装的手工同步规则，并把其代价作为 v3 需求证据留档；Q5 项目目的采用起草原文。

### 最终状态的实际差异

本 Change Record 所在 HEAD 上，消费者副本与分发包的真实递归比较：

```text
$ diff -r template/.harness .harness
Only in .harness/changes: 2026-07-27-bootstrap-adoption-1
Files template/.harness/manifest.json and .harness/manifest.json differ
Only in .harness/rules: project.md
Only in .harness/wiki: conventions.md
Only in .harness/wiki: overview.md
```

即最终差异共三类：

1. `manifest.json` 的 `origin` 印章（`init` 写入）**与** `project-rules` 组件注册（bootstrap 写入）；
2. 项目层目标资产：`rules/project.md`、`wiki/overview.md`、`wiki/conventions.md`；
3. Change Record 审计元数据：`changes/2026-07-27-bootstrap-adoption-1/`。

零回灌（`git diff main -- template/` 为空）证明的是**生产者目录未被消费者内容修改**，它并不意味着消费者副本仍只比分发包多一个 `origin` 印章；两者是不同命题。

## Verification evidence

### 资产提交（本 Change Record 之前已存在，逐个列出，不使用范围表示）

- `c36b7ed37a3f7a772f52a74c49bf328773437f5c` — 安装提交：`init` 产物（消费者副本 `.harness/` 与三个投影）。
- `003829b041ac1e6981912fbdf46070ba239cdccd` — `rules/project.md`、`manifest.json` 的 `project-rules` 注册、三个投影重生成。
- `9c50ed542534c8c91061cd39009c23a417deb3d9` — `wiki/overview.md` 与 `wiki/conventions.md`。
- `2b8100bd60b0000d20a79ae4a9b77b412aeb33a7` — `.github/workflows/validate.yml` 追加两条消费者门禁。
- `8c355041963d03c677940117b9c227ff02a0b8bb` — 依 PR #7 第一轮审阅 F3 的设计方裁定，修订 `rules/project.md` §2 的门禁证据载体条款（命令原文 + 命令自身的终态摘要行 + 退出码）。
- `4651c0297fb0c72dba4eb1805279178c30c2643a` — 依 PR #7 复审 F1 的设计方裁定，将该条款闭合到门禁输出的**全部**情形：(a) 有终态摘要行者记原文、(b) 成功且零输出者逐字记 `<empty>`、(c) 一律禁止人工断言。
- `444cc95812b760ee32a0ad836a0ec3771cd48e7d` — 依 PR #7 第三轮复审的设计方裁定，把该条款改写为**与退出码解耦的输出域三分法**（空 / 非空可解码 / 非空不可解码），互斥穷举由构造保证，并给出「终态摘要行 = 最后一个非空行」的可判定定义；取代上一条的按成功状态划分。
- `f5c3b2a3e962f9f87fdeaa81213bf5014293f89a` — 依 PR #7 第四轮复审的设计方裁定，规定 **stdout / stderr 分流独立捕获与独立记录**（取消「合并输出」概念），并把各分支补成**全函数**：(b) 增设「无非空行 → 字节数 + SHA-256」子分支，写入「行」的字节级定义；另据内部对抗扫描补上「必记行全为控制字节 → 字节数 + SHA-256」例外。

以上八个提交均不含本 Change Record 的任何审计元数据；资产 diff 即证据，未另做副本。本 Change Record 落在其后的审计提交中。

### 7 条交付门禁

按 `rules/project.md` §2 的证据规则记录。每条门禁的证据 = **退出码** + **stdout 载体** + **stderr 载体**；两个流分别独立捕获、分别判定，不存在合并输出。

分流实测判定表（在本审计提交的父提交上以两个独立管道捕获）：

| 门禁 | exit | stdout 字节 | stdout 分支 | stderr 字节 | stderr 分支 |
| ---: | ---: | ---: | --- | ---: | --- |
| 1 | 0 | 27 | (b) 末非空行 | 0 | (a) `<empty>` |
| 2 | 0 | 27 | (b) 末非空行 | 0 | (a) `<empty>` |
| 3 | 0 | 99 | (b) 末非空行 | 0 | (a) `<empty>` |
| 4 | 0 | 0 | (a) `<empty>` | 23862 | (b) 末非空行 |
| 5 | 0 | 0 | (a) `<empty>` | 0 | (a) `<empty>` |
| 6 | 0 | 27 | (b) 末非空行 | 0 | (a) `<empty>` |
| 7 | 0 | 10 | (b) 末非空行 | 0 | (a) `<empty>` |

**分流暴露出的一个事实**：第 4 条 `unittest` 的全部输出在 **stderr**，stdout 为 0 字节——这是 `unittest` 的既有行为。上一版按「合并输出」记录时，该事实被合并操作掩盖，记录看不出摘要行来自哪个流。这正是分流捕获相对合并捕获的实质收益，不只是消除了拼接顺序的歧义。

无门禁落入 (c)，无门禁落入 (b) 的「无非空行」或「控制字节」子分支。

### 7 条门禁逐条证据

```text
### 1  python3 template/.harness/bin/validate.py
exit=0
stdout: Harness contract is valid.
stderr: <empty>
### 2  python3 template/.harness/bin/harness.py validate
exit=0
stdout: Harness contract is valid.
stderr: <empty>
### 3  python3 template/.harness/bin/harness.py adapt --check --root template/.harness
exit=0
stdout: adapt: ok
        （同流附记：[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections）
stderr: <empty>
### 4  python3 -m unittest discover -s tests -v
exit=0
stdout: <empty>
stderr: OK (skipped=2)
        （同流附记：Ran 175 tests in 12.316s）
### 5  git diff --check e338db8 HEAD
exit=0
stdout: <empty>
stderr: <empty>
### 6  python3 .harness/bin/harness.py validate
exit=0
stdout: Harness contract is valid.
stderr: <empty>
### 7  python3 .harness/bin/harness.py adapt --check
exit=0
stdout: adapt: ok
stderr: <empty>
```

各条 (b) 分支记录的均为该流最后一个非空行的原文；括注为规则允许的同流附记原文行。第 4 条附记的 `Ran` 行含该次运行的动态耗时，第四轮复审已明确接受（规则保存的是该次运行的证据，不承诺未来复跑逐字节相同）。

### 零回灌核对

```text
$ git diff main -- template/ | wc -l
       0
```

### 隔离性

全部生产者契约测试的扫描根固定在 `template/.harness`（`tests/test_template_contract.py:9`、`tests/test_validate.py:14`、`tests/test_harness_cli.py:18`、`tests/test_adapters.py:14`），消费者副本不进入任何扫描域。未对 `tests/` 做任何适配改动。

### v3 `upgrade` 需求证据（本次实测）

删除重装路径下，放回 `rules/project.md` 但忘记重新注册组件时，消费者两条门禁**全绿**而投影中已无 `project-rules`（`grep -c project-rules CLAUDE.md` 输出 0）。完整探针与代价分析见 `wiki/conventions.md` §6。

## Exceptions

1. **Skill 契约留白（已上报，待设计方裁定）**：定制记录的 Asset 列要求 bundle 相对路径，但三个平台投影位于分发包之外。本次按「难以归类仍须成行」处理，路径以仓库根相对写出并显式标注。详见 `customization-record.md`。
2. **本次未验证「受管块外用户字节逐字节保留」**：三个投影文件接入前均不存在，v1 该项核心承诺在本次 dogfooding 中没有真实样本。若需该证据，须选一个已有 `CLAUDE.md` 的项目作为接入 #2。
3. **CI 新增步骤的真实结论**须以远端 Actions 运行为准；本地无法证明 GitHub 侧行为。

## 整改记录（PR #7 第一轮独立审阅）

审阅记录：`docs/reviews/2026-07-27-pr-7-scaffold-self-adoption-review.md`，结论 Request changes，绑定 HEAD `ce45a7a7359ab271c878732e0b004c664218fc01`，3 项 Important。设计方裁决后的整改：

| Finding | 裁决与整改 |
| --- | --- |
| F1 定制记录误判 | 接受审阅方。三行投影的 Reusability 由 `generic` 改为 `project`（实际变更内容是本项目的 `project-rules` 注册，而非投影机制的通用性）；Cursor 行 Action 由 `replaced` 改为 `modified`（审阅方实测 26/26 行原文保留、新增 1 行；整文件所有权是写入机制，不等于内容谱系）。 |
| F2 init 时点事实误作最终状态 | 「唯一差异为 `origin` 印章」逐字限定到「`init` 刚完成、尚未 bootstrap 定制」的时点，并在本文件新增「最终状态的实际差异」一节列出三类真实差异；PR #7 正文同步修正。 |
| F3 门禁证据载体 | 设计方选审阅方的方案 2：先以资产提交 `8c355041963d03c677940117b9c227ff02a0b8bb` 修订 `rules/project.md` §2 的证据条款，再由本审计提交对齐 summary，消除「规则与首条 Change Record 从第一天起互相矛盾」。 |

本轮整改遵守 Skill 的两段提交契约：规则修订作为资产提交先落，审计提交在其后，且上方资产提交清单已逐个扩充其完整 SHA。

## 整改记录（PR #7 复审 d80ec6a）

审阅记录：`docs/reviews/2026-07-27-pr-7-scaffold-self-adoption-rereview-d80ec6a.md`，结论 Request changes，绑定 HEAD `d80ec6a40c14facc25f39af7ab8674e4a05795f2`，2 项 Important，六维总分 20/24。上一轮 3 项仓库内整改经复审确认全部关闭。

| Finding | 裁决与整改 |
| --- | --- |
| F1 静默成功命令无合法证据载体 | 接受审阅方，并按设计方要求做**类修复**而非实例修复：不是给第 5 条门禁单独开一个特例，而是把 §2 的证据条款闭合到门禁输出的**全部**情形——(a) 有终态摘要行、(b) 成功且零输出记 `<empty>`、(c) 禁止人工断言，并声明 (a)(b) 互斥穷举、遇到两者皆不适用者须先补规则不得临场自创。资产提交 `4651c0297fb0c72dba4eb1805279178c30c2643a` 先落，本审计提交随后把第 5 条证据改为 `<empty>` 形式。 |
| F2 PR 正文与仓库记录漂移 | 按审阅方要求订正统计（`7 project / 0 generic / 0 stack`）、恢复第 4 条命令的 `-v`、把「完整输出见 summary」改为按证据载体规则的准确表述。并按设计方的类修复要求，把 PR 正文中**复制自仓库记录的可漂移统计**改写为指向 `customization-record.md@<审计 SHA>` 的指针，正文只保留不可漂移的论断，从结构上消除正文再次与仓库记录矛盾的可能。 |

**本轮的方法学观察**（供流程复盘）：两轮 Important 的根因同属一类——「用存在命题交付本应是全称命题的契约」。第一轮的证据条款只枚举了已知的有输出命令，复审立刻在未枚举的静默命令上找到反例；PR 正文则以复制而非引用的方式重复了可漂移事实，于是每次仓库记录变化都可能产生新的矛盾实例。两次都按「修类不修实例」（[不变式闭包设计法](../../../docs/process/invariant-closure-design.md) §3）处理：前者把规则闭合到输出全域，后者把正文改为指针以消除复制源。

## 整改记录（PR #7 第三轮复审 8a57a1a）

审阅记录：`docs/reviews/2026-07-27-pr-7-scaffold-self-adoption-rereview-8a57a1a.md`，结论 Request changes，绑定 HEAD `8a57a1a8bae71c8fb80ba228f4cac3371684dfd5`，1 项 Important，六维总分 21/24。上一轮 F2（PR 正文指针化）经复审明确接受，不再要求把统计内联回正文；Spec 一路已判 Approve。

| Finding | 裁决与整改 |
| --- | --- |
| 证据规则的全称范围自我否定 | 设计方裁定审阅方的方案 2，两个子论点均成立：其一，规则一边宣称 (a)(b) 互斥穷举、一边在同段承认可能存在两者皆不适用的门禁，文本自我否定；其二，用**成功状态**作划分维度是错的——非零退出且零输出既无摘要行也不满足「成功且零输出」，落在两支之外。整改：把划分维度换成**输出本身**，沿「空 / 非空」与非空时「可否 UTF-8 严格解码」两个构造性维度三分，穷举性由构造保证而非由声称保证；退出码升为每条门禁独立必记字段，成功与否只由它表达；并把「终态摘要行」定义为**最后一个非空行**，消除「哪一行算摘要」的人工判断。资产提交 `444cc95812b760ee32a0ad836a0ec3771cd48e7d` 先落，本审计提交随后对齐。 |

**本轮的方法学观察**：这是同一根因的第三次实例，且这次的教训比前两次更深一层——前两轮的问题是「枚举不全」，本轮的问题是**划分维度选错**。按成功状态划分时，无论怎样补充分支都无法穷举，因为该维度与「输出长什么样」正交；换成输出自身的构造性维度后，穷举性不再需要声称，它由划分方式本身产生。可machine化的判据（0 字节 / 严格解码 / 最后一个非空行）同时消除了执行者的自由裁量。这条经验适用于任何「声称覆盖全域」的自然语言契约，建议纳入流程复盘。

## 整改记录（PR #7 第四轮复审 0bcbbc8）

审阅记录：`docs/reviews/2026-07-27-pr-7-scaffold-self-adoption-rereview-0bcbbc8.md`，结论 Request changes，绑定 HEAD `0bcbbc8c410c655998d2720c0f7861e1e696c0ae`，Standards / Spec 各 1 项 Important，六维总分 20/24。Gate 4 动态耗时经复审明确接受，不构成问题。

| Finding | 裁决与整改 |
| --- | --- |
| (b) 分支存在「无非空行」的未定义子域（最小反例 `b"\n"`） | 接受。分类穷举不等于**记录义务闭合**：分类能选中 (b)，但该分支要求记录的对象可以不存在。整改把 (b) 内部沿「是否存在非空行」二分，无非空行者记字节数 + SHA-256，使每个分支要求记录的对象必然存在；并写入「行」的字节级定义（仅 `0x0A` 为分隔符，去除末尾一个 `0x0D`），消除对「行」的临场解释。 |
| stdout / stderr 的「合并输出」无唯一捕获语义 | 接受审阅方案 2。两个流**分别独立捕获、分别记录**，规则中不再存在「合并输出」这一对象，拼接顺序、运行时交错、多字节序列跨流分布三类歧义因此不可能发生——不是规定了一种合并方式，而是取消了合并这一步。 |

资产提交 `f5c3b2a3e962f9f87fdeaa81213bf5014293f89a` 先落，本审计提交随后对齐。

**本轮的方法学观察**：前三轮的教训依次是「枚举不全」→「划分维度选错」→ 本轮的**两个新层次**。其一，*分类穷举 ≠ 记录义务闭合*：一个全函数不仅要求每个输入落入某分支，还要求该分支的输出确实存在；只检查前者会漏掉后者。其二，*规则的输入本身必须先被唯一确定*：在输入字节串未定义之前，任何关于它的判定规则都不可能是良定义的——三分法再完美，喂给它的东西不唯一，结论就不唯一。取消合并（而非规定合并顺序）是更强的修法：它消灭了不确定性的来源，而不是给不确定性挑一个约定。

**内部对抗扫描**（本轮起作为交付前纪律，见下）另发现并关闭第三个缝隙：必记行可以整行由控制字节构成（`b"\r\r\n"` 的最后一个非空行是单个 `0x0D`），无法在 Markdown 记录中无损呈现，强求「记录原文」会逼出规则自身禁止的临场转义记法；该子域已并入字节数 + SHA-256 载体。

## Decision

待独立审阅方在精确 HEAD 上裁定（Approve，可以合入 / Request changes，禁止合入），审阅记录归档于 `docs/reviews/`。
