# wence_ai

> 中南大学计算机学院毕业设计——基于多智能体的AI辅助写作系统“文策AI”

# 删掉tag重新提交

```bash
# 删除本地和远程的 tag
git tag -d v0.3.0
git push github --delete v0.3.0

# 修改完代码后重新打 tag 并推送
git add . && git commit -m "chore：修改CLCI"
git tag v0.3.0
git push github && git push github --tags
```

在58890端口会运行一个wpscloudsrv的服务，要启动，不然看不到wps加载项列表

```bash
sudo pkill -f wpsclouds
```

# 参考文献

(学院要求参考文献引用至少30篇以上，包括中英文，以及近5年论文为主，必须有2025年论文)

1. https://github.com/HuggingAGI/AwesomeAgentPapers?tab=readme-ov-file 2025年AI Agent论文综述资料
2. https://vscode.js.cn/docs/copilot/agents/subagents

# 调研报告参考文献

1. Agent AI: Surveying the Horizons of Multimodal Interaction
2. OpenAI. (2023). GPT-4 Technical Report.
3. Adapting LLM Agents Through Communication
4. CoMM: Collaborative Multi-Agent, Multi-Reasoning-Path Prompting for Complex Problem Solving
5. Describe, Explain, Plan and Select: Interactive Planning with LLMs Enables Open-World Multi-Task Agents
6. SwiftSage: A Generative Agent with Fast and Slow Thinking for Complex Interactive Tasks
7. A survey on large language model based autonomous agents
8. Large Language Model based Multi-Agents: A Survey of Progress and Challenges
9. Personal LLM Agents: Insights and Survey about the Capability, Efficiency and Security
10. Multi-Agent Collaboration Mechanisms: A Survey of LLMs
11. Understanding the planning of LLM agents: A survey
12. The Rise and Potential of Large Language Model Based Agents: A Survey
13. LLM-Based Human-Agent Collaboration and Interaction Systems: A Survey
14. GitHub: https://github.com/langchain-ai/langgraph
15. 基于大语言模型的AI Agents https://www.breezedeus.com/article/ai-agent-part3
16. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation

# 调研报告参考文献

[1] Tran K T, Dao D, Nguyen M D, Pham Q V, O’Sullivan B, Nguyen H D.
Multi-Agent Collaboration Mechanisms: A Survey of LLMs[EB/OL].
arXiv:2501.06322, 2025.

