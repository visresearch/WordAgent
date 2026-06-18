# Changelog

## [v0.5.1]

### Fixed
- 修复多智能体模式生成文档的json schema不同步的问题
- 修复Microsoft word加载项paraID的问题，放弃使用paraIndex，使用隐藏书签实现paraID
- 修复了旧的提示词会干扰agent调用generate_document工具生成文档的问题
- 修复了Microsoft word加载项重复隐藏书签的bug
- 修复了generate_document工具的提示词
- 修复前端about界面版本号不匹配的问题

### Added
- 添加系统logger，记录系统运行日志，添加终端level颜色警告
- 添加Microsoft word加载项上下文圆环

### Deleted
- 删除Microsoft word加载项paraIndex索引漂移补偿的逻辑，简化代码

### Changed
- 更新py依赖
- 修改Microsoft word加载项批注高亮
- 加大短期记忆上下文参数
- 修改generate_document工具，insertParaID参数为必填参数，约定0代表空文章开头

## [v0.5.0]

### Added
- 添加新版打包脚本，生成installer.exe和deb包
- 添加issue模板和pull request模板

### Fixed
- 修复microsoft word加载项的paraID的问题，用paraIndex充当paraID，使用索引漂移补偿的方式
- 修复microsoft word选区preview等小问题

### Changed
- 修改文档和官网内容

## [v0.4.6]

### Fixed
- json schema样式已经变更，同步表格cell的情况
- 修复wps空文章，导致插入第一个段落出现段落对象无法显示的问题

### Added
- 添加前端获取当前版本号的接口，在about中显示版本号

### Changed
- 修改README和文档内容

## [v0.4.5]

### Added
- read_document工具添加mode参数，适配轻量读取模式

### Fixed
- 优化前端wps插件search_document工具调用，添加原生的轻量搜索
- 修复后端传输的原始LLM信息
- 优化搜索工具解析全文导致WPS UI暂时卡死的问题
- 修复短期记忆的bug

### Changed
- 修改README和文档内容


## [v0.4.2]

### Fixed
- 修复非多模态大模型，输入图片接口报错，应该降级为OCR读取图片
- 修复chatinput输入框输入文字过长，显示问题
- 修复前端紧凑列表会显示成一排的bug

### Changed
- 修改文档和官网内容

## [v0.4.2]

### Fixed
- Microsoft word加载项利用隐藏书签的name，随机一个9位uid，作为paraID
- 删除段落暂时使用用户手动删除方案

### Changed
- 修改Microsoft word加载项深度思考内容展开条件
- 修改文档和官网内容

### Added
- 添加运行python工具

## [v0.4.1]

### Added
- 添加paraIndex和paraID到json schema
- 添加版本检查功能

### Fixed
- 修复深度思考，重复进入深度思考前端不能更新的问题

### Changed
- 修改深度思考内容展开条件
- 修改文档

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
