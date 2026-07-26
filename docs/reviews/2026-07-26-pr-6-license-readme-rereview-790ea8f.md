# PR #6 License and README 整改复审

- 审阅日期：2026-07-26
- PR：#6 `Release readiness: MIT license and README refresh`
- 基线：`main@104df2db4b60b5b829e374a4a17e7886a2d1fcea`
- 固定 HEAD：`790ea8f080774d24650427607d6e9eec4bfc5b0e`
- PR 总提交：5 个；本轮整改提交：`60bd0bb`、`7d8e6c5`、`790ea8f`
- 完整变更：6 个文件，`+80/-6`
- 审阅方式：Standards / Spec 双路独立复审、真实 `init` 探针、OSI/SPDX MIT 文本对照、许可证边界定向变异、全量测试、远端 CI 与 README 事实核对
- 当前结论：**Request changes，禁止合入**

本结论只绑定上述精确 HEAD。任何新提交都必须重新锁定 HEAD 并执行新的独立审阅，不能继承本次结论。

## 上轮四点整改状态

1. **source bundle / init / notice 闭环：行为已关闭。** `template/.harness/LICENSE` 已进入精确 bundle 文件集；真实 `init` 后安装到 `.harness/LICENSE`，并与 bundle、根 LICENSE 字节一致。
2. **中立性与法定通知测试边界：未关闭。** 设计裁决方向正确，但 producer-history 豁免的机械实现宽于裁决。
3. **block-owned / file-owned 唯一措辞：已关闭。** README 已明确 CLAUDE.md / AGENTS.md 仅更新受管区块，Cursor 文件由工具整文件拥有并重建。
4. **新 HEAD 门禁、真实 init 探针与 CI：部分关闭。** 169 项测试、validate、真实 init 和远端 CI 均通过；但“notice 文本正确”的回归测试缺少权威全文锚点。

## Findings

### [Important] producer-history 豁免覆盖了整个 LICENSE，而非唯一法定版权行

位置：

- `docs/design/harness-v1.md:83`
- `tests/test_template_contract.py:50-65`

设计裁决要求：

- 仅 `LICENSE` 中的版权持有人与年份属于法定通知；
- `LICENSE` 内除版权行外的其他约束不放松；
- 其他文件继续执行全部 producer-history token 扫描。

实现却使用：

```python
exempt_tokens_by_path = {"LICENSE": ("StevenG3",)}
...
if token in exempt:
    continue
```

这会跳过 `LICENSE` 全文中的所有 `StevenG3`，不是只跳过唯一版权行。独立变异将下列内容追加到版权行之外：

```text
StevenG3 internal producer-history note outside the copyright line
```

结果：

```text
test_template_contract.py: 3 tests OK
test_harness_cli.py: 66 tests OK (skipped=2)
validate.py: Harness contract is valid
```

因此当前测试无法落实设计所称“LICENSE 内除版权行外不放松”，法定通知例外仍可能掩盖生产者历史泄漏。

整改要求：

1. 只允许一个逐字匹配的法定版权行，例如 `Copyright (c) 2026 StevenG3`，并断言该行唯一。
2. 从扫描输入中只剔除这一整行；LICENSE 的所有其余行继续执行全部 forbidden token 扫描。
3. 增加负例，证明 `StevenG3` 出现在 LICENSE 的任意其他位置都会失败。

### [Important] 真实 init 测试没有证明 MIT notice 全文正确

位置：

- `tests/test_harness_cli.py:1661-1679`
- `LICENSE:1-21`
- `template/.harness/LICENSE:1-21`

当前测试证明：

- source LICENSE 存在；
- installed LICENSE 与 source LICENSE 字节相同；
- installed LICENSE 包含 `MIT License` 和版权行。

它没有将 source LICENSE 锚定到根 LICENSE、固定全文或权威文本，也没有断言授权段、通知保留条件和免责声明存在。独立变异将：

```text
Permission is hereby granted
```

替换为无效占位文本，同时保留标题和版权行；上述 template-contract、全部 CLI 测试及 validate 仍然通过。installed 与已损坏 source 字节一致并不能证明 notice 文本正确。

当前 HEAD 的实物文本本身正确：根 LICENSE、bundle LICENSE、真实 init 后的 installed LICENSE 三者 SHA-256 均为：

```text
c76ac50199f94e4d75cb6f6ca4dd53d92bd7752bdb7e1911599a71448ad12a70
```

且本地文本与 SPDX MIT 模板在替换年份/版权持有人并归一化空白后相同。权威参考：

- https://opensource.org/license/mit
- https://spdx.org/licenses/MIT.html

问题在于回归门禁没有保护这一当前正确状态。

整改要求：

1. 将 bundle LICENSE 全文锚定到经审定的根 LICENSE、固定预期字节或固定 SHA-256；不得仅自证 `installed == source`。
2. 保留 `installed == bundle`，从而形成“权威全文 → bundle → installed”的可验证链。
3. 增加负例，证明删除或篡改授权段、通知保留条件、免责声明中的任一段都会失败。

## Standards 审阅

- 1 项 Important：producer-history 豁免宽于 `docs/design/harness-v1.md:83` 的设计裁决。
- 当前 bundle / init 实物闭环正确，README 投影语义正确。
- 双份 LICENSE 是分发要求，不作为 Duplicated Code smell；未发现其他 smell。

## Spec 审阅

- 2 项 Important：notice 正确性测试没有权威全文锚点；豁免没有限定到唯一版权行。
- source bundle、真实 init、当前 LICENSE 文本、README block/file-owned 措辞、169 项测试及 CI 的当前状态均正确。
- 未发现无关 scope creep。

## 六维评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| A. 需求符合度 | 3/4 | 当前行为闭环，但两项明确的测试边界要求只部分实现。 |
| B. 事实准确性 | 4/4 | README、设计裁决及当前 LICENSE 文本与实现一致。 |
| C. 通用性 | 3/4 | 文件级 holder-token 豁免会容许未来生产者历史混入 LICENSE 非版权行。 |
| D. 可维护性 | 3/4 | 根与 bundle 双份许可证缺少机器化权威锚点。 |
| E. 验证充分性 | 2/4 | 全量门禁绿，但两种违反规格的定向变异仍然全绿。 |
| F. 可追溯性 | 4/4 | 三段整改提交、设计裁决、测试和 CI 均可追溯。 |

总分：**19/24**。存在 2 项 Important 合入阻断，当前不得合入。

## 独立验证证据

```text
$ python3 template/.harness/bin/validate.py
Harness contract is valid.

$ python3 -m unittest discover -s tests -q
Ran 169 tests in 16.885s
OK (skipped=2)

$ git diff --check \
  104df2db4b60b5b829e374a4a17e7886a2d1fcea...790ea8f080774d24650427607d6e9eec4bfc5b0e
无输出，exit 0
```

真实 `init` 探针：

```text
init_rc=0
license_notice_hits={
  ".harness/LICENSE": [
    "MIT License",
    "Copyright (c) 2026 StevenG3",
    "Permission is hereby granted",
    "The above copyright notice and this permission notice shall be included"
  ]
}
installed_byte_identical_to_bundle=True
installed_byte_identical_to_root=True
spdx_normalized_equal=True
```

- README 本地相对链接全部存在。
- adapter 表与 README 一致：Claude/Codex 为 `mode: block`，Cursor 为 `mode: file`。
- 远端 `Validate Harness / validate` 在固定 HEAD 上 SUCCESS，run `30200526083`。
- PR 状态：`OPEN / Draft / MERGEABLE`。

## 合入意见

**不得合入当前 HEAD。**

实现方需关闭上述 2 项 Important，并在整改报告中给出：

1. “权威全文 → bundle → installed”的逐字节证据链；
2. 仅剔除唯一法定版权行、其余 LICENSE 内容完整扫描的实现；
3. 两个负例：破坏 MIT 正文必须失败；版权行外出现 holder token 必须失败；
4. 新 HEAD 上的 169+ 全量门禁、真实 init 探针及远端 CI。

推送新 HEAD 后必须重新执行 Standards / Spec 双路审阅。本记录不批准任何后续 HEAD。
