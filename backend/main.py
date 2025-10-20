"""
淘沙分析平台 - FastAPI主应用
"""

from contextlib import asynccontextmanager
from utils.logger import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.config import settings
from api.nlquey_routes import router as nlquey_router
from api.metadata_routes import router as metadata_router
from api.user_routes import router as user_router
from services.query_engine import get_query_engine
from services.nlquery_service.async_query_service import get_async_query_service
from models.db_base import get_db_session
from services.training_service.vector_training_service import VectorTrainingService


async def _train_vector_database_async(vector_training_service: VectorTrainingService):
    """异步执行向量数据库训练

    Args:
        vector_training_service: 向量训练服务实例
    """
    try:
        logger.info("开始执行向量数据库训练...")
        result = vector_training_service.train_vector_database("应用启动时的向量数据库初始化")

        if result["success"]:
            logger.info(f"向量数据库训练成功: {result}")
        else:
            logger.error(f"向量数据库训练失败: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"异步向量数据库训练异常: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    logger.info("=== 淘沙分析平台启动中 ===")

    try:
        # 初始化查询引擎服务
        query_engine = get_query_engine()
        logger.info(f"查询引擎初始化完成")

        # 初始化异步查询服务
        async_query_service = get_async_query_service()
        logger.info("异步查询服务初始化完成")

        # 初始化向量数据库训练服务
        with get_db_session() as db:
            vector_training_service = VectorTrainingService(db)

            # 异步执行向量数据库训练
            import asyncio
            asyncio.create_task(_train_vector_database_async(vector_training_service))

            logger.info("向量数据库训练服务初始化完成，开始后台训练...")

        logger.info("=== 淘沙分析平台启动成功 ===")

    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise

    yield

    # 关闭时的清理
    logger.info("=== 淘沙分析平台关闭中 ===")
    try:
        # 关闭查询引擎连接
        query_engine = get_query_engine()
        query_engine.close()
        logger.info("查询引擎连接已关闭")

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

api_prefix = "/api/taosha/v1"

# 注册路由
app.include_router(nlquey_router, prefix=api_prefix)
app.include_router(metadata_router, prefix=api_prefix)
app.include_router(user_router, prefix=api_prefix)

@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "api_prefix": api_prefix
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
    logger.info(f"ChromaDB路径: {settings.vector_store_type}")
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        reload_excludes=["database/*", "*.log", "__pycache__/*"] if settings.debug else None,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()