# Changelog

## Unreleased

### Added
- 添加CONTRIBUTING.md和SECURITY.md
- 添加调整过后的内置skill
- 前端添加中英文切换
- read_document工具full模式返回值添加page信息
- 添加insert_break工具，插入分页符
- 添加create_document工具，创建新文档
- 添加generate_document和insert_break工具的前端返回值，方遍agent直接理解

### Changed
- 更改temputure默认值和取值范围
- 更新所有py依赖
- 更新所有node依赖部分
- 更新官网web文档
- 将WPS红蓝批注改为原生的修订模式
- 将Microsoft Word红蓝高亮修改为原生的修订模式
- 修改generate_document工具schema中table字段，把table放到了paragraphs的中间，用来表示表格是段落的一部分，表示表格在段落中的位置(read_document工具的json schema未修改)
- 规定空段落也必须要有pStyle

### Fixed
- 修复上下文溢出重试的bug
- 修复历史遗留工具名拼错的bug
- 修复未定义的Microsoft word旧内容控件
- 优化上下文压缩的系统提示词
- 取消加载SKILL上下文最大限制截断
- 修复空白段落的bug
- 修复read_document工具没有读取到文档图片样式信息的问题
- 修复insertParaID参数为0时的规则，不再只允许空文章
- 修复换行换页导致的锚点定位错误的bug
- 同步修复删除工具的提示词，取消pending删除段落机制，删除段落在修订模式下立即生效

## [v0.5.2]

### Added
- 添加系统托盘功能
- 添加macOS打包

### Fixed
- 修复deb包安装后，软件没有权限修改/opt目录下文件bug，配置文件目录修改到~/.wence_ai下

### Changed
- 修改OCR识别图片为灰度图片
- 更新所有py依赖
- 修改图标
- 修改README

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
