# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件
用于将 WenCe AI 后端打包成单个可执行文件
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 项目根目录（从 deploy 目录向上一级）
root_dir = os.path.abspath('..')

# 收集所有需要的数据文件
datas = [
    ('../.env.example', '.'),  # 示例配置文件
    ('../README.md', '.'),
    # 打包 app 模块（FastAPI 应用）
    ('../app', 'app'),
    # 打包前端构建目录
    ('../../wence_frontend/wence_word_plugin/wps-addon-build', 'frontend'),
    # 配置文件目录
    ('../config', 'config'),
]

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
    'json',
    'asyncio',
    
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
        'PIL',
        'tkinter',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
        
        # 排除深度学习框架（不需要）
        'tensorflow',
        'torch',
        'torchvision',
        'keras',
        'jax',
        
        # 排除数据科学库（不需要）
        'pandas',
        'numpy',
        'scipy',
        'sklearn',
        'pytz',
        
        # 排除其他不需要的库
        'babel',
        'sphinx',
        'docutils',
        'lxml',
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

# 单文件模式（onefile=True）
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wence_ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台输出（方便查看日志）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)

# 如果需要目录模式（更快启动，体积更大），使用以下配置：
# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name='wence-ai',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=True,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='wence-ai',
# )
