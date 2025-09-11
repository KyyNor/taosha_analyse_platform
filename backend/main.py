"""
淘沙分析平台 - FastAPI主应用
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from api.routes import router
from services import get_database_service, get_nl2sql_service

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.database_dir / "app.log", encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    logger.info("=== 淘沙分析平台启动中 ===")
    
    try:
        # 初始化数据库服务
        db_service = get_database_service()
        tables = db_service.get_tables()
        logger.info(f"数据库初始化完成，发现 {len(tables)} 个表: {tables}")
        
        # 初始化NL2SQL服务（这会触发Vanna训练）
        nl2sql_service = get_nl2sql_service()
        logger.info("NL2SQL服务初始化完成")
        
        logger.info("=== 淘沙分析平台启动成功 ===")
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise
    
    yield
    
    # 关闭时的清理
    logger.info("=== 淘沙分析平台关闭中 ===")
    try:
        # 关闭数据库连接
        db_service = get_database_service()
        db_service.close()
        logger.info("数据库连接已关闭")
        
        logger.info("=== 淘沙分析平台已关闭 ===")
    except Exception as e:
        logger.error(f"应用关闭时出错: {e}", exc_info=True)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="自然语言转SQL的AI+BI分析平台",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1", tags=["查询"])

@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "api_prefix": "/api/v1"
    }

@app.get("/api", tags=["API信息"])
async def api_info():
    """API信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "查询": "/api/v1/query",
            "表列表": "/api/v1/tables",
            "表信息": "/api/v1/table/{table_name}",
            "系统状态": "/api/v1/status",
            "健康检查": "/api/v1/health",
            "重载元数据": "/api/v1/metadata/reload"
        }
    }

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "detail": str(exc) if settings.debug else "请联系管理员"
        }
    )

def main():
    """主函数"""
    import uvicorn
    
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"数据库路径: {settings.duckdb_path}")
    logger.info(f"ChromaDB路径: {settings.chromadb_path}")
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()