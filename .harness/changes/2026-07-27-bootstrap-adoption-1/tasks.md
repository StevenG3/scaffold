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
- [ ] 第三轮独立复审（由审阅方执行；实现方不自评、不合并）。
