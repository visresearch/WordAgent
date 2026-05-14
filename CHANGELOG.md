
# Changelog

## Unrelease

### Added
- 添加paraIndex和paraID到json schema
- 添加版本检查功能

### Fixed
- 修复深度思考，重复进入深度思考前端不能更新的问题

### Changed
- 修改深度思考内容展开条件

## [v0.4.0]

### Added
- WPS Word支持多文档编辑
- 添加file工具

### Changed
- 解耦memory和context
- 单多智能体模式复用tools代码
- 重构长期记忆memory.md
- 增强短期记忆
- 修改wence_data结构
- 优化提示词结构

### Fixed
- 修复后端有时候会done两次，记录两次相同的AI回答的问题
- 修复上一个提交，引入的删除文档工具调用前端处理的bug以及批注缺失的bug
- 将generate_document和delete_document加入pending，在pending中计算好index，放到done之后执行修改文档

## [v0.3.6]

### Added
- 多智能体模式与单智能体模式评估

### Fixed
- 前端search_document工具调用bug
- 防御MCP工具调用报错问题
- Mutli-agent运行问题

### Changed
- 提取长期记忆改为异步，不阻塞done
- 重构多智能体模式plan
- 修改官网文档

## [v0.3.5]

### Added
- Microsoft Word 自签证流程

### Changed
- 官网/文档内容更新

### Fixed
- Microsoft Word 插件深度思考bug
- 前端插件历史会话bug

---

## [v0.3.4] - 2026-04-20

### Changed
- 官网/文档内容更新

### Fixed
- SKIlls 工具问题
- 深度思考bug

---
