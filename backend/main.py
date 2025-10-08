"""
淘沙分析平台后端服务入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from utils.logger import setup_logging
from api.v1.api import api_router
# from utils.database import DatabaseManager
from utils.exceptions import TaoshaException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    
    # 暂时跳过数据库初始化，避免复杂的依赖问题
    # db_manager = DatabaseManager()
    # await db_manager.initialize()
    
    logger = get_settings().logger
    logger.info("淘沙分析平台后端服务启动完成")
    
    yield
    
    # 关闭时执行
    # await db_manager.close()
    logger.info("淘沙分析平台后端服务关闭完成")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()
    
    app = FastAPI(
        title="淘沙分析平台 API",
        description="基于自然语言的企业数据分析平台",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # 异常处理器
    @app.exception_handler(TaoshaException)
    async def taosha_exception_handler(request: Request, exc: TaoshaException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.error_code,
                "message": exc.message,
                "data": None,
                "timestamp": int(exc.timestamp.timestamp())
            }
        )
    
    # 注册路由
    app.include_router(api_router, prefix="/api/taosha/v1")
    
    @app.get("/")
    async def root():
        return {
            "code": 0,
            "message": "淘沙分析平台 API 服务运行正常",
            "data": {
                "version": "1.0.0",
                "docs_url": "/docs" if settings.DEBUG else None
            }
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )