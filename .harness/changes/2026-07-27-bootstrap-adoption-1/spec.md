# Change Specification — 接入 #1：scaffold 自身接入 Harness

## Goal

本仓库以**消费者**身份完成 Harness 接入并完成 bootstrap 定制：仓库根存在已定制、已校验、已接入三个 Agent 平台的 `.harness/`，且它与对外分发的 `template/.harness/` 物理分离、互不污染。

## Scope

- 新增消费者副本 `.harness/`（由 `harness.py init` 安装）与三个平台投影 `CLAUDE.md`、`AGENTS.md`、`.cursor/rules/harness.mdc`。
- 新增项目层资产：`.harness/rules/project.md`、`.harness/wiki/overview.md`、`.harness/wiki/conventions.md`。
- 在 `.harness/manifest.json` 的 `components` 注册 `project-rules`。
- 在 `.github/workflows/validate.yml` 追加两条消费者副本门禁。
- 本 Change Record 自身（含定制记录）。

## Non-goals

- **不改动 `template/.harness/` 的任何字节**（分发包契约、Manifest Schema、CLI 行为、校验器一律零触碰）。
- 不改动 `tests/` 下任何测试以适配本次接入。
- 不实施 v2 分层能力（D1–D4 任何一项），不实现 v3 `upgrade`。
- 不改写 `docs/` 下既有设计、ADR、流程与审阅记录。
- 不翻译随分发包发行的英文文件。

## Acceptance criteria

机械可验证：

1. 7 条交付门禁全部 exit 0（`rules/project.md` §2 列举）。
2. 生产者测试套件 175 tests 保持全绿（`python3 -m unittest discover -s tests`，exit 0）。
3. `git diff main -- template/` 输出为空，证明零内容流入分发包。
4. `git diff --check` 空白字符检查 exit 0。
5. 本 Change Record 目录含 `manifest.json` 的 `change_management.required_files` 声明的全部文件（`summary.md`、`spec.md`、`tasks.md`），且加入后消费者 `validate` 仍 exit 0。

需要人的决策：

6. 访谈五题由项目所有者裁决（Q1 行文语言、Q2 门禁构成、Q3 CI 纳管、Q4 同步策略、Q5 项目目的）。
7. 独立审阅方在精确 HEAD 上给出 Approve 后方可合入；实现方不自评通过、不执行合并。
