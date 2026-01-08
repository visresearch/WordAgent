"""
WenCe AI Writing Assistant - 入口文件
"""

import uvicorn


if __name__ == "__main__":
    from app.core.config import settings
    
    print("启动 WenCe AI Writing Assistant API 服务...")
    print(f"访问地址: http://localhost:{settings.PORT}")
    print(f"API 文档: http://localhost:{settings.PORT}{settings.API_PREFIX}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
