"""
API 依赖注入
后续添加数据库会话、用户认证等公共依赖
"""


# 示例：后续可添加数据库会话依赖
# async def get_db() -> Generator:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# 示例：后续可添加当前用户依赖
# async def get_current_user() -> Any:
#     pass
