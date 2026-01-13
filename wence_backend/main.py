"""
WenCe AI Writing Assistant - 入口文件
"""

import uvicorn


if __name__ == "__main__":
    import sys
    import signal
    
    def signal_handler(sig, frame):
        print("\n正在安全关闭服务...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        from app.core.config import settings
        
        print("启动 WenCe AI Writing Assistant API 服务...")
        print(f"访问地址: http://{settings.HOST}:{settings.PORT}")
        print(f"API 文档: http://{settings.HOST}:{settings.PORT}{settings.API_PREFIX}/docs")
        print("按 Ctrl+C 停止服务")
        
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
