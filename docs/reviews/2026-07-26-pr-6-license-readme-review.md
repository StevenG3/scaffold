# PR #6 License and README 独立审阅

- 审阅日期：2026-07-26
- PR：#6 `Release readiness: MIT license and README refresh`
- 基线：`main@104df2db4b60b5b829e374a4a17e7886a2d1fcea`
- 固定 HEAD：`a30904dcd50e635a876104cf8ff4704fccd2db5f`
- 变更规模：2 个提交，2 个文件，`+26/-5`
- 审阅方式：Standards / Spec 双路独立审阅、OSI MIT 标准文本对照、真实 `init` 分发探针、README 事实与链接核对、全量测试及远端 CI 核对
- 当前结论：**Request changes，禁止合入**

本结论只绑定上述精确 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## Findings

### [Important] MIT 版权与许可通知没有进入实际分发副本

位置：

- `LICENSE:1-21`
- `template/.harness/bin/harness.py:738-740,943-954`
- `tests/test_template_contract.py:10-31,49-55`
- `docs/adr/0001-portable-harness-contract.md:15-17`
- `template/.harness/README.md:1-11`

新 `LICENSE` 与 OSI 的标准 MIT 文本语义一致；其第 12–13 行同时规定，版权声明和许可声明必须包含在软件的所有副本或实质性部分中。权威文本：

- https://opensource.org/license/mit

本项目的核心分发单元不是仓库根目录，而是 `template/.harness/`：

- ADR-0001 明确“所有目标项目运行资产”都在该目录中，目标项目只需复制它；
- `harness.py init` 将 `BIN_DIR.parent` 作为 source，并仅 `copytree(source, target/.harness)`；
- 精确 bundle 文件集测试当前不包含 LICENSE；
- producer-history 测试还禁止分发包出现 `StevenG3`。

真实执行：

```text
$ python3 template/.harness/bin/harness.py init \
    --target <temp-project> \
    --adapters claude-code,codex,cursor
init: ok
```

安装结果包含 `.harness/`、`CLAUDE.md`、`AGENTS.md` 和 Cursor 投影，但全树扫描结果为：

```text
license_notice_hits=[]
```

因此通过 README 推荐的一键实例化得到的核心产品副本不携带 MIT 授权、免责声明或版权通知。这同时违反了本 PR 的“发布就绪”目标、MIT 自身的通知条件及分发包自包含契约。根仓库存在 LICENSE 不能替代随实例化副本提供 notice。

整改要求：

1. 将完整且适用的 MIT 版权与许可通知纳入 `template/.harness/`，确保 `init` 后仍存在。
2. 更新精确 bundle 文件集契约，并增加真实 `init` 后 notice 存在且文本正确的回归测试。
3. 明确裁决 producer-neutral 原则与版权通知的边界：版权持有人不是“生产者历史泄漏”，对应测试应对许可证文件作精确例外，而不是放松其他资产扫描。
4. 保持第三方内容 caveat：分发许可证不得声称授予本项目无权授予的第三方原文权利。

### [Important] README 把 Cursor 整文件投影误写成受管区块投影

位置：

- `README.md:29-31`
- `template/.harness/bin/harness.py:288-304`
- `docs/design/harness-v1.md:227-235`
- `template/.harness/README.md:30-34`

README 状态行把三个平台投影统称为：

> 以受管区块形式生成的平台投影（CLAUDE.md / AGENTS.md / .cursor/rules/harness.mdc）

实际契约明确区分：

- Claude Code：`mode: block`，只更新 `CLAUDE.md` 受管区块；
- Codex：`mode: block`，只更新 `AGENTS.md` 受管区块；
- Cursor：`mode: file`，`.cursor/rules/harness.mdc` 为工具整文件所有并整体重建，仅保留 marker 用于完整性检查。

当前措辞可能让用户误以为 Cursor 文件的 marker 外内容也会像前两者一样保留，而 `adapt` 实际可以整体重建该文件。这是发布 README 中的用户数据边界错误。

整改要求：逐字区分“CLAUDE.md / AGENTS.md 使用受管区块”和“Cursor 规则文件由工具整文件生成并拥有”；不得继续用同一个“受管区块形式”修饰三者。

## Standards 审阅

- 1 项 Important：MIT notice 没有随核心分发副本复制，违反许可证通知条件与仓库自包含标准。
- 根 `LICENSE` 文本与 OSI MIT 模板逐词一致（忽略换行布局及版权占位替换）。
- README 其余命令、数字、路径和本地链接准确。
- 未发现独立 smell-baseline 判断项。

## Spec 审阅

- 2 项 Important：发布就绪缺少实际分发 notice；Cursor 投影所有权陈述错误。
- Schema v2、单文件 CLI、bootstrap、168 项测试及 v2 反馈门槛均与仓库事实一致。
- 未发现无关 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 2/4 | 根许可证与状态更新已交付，但实际分发副本仍不具备许可证通知。 |
| B. 事实准确性 | 2/4 | Cursor 整文件所有权被错误描述为受管区块。 |
| C. 通用性 | 2/4 | 复制式脚手架落地到任意项目后都会丢失许可证 notice。 |
| D. 可维护性 | 4/4 | 变更局部清晰，所需整改边界明确。 |
| E. 验证充分性 | 3/4 | 168 项测试和 CI 通过，但缺少安装后许可证存在性测试。 |
| F. 可追溯性 | 3/4 | PR、提交、版权选择与验证记录清晰；分发许可链尚未闭环。 |

总分：**16/24**。存在 2 项 Important 合入阻断，当前不得合入。

## 独立验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 168 tests in 17.820s
OK (skipped=2)

$ git diff --check 104df2db4b60b5b829e374a4a17e7886a2d1fcea...a30904dcd50e635a876104cf8ff4704fccd2db5f
无输出，exit 0
```

- 本地 README 相对链接检查通过。
- README 所写 `init` 命令已真实运行成功。
- OSI/SPDX MIT 文本与本地 LICENSE 对照通过，差异仅为换行布局和版权占位替换。
- 相对基线没有修改 `template/.harness/`、tests 或 CI；这也直接解释了 notice 缺口为何未被现有门禁捕获。
- 远端 `validate` workflow 在固定 HEAD 上成功。
- PR 状态：`OPEN / Draft / MERGEABLE`。

## 合入意见

**不得合入当前 HEAD。**

实现方需关闭上述 2 项 Important，并在整改报告中逐项给出：

1. source bundle、真实 init 目标和许可证 notice 的完整闭包；
2. 精确文件集与 producer-history 测试如何同时保护中立性和法定通知；
3. README 对 block-owned 与 file-owned 投影的唯一措辞；
4. 新 HEAD 上的全量门禁、真实 init notice 探针及远端 CI。

推送新 HEAD 后必须重新执行 Standards / Spec 双路审阅。本记录不批准任何后续 HEAD。
