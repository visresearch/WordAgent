> ## Documentation Index
> Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# How Claude Code works

> Understand the agentic loop, built-in tools, and how Claude Code interacts with your project.

Claude Code is an agentic assistant that runs in your terminal. While it excels at coding, it can help with anything you can do from the command line: writing docs, running builds, searching files, researching topics, and more.

This guide covers the core architecture, built-in capabilities, and [tips for working effectively](#work-effectively-with-claude-code). For step-by-step walkthroughs, see [Common workflows](/en/common-workflows). For extensibility features like skills, MCP, and hooks, see [Extend Claude Code](/en/features-overview).

## The agentic loop

When you give Claude a task, it works through three phases: **gather context**, **take action**, and **verify results**. These phases blend together. Claude uses tools throughout, whether searching files to understand your code, editing to make changes, or running tests to check its work.

<img src="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=e30acfc80d6ff01ec877dd19c7af58b2" alt="The agentic loop: Your prompt leads to Claude gathering context, taking action, verifying results, and repeating until task complete. You can interrupt at any point." data-og-width="720" width="720" data-og-height="280" height="280" data-path="images/agentic-loop.svg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=280&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=8620f6ebce761a1e8bbf7f0a0255cc15 280w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=560&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=7b46b5ff4454aa4a03725eee625b39a0 560w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=840&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=7fa0397bc37d147e3bf3bb6296c6477f 840w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=1100&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=73b2a7040c4c93821c4d5bbee9f4a2d4 1100w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=1650&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=17703cbeb6f59b40a00ab24f56d5f8f9 1650w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?w=2500&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=20dedb60b95d45a1bd60a0cccaf3e1ff 2500w" />

The loop adapts to what you ask. A question about your codebase might only need context gathering. A bug fix cycles through all three phases repeatedly. A refactor might involve extensive verification. Claude decides what each step requires based on what it learned from the previous step, chaining dozens of actions together and course-correcting along the way.

You're part of this loop too. You can interrupt at any point to steer Claude in a different direction, provide additional context, or ask it to try a different approach. Claude works autonomously but stays responsive to your input.

The agentic loop is powered by two components: [models](#models) that reason and [tools](#tools) that act. Claude Code serves as the **agentic harness** around Claude: it provides the tools, context management, and execution environment that turn a language model into a capable coding agent.

### Models

Claude Code uses Claude models to understand your code and reason about tasks. Claude can read code in any language, understand how components connect, and figure out what needs to change to accomplish your goal. For complex tasks, it breaks work into steps, executes them, and adjusts based on what it learns.

[Multiple models](/en/model-config) are available with different tradeoffs. Sonnet handles most coding tasks well. Opus provides stronger reasoning for complex architectural decisions. Switch with `/model` during a session or start with `claude --model <name>`.

When this guide says "Claude chooses" or "Claude decides," it's the model doing the reasoning.

### Tools

Tools are what make Claude Code agentic. Without tools, Claude can only respond with text. With tools, Claude can act: read your code, edit files, run commands, search the web, and interact with external services. Each tool use returns information that feeds back into the loop, informing Claude's next decision.

The built-in tools generally fall into four categories, each representing a different kind of agency.

| Category              | What Claude can do                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File operations**   | Read files, edit code, create new files, rename and reorganize                                                                                                |
| **Search**            | Find files by pattern, search content with regex, explore codebases                                                                                           |
| **Execution**         | Run shell commands, start servers, run tests, use git                                                                                                         |
| **Web**               | Search the web, fetch documentation, look up error messages                                                                                                   |
| **Code intelligence** | See type errors and warnings after edits, jump to definitions, find references (requires [code intelligence plugins](/en/discover-plugins#code-intelligence)) |

These are the primary capabilities. Claude also has tools for spawning subagents, asking you questions, and other orchestration tasks. See [Tools available to Claude](/en/settings#tools-available-to-claude) for the complete list.

Claude chooses which tools to use based on your prompt and what it learns along the way. When you say "fix the failing tests," Claude might:

1. Run the test suite to see what's failing
2. Read the error output
3. Search for the relevant source files
4. Read those files to understand the code
5. Edit the files to fix the issue
6. Run the tests again to verify

Each tool use gives Claude new information that informs the next step. This is the agentic loop in action.

**Extending the base capabilities:** The built-in tools are the foundation. You can extend what Claude knows with [skills](/en/skills), connect to external services with [MCP](/en/mcp), automate workflows with [hooks](/en/hooks), and offload tasks to [subagents](/en/sub-agents). These extensions form a layer on top of the core agentic loop. See [Extend Claude Code](/en/features-overview) for guidance on choosing the right extension for your needs.

## What Claude can access

This guide focuses on the terminal. Claude Code also runs in [VS Code, JetBrains IDEs, and other environments](/en/ide-integrations).

When you run `claude` in a directory, Claude Code gains access to:

* **Your project.** Files in your directory and subdirectories, plus files elsewhere with your permission.
* **Your terminal.** Any command you could run: build tools, git, package managers, system utilities, scripts. If you can do it from the command line, Claude can too.
* **Your git state.** Current branch, uncommitted changes, and recent commit history.
* **Your [CLAUDE.md](/en/memory).** A markdown file where you store project-specific instructions, conventions, and context that Claude should know every session.
* **Extensions you configure.** [MCP servers](/en/mcp) for external services, [skills](/en/skills) for workflows, [subagents](/en/sub-agents) for delegated work, and [Claude in Chrome](/en/chrome) for browser interaction.

Because Claude sees your whole project, it can work across it. When you ask Claude to "fix the authentication bug," it searches for relevant files, reads multiple files to understand context, makes coordinated edits across them, runs tests to verify the fix, and commits the changes if you ask. This is different from inline code assistants that only see the current file.

## Work with sessions

Claude Code saves your conversation locally as you work. Each message, tool use, and result is stored, which enables [rewinding](#undo-changes-with-checkpoints), [resuming, and forking](#resume-or-fork-sessions) sessions. Before Claude makes code changes, it also snapshots the affected files so you can revert if needed.

**Sessions are ephemeral.** Unlike claude.ai, Claude Code has no persistent memory between sessions. Each new session starts fresh. Claude doesn't "learn" your preferences over time or remember what you worked on last week. If you want Claude to know something across sessions, put it in your [CLAUDE.md](/en/memory).

### Work across branches

Each Claude Code conversation is a session tied to your current directory. When you resume, you only see sessions from that directory.

Claude sees your current branch's files. When you switch branches, Claude sees the new branch's files, but your conversation history stays the same. Claude remembers what you discussed even after switching.

Since sessions are tied to directories, you can run parallel Claude sessions by using [git worktrees](/en/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees), which create separate directories for individual branches.

### Resume or fork sessions

When you resume a session with `claude --continue` or `claude --resume`, you pick up where you left off using the same session ID. New messages append to the existing conversation. Your full conversation history is restored, but session-scoped permissions are not. You'll need to re-approve those.

<img src="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=f671b603cc856119c95475b9084ebfef" alt="Session continuity: resume continues the same session, fork creates a new branch with a new ID." data-og-width="560" width="560" data-og-height="280" height="280" data-path="images/session-continuity.svg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=280&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=bddf1f33d419a27d7427acdf06058804 280w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=560&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=417478eb9b86003b8eebaac058a8618a 560w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=840&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=1d89d26e2c0487f067d187c3fa5f7170 840w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=1100&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=8ea739a1f7860e4edbbcf74d444e37b2 1100w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=1650&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=9cb5095d6a8920f04c3b78d31a69c809 1650w, https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?w=2500&fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=d67e1744e4878813d20c6c3f39d9459d 2500w" />

To branch off and try a different approach without affecting the original session, use the `--fork-session` flag:

```bash  theme={null}
claude --continue --fork-session
```

This creates a new session ID while preserving the conversation history up to that point. The original session remains unchanged. Like resume, forked sessions don't inherit session-scoped permissions.

**Same session in multiple terminals**: If you resume the same session in multiple terminals, both terminals write to the same session file. Messages from both get interleaved, like two people writing in the same notebook. Nothing corrupts, but the conversation becomes jumbled. Each terminal only sees its own messages during the session, but if you resume that session later, you'll see everything interleaved. For parallel work from the same starting point, use `--fork-session` to give each terminal its own clean session.

### The context window

Claude's context window holds your conversation history, file contents, command outputs, [CLAUDE.md](/en/memory), loaded skills, and system instructions. As you work, context fills up. Claude compacts automatically, but instructions from early in the conversation can get lost. Put persistent rules in CLAUDE.md, and run `/context` to see what's using space.

#### When context fills up

Claude Code manages context automatically as you approach the limit. It clears older tool outputs first, then summarizes the conversation if needed. Your requests and key code snippets are preserved; detailed instructions from early in the conversation may be lost. Put persistent rules in CLAUDE.md rather than relying on conversation history.

To control what's preserved during compaction, add a "Compact Instructions" section to CLAUDE.md or run `/compact` with a focus (like `/compact focus on the API changes`).

Run `/context` to see what's using space. MCP servers add tool definitions to every request, so a few servers can consume significant context before you start working. Run `/mcp` to check per-server costs.

#### Manage context with skills and subagents

Beyond compaction, you can use other features to control what loads into context.

[Skills](/en/skills) load on demand. Claude sees skill descriptions at session start, but the full content only loads when a skill is used. For skills you invoke manually, set `disable-model-invocation: true` to keep descriptions out of context until you need them.

[Subagents](/en/sub-agents) get their own fresh context, completely separate from your main conversation. Their work doesn't bloat your context. When done, they return a summary. This isolation is why subagents help with long sessions.

See [context costs](/en/features-overview#understand-context-costs) for what each feature costs, and [reduce token usage](/en/costs#reduce-token-usage) for tips on managing context.

## Stay safe with checkpoints and permissions

Claude has two safety mechanisms: checkpoints let you undo file changes, and permissions control what Claude can do without asking.

### Undo changes with checkpoints

**Every file edit is reversible.** Before Claude edits any file, it snapshots the current contents. If something goes wrong, press `Esc` twice to rewind to a previous state, or ask Claude to undo.

Checkpoints are local to your session, separate from git. They only cover file changes. Actions that affect remote systems (databases, APIs, deployments) can't be checkpointed, which is why Claude asks before running commands with external side effects.

### Control what Claude can do

Press `Shift+Tab` to cycle through permission modes:

* **Default**: Claude asks before file edits and shell commands
* **Auto-accept edits**: Claude edits files without asking, still asks for commands
* **Plan mode**: Claude uses read-only tools only, creating a plan you can approve before execution
* **Delegate mode**: Claude coordinates work through [agent teammates](/en/agent-teams) only, with no direct implementation. Only available when an agent team is active.

You can also allow specific commands in `.claude/settings.json` so Claude doesn't ask each time. This is useful for trusted commands like `npm test` or `git status`. Settings can be scoped from organization-wide policies down to personal preferences. See [Permissions](/en/permissions) for details.

***

## Work effectively with Claude Code

These tips help you get better results from Claude Code.

### Ask Claude Code for help

Claude Code can teach you how to use it. Ask questions like "how do I set up hooks?" or "what's the best way to structure my CLAUDE.md?" and Claude will explain.

Built-in commands also guide you through setup:

* `/init` walks you through creating a CLAUDE.md for your project
* `/agents` helps you configure custom subagents
* `/doctor` diagnoses common issues with your installation

### It's a conversation

Claude Code is conversational. You don't need perfect prompts. Start with what you want, then refine:

```
> Fix the login bug

[Claude investigates, tries something]

> That's not quite right. The issue is in the session handling.

[Claude adjusts approach]
```

When the first attempt isn't right, you don't start over. You iterate.

#### Interrupt and steer

You can interrupt Claude at any point. If it's going down the wrong path, just type your correction and press Enter. Claude will stop what it's doing and adjust its approach based on your input. You don't have to wait for it to finish or start over.

### Be specific upfront

The more precise your initial prompt, the fewer corrections you'll need. Reference specific files, mention constraints, and point to example patterns.

```
> The checkout flow is broken for users with expired cards.
> Check src/payments/ for the issue, especially token refresh.
> Write a failing test first, then fix it.
```

Vague prompts like "fix the login bug" work, but you'll spend more time steering. Specific prompts like the above often succeed on the first attempt.

### Give Claude something to verify against

Claude performs better when it can check its own work. Include test cases, paste screenshots of expected UI, or define the output you want.

```
> Implement validateEmail. Test cases: 'user@example.com' → true,
> 'invalid' → false, 'user@.com' → false. Run the tests after.
```

For visual work, paste a screenshot of the design and ask Claude to compare its implementation against it.

### Explore before implementing

For complex problems, separate research from coding. Use plan mode (`Shift+Tab` twice) to analyze the codebase first:

```
> Read src/auth/ and understand how we handle sessions.
> Then create a plan for adding OAuth support.
```

Review the plan, refine it through conversation, then let Claude implement. This two-phase approach produces better results than jumping straight to code.

### Delegate, don't dictate

Think of delegating to a capable colleague. Give context and direction, then trust Claude to figure out the details:

```
> The checkout flow is broken for users with expired cards.
> The relevant code is in src/payments/. Can you investigate and fix it?
```

You don't need to specify which files to read or what commands to run. Claude figures that out.

## What's next

<CardGroup cols={2}>
  <Card title="Extend with features" icon="puzzle-piece" href="/en/features-overview">
    Add Skills, MCP connections, and custom commands
  </Card>

  <Card title="Common workflows" icon="graduation-cap" href="/en/common-workflows">
    Step-by-step guides for typical tasks
  </Card>
</CardGroup>

---

# 中文翻译

> ## 文档索引
> 获取完整的文档索引：https://code.claude.com/docs/llms.txt
> 使用该文件查看所有可用页面后再进一步探索。

# Claude Code 的工作原理

> 了解代理循环、内置工具，以及 Claude Code 如何与你的项目交互。

Claude Code 是一个运行在终端中的代理助手。虽然它在编码方面表现出色，但它可以帮助你完成任何可以通过命令行完成的事情：编写文档、运行构建、搜索文件、研究主题等等。

本指南涵盖核心架构、内置功能和[高效使用技巧](#高效使用-claude-code)。有关分步操作指南，请参阅[常见工作流](/en/common-workflows)。有关技能、MCP 和钩子等扩展功能，请参阅[扩展 Claude Code](/en/features-overview)。

## 代理循环

当你给 Claude 一个任务时，它通过三个阶段来完成：**收集上下文**、**采取行动**和**验证结果**。这三个阶段相互交融。Claude 全程使用工具——无论是搜索文件以理解代码、编辑以做出更改，还是运行测试以检查结果。

<img src="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/agentic-loop.svg?fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=e30acfc80d6ff01ec877dd19c7af58b2" alt="代理循环：你的提示引导 Claude 收集上下文、采取行动、验证结果，并重复直到任务完成。你可以在任何时候打断。" width="720" height="280" />

循环会根据你的需求进行调整。关于代码库的问题可能只需要收集上下文。修复 Bug 会反复经历所有三个阶段。重构可能涉及大量验证。Claude 根据从上一步学到的内容决定每一步需要什么，将数十个操作串联在一起并在过程中不断修正方向。

你也是这个循环的一部分。你可以在任何时候打断 Claude，引导它走向不同的方向、提供额外的上下文，或者要求它尝试不同的方法。Claude 自主工作的同时始终响应你的输入。

代理循环由两个组件驱动：负责推理的[模型](#模型)和负责行动的[工具](#工具)。Claude Code 作为 Claude 的**代理框架**：提供工具、上下文管理和执行环境，将语言模型转变为一个强大的编码代理。

### 模型

Claude Code 使用 Claude 模型来理解你的代码并推理任务。Claude 可以阅读任何语言的代码，理解组件之间的关联，并找出需要更改什么来完成你的目标。对于复杂任务，它会将工作分解为多个步骤，逐步执行并根据学到的内容进行调整。

有[多个模型](/en/model-config)可用，各有不同的权衡。Sonnet 可以很好地处理大多数编码任务。Opus 在复杂的架构决策方面提供更强的推理能力。可以在会话中使用 `/model` 切换，或使用 `claude --model <名称>` 启动。

当本指南说"Claude 选择"或"Claude 决定"时，指的是模型在进行推理。

### 工具

工具是让 Claude Code 具备代理能力的关键。没有工具，Claude 只能用文本回复。有了工具，Claude 可以采取行动：读取代码、编辑文件、运行命令、搜索网络、与外部服务交互。每次工具使用都会返回信息，反馈到循环中，为 Claude 的下一个决策提供依据。

内置工具大致分为四类，每类代表不同层面的代理能力。

| 类别 | Claude 能做什么 |
| --- | --- |
| **文件操作** | 读取文件、编辑代码、创建新文件、重命名和重组 |
| **搜索** | 按模式查找文件、用正则搜索内容、探索代码库 |
| **执行** | 运行 shell 命令、启动服务器、运行测试、使用 git |
| **网络** | 搜索网络、获取文档、查找错误信息 |
| **代码智能** | 编辑后查看类型错误和警告、跳转到定义、查找引用（需要[代码智能插件](/en/discover-plugins#code-intelligence)） |

这些是主要功能。Claude 还有用于生成子代理、向你提问和其他编排任务的工具。完整列表参见[Claude 可用的工具](/en/settings#tools-available-to-claude)。

Claude 根据你的提示和沿途学到的内容选择使用哪些工具。当你说"修复失败的测试"时，Claude 可能会：

1. 运行测试套件查看哪些失败了
2. 读取错误输出
3. 搜索相关的源文件
4. 读取这些文件以理解代码
5. 编辑文件来修复问题
6. 再次运行测试进行验证

每次工具使用都会给 Claude 新的信息，为下一步提供依据。这就是代理循环的实际运作方式。

**扩展基本能力：** 内置工具是基础。你可以通过[技能](/en/skills)扩展 Claude 的知识，通过 [MCP](/en/mcp) 连接到外部服务，通过[钩子](/en/hooks)自动化工作流，以及通过[子代理](/en/sub-agents)委派任务。这些扩展在核心代理循环之上形成一层。详情参见[扩展 Claude Code](/en/features-overview)。

## Claude 能访问什么

本指南聚焦于终端。Claude Code 也可以在 [VS Code、JetBrains IDE 和其他环境](/en/ide-integrations)中运行。

当你在某个目录下运行 `claude` 时，Claude Code 可以访问：

* **你的项目。** 当前目录及子目录中的文件，以及经你许可的其他位置的文件。
* **你的终端。** 任何你能运行的命令：构建工具、git、包管理器、系统工具、脚本。你能在命令行做的，Claude 也能做。
* **你的 git 状态。** 当前分支、未提交的更改和最近的提交历史。
* **你的 [CLAUDE.md](/en/memory)。** 一个 Markdown 文件，你可以在其中存储项目特定的指令、约定和 Claude 每次会话都应该知道的上下文。
* **你配置的扩展。** 用于外部服务的 [MCP 服务器](/en/mcp)、用于工作流的[技能](/en/skills)、用于委派工作的[子代理](/en/sub-agents)，以及用于浏览器交互的 [Claude in Chrome](/en/chrome)。

由于 Claude 能看到整个项目，它可以跨项目工作。当你让 Claude "修复身份验证的 Bug"时，它会搜索相关文件、读取多个文件以理解上下文、跨文件进行协调编辑、运行测试验证修复，并在你要求时提交更改。这与仅能看到当前文件的行内代码助手不同。

## 会话管理

Claude Code 在你工作时将对话保存在本地。每条消息、工具调用和结果都会被存储，这使得[回滚](#通过检查点撤销更改)、[恢复和分叉](#恢复或分叉会话)会话成为可能。在 Claude 进行代码更改之前，它还会对受影响的文件进行快照，以便你在需要时恢复。

**会话是临时性的。** 与 claude.ai 不同，Claude Code 在会话之间没有持久记忆。每个新会话从零开始。Claude 不会随时间"学习"你的偏好，也不会记住你上周做了什么。如果你希望 Claude 跨会话记住某些信息，请将其放入 [CLAUDE.md](/en/memory)。

### 跨分支工作

每个 Claude Code 对话都是绑定到当前目录的会话。当你恢复时，只能看到该目录下的会话。

Claude 看到的是当前分支的文件。当你切换分支时，Claude 看到新分支的文件，但对话历史保持不变。即使切换分支后，Claude 仍然记得你们讨论过的内容。

由于会话绑定到目录，你可以使用 [git worktree](/en/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees) 来运行并行的 Claude 会话，它会为各个分支创建单独的目录。

### 恢复或分叉会话

当你使用 `claude --continue` 或 `claude --resume` 恢复会话时，你使用相同的会话 ID 从上次离开的地方继续。新消息追加到现有对话中。完整的对话历史会被恢复，但会话作用域的权限不会。你需要重新审批这些权限。

<img src="https://mintcdn.com/claude-code/ELkJZG54dIaeldDC/images/session-continuity.svg?fit=max&auto=format&n=ELkJZG54dIaeldDC&q=85&s=f671b603cc856119c95475b9084ebfef" alt="会话连续性：resume 继续同一会话，fork 用新 ID 创建一个新分支。" width="560" height="280" />

要分支出去尝试不同的方法而不影响原始会话，使用 `--fork-session` 标志：

```bash
claude --continue --fork-session
```

这会创建一个新的会话 ID，同时保留到该点为止的对话历史。原始会话不受影响。与恢复一样，分叉的会话不继承会话作用域的权限。

**在多个终端中使用同一会话**：如果你在多个终端中恢复同一个会话，两个终端都会写入同一个会话文件。两边的消息会交错，就像两个人在同一个笔记本上写字。不会损坏任何东西，但对话会变得混乱。每个终端在会话期间只能看到自己的消息，但如果你稍后恢复该会话，会看到所有消息交错在一起。对于从同一起点进行并行工作，使用 `--fork-session` 让每个终端有自己独立的会话。

### 上下文窗口

Claude 的上下文窗口包含你的对话历史、文件内容、命令输出、[CLAUDE.md](/en/memory)、已加载的技能和系统指令。随着你的工作，上下文会逐渐填满。Claude 会自动压缩，但对话早期的指令可能会丢失。将持久性规则放入 CLAUDE.md，并运行 `/context` 查看空间使用情况。

#### 上下文满时

当你接近上限时，Claude Code 会自动管理上下文。它首先清除较旧的工具输出，然后在需要时总结对话。你的请求和关键代码片段会被保留；对话早期的详细指令可能会丢失。将持久性规则放入 CLAUDE.md，而不是依赖对话历史。

要控制压缩时保留的内容，在 CLAUDE.md 中添加"Compact Instructions"部分，或使用带焦点的 `/compact` 运行（如 `/compact focus on the API changes`）。

运行 `/context` 查看空间使用情况。MCP 服务器会在每个请求中添加工具定义，因此几个服务器就可能在你开始工作之前消耗大量上下文。运行 `/mcp` 查看每个服务器的开销。

#### 使用技能和子代理管理上下文

除了压缩之外，你还可以使用其他功能来控制加载到上下文中的内容。

[技能](/en/skills)按需加载。Claude 在会话开始时看到技能描述，但完整内容仅在使用技能时加载。对于你手动调用的技能，设置 `disable-model-invocation: true` 可以在需要之前将描述排除在上下文之外。

[子代理](/en/sub-agents)拥有自己全新的上下文，与主对话完全分离。它们的工作不会膨胀你的上下文。完成后，它们返回摘要。这种隔离性正是子代理在长时间会话中有帮助的原因。

参见[上下文开销](/en/features-overview#understand-context-costs)了解每个功能的开销，以及[减少 Token 使用量](/en/costs#reduce-token-usage)了解管理上下文的技巧。

## 通过检查点和权限保持安全

Claude 有两个安全机制：检查点让你撤销文件更改，权限控制 Claude 无需询问即可执行的操作。

### 通过检查点撤销更改

**每次文件编辑都是可逆的。** 在 Claude 编辑任何文件之前，它会快照当前内容。如果出错了，按两次 `Esc` 回退到之前的状态，或者让 Claude 撤销。

检查点是会话本地的，独立于 git。它们只覆盖文件更改。影响远程系统（数据库、API、部署）的操作无法通过检查点恢复，这就是为什么 Claude 在运行具有外部副作用的命令之前会征求你的同意。

### 控制 Claude 的操作权限

按 `Shift+Tab` 在权限模式之间切换：

* **默认模式**：Claude 在编辑文件和执行 shell 命令前会询问
* **自动接受编辑**：Claude 无需询问即可编辑文件，但仍会询问命令执行
* **计划模式**：Claude 仅使用只读工具，创建一个计划供你在执行前审核
* **委派模式**：Claude 仅通过[代理队友](/en/agent-teams)协调工作，不直接实现。仅在代理团队激活时可用。

你也可以在 `.claude/settings.json` 中允许特定命令，这样 Claude 就不必每次都询问。这对于 `npm test` 或 `git status` 等受信任的命令很有用。设置可以从组织级策略到个人偏好进行分层。详情参见[权限](/en/permissions)。

---

## 高效使用 Claude Code

以下技巧帮助你从 Claude Code 获得更好的结果。

### 向 Claude Code 寻求帮助

Claude Code 可以教你如何使用它。提问如"如何设置钩子？"或"构建 CLAUDE.md 的最佳方式是什么？"，Claude 会进行解释。

内置命令也会指导你完成设置：

* `/init` 引导你为项目创建 CLAUDE.md
* `/agents` 帮助你配置自定义子代理
* `/doctor` 诊断安装中的常见问题

### 这是一种对话

Claude Code 是对话式的。你不需要完美的提示词。从你想要的开始，然后逐步细化：

```
> 修复登录 Bug

[Claude 调查、尝试某种方案]

> 这不太对。问题出在会话处理上。

[Claude 调整方法]
```

当第一次尝试不正确时，你不需要从头开始。你可以迭代。

#### 打断和引导

你可以在任何时候打断 Claude。如果它走错了方向，直接输入你的纠正然后按回车。Claude 会停下当前操作，根据你的输入调整方法。你不需要等它完成或从头来过。

### 预先提供具体信息

初始提示越精确，你需要的纠正就越少。引用具体文件、提及约束条件，并指向示例模式。

```
> 结账流程对使用过期卡的用户出错了。
> 检查 src/payments/ 中的问题，特别是 token 刷新部分。
> 先写一个失败的测试，然后修复它。
```

模糊的提示如"修复登录 Bug"可以工作，但你会花更多时间引导。像上面这样具体的提示通常一次就能成功。

### 给 Claude 可验证的依据

当 Claude 可以检查自己的工作时表现更好。包含测试用例、粘贴预期 UI 的截图，或定义你想要的输出。

```
> 实现 validateEmail。测试用例：'user@example.com' → true，
> 'invalid' → false，'user@.com' → false。完成后运行测试。
```

对于视觉相关的工作，粘贴设计截图并要求 Claude 将其实现与截图进行对比。

### 先探索再实现

对于复杂问题，将调研与编码分开。使用计划模式（按两次 `Shift+Tab`）先分析代码库：

```
> 读取 src/auth/ 并理解我们如何处理会话。
> 然后制定添加 OAuth 支持的计划。
```

审查计划，通过对话细化它，然后让 Claude 实现。这种两阶段方法比直接跳到编码产生更好的结果。

### 委派，而非指令

把它想象成向一个能干的同事委派工作。提供上下文和方向，然后信任 Claude 去搞清细节：

```
> 结账流程对使用过期卡的用户出错了。
> 相关代码在 src/payments/。你能调查并修复吗？
```

你不需要指定读取哪些文件或运行什么命令。Claude 会自己搞清楚。

## 下一步

- [**使用功能扩展**](/en/features-overview) — 添加技能、MCP 连接和自定义命令
- [**常见工作流**](/en/common-workflows) — 典型任务的分步指南
