# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件
用于将 WenCe AI 后端打包成单个可执行文件
"""

import sys
import os
import subprocess
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 项目根目录（从 deploy 目录向上一级）
root_dir = os.path.abspath('..')

# 发布版本只从环境变量或 Git tag 获取，并通过运行时 .env 注入给应用。
_repo_root = os.path.abspath(os.path.join(os.path.dirname(SPEC), '..', '..'))


def _release_version():
    version = (os.environ.get('APP_VERSION') or '').strip()
    if version:
        return version

    ref_type = (os.environ.get('GITHUB_REF_TYPE') or '').strip().lower()
    ref_name = (os.environ.get('GITHUB_REF_NAME') or '').strip()
    if ref_type == 'tag' and ref_name:
        return ref_name

    try:
        return subprocess.check_output(
            ['git', 'describe', '--tags'],
            cwd=_repo_root,
            text=True,
        ).strip()
    except Exception:
        return ''


version_value = _release_version()
generated_env_path = ''
if version_value:
    os.environ.setdefault('APP_VERSION', version_value)
    generated_env_dir = os.path.abspath(os.path.join(os.path.dirname(SPEC), 'build', 'runtime_env'))
    generated_env_path = os.path.join(generated_env_dir, '.env')
    os.makedirs(generated_env_dir, exist_ok=True)
    with open(generated_env_path, 'w', encoding='utf-8') as f:
        f.write(f'APP_VERSION={version_value}\n')

# 收集所有需要的数据文件
datas = [
    ('../README.md', '.'),
    # 打包 app 模块（FastAPI 应用）
    ('../app', 'app'),
    # 打包前端构建目录（pnpm build 输出到 dist）
    ('../../frontend/wps_word_plugin/dist', 'frontend'),
    ('../../frontend/microsoft_word_plugin/dist', 'msoffice'),
]
if generated_env_path:
    datas.append((generated_env_path, '.'))

# 可选数据文件（不一定存在于 CI 环境）
optional_dirs = [
    ('../gui/resources', 'gui/resources'),
]
for src, dst in optional_dirs:
    src_path = os.path.abspath(os.path.join(os.path.dirname(SPEC), src))
    if os.path.exists(src_path):
        datas.append((src, dst))

# 收集隐藏导入（LangChain 和依赖库的所有模块）
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',

    # FastAPI
    'fastapi',
    'fastapi.responses',
    'starlette',
    'starlette.middleware',
    'starlette.middleware.cors',
    
    # Pydantic
    'pydantic',
    'pydantic_core',
    'pydantic_settings',
    
    # SQLAlchemy
    'sqlalchemy',
    'sqlalchemy.ext.asyncio',
    'aiosqlite',
    
    # OpenAI & AI clients
    'openai',
    'httpx',
    'anyio',
    
    # LangChain
    'langchain',
    'langchain_core',
    'langchain_openai',
    'langchain_anthropic',
    'langchain_community',
    'langgraph',
    
    # Other dependencies
    'dotenv',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'json',
    'asyncio',
    
    # PySide6 / GUI
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    
    # App 模块
    'app',
    'app.main',
    'app.core',
    'app.core.config',
    'app.core.db',
    'app.api',
    'app.api.routes',
    'app.api.routes.chat',
    'app.api.routes.history',
    'app.api.routes.models',
    'app.api.routes.settings',
    'app.services',
    'app.services.agent',
    'app.services.chat_history',
    'app.services.llm_client',
    'app.models',
    'app.models.chat',
    'app.models.db_models',
    'app.models.doc',
]

# 自动收集 langchain 的所有子模块
hiddenimports += collect_submodules('langchain')
hiddenimports += collect_submodules('langchain_core')
hiddenimports += collect_submodules('langchain_openai')
hiddenimports += collect_submodules('langgraph')

# 分析入口文件
a = Analysis(
    ['../main.py'],  # 主文件在上层目录
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型库（AI/ML 库，我们不需要）
        'matplotlib',
        'seaborn',
        'tkinter',
        'jupyter',
        'notebook',

        # 排除深度学习框架（不需要）
        'tensorflow',
        'torch',
        'torchvision',
        'keras',
        'jax',

        # 排除其他不需要的库
        'evaluation',
        'babel',
        'tqdm',
        'sphinx',
        'docutils',
        'openpyxl',
        'pygraphviz',
        'fsspec',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 图标路径
icon_path = os.path.join(os.path.dirname(SPEC), 'robot.ico')

# 目录模式（更快启动）
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='wence_ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='wence_ai',
)
