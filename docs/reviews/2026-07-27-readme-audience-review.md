# README 受众与内容结构审阅（修订版）

- 审阅日期：2026-07-27
- 修订：同日补充「优秀 README 行业共识」对照，指出当前不足
- 审阅对象：仓库根目录 [`README.md`](../../README.md)
- 固定点（`main`）：`e338db8936a07b2f102df6fbd0bfa900577545b7`
- 审阅角色：独立客座审阅
- 结论：**Request changes**

## 验收准则（用户给定 Spec）

1. **说明项目的目的**
2. **说明项目的用法**
3. **不用说明项目的开发方式**

本记录以这三条为硬门槛。行业共识用于解释「为什么这样写更好」，不另开与用户准则冲突的新门槛。

---

## 优秀 README 通常怎么写（检索摘要）

综合 [GitHub Docs · About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)、[Make a README](https://www.makeareadme.com/)、[Standard Readme（中文规范）](https://github.com/RichardLitt/standard-readme/blob/main/spec.zh-CN.md)、以及近年实践文（如 [OpenMark](https://openmarkapp.com/blog/how-to-write-readme-md)、[Dokly README structure](https://www.dokly.co/blog/readme-file-structure)），成熟开源 README 的共识高度一致：

### 60 秒内要答完的问题

访客扫一眼就应得到：

| 问题 | 好 README 的答法 |
| --- | --- |
| 这是什么？ | 标题下 **一句** 产品描述（动词开头或「X 是用于 Y 的 Z」） |
| 为什么有用？ | 短「为何」或 Features，对准用户痛点，不是仓库史 |
| 怎么开始？ | **可复制粘贴** 的安装 / 第一条命令 + 最小成功路径 |
| 怎么用？ | Usage / 示例；CLI 要写清常用命令 |
| 去哪深入？ | 链到 `docs/`，正文不展开全书 |
| 许可？ | 单独、简短的 License |

GitHub 原文概括为：项目做什么、为什么有用、用户如何开始、去哪求助、谁在维护。并明确：**README 只放开始使用（与必要时开始贡献）的必要信息；更长文档放到 wiki / docs。**

### 推荐章节顺序（工具类 / CLI 项目）

1. 名称 + 一句话描述  
2. （可选）徽章、截图 / 终端演示  
3. **目的 / 解决什么问题**（短）  
4. **安装或接入**（前置条件 + 命令）  
5. **用法 / 快速开始**（最小可运行示例，含期望结果更佳）  
6. （可选）功能列表、配置、常见问题  
7. 进一步文档链接  
8. （可选）贡献入口 → `CONTRIBUTING.md`，**不要把完整开发流程写进 README**  
9. License  

Make a README 的模板几乎就是：Description → Installation → Usage → Contributing → License。Standard Readme 把 **用法（含代码块）** 列为默认必需。

### 明确不该占 README 主舞台的内容

行业实践反复提醒：

- **过程叙事**：设计演进史、范式变迁长文、多轮审阅复盘——属于 `docs/` / blog，不是首页。  
- **维护者专属命令**与**终端用户命令**混写：Dokly 等指南要求 *installation for end users* 与 *local development setup* 分开。  
- **实施计划、ADR 全目录、审阅轮次清单**：对贡献者有用，应链过去，不应成为扫读主路径。  
- 大段无命令的散文、把 Roadmap /「即将如何设计」放在前三屏（常见失败模式）。

一句话：**README 是产品前门，不是工程笔记本。**

---

## 当前 README 对照总表

| 期望能力 | 行业共识位置 | 当前 README 现状 | 判定 |
| --- | --- | --- | --- |
| 一句话说清是什么 | 标题下第一句 | 第一句是「本仓库用于**沉淀并维护**…」，主语是仓库维护 | 弱 |
| 目的 / 为何有用 | 开篇短节 | 「背景」偏 Prompt→Context→Harness **范式史**；用户痛点有，但淹没在叙事里 | 部分满足 |
| 安装 / 接入 | 靠前、可复制 | **没有独立安装/接入章**；`init` 挤在文末「快速验证」 | 不足 |
| 用法示例 | 靠前、可复制 | 无分步 Usage；无「跑完应看到什么」 | 不足 |
| 开发方式 | 应淡出或外链 | 「状态」写不变式闭包设计法、v2 规划准入；「设计与决策」列实施计划与审阅链 | **违规（准则 3）** |
| 许可 | 短节即可 | 有，且第三方摘要说明清楚 | 可保留 |
| 参考资料 | 可选外链 | 参考摘要链接合理，但插在目的与用法之间，打断扫读 | 宜后移 |

**章节实际顺序（现状）**：背景 → 本仓库做什么 → 参考资料 → 许可 → 状态 → 设计与决策（含审阅） → 快速验证 → License  

**行业推荐顺序**：目的 → 接入/用法 →（短）许可 →（可选）外链  

使用者要读到第一条真正有用的命令，需要穿过约半篇过程文档——这与「60 秒决策」模型相反。

---

## Spec Findings（对照用户三条准则）

### [P2] 用法不是主路径，且与维护者验证混写

**位置**：文末「快速验证」；全文无「用法 / 快速开始」标题。

**不足（结合行业共识）**：

1. Make a README / Standard Readme / GitHub Docs 都把 **Usage 或 Quick start** 当作默认核心；当前项目把它降级成「验证」附属句。  
2. 同一段混有：  
   - 消费者：`harness.py init --target …`  
   - 生产者：`unittest`、`validate.py` 校验分发包  
   这正是指南里说的 *end-user install* 与 *dev test* 未分离。  
3. 缺少最小成功路径的**有序步骤**（前置条件 → init → bootstrap → 日常 `validate` / `adapt`），也缺少「成功时长什么样」的一句期望输出。  
4. CLI 项目应在 Usage 里点名 `init` / `adapt` / `validate` 各自何时用；现状靠括号夹注，不可扫读。

**要求**：

1. 新增靠前的 **「用法」或「快速开始」**，只写消费者路径。  
2. 用有序列表 + fenced 命令块；写明 Python 3.9+。  
3. 仓库自测命令若保留，放到文末「维护者」小节或 `docs/`，不得与用法并列。

### [P2] 大量说明开发方式与过程资产

**位置**：「本仓库做什么」「状态」「设计与决策」及审阅列表。

**不足（结合行业共识）**：

1. GitHub：「README 只含开始使用所需信息；更长文档放 wiki/docs。」当前把设计规格、ADR、**实施计划**、多轮**审阅记录**做成 README 主体导航。  
2. 「发现一次 Agent 错误 → 工程化消除同类错误」「不变式闭包设计法」「v2 以反馈为准入」是**研发方法论 / 路线图治理**，不是用法。  
3. 「本仓库做什么」三条里，有两条在讲 Git 管理与可追溯决策——维护者视角，不是「接到我项目后我得到什么」。  
4. 优秀 README 若提 Contributing，通常是一条链接；不会在首页展开审阅轮次与流程生效声明。

**要求**：

1. 删除或压缩上述过程正文；最多保留「详细设计见 `docs/design/`、`docs/adr/`」一条。  
2. 「状态」若保留：只写**产品能力**（例如已提供 v1：`init` / `adapt` / `validate` 与平台投影），不写流程/规划治理。  
3. 审阅记录、实施计划留在 `docs/reviews/`、`docs/plans/`，README 不枚举。

### [P3] 目的有素材，但第一句选错主语

**位置**：开篇与「背景」。

**不足**：

- 好 README 的第一句回答「这是什么 / 做什么」；当前第一句回答「这个仓库用来沉淀什么」。  
- 「背景」写成范式简史，对决定是否 `init` 的读者增益低；细节更适合 `docs/reference/`。

**建议**（与 P2 同改即可）：

用 2–4 句写清：解决 Agent 在真实仓库里「能写但不稳」的问题；给谁（要把约束/流程交给 Agent 的团队）；交付物（可复制的 `.harness/` + CLI）。

---

## Standards Findings

### [P3] 扫读结构违反「短段落 + 早出现命令」

当前几乎全是长段落，关键命令出现晚。行业建议：短段、列表、代码块；命令尽早出现。许可与第三方声明可保留，但宜放在用法之后，避免插在目的与用法之间。

无阻塞级死链或排版硬伤；本条不单独阻塞，随 P2 结构调整即可。

---

## 建议改写骨架（开发者可直接套）

```markdown
# Scaffold — 通用 AI Coding Harness

一句话：给 AI Coding Agent 用的可移植约束与交付脚手架（Harness），
让需求→实现→校验在真实仓库里可重复、可审计。

## 它解决什么问题
（3–5 条用户痛点 / 得到什么；不要写仓库如何维护自己）

## 快速开始
### 前置条件
Python 3.9+

### 接到目标项目
```bash
python3 template/.harness/bin/harness.py init --target /path/to/your-project
```
（一句：会安装 `.harness/` 并生成平台投影）

### 定制
在目标项目中运行 harness-bootstrap Skill（链到包内说明即可）

### 日常命令
- validate：…
- adapt：…

## 许可
MIT；第三方摘要例外一句话 + 链接

## 进一步阅读
- 设计 / ADR：docs/design、docs/adr
- 不要在此贴实施计划与审阅轮次
```

（可选）文末三行「维护本仓库」：`validate.py` / `unittest`——与用法严格分开。

---

## 总判与合入意见

| 准则 | 判定 |
| --- | --- |
| 1. 目的 | **部分满足** |
| 2. 用法 | **不足** |
| 3. 不写开发方式 | **不满足** |

**就「README 是否可作为对外入口」：Request changes。**  
不要求回滚产品功能；只要求按上表把 README 从「工程笔记本首页」改成「产品前门」。

开发者修订后请在 PR / 提交说明中引用本文件，便于对照关闭 P2。

## 主要参考（检索来源）

- [GitHub Docs — About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)  
- [Make a README](https://www.makeareadme.com/)  
- [Standard Readme 规范（中文）](https://github.com/RichardLitt/standard-readme/blob/main/spec.zh-CN.md)  
- [OpenMark — README that developers actually read](https://openmarkapp.com/blog/how-to-write-readme-md)  
- [Dokly — README file structure](https://www.dokly.co/blog/readme-file-structure)  

## 审阅范围

- 已读：`README.md`（`main` @ `e338db8`）。  
- 未把其它 PR 的功能实现纳入本 README 准则审阅。  
- 审阅者不合并；由维护者处理本记录与后续 README 修订的合入。
