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
- [ ] 推送分支、开 Draft PR、记录 CI 结论。
- [ ] 独立审阅（由审阅方执行；实现方不自评、不合并）。
