#!/usr/bin/env python3
"""
WenCe AI 打包脚本 - 跨平台
将前后端打包成单个可执行文件
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "wence_backend"
FRONTEND_DIR = PROJECT_ROOT / "wence_frontend" / "wence_word_plugin"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = BUILD_DIR / "dist"


def run_command(cmd, cwd=None, shell=False):
    """执行命令"""
    print(f"执行: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    result = subprocess.run(
        cmd, 
        cwd=cwd, 
        shell=shell,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        sys.exit(1)
    return result.stdout


def build_frontend():
    """构建前端"""
    print("\n" + "="*50)
    print("步骤 1/4: 构建前端...")
    print("="*50)
    
    # 检查 node_modules
    if not (FRONTEND_DIR / "node_modules").exists():
        print("安装前端依赖...")
        run_command("pnpm install", cwd=FRONTEND_DIR, shell=True)
    
    # 构建
    print("构建前端静态文件...")
    run_command("pnpm build", cwd=FRONTEND_DIR, shell=True)
    
    frontend_dist = FRONTEND_DIR / "dist"
    if not frontend_dist.exists():
        print("错误: 前端构建失败，dist 目录不存在")
        sys.exit(1)
    
    print("✓ 前端构建完成")
    return frontend_dist


def prepare_static(frontend_dist):
    """准备静态文件目录"""
    print("\n" + "="*50)
    print("步骤 2/4: 准备静态文件...")
    print("="*50)
    
    static_dir = BACKEND_DIR / "static"
    
    # 清理旧的静态目录
    if static_dir.exists():
        shutil.rmtree(static_dir)
    
    # 复制前端构建产物
    shutil.copytree(frontend_dist, static_dir)
    
    # 创建插件目录
    plugin_dir = static_dir / "plugin"
    plugin_dir.mkdir(exist_ok=True)
    
    # 复制打包专用的 manifest.xml（路径已调整）
    plugin_src = BUILD_DIR / "plugin"
    if plugin_src.exists():
        for file in plugin_src.glob("*.xml"):
            shutil.copy(file, plugin_dir / file.name)
    else:
        # 如果没有专用文件，从前端复制
        manifest_src = FRONTEND_DIR / "manifest.xml"
        if manifest_src.exists():
            shutil.copy(manifest_src, plugin_dir / "manifest.xml")
        
        ribbon_src = FRONTEND_DIR / "public" / "ribbon.xml"
        if ribbon_src.exists():
            shutil.copy(ribbon_src, plugin_dir / "ribbon.xml")
    
    # 复制 images
    images_src = FRONTEND_DIR / "public" / "images"
    if images_src.exists():
        shutil.copytree(images_src, plugin_dir / "images")
    
    print("✓ 静态文件准备完成")
    return static_dir


def create_packaged_main():
    """创建打包专用的入口文件"""
    print("\n" + "="*50)
    print("步骤 3/4: 创建打包入口...")
    print("="*50)
    
    main_content = '''"""
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
'''
    
    main_path = BACKEND_DIR / "main_packaged.py"
    main_path.write_text(main_content, encoding="utf-8")
    
    print("✓ 打包入口创建完成")
    return main_path


def build_executable():
    """使用 PyInstaller 打包"""
    print("\n" + "="*50)
    print("步骤 4/4: 打包可执行文件...")
    print("="*50)
    
    # 清理旧的构建
    for dir_name in ["build", "dist"]:
        dir_path = BACKEND_DIR / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
    
    # PyInstaller 命令
    app_name = "wence_ai"
    if platform.system() == "Windows":
        app_name += ".exe"
    
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        "--name", "wence_ai",
        "--add-data", f"static{os.pathsep}static",
        "--add-data", f"data{os.pathsep}data",
        "--add-data", f"app{os.pathsep}app",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--collect-submodules", "openai",
        "--collect-submodules", "pydantic",
        "--collect-submodules", "fastapi",
        "--noconfirm",
        "--clean",
        "main_packaged.py"
    ]
    
    run_command(pyinstaller_args, cwd=BACKEND_DIR)
    
    # 移动产物到 build/dist
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 复制可执行文件
    exe_name = "wence_ai.exe" if platform.system() == "Windows" else "wence_ai"
    exe_src = BACKEND_DIR / "dist" / exe_name
    exe_dst = DIST_DIR / exe_name
    
    if exe_src.exists():
        shutil.copy(exe_src, exe_dst)
        if platform.system() != "Windows":
            os.chmod(exe_dst, 0o755)
    
    # 复制静态文件
    static_src = BACKEND_DIR / "static"
    static_dst = DIST_DIR / "static"
    if static_dst.exists():
        shutil.rmtree(static_dst)
    shutil.copytree(static_src, static_dst)
    
    # 创建空的 data 目录
    (DIST_DIR / "data").mkdir(exist_ok=True)
    
    # 清理 backend 中的临时文件
    for dir_name in ["build", "dist", "__pycache__"]:
        dir_path = BACKEND_DIR / dir_name
        if dir_path.exists() and dir_name != "dist":
            shutil.rmtree(dir_path)
    
    spec_file = BACKEND_DIR / "wence_ai.spec"
    if spec_file.exists():
        spec_file.unlink()
    
    print("✓ 打包完成")
    print(f"\n输出目录: {DIST_DIR}")


def main():
    print("="*50)
    print("  WenCe AI 打包工具")
    print(f"  平台: {platform.system()} {platform.machine()}")
    print("="*50)
    
    # 检查 PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安装 PyInstaller...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 执行打包步骤
    frontend_dist = build_frontend()
    prepare_static(frontend_dist)
    create_packaged_main()
    build_executable()
    
    print("\n" + "="*50)
    print("  打包完成!")
    print("="*50)
    print(f"\n可执行文件位置: {DIST_DIR}")
    print("\n运行方式:")
    if platform.system() == "Windows":
        print("  .\\dist\\wence_ai.exe")
    else:
        print("  ./dist/wence_ai")
    print("\nWPS 插件加载地址:")
    print("  http://localhost:8000/plugin/manifest.xml")


if __name__ == "__main__":
    main()
