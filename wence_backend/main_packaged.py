"""
WenCe AI - 打包版入口文件
"""

import os
import sys
from pathlib import Path

# 确定运行时的基础路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# 设置数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 设置环境变量
os.environ.setdefault("WENCE_BASE_DIR", str(BASE_DIR))
os.environ.setdefault("WENCE_DATA_DIR", str(DATA_DIR))
os.environ.setdefault("WENCE_STATIC_DIR", str(BASE_DIR / "static"))

import uvicorn
from app.main import app
from app.core.config import settings


def main():
    print("="*50)
    print("  WenCe AI Writing Assistant")
    print("="*50)
    print(f"")
    print(f"  服务地址: http://localhost:{settings.PORT}")
    print(f"  API 文档: http://localhost:{settings.PORT}/api/docs")
    print(f"")
    print(f"  WPS 插件加载地址:")
    print(f"  http://localhost:{settings.PORT}/plugin/manifest.xml")
    print(f"")
    print("="*50)
    print("按 Ctrl+C 停止服务")
    print("")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
