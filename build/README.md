# WenCe AI 打包部署指南

## 架构说明

打包后的应用结构：
```
wence_ai/
├── wence_ai.exe (或 wence_ai)    # 可执行文件
├── data/                          # 数据目录（运行时生成）
│   └── wence_ai.db               # SQLite 数据库
└── static/                        # 前端静态文件
    ├── manifest.xml              # WPS 插件清单
    ├── index.html
    └── assets/
```

用户运行可执行文件后：
1. 启动本地 HTTP 服务器（默认端口 8000）
2. 提供后端 API 服务
3. 托管前端静态文件和 WPS 插件
4. WPS 通过 URL 加载在线插件

## 快速开始

### 1. 安装打包依赖

```bash
cd wence_backend
pip install pyinstaller
```

### 2. 构建前端

```bash
cd wence_frontend/wence_word_plugin
pnpm install
pnpm build
```

### 3. 打包应用

**Linux:**
```bash
cd build
chmod +x build.sh
./build.sh
```

**Windows:**
```powershell
cd build
.\build.ps1
```

或者使用 Python 脚本（跨平台）：
```bash
python build.py
```

### 4. 运行打包后的应用

**Linux:**
```bash
./dist/wence_ai
```

**Windows:**
```powershell
.\dist\wence_ai.exe
```

## WPS 加载在线插件

1. 运行可执行文件，启动服务
2. 打开 WPS 文字
3. 开发者工具 → 加载网络加载项
4. 输入 URL: `http://localhost:8000/plugin/manifest.xml`
5. 点击确定，插件将自动加载

## 配置说明

可通过环境变量或 `.env` 文件配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| PORT | 服务端口 | 8000 |
| HOST | 监听地址 | 0.0.0.0 |
| DEBUG | 调试模式 | false |
| OPENAI_API_KEY | OpenAI API 密钥 | - |
| OPENAI_BASE_URL | OpenAI 兼容接口地址 | - |

## 发布给用户

打包完成后，`dist/` 目录下的内容即可发布给用户：

```
dist/
├── wence_ai (Linux) 或 wence_ai.exe (Windows)
└── static/
```

用户只需：
1. 下载并解压
2. 双击运行可执行文件
3. 在 WPS 中加载插件 URL

## 注意事项

1. **首次运行**：会在程序目录下创建 `data/wence_ai.db` 数据库文件
2. **端口占用**：确保 8000 端口未被占用，或修改配置
3. **防火墙**：Windows 首次运行可能需要允许网络访问
4. **HTTPS**：如需 HTTPS，可使用 nginx 反向代理
