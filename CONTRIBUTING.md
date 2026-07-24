# Contributing to WordAgent

感谢你关注并参与 WordAgent！

WordAgent 是一个面向 WPS Office 和 Microsoft Word 的开源 AI 写作智能体项目。我们欢迎 Bug 修复、新功能、文档改进、内置 Skill、模型适配、界面优化和测试用例等各种形式的贡献。

在提交 Issue 或 Pull Request 前，请阅读本指南。

## 贡献方式

你可以通过以下方式参与项目：

* 报告 Bug
* 提出功能建议
* 改进中英文文档
* 修复后端或前端问题
* 增加模型服务商适配
* 改进 Single Agent 或 Multi Agent 工作流
* 提交新的内置 Skill
* 补充测试用例
* 改进 WPS 或 Microsoft Word 加载项
* 改进 Windows、Linux 或 macOS 打包流程

## 开发环境

推荐使用以下环境：

* Python 3.11 或更高版本
* Node.js 22 或更高版本
* uv
* pnpm 10
* Git
* WPS Office 或 Microsoft Word，用于加载项功能测试

克隆仓库：

```bash
git clone https://github.com/visresearch/WordAgent.git
cd WordAgent
```

建议先从仓库创建 Fork，再从自己的 Fork 创建开发分支。

## 分支命名

请从最新的 `master` 分支创建功能分支：

```bash
git checkout master
git pull origin master
git checkout -b feat/your-feature
```

推荐使用以下分支前缀：

| 类型       | 示例                               |
| -------- | -------------------------------- |
| 新功能      | `feat/add-model-provider`        |
| Bug 修复   | `fix/skill-loading-error`        |
| 文档       | `docs/update-installation-guide` |
| 重构       | `refactor/agent-runtime`         |
| 测试       | `test/add-skill-tests`           |
| 内置 Skill | `skill/academic-writing`         |
| 构建和 CI   | `build/update-pyinstaller`       |

请避免在 `master` 分支上直接开发。

## 后端开发

进入后端目录：

```bash
cd backend
```

安装正式依赖和开发依赖：

```bash
uv sync --extra dev
```

启动后端：

```bash
uv run python main.py
```

运行测试：

```bash
uv run pytest
```

运行 Ruff：

```bash
uv run ruff check .
```

自动修复 Ruff 可以处理的问题：

```bash
uv run ruff check . --fix
```

检查代码格式：

```bash
uv run black --check .
```

自动格式化代码：

```bash
uv run black .
```

运行类型检查：

```bash
uv run mypy app
```

提交后端代码前，至少应运行：

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

### Python 代码要求

* 新增公共函数和方法应尽量添加类型注解。
* 避免无必要的全局可变状态。
* 异步接口应保持异步调用链，避免在事件循环中执行长时间阻塞操作。
* 工具输入和输出优先使用明确的数据模型。
* 不要在代码中硬编码 API Key、访问令牌、密码或用户路径。
* 新功能应包含必要的异常处理和日志。
* 不要随意修改前后端通信字段；必须修改时，应同步更新两个前端。
* 新增依赖应说明用途，避免引入体积过大的依赖。

## WPS 加载项开发

进入 WPS 加载项目录：

```bash
cd frontend/wps_word_plugin
```

安装依赖：

```bash
pnpm install
```

启动开发服务器：

```bash
pnpm dev
```

构建：

```bash
pnpm build
```

运行代码检查：

```bash
pnpm lint
```

格式化代码：

```bash
pnpm format
```

请不要手动修改 `dist/` 目录中的构建产物。

## Microsoft Word 加载项开发

进入 Microsoft Word 加载项目录：

```bash
cd frontend/microsoft_word_plugin
```

安装依赖：

```bash
pnpm install
```

启动开发服务器：

```bash
pnpm dev-server
```

构建开发版本：

```bash
pnpm build:dev
```

构建生产版本：

```bash
pnpm build
```

运行代码检查：

```bash
pnpm lint
```

检查加载项清单：

```bash
pnpm validate
```

格式化代码：

```bash
pnpm prettier
```

启动 Microsoft Word 调试：

```bash
pnpm start
```

结束调试：

```bash
pnpm stop
```

## 前端贡献要求

* WPS 和 Microsoft Word 中共有的功能，应尽量保持行为一致。
* 修改前后端 API 时，需要检查两个加载项是否都需要同步修改。
* 界面改动应附带截图或录屏。
* 不要提交无关的格式化修改。
* 不要手动编辑生成后的 `dist/` 文件。
* 应尽量保持现有界面设计和交互风格。
* 修改加载项清单后，应运行对应的清单验证命令。

## 提交内置 Skill

内置 Skill 应保存在：

```text
backend/app/resources/builtin_skills/
```

推荐结构：

```text
builtin_skills/
├── manifest.json
└── academic-writing/
    ├── SKILL.md
    ├── examples.md
    └── terminology.md
```

运行时，内置 Skill 会被同步到统一的用户 Skill 目录：

```text
wence_data/project/skills/
```

### Skill 文件夹命名

Skill 文件夹名应满足以下要求：

* 使用小写英文。
* 使用 `kebab-case`。
* 发布后保持稳定。
* 不使用空格和特殊字符。
* 名称应能清楚表达 Skill 的用途。

推荐：

```text
academic-writing
humanizer-zh
technical-report
meeting-summary
```

不推荐：

```text
Skill 1
new_skill
test
我的技能
```

### SKILL.md 格式

每个 Skill 必须包含一个 `SKILL.md`：

```markdown
---
name: Academic Writing
description: 用于撰写、扩展和润色学术论文、研究报告及相关内容。
---

# Academic Writing

## 使用场景

当用户需要撰写学术论文、研究报告、实验分析或相关正式内容时使用本 Skill。

## 工作流程

1. 理解用户的研究主题和写作要求。
2. 分析当前文档结构。
3. 缺少资料时先进行研究。
4. 生成结构清晰、论证完整的内容。
5. 检查术语、逻辑和格式一致性。

## 约束

- 不得虚构实验数据和参考文献。
- 不确定的信息应明确说明。
- 保持学术表达准确、客观。
```

### Skill 贡献要求

* 一个 Pull Request 尽量只新增或修改一个 Skill。
* `description` 应明确说明触发场景，而不是只写宽泛介绍。
* Skill 应提供可执行的工作流程和明确约束。
* 较长的示例、术语表和参考内容应拆分到其他 Markdown 文件。
* 不得包含 API Key、用户数据或私有资料。
* 默认不接受包含可执行 Python、Shell、JavaScript 脚本的 Skill。
* 引用第三方内容时，应确认许可证允许再分发，并保留必要声明。
* 修改内置 Skill 时，应同步更新 `manifest.json` 中的版本号。
* 不得覆盖或删除用户创建的本地 Skill。
* 应测试 Skill 的发现、启用、停用和上下文加载行为。

提交 Skill 时，请在 Pull Request 中说明：

1. Skill 的用途。
2. 适用场景。
3. 触发示例。
4. 测试方式。
5. 内容来源和许可证。
6. 是否会覆盖现有 Skill。

## Commit 规范

推荐使用 Conventional Commits 格式：

```text
<type>(<scope>): <description>
```

常用类型：

| 类型         | 用途         |
| ---------- | ---------- |
| `feat`     | 新功能        |
| `fix`      | Bug 修复     |
| `docs`     | 文档修改       |
| `refactor` | 不改变行为的代码重构 |
| `test`     | 测试相关       |
| `style`    | 纯格式修改      |
| `build`    | 构建系统或依赖修改  |
| `ci`       | CI 工作流修改   |
| `chore`    | 其他维护工作     |

示例：

```text
feat(skill): add built-in academic writing skill
fix(agent): prevent disabled skills from loading
docs: add contribution guide
refactor(frontend): unify skill settings components
test(skill): add built-in skill synchronization tests
```

Commit 信息应简洁、明确，并描述实际修改。

## 提交 Pull Request

提交前，请确保自己的分支基于最新的 `master`：

```bash
git fetch upstream
git rebase upstream/master
```

推送分支：

```bash
git push origin feat/your-feature
```

然后向 WordAgent 的 `master` 分支创建 Pull Request。

### Pull Request 应包含

* 修改目的和背景。
* 主要实现方式。
* 测试方法和测试结果。
* 影响的平台，例如 Windows、Linux、macOS、WPS 或 Microsoft Word。
* 界面修改的截图或录屏。
* 关联的 Issue，例如 `Closes #123`。
* 新增依赖的原因。
* 可能存在的兼容性影响。

推荐的 Pull Request 描述：

```markdown
## 修改内容

简要说明本次修改解决了什么问题。

## 实现方式

说明主要实现思路和关键修改。

## 测试

- [ ] 后端测试通过
- [ ] Ruff 检查通过
- [ ] Black 格式检查通过
- [ ] WPS 加载项构建通过
- [ ] Microsoft Word 加载项构建通过
- [ ] 已进行实际办公软件测试

## 影响范围

说明会影响哪些模块和平台。

## 截图

如涉及界面修改，请提供截图或录屏。

## 关联 Issue

Closes #123
```

### Pull Request 检查清单

提交前请确认：

* [ ] 修改内容与 Pull Request 主题一致。
* [ ] 没有包含 API Key、密码或其他敏感信息。
* [ ] 没有提交无关的生成文件。
* [ ] 已更新相关文档。
* [ ] 已运行适用的测试和检查命令。
* [ ] 新增代码包含必要的异常处理。
* [ ] 前后端接口修改已同步处理。
* [ ] WPS 和 Microsoft Word 共用功能已检查一致性。
* [ ] 新增第三方内容符合许可证要求。
* [ ] Commit 信息清晰明确。

## 提交 Issue

### Bug 报告

Bug Issue 应尽量包含：

* WordAgent 版本。
* 操作系统及版本。
* WPS Office 或 Microsoft Word 版本。
* Python 和 Node.js 版本。
* 使用的模型和 API 服务商。
* 完整复现步骤。
* 预期行为。
* 实际行为。
* 相关日志和错误信息。
* 必要的截图或录屏。

提交日志前，请删除：

* API Key
* Access Token
* Cookie
* 用户文档内容
* 个人信息
* 本地敏感路径

### 功能建议

功能建议应说明：

* 当前存在的问题。
* 期望的使用场景。
* 建议的交互方式。
* 可能影响的模块。
* 是否愿意参与实现。

## 依赖修改

新增或升级 Python 依赖时：

```bash
cd backend
uv add package-name
uv lock
uv sync --extra dev
```

提交以下文件的相关变更：

```text
backend/pyproject.toml
backend/uv.lock
```

更新前端依赖时，应使用 `pnpm`，并提交对应的：

```text
package.json
pnpm-lock.yaml
```

请不要混用 npm、Yarn 和 pnpm，也不要在没有必要的情况下整体刷新锁文件。

## 文档修改

项目包含中英文 README 和独立文档站。

修改用户可见功能时，请检查是否需要同步更新：

```text
README.md
README.zh-CN.md
web/docs/
```

涉及命令、路径和配置时，请确保文档与实际代码一致。

## 安全问题

请不要在公开 Issue 中发布：

* 可用的 API Key
* 身份凭据
* 未公开的安全漏洞利用方法
* 包含个人数据的用户文档
* 其他敏感信息

发现安全问题时，请优先使用 GitHub 的私有安全报告功能，或联系项目维护者。

## 行为准则

请保持友善、专业和尊重。

我们不接受以下行为：

* 人身攻击或歧视性言论。
* 恶意骚扰其他参与者。
* 故意提交破坏性代码。
* 未经授权发布他人的隐私信息。
* 大量提交无关 Issue 或 Pull Request。

维护者有权关闭不符合项目目标、质量要求或行为准则的 Issue 和 Pull Request。

## 许可证

WordAgent 使用 Apache License 2.0。

向本项目提交代码、文档或其他内容，即表示你同意将自己的贡献按照项目使用的 Apache License 2.0 进行授权。

感谢你为 WordAgent 做出的贡献！
