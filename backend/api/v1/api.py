"""
API v1 路由配置
"""
from fastapi import APIRouter

# 导入各个模块的路由
from .metadata import router as metadata_router
# from .nlquery import router as nlquery_router
# from .websocket import router as websocket_router
from .query_history import router as query_history_router
from .auth import router as auth_router
from .users import router as users_router
from .roles import router as roles_router
# from .system import router as system_router

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证管理"])
api_router.include_router(users_router, prefix="/users", tags=["用户管理"])
api_router.include_router(roles_router, prefix="/roles", tags=["角色管理"])
api_router.include_router(metadata_router, prefix="/metadata", tags=["元数据管理"])
# api_router.include_router(nlquery_router, prefix="/nlquery", tags=["自然语言查询"])
# api_router.include_router(websocket_router, tags=["WebSocket通信"])
api_router.include_router(query_history_router, prefix="/query", tags=["查询历史"])
# api_router.include_router(system_router, prefix="/system", tags=["系统管理"])

@api_router.get("/ping")
async def ping():
    """健康检查接口"""
    return {
        "code": 0,
        "message": "pong",
        "data": {
            "status": "healthy",
            "version": "1.0.0"
        }
    }