# Change Tasks — 接入 #1

## Phase A：安装与侦察

- [x] 在 `adopt/scaffold-self` 分支上执行 `python3 template/.harness/bin/harness.py init --target .`（exit 0）。
- [x] 核对消费者副本与分发包的逐字节差异，确认唯一差异是 `origin` 印章。
- [x] 运行消费者两条门禁（`validate` / `adapt --check`），均 exit 0。
- [x] 确认生产者测试套件不受影响（175 tests，OK，exit 0），且未对测试做任何适配。
- [x] 侦察代码库：技术栈、门禁命令、CI、强制流程、角色分工、审阅记录惯例、既有 Agent 指令约定、分发包 token 禁令。
- [x] 按 Skill 访谈规则起草 5 个必须由所有者作答的问题；其余 14 个议题由侦察证据自动作答。
- [x] 资产提交 1（安装产物）：`c36b7ed37a3f7a772f52a74c49bf328773437f5c`。

## Phase B：定制与门禁

- [x] 写 `.harness/rules/project.md`（中文）：项目目的、7 条门禁、审批约定、同步规则、行文语言、回灌禁令。
- [x] 在 `.harness/manifest.json` 注册 `project-rules` 组件，并重跑 `adapt` 更新三个投影。
- [x] 资产提交 2：`003829b041ac1e6981912fbdf46070ba239cdccd`。
- [x] 写 `.harness/wiki/overview.md` 与 `.harness/wiki/conventions.md`（中文骨架，待补充位置显式标注）。
- [x] 实测并记录 v3 `upgrade` 需求证据（删除重装路径下的静默失败探针）。
- [x] 资产提交 3：`9c50ed542534c8c91061cd39009c23a417deb3d9`。
- [x] 在 `.github/workflows/validate.yml` 追加两条消费者门禁步骤，YAML 解析核对 9 steps。
- [x] 资产提交 4：`2b8100bd60b0000d20a79ae4a9b77b412aeb33a7`。

## Phase B：审计

- [x] 跑完 7 条门禁并留存真实输出。
- [x] 核对 `git diff main -- template/` 为空（零回灌）。
- [x] 写本 Change Record（`spec.md` / `tasks.md` / `summary.md` / `customization-record.md`），作为审计提交落在全部资产提交之后。
- [x] 推送分支、开 Draft PR（#7）、记录 CI 结论（run `30210002988`，success）。
- [x] 第一轮独立审阅（Request changes，3 项 Important）。

## R1 整改（PR #7 第一轮）

- [x] F3：资产提交先行——修订 `rules/project.md` §2 证据载体条款（`8c355041963d03c677940117b9c227ff02a0b8bb`）。
- [x] F1：定制记录三行投影 Reusability 改 `project`，Cursor 行 Action 改 `modified`。
- [x] F2：`summary.md` 与 PR #7 正文把「唯一差异为 origin 印章」限定到 init 时点，并列出最终状态的真实差异。
- [x] `summary.md` 资产提交清单扩充新的规则修订 SHA（逐个列出，不用范围表示）。
- [x] 整改后重跑 7 条门禁、零回灌核对、推送并确认新 HEAD 的远端 CI。
- [x] 第二轮独立复审（Request changes，2 项 Important；上一轮 3 项确认关闭）。

## R2 整改（PR #7 复审 d80ec6a）

- [x] F1：资产提交先行——把 `rules/project.md` §2 证据条款闭合到门禁输出全域，(a) 摘要行 / (b) `<empty>` / (c) 禁人工断言，并声明互斥穷举（`4651c0297fb0c72dba4eb1805279178c30c2643a`）。
- [x] F1：`summary.md` 第 5 条门禁证据改为 `<empty>` 形式（实测 stdout+stderr 合计 0 字节）。
- [x] `summary.md` 资产提交清单扩充新的规则闭合 SHA（逐个列出，不用范围表示）。
- [x] F2：PR #7 正文订正统计为 `7 project / 0 generic / 0 stack`、恢复第 4 条命令 `-v`、修正证据措辞。
- [x] F2 类修复：正文中可漂移的统计改写为指向 `customization-record.md@<审计 SHA>` 的指针，只保留不可漂移论断。
- [x] 整改后重跑 7 条门禁、零回灌核对、推送并确认新 HEAD 的远端 CI。
- [x] 第三轮独立复审（Request changes，1 项 Important；Spec 一路 Approve，F2 指针化获接受）。

## R3 整改（PR #7 第三轮复审 8a57a1a）

- [x] 资产提交先行——把 `rules/project.md` §2 改写为与退出码解耦的输出域三分法：(a) 0 字节记 `<empty>`、(b) 非空可解码记最后一个非空行、(c) 非空不可解码记字节数与 SHA-256；删除按成功划分的旧文字与自否让步从句（`444cc95812b760ee32a0ad836a0ec3771cd48e7d`）。
- [x] 实测复核既有 7 条门禁证据在新规则下依然成立：1–4、6、7 记录的摘要行恰为各自输出的最后一个非空行，5 仍为 (a)；证据行无需变动。
- [x] `summary.md` 增补输出域判定表并对齐措辞；资产提交清单扩充至 7 个完整 SHA（逐个列出，不用范围表示）。
- [x] 整改后重跑 7 条门禁、零回灌核对、推送并确认新 HEAD 的远端 CI。
- [x] 第四轮独立复审（Request changes，Standards / Spec 各 1 项 Important；gate 4 动态耗时获接受）。

## R4 整改（PR #7 第四轮复审 0bcbbc8）

- [x] 资产提交先行——`rules/project.md` §2 规定 stdout / stderr 分流独立捕获与独立记录（取消「合并输出」概念）；(b) 增设「无非空行 → 字节数 + SHA-256」子分支；写入「行」的字节级定义；补「必记行全为控制字节」例外（`f5c3b2a3e962f9f87fdeaa81213bf5014293f89a`）。
- [x] 交付前内部对抗扫描：25 个边界字节串用例 + 20 万随机字节串模糊测试，未定义/异常用例 0；扫描过程中发现并关闭控制字节缝隙。
- [x] 七条门禁分流重跑，逐条给出 stdout / stderr 各自载体判定；如实记录第 4 条输出全在 stderr 这一事实。
- [x] `summary.md` 证据块改为分流形式（退出码 + 两个流的载体），判定表更新；资产 SHA 枚举扩充至 8 个完整 SHA。
- [x] 整改后重跑 7 条门禁、零回灌核对、推送并确认新 HEAD 的远端 CI。
- [x] 第五轮独立复审（Request changes，Standards 3 项 / Spec 2 项 Important，3 个不同问题）。

## R5 整改（PR #7 第五轮复审 3a2ccbf）

- [x] 资产提交先行——`rules/project.md` §2 的「不可呈现」判据由字节级 C0/DEL 换成固定枚举的不可呈现码点集（C0、DEL、C1 含 NEL、U+2028/U+2029、双向控制符、U+FEFF），版本无关（`9e14d339d7797a3da824c9d4256316da18103f2d`）。
- [x] 扫描证据落地 `evidence/`：扫描器 `carrier_sweep.py`（仅标准库、seed 写死、确定性）、`boundary-cases.md`（52 个定向用例逐条表）、`run-manifest.md`（算法/域/seed/迭代数/复现命令/结果摘要）。
- [x] 扫描方法学更正：定向用例逐条携带期望分支，从流程 §2.3 对抗域逐项取材，并加测集合外边界邻居；在运行清单中写明随机模糊测试无法验证判据本身。
- [x] 重跑扫描并记录结果摘要 `212e19d9…`（定向 52/失败 0；随机 20 万/逃逸 0；五分支全覆盖）。
- [x] PR 正文删除全部载体语义叙述，只保留不可漂移陈述 + 精确 SHA 指针。
- [x] 整改后重跑 7 条门禁、零回灌核对、推送并确认新 HEAD 的远端 CI。
- [x] 内部 Opus 独立审阅（5 项 Important + 3 项 Minor，均裁定为真）。

## R5b 整改（内部 Opus 审阅 badccea9）

- [x] 资产提交先行——规则取消对码点集补集的全称断言，改述为本项目固定约定 + 明写残余风险；集合扩充至已知不可见字符族；附记行同受不可呈现检查（`16397a4daffec8119b3d432a40f9448e975b28df`）。
- [x] 资产提交——修正码点表中隔离符范围自相矛盾的一行，拆为两行（`1d8c170bc76e080b2b0f2ecce9a5312c7021724d`）。
- [x] `carrier_sweep.py` 同步扩集；B 组覆盖每个新增族；邻居改用已分配且可见的码点（U+00A0、U+2010、U+2027、U+202F、U+3000），移除未分配的 U+2065 与已入集的 U+206A。
- [x] 新增 `--emit-markdown`：`boundary-cases.md` 改为真正生成，输入完整 `repr` 不截断；结果摘要扩展为绑定输入字节列。
- [x] 新增 `--baseline`：红基线实测 69 个用例中 30 个见红，当前判据下全绿。
- [x] `run-manifest.md` 与 `summary.md` 载明 `evidence/` 审计元数据身份的设计方裁定，并把它列为第二处 Skill 契约缺口。
- [x] 重跑全量定向 + 随机 + 基线；7 条门禁；零回灌；推送并确认远端 CI。
- [x] 内部审阅方复核本次 delta：前 8 项确认关闭，判定「可交外部审阅」，新发现 2 项 Minor。

## R5c 整改（内部复审 149805a，微轮次）

- [x] Minor B（资产提交先行）：码点表类别标签逐行清理，每个标签恰好命名其范围所含内容；集合不变（`4c0a6efce013009126af1f483e738f746ddae9d6`）。
- [x] Minor A：`carrier_sweep.py` 拒绝未知参数（stderr 用法行 + 退出 2）；退出码语义按模式区分——默认模式承载判定，`--baseline` 与 `--emit-markdown` 为报告模式不承载判定。
- [x] Minor A：`run-manifest.md` 退出码一节改为逐模式表格，刷新脚本 SHA-256。
- [x] 重跑三种模式实测退出码（0 / 0 / 0）与未知参数（2）；再生成 `boundary-cases.md`；结果摘要不变（用例未改动）。
- [x] 7 条门禁、零回灌、推送、远端 CI。
- [x] 外部审阅方独立复审（140b65bf）：2 项 Important，变异探针为决定性证据。

## R6 整改（外部复审 140b65bf）

- [x] 定向用例改为携带**期望分支 + 期望载体值**；期望载体独立构造（原文手写字面串；哈希 = 字面字节数 + 直接 `hashlib.sha256()`），`_digest()`/`carrier()` 不参与构造。
- [x] 通过条件改为分支与载体双重比对；`result_digest()` 绑定实际载体值。
- [x] `--emit-markdown` 生成表新增期望载体 / 实际载体两列，完整不截断；结论句按失败数如实分支。
- [x] 默认模式内置比较器自检（4 变异必拒 + 1 对照必受）与 argv 自检（9 项）；任一失败即非零退出。
- [x] `--baseline` 与 `--emit-markdown` 组合被拒绝（两种顺序，退出 2），argv 自检覆盖该回归。
- [x] 复现审阅方变异探针：打桩 `_digest()` 后 `failures=47`、`digest_unchanged=False`（整改前为 0 / True）。
- [x] 再生成 `boundary-cases.md`；刷新脚本 SHA 与结果摘要；7 条门禁、零回灌、推送、远端 CI。
- [x] 内部审阅方以变异攻击 brief 复核（a402986b）：顶住 11 类变异，判定 Ready；另 1 Important + 2 Minor + 1 nit。

## R6b 整改（内部变异攻击复审 a402986b）

- [x] Important A：为随机域加独立值 oracle（`oracle_carrier()`，第二次独立转写，不调用 `carrier()`/`_digest()`），`run_fuzz()` 逐输入比对分支与载体值，失配即见红；M10 前后由「绿、digest 不变」变为「`fuzz_mismatches=170981`、digest 改变」。
- [x] Minor B：两项自检在 emit 模式同样运行，通过数与失配数写入表头；实测比较器污染改变表头（5/5 → 1/5、4/5、2/5）。
- [x] Minor C：`--emit-markdown PATH` 由脚本原子写入（临时文件 + `os.replace()`），run-manifest 改用安全命令，stdout 形式保留供 diff。
- [x] nit：`-h`/`--help` 打印用法到 stdout 并退出 0；argv 自检扩至 15 项。
- [x] 再生成 `boundary-cases.md`；刷新脚本 SHA 与结果摘要；7 条门禁、零回灌、推送、远端 CI。
- [x] 外部审阅方独立复审（50a6060）：3 项 Important + 2 项 Minor。

## R7 整改（外部复审 50a6060）

- [x] F1：拆分可信计算基——空流期望用独立字面量；oracle 拥有自己的第二份码点集并在导入时交叉断言；新增 5 项共因自检；run-manifest 新增可信计算基披露。两个审阅探针实测均 exit 1。
- [x] F2：先校验完整 argv 再选模式；help 仅可单独出现；argv 自检 15 → 22 项，覆盖 help × 未知 / × 各模式 / × 路径 / × 三元 / × 顺序。
- [x] F3(a)：新增长度 0–2 **全域穷举**（65,793 输入，失配 0）——唯一给出全称承诺的层。
- [x] F3(b)：撤回长度 3–6 的全域措辞，精确限定为「200,000 次抽取、137,527 个唯一输入、仅对被抽到的输入成立」；manifest / 生成表 / summary 统一。
- [x] Minor：修正自相矛盾的 fuzz 能力陈述；依赖清单补 `os`、`tempfile`。
- [x] 交付前 **∀ 句审计**（常设义务，本轮起）：逐句标注 构造保证 / 已限定 / 撤回。
- [x] 再生成表；刷新脚本 SHA 与结果摘要；7 条门禁、零回灌、推送、远端 CI。
- [x] 内部定向审阅（002b5d21）：∀ 审计表 12 行中 11 行顶住证伪；第 7 行穷举层捕获对其他层不可见的投毒。1 Important + 1 Minor。

## R7b 整改（内部定向审阅 002b5d21）

- [x] Important A：检查侧拥有独立的 `ORACLE_BRANCH_*` 标签字面量（定向期望改用之），导入时成对交叉断言 + 各自唯一性检查；新增 3 项共因自检；S1/S2 实测均 exit 1。
- [x] Important A：`run-manifest.md` 披露表补入分支标签常量与「双侧同改」残余风险；诚实记录 digest 变化只是事后可察觉，不代替事前拒绝。
- [x] Minor B：空路径 / 纯空白路径在参数校验阶段拒绝（exit 2 + usage），不再以 `FileNotFoundError` 栈回溯 exit 1；argv 自检 22 → 24 项。
- [x] 前瞻性说明写入 run-manifest：闭合只认证已交付的 argv 空间，新增 flag 须同步扩充自检。
- [x] ∀ 句审计表更新：第 6 行降级为「已限定」，新增第 5b 行，第 4 行限定语补全。
- [x] 重跑全部层次与自检；再生成表；刷新脚本 SHA；7 条门禁、零回灌、推送、远端 CI。
- [x] 外部审阅方第 8 轮独立复审（4d698f98）：2 项 Important + 2 项 Minor，并给出可复现审阅协议。

## R8 整改（外部复审 4d698f98）

- [x] I1：定义唯一认证状态（六层合取）；`--emit-markdown PATH` 在任一层失败时拒绝写入正式文件并 exit 1；诊断输出仅走 stdout + 不认证横幅 + exit 1；结论块逐层如实分支，无条件的「EVERY ... agrees」句已消除。
- [x] I1：新增认证自检 9 项（穷举失败 / 抽样失败 / 自检失败 / undefined / directed 各自阻断认证，并验证结论文本随之改变）。
- [x] I1：按审阅协议第 6 步复跑其探针 —— `emit_rc=1`、`does NOT certify=True`、正式文件未被覆盖。
- [x] I2(a)：digest 检测范围收窄并三处同步；与 `b"\x00"*6` 探针实测一致。
- [x] I2(b)：确定性收窄至实测解释器版本（`Python 3.14.5`）+ 固定 seed，明确不作跨版本承诺并引用 CPython 文档；未自造 PRNG。
- [x] I2(c)：比较器污染表述限定为枚举的变异类。
- [x] I2：以审阅方 `rg` 收集命令重做 ∀ 审计（命中 175 行 / 7 文件），按五分法人工分类，新增第 13–17 行；审计自身完成度限定为「收集器命中集 + 人工分类」并列出已知不足。
- [x] Minor 1 / Minor 2：抽样层措辞更正并入审计表；默认语义三处同步为「四类自检 + 穷举层」。
- [x] 自跑审阅协议第 5 步绿灯电池与第 6 步变异探针；7 条门禁、零回灌、推送、远端 CI。
- [ ] 三个独立 Opus 会话按协议执行自验；通过后再交外部审阅方。
