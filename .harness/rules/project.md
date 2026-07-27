# 项目规则 — scaffold

本文件由 `harness-bootstrap` Skill 在接入 #1 中生成，内容取自代码库侦察证据与项目所有者的访谈裁决。

## 1. 项目目的

维护一套通用、可复制、与业务解耦的 AI Coding Harness 分发包与实例化工具链，让 Agent 在真实工程中稳定、可审计地交付代码。

本仓库同时是**生产者**与**消费者**：

- 生产者资产：`template/.harness/`（对外分发的 Harness 分发包）；
- 消费者实例：仓库根的 `.harness/`（本仓库自己使用的 Harness）。

两者物理分离，不可混用。

## 2. 交付质量门禁（7 条，全部须 exit 0）

交付前在仓库根依次执行；任何一条非 0 即为未完成。前 5 条与 `.github/workflows/validate.yml` 逐条对应，后 2 条针对消费者副本。

生产者侧（CI 已固化）：

1. `python3 template/.harness/bin/validate.py`
2. `python3 template/.harness/bin/harness.py validate`
3. `python3 template/.harness/bin/harness.py adapt --check --root template/.harness`
4. `python3 -m unittest discover -s tests -v`
5. `git diff --check <base-sha> HEAD`

消费者侧（本次接入起纳入 CI）：

6. `python3 .harness/bin/harness.py validate`
7. `python3 .harness/bin/harness.py adapt --check`

门禁证据须记入 Change Record 的 `summary.md`。

**退出码**：每条门禁独立必记，与输出载体的选择无关。成功与失败都由退出码表达，输出载体不承担这一职责。

**输出载体**：对 stdout 与 stderr 合并后的输出，按下列三分法记录。三分只沿两个构造性维度切分——输出为空 / 非空，以及非空时可否按 UTF-8 严格解码——因此互斥性与穷举性由构造本身保证，与命令是否成功无关：

- **(a) 输出为空**（stdout + stderr 合计 0 字节）：逐字记录 `<empty>`。这是对「无输出」这一事实的结构化记法，不是伪造的命令输出。
- **(b) 输出非空且可按 UTF-8 严格解码**：记录**最后一个非空行**的原文。这是「终态摘要行」的可判定定义，取代任何依赖人工判断「哪一行算摘要」的说法；不要求记录全量 verbose 输出。允许额外附记同一输出中的其他原文行（例如 `unittest` 的 `Ran` 行），但最后一个非空行是必记的下限。
- **(c) 输出非空且不可按 UTF-8 严格解码**：记录输出的总字节数与其 SHA-256。

**禁止人工断言**：任何情形下都不得以「已检查」「均通过」之类的人工结论代替命令输出或上述记法。

若出现本三分法之外的情形（按上述构造，理论上不存在），须先修订本规则再记录，不得临场自创记法。

## 3. 变更审批约定

角色三分，边界见 [`docs/process/invariant-closure-design.md`](../../docs/process/invariant-closure-design.md) §5：

- **设计方**：拥有契约与裁决权；契约修订独立成 docs 提交，先于实现。
- **实现方**：实现、测试、提交；**不**修改审阅记录、**不**自评通过、**不**执行合并。
- **审阅方**：独立复现、独立裁定，是唯一的合入决定者；结论只绑定精确 HEAD，任何新提交都必须重新锁定 HEAD 重审。

流程：

1. 变更在专用分支上完成，通过 GitHub PR 提交。
2. 独立审阅产出审阅记录，落在 `docs/reviews/`，命名 `YYYY-MM-DD-<主题>-review.md`；复审为 `YYYY-MM-DD-<主题>-rereview-<短 HEAD>.md`。
3. 审阅记录抬头必须含：审阅日期、PR、基线、固定 HEAD、变更规模、审阅方式、当前结论，并显式声明结论只绑定该精确 HEAD。
4. 结论为「Approve，可以合入」后，由审阅方执行合入。
5. 提交信息使用英文 Conventional Commits，并带 `Co-Authored-By` trailer。

设计与整改一律遵循[不变式闭包设计法](../../docs/process/invariant-closure-design.md)（状态 Approved，强制生效）：正式设计须交付全称不变式、闭包枚举表、对抗输入域全集与兼容性边界；整改须修类不修实例、红测先行、探针主动扩展、契约留白上报。

## 4. 消费者副本与分发包的同步规则

v1 的 CLI 只有 `init` / `adapt` / `validate`，**没有 `upgrade`**；`init` 在目标已存在 `.harness/` 时以 `INIT_TARGET_EXISTS` 拒绝覆盖（`template/.harness/bin/harness.py:929-931`）。因此同步只能手工进行：

**凡改动 `template/.harness/` 的变更，必须在同一变更内同步消费者副本**，步骤为：

1. 备份仓库根 `.harness/` 中的项目层定制资产（`rules/project.md`、`wiki/*`、`changes/*`）；
2. 删除仓库根的 `.harness/`；
3. 执行 `python3 template/.harness/bin/harness.py init --target .`；
4. 将第 1 步备份的项目层资产放回，并重新在 `manifest.json` 中注册项目层组件；
5. 重跑第 2 节的全部 7 条门禁。

该流程的手工代价（尤其第 1、4 步的定制资产保全）是 v3 `upgrade` 能力的真实需求证据，记录在 [`wiki/conventions.md`](../wiki/conventions.md)。

## 5. 行文语言约定

- 项目层资产（`rules/project.md`、`wiki/*`、Change Record）用**中文**，与 `docs/` 下的设计、ADR、流程与审阅记录保持一致。
- 随分发包发行的英文文件（`README.md`、`rules/delivery.md`、`agents/coordinator.md`、`skills/*`、`templates/change/*`、`LICENSE`）**保持英文原样**，不翻译、不改写。
- `template/.harness/` 内一律英文且保持项目中立。

## 6. 禁令：项目层内容永不回灌分发包

`tests/test_template_contract.py:11` 禁止分发包内出现生产者上下文 token，其中包括字面量 `scaffold`（唯一豁免是 bundled `LICENSE` 中的一行版权声明，设计方裁决见 `docs/design/harness-v1.md` §5.1）。

因此：本文件与 `wiki/` 下的任何内容都**不得**流入 `template/.harness/`。一旦回灌，契约测试立即见红。ADR-0001 也正是以「复制时会混入 scaffold 的 Change 历史和生产者上下文」为由拒绝了「把 `.harness/` 直接作为本仓库自身实例」；本次接入保持两棵树物理分离，与该裁决一致。
