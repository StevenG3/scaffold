# Harness v0 设计规格

- 状态：Approved
- 批准日期：2026-07-19
- 目标版本：Schema v1
- 对应决策：[ADR-0001：可移植 Harness 契约](../adr/0001-portable-harness-contract.md)

## 1. 背景

本仓库的目标是提供可复制、可演进、与具体业务解耦的 AI Coding Harness。当前仓库只有工程说明与参考摘要，尚未形成可直接放入其他项目的交付物。

v0 的任务不是一次性实现完整 Harness，而是交付一个最小但完整的垂直切片：目标项目能够复制一个目录，获得 Agent 入口、组件索引、最小交付流程、Change 模板和可机械执行的结构校验。

## 2. 头脑风暴结论

设计前比较了三条路线：

1. 只编写架构与目录文档：决策风险低，但无法验证约束能否机械执行。
2. 一次性搭建完整 Harness：表面进展快，但会在缺少真实反馈时过早固化十阶段流程、MCP 和多 Agent 编排。
3. 实现可执行的最小 Harness 垂直切片：同时覆盖约束、模板、校验和 Dry Run，且保持小范围。

采用方案 3。它最符合 Harness Engineering 的原则：先建立短反馈回路，再根据真实失败持续演进。

头脑风暴还识别并修正了四个通用性问题：

- 校验器和运行资产不能散落到目标项目根目录。
- Schema 不能固化单一 Application Owner 或固定 Skill 名称。
- 机械校验不能依赖特定语言的 Markdown 标题。
- scaffold 自身的设计与变更历史不能进入目标项目的分发包。

## 3. 目标

v0 必须满足以下结果：

- 目标项目复制 `template/.harness/` 后即可获得完整 Harness 资产。
- Manifest 为 Agent 和工具提供统一、可扩展的机器入口。
- 校验器支持 Python 3.9 及以上版本，无需第三方 Python 包，并且只读、确定性、可用于 CI。
- 最小 Agent、Rule、Skill 和 Change Template 共同演示一次完整交付路径。
- 分发包不包含 scaffold 仓库专属名称、日期、审阅记录或实现历史。
- 设计、架构决策、实施计划、PR 审阅和合入结果在本仓库内可追溯。

## 4. 非目标

v0 不实现以下内容：

- 完整十阶段开发流水线。
- 多 Agent 调度或远程 Agent 执行。
- MCP Server 配置与外部系统集成。
- 面向目标项目的自动安装器、升级器或卸载器。
- 任何语言、框架、行业或业务专属规则。
- 对 Markdown 正文质量、自然语言含义或完整 YAML 语法的解析。
- 为目标项目生成 GitHub、GitLab 或其他 CI 平台配置。

## 5. 分层架构

### 5.1 可移植分发包

```text
template/
└── .harness/
    ├── manifest.json
    ├── README.md
    ├── agents/
    │   └── coordinator.md
    ├── rules/
    │   └── delivery.md
    ├── skills/
    │   └── change-delivery/
    │       └── SKILL.md
    ├── templates/
    │   └── change/
    │       ├── summary.md
    │       ├── spec.md
    │       └── tasks.md
    ├── changes/
    │   └── README.md
    └── bin/
        └── validate.py
```

`template/.harness/` 是唯一需要复制到目标项目的运行资产。其内部路径自包含，不依赖 scaffold 仓库的其他目录。

### 5.2 生产者侧资产

```text
docs/
├── design/
│   └── harness-v0.md
├── adr/
│   └── 0001-portable-harness-contract.md
├── plans/
│   └── harness-v0-implementation.md
└── reviews/

tests/
├── fixtures/
└── test_validate.py

.github/
└── workflows/
    └── validate.yml
```

这些文件服务于 scaffold 的设计、测试和审计，不属于分发包。目标项目复制 `.harness/` 时不会继承本仓库的历史。

## 6. Manifest 契约

`template/.harness/manifest.json` 使用 UTF-8 JSON，不允许注释。v0 示例为：

```json
{
  "schema_version": 1,
  "entrypoint": "README.md",
  "components": [
    {
      "id": "coordinator",
      "kind": "agent",
      "path": "agents/coordinator.md"
    },
    {
      "id": "delivery-rule",
      "kind": "rule",
      "path": "rules/delivery.md"
    },
    {
      "id": "change-delivery",
      "kind": "skill",
      "path": "skills/change-delivery/SKILL.md"
    }
  ],
  "change_management": {
    "template": "templates/change",
    "records": "changes",
    "required_files": [
      "summary.md",
      "spec.md",
      "tasks.md"
    ]
  }
}
```

### 6.1 字段规则

- `schema_version`：必填整数；v0 仅接受 `1`。
- `entrypoint`：必填相对文件路径；相对 Manifest 所在目录解析。
- `components`：必填数组；至少包含一个组件。
- `components[].id`：必填非空字符串，在 Manifest 内唯一。
- `components[].kind`：必填；内置值为 `agent`、`rule`、`skill`，扩展值必须以 `x-` 开头。
- `components[].path`：必填相对文件路径。
- `change_management.template`：必填相对目录路径。
- `change_management.records`：必填相对目录路径。
- `change_management.required_files`：必填非空数组；成员为模板目录内的相对文件路径且不得重复。

顶层、组件和 Change Management 中未定义的字段只有以 `x-` 开头时才允许。这样既能捕获拼写错误，也为项目扩展保留命名空间。

### 6.2 路径规则

- 所有 Manifest 路径都相对 Manifest 所在目录解析。
- 禁止绝对路径和任何 `..` 路径段。
- 路径解析后的真实位置必须位于 Harness 根目录内。
- 指向 Harness 根目录之外的符号链接视为契约错误。
- Manifest 引用的文件必须存在、是普通文件且非空。
- Manifest 引用的目录必须存在且是目录。

## 7. 组件职责

### 7.1 README 入口

`.harness/README.md` 是人和 Agent 的统一入口，说明 Harness 的目的、启动顺序、组件地图、最小交付流程和验证命令。正文语言及标题不属于机器契约。

### 7.2 Coordinator 示例

`agents/coordinator.md` 演示一个最小协调角色：读取入口与 Manifest、加载任务所需规则和 Skill、要求变更记录、检查验证证据。`coordinator` 只是模板实例，不是 Schema 中的保留角色；目标项目可以替换或增加其他 Agent。

### 7.3 Delivery Rule 示例

`rules/delivery.md` 表达稳定而通用的交付约束：理解、计划、执行、验证。规则不得出现特定语言、框架或业务领域要求。

### 7.4 Change Delivery Skill

`skills/change-delivery/SKILL.md` 使用 Agent Skills 风格的 frontmatter，至少包含顶层 `name` 和 `description`。Skill 说明何时使用、输入、执行步骤、输出与验证方式，但不固化十阶段流水线。

### 7.5 Change Template

- `spec.md`：目标、范围、非目标和验收标准。
- `tasks.md`：可执行步骤、依赖和完成状态。
- `summary.md`：当前状态、实现结果、验证证据、例外和最终结论。

模板正文可以翻译或调整。机器契约只要求 Manifest 声明的文件存在且非空，不依赖固定标题。

### 7.6 Change Records

`changes/README.md` 解释记录目录的用途。空记录目录合法；每个非隐藏子目录都视为一条 Change Record，并必须包含 `required_files` 声明的全部文件。

## 8. 数据流

```text
Agent 或开发者读取 .harness/README.md
→ 读取 manifest.json
→ 根据任务选择 Component
→ 从 Change Template 建立变更记录
→ 执行任务并持续记录证据
→ 运行 bin/validate.py
→ CI 和 Reviewer 使用同一结果验收
```

Manifest 是组件发现的机器入口，README 是使用说明，Change Record 是过程状态，Validator 是外部质量门禁。四者职责不重叠。

## 9. 校验器设计

### 9.1 命令接口

```bash
python3 template/.harness/bin/validate.py
python3 template/.harness/bin/validate.py --root path/to/harness
python3 template/.harness/bin/validate.py --format json
```

- 无 `--root` 时，以 `validate.py` 所在目录的父目录为 Harness 根目录。
- `--root` 指向包含 `manifest.json` 的 Harness 根目录。
- `--format` 接受 `text` 或 `json`，默认 `text`。
- 校验器不写入、不修复、不规范化目标文件。

### 9.2 输出与退出码

- 所有契约错误一次性收集，并按错误代码、路径、消息稳定排序。
- Text 输出面向人阅读，每行一项错误。
- JSON 输出为包含 `valid`、`errors`、`root`、`schema_version` 的对象；`root` 是规范化后的绝对路径，无法读取 Schema 时 `schema_version` 为 `null`。
- `errors` 始终是数组；每项固定包含字符串字段 `code`、`path`、`message`，验证成功时为空数组。
- Text 错误格式固定为 `[CODE] path: message`。
- 退出码 `0`：契约有效。
- 退出码 `1`：Manifest、组件、模板或 Change Record 违反契约。
- 退出码 `2`：命令参数错误、根目录不可访问或校验器自身发生非预期错误。

### 9.3 Skill Frontmatter

校验器只检查 `kind: skill` 文件是否：

- 以 `---` 开始并包含闭合的 `---`。
- Frontmatter 区域存在非空的顶层 `name:`。
- Frontmatter 区域存在非空的顶层 `description:`。

校验器不实现完整 YAML，不解析嵌套字段，也不约束其他 frontmatter 属性。

## 10. 测试设计

测试使用 Python 标准库 `unittest`、`tempfile` 和 `shutil`，不安装第三方依赖。测试矩阵至少覆盖：

1. 官方最小模板验证成功。
2. Manifest 缺失、JSON 损坏和 schema 版本错误。
3. Component ID 重复。
4. 未知普通 `kind` 被拒绝，`x-*` 扩展被接受。
5. 绝对路径、目录穿越和符号链接逃逸被拒绝。
6. Component 文件缺失、类型错误或为空。
7. Skill frontmatter 缺少 `name` 或 `description`。
8. Change Template 缺少必需文件。
9. 实际 Change Record 不完整。
10. Text、JSON 输出和退出码稳定。
11. 将 `template/.harness/` 复制到临时项目后仍能独立验证。
12. 校验前后文件树与内容哈希一致，证明校验器只读。

## 11. CI 门禁

本仓库增加 GitHub Actions 工作流，至少执行：

```bash
python3 template/.harness/bin/validate.py
python3 -m unittest discover -s tests -v
```

CI 配置属于生产者侧资产。分发文档可以展示通用命令，但不向目标项目复制 GitHub Actions，也不假定其 CI 平台。

## 12. 验收标准

实现必须同时满足：

- `template/.harness/` 是完整、自包含的分发单元。
- 分发包中不存在 scaffold 仓库专属名称、日期、审阅记录或实现历史。
- 使用 Python 3.9 及以上版本的标准库即可运行，不需要安装依赖。
- 官方模板校验退出码为 `0`。
- 所有单元测试通过。
- 复制到临时项目后的可移植性测试通过。
- 只读性测试通过。
- GitHub Actions 通过。
- `git diff --check` 无错误。
- 未引入非目标中列出的完整流程、集成或业务规则。

## 13. 可追溯链

本功能的工程证据按以下顺序关联：

```text
docs/design/harness-v0.md
→ docs/adr/0001-portable-harness-contract.md
→ docs/plans/harness-v0-implementation.md
→ 实现 PR
→ docs/reviews/ 下的独立审阅记录
→ 合入提交
```

设计和 ADR 由规划者维护；实现由开发者完成；审阅与合入由独立审阅者执行。分发包不携带这条生产者侧历史。

## 14. 实施边界

开发者可以在不改变外部契约的前提下调整校验器内部函数划分和测试夹具组织。以下变化必须先修改设计或新增 ADR 并重新批准：

- 修改 Manifest 必填字段或路径解析规则。
- 修改退出码语义或 JSON 输出顶层字段。
- 引入第三方运行时依赖。
- 将生产者侧文件加入分发包。
- 扩大到 v0 非目标范围。
