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
- `8c355041963d03c677940117b9c227ff02a0b8bb` — 依 PR #7 审阅 F3 的设计方裁定，修订 `rules/project.md` §2 的门禁证据载体条款（命令原文 + 命令自身的终态摘要行 + 退出码）。

以上五个提交均不含本 Change Record 的任何审计元数据；资产 diff 即证据，未另做副本。本 Change Record 落在其后的审计提交中。

### 7 条交付门禁

按 `rules/project.md` §2 修订后的证据载体条款记录：每条门禁给出**命令原文、命令自身产出的终态摘要行与退出码**；不要求全量 verbose 输出（第 4 条的 175 行用例明细因此不入档）。全部在仓库根执行，均 exit 0。

```text
### 1  python3 template/.harness/bin/validate.py
Harness contract is valid.
exit=0
### 2  python3 template/.harness/bin/harness.py validate
Harness contract is valid.
exit=0
### 3  python3 template/.harness/bin/harness.py adapt --check --root template/.harness
[ADAPT_SKIPPED_TEMPLATE] .: origin is null; template bundles do not generate projections
adapt: ok
exit=0
### 4  python3 -m unittest discover -s tests -v
Ran 175 tests in 10.065s
OK (skipped=2)
exit=0
### 5  git diff --check e338db8 HEAD
exit=0
### 6  python3 .harness/bin/harness.py validate
Harness contract is valid.
exit=0
### 7  python3 .harness/bin/harness.py adapt --check
adapt: ok
exit=0
```

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

本轮整改遵守 Skill 的两段提交契约：规则修订作为资产提交先落，本审计提交在其后，且上方资产提交清单已逐个扩充其完整 SHA。

## Decision

待独立审阅方在精确 HEAD 上裁定（Approve，可以合入 / Request changes，禁止合入），审阅记录归档于 `docs/reviews/`。
