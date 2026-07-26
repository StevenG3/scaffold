# PR #6 License and README 第二轮整改复审

- 审阅日期：2026-07-26
- PR：#6 `Release readiness: MIT license and README refresh`
- 基线：`main@104df2db4b60b5b829e374a4a17e7886a2d1fcea`
- 固定 HEAD：`a76dccf86b167a2d24800c291a424c16d25e3a5b`
- 本轮 fixed point：`790ea8f080774d24650427607d6e9eec4bfc5b0e`
- 本轮提交：`a76dccf test: pin the MIT notice chain and narrow the copyright exemption`
- 本轮范围：仅 `tests/test_harness_cli.py`、`tests/test_template_contract.py`，`+159/-18`
- PR 完整范围：6 个文件，`+227/-12`
- 审阅方式：Standards / Spec 双路独立复审、全量测试、真实 `init`、OSI/SPDX 文本对照、两项定向变异、跨测试模块导入验证、README 与 PR 元数据核对
- 当前结论：**Request changes，禁止合入**

本结论只绑定上述精确 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## 上轮两项 Important 关闭情况

### 已关闭：法定版权行豁免窄度

`tests/test_template_contract.py` 现在：

- 要求 `Copyright (c) 2026 StevenG3` 逐字出现且仅出现一次；
- 只从 LICENSE 扫描输入中删除这一整行；
- 对 LICENSE 剩余内容恢复 `StevenG3` 及其他全部 forbidden token；
- 覆盖 holder token 出现在版权行外、其他生产者 token 出现在 LICENSE 内的负例。

独立把下列内容追加到 bundle LICENSE：

```text
StevenG3 internal producer-history note outside the copyright line
```

相关测试结果为恰好 3 项失败：

```text
test_bundle_license_is_the_audited_root_notice
test_pristine_bundle_copy_passes_the_same_scan
test_bundle_contains_no_producer_history
```

### 已关闭：MIT notice 全文权威锚点

当前链路为：

```text
审定 SHA-256
→ 根 LICENSE
→ template/.harness/LICENSE
→ 真实 init 后的 .harness/LICENSE
```

三份文件当前字节一致，SHA-256 为：

```text
c76ac50199f94e4d75cb6f6ca4dd53d92bd7752bdb7e1911599a71448ad12a70
```

与 SPDX MIT 模板替换年份、版权持有人并归一化空白后相同。权威参考：

- https://opensource.org/license/mit
- https://spdx.org/licenses/MIT.html

独立将 `Permission is hereby granted` 替换为损坏文本，相关测试恰好 3 项失败：

```text
test_bundle_license_is_the_audited_root_notice
test_tampering_with_any_substantive_segment_fails
test_real_init_lands_byte_identical_license
```

其中包含真实 `init` 测试，证明 installed 副本不再仅对 source 自证。

### 已接受：跨测试模块复用

`tests/test_harness_cli.py` 从 `test_template_contract` 复用 `assert_valid_mit_notice`。该 helper 表达单一许可证语义，避免复制断言；仓库已有 `test_schema_v2.py` 复用 `test_validate` helper 的惯例。全量 discover 与 `python3 tests/test_harness_cli.py -q` 均通过，未发现导入顺序、重复收集或可移植性问题，不构成 finding。

## Finding

### [Important] README 与 PR 发布事实再次落后于 exact HEAD

位置：

- `README.md:31`
- PR #6 正文“目的 / 状态 / 验证”

README 当前仍声称：

```text
169 个测试与配套 CI 门禁
```

本轮新增 6 项测试后，独立全量运行结果为：

```text
Ran 175 tests in 19.005s
OK (skipped=2)
```

PR 正文也仍写：

- “不涉及任何分发包内容改动”；
- “168 tests，与基线一致”；
- “README / LICENSE 均在分发包之外，测试面不应变动”。

这些陈述与当前 PR 已新增 `template/.harness/LICENSE`、修改测试并达到 175 项的事实直接冲突。该 PR 的核心目标正是把公开发布状态更新到已交付事实，因此不能以新的过期状态完成发布就绪。

整改要求：

1. 将 README 的测试数更新为 175，或删除易随新增测试漂移的精确数量，只承诺全量测试与 CI 门禁。
2. 同步 PR 正文：说明 bundle LICENSE、许可证回归测试与当前 175 项结果；移除“不涉及分发包”“测试面不变”等失效陈述。
3. 新 HEAD 重跑全量测试、validate、两项变异和远端 CI。

## Standards 审阅

- 1 项 Important：`README.md:31` 的发布事实已从 169 漂移到实际 175。
- possible Shotgun Surgery（判断项）：公开 README 固定精确测试数，导致每次补回归测试都要同步修改发布文档；可考虑删除精确数量。
- 上轮许可证窄度问题已关闭；跨模块 helper 复用可接受；无其他 documented-standard breach 或 smell。

## Spec 审阅

- 1 项 Important：PR 目标要求 README 反映已交付状态，但当前测试数及 PR 验证正文仍与 exact HEAD 不一致。
- 上轮两项 Important 均已关闭；两种变异各触发 3 项失败，真实 init、SHA 链与全 token 扫描符合规格。
- 未发现 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 3/4 | 两项核心测试边界已关闭，但发布状态更新仍不完整。 |
| B. 事实准确性 | 3/4 | 许可证与投影事实正确；README 和 PR 正文测试数字过期。 |
| C. 通用性 | 4/4 | 法定通知例外已收窄，bundle 在任意目标项目保持正确。 |
| D. 可维护性 | 4/4 | SHA 锚点、共享 helper 和负例边界清晰。 |
| E. 验证充分性 | 4/4 | 两项反证、真实 init、175 项测试和 CI 均覆盖。 |
| F. 可追溯性 | 3/4 | 提交与测试清楚，但 PR 正文仍描述旧范围和旧证据。 |

总分：**21/24**。存在 1 项 Important 合入阻断，当前不得合入。

## 独立验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 175 tests in 19.005s
OK (skipped=2)

$ git diff --check \
  104df2db4b60b5b829e374a4a17e7886a2d1fcea...a76dccf86b167a2d24800c291a424c16d25e3a5b
无输出，exit 0
```

真实 `init` 与许可证文本：

```text
init_rc=0
license_sha256=c76ac50199f94e4d75cb6f6ca4dd53d92bd7752bdb7e1911599a71448ad12a70
root_bundle_installed_equal=True
spdx_normalized_equal=True
```

- 本轮提交相对 `790ea8f` 仅修改两个测试文件。
- 远端 `Validate Harness / validate` 在固定 HEAD 上 SUCCESS，run `30201191602`。
- PR 状态：`OPEN / Draft / MERGEABLE`。

## 合入意见

**不得合入当前 HEAD。**

许可证通知链和豁免边界已经通过复审，不需再次改写。实现方只需同步 README 与 PR 正文的发布事实，并在新 HEAD 上提供全量门禁、两项变异及 CI 证据。

推送新 HEAD 后必须重新执行 Standards / Spec 双路审阅。本记录不批准任何后续 HEAD。
