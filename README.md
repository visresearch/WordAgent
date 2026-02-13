# wence_ai

> 中南大学计算机学院毕业设计——基于多智能体的AI辅助写作系统“文策AI”

# 删掉tag重新提交

```bash
# 删除本地和远程的 tag
git tag -d v0.2.0
git push github --delete v0.2.0

# 修改完代码后重新打 tag 并推送
git add . && git commit -m "fix:修复QT启动不了wpscloudsrv的问题"
git tag v0.2.0
git push github && git push github --tags
```

在58890端口会运行一个wpscloudsrv的服务，要启动，不然看不到wps加载项列表

```bash
sudo pkill -f wpsclouds
```

# 参考文献

(学院要求参考文献引用至少30篇以上，包括中英文，以及近5年论文为主，必须有2025年论文)

1. https://github.com/HuggingAGI/AwesomeAgentPapers?tab=readme-ov-file 2025年AI Agent论文综述资料
