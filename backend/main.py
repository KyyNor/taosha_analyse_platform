"""
淘沙分析平台 - FastAPI主应用
"""
import asyncio, platform, os, time
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


from contextlib import asynccontextmanager
from pathlib import Path
from utils.logger import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.config import settings
from api.nlquey_routes import router as nlquey_router
from api.metadata_routes import router as metadata_router
from api.user_routes import router as user_router
from api.agents_routes import router as agents_router
from api.fraudhunter import (
    indicator_task_router,
    indicator_router,
    task_router as fraudhunter_task_router,
    wide_table_router
)
from services.query_engine import get_query_engine
from services.nlquery_service.async_query_service import get_async_query_service
from models.db_base import get_db_session
from services.vector_store.vector_training_service import VectorTrainingService
from services.tracking_service.observability_service import initialize_observability
from services.metadata_service.metadata_sync_service import MetadataSyncService
# from services.agents.fine_report_tools import get_browser, _cleanup_browser  # 已改为异步版本


def _acquire_startup_lock():
    """获取启动锁，确保在多worker环境下只有一个进程执行初始化

    Returns:
        bool: 是否成功获取锁
    """
    lock_file_path = Path(__file__).parent / ".startup_lock"

    try:
        # 检查锁文件是否已存在
        if lock_file_path.exists():
            try:
                # 读取锁文件内容，获取PID和创建时间
                lock_content = lock_file_path.read_text().strip()
                if lock_content:
                    parts = lock_content.split(':')
                    if len(parts) >= 2:
                        stored_pid = parts[0]
                        stored_time = float(parts[1])

                        # 检查锁文件是否过期（超过10分钟）
                        current_time = time.time()
                        if current_time - stored_time < 600:  # 10分钟
                            logger.info(f"检测到其他worker (PID: {stored_pid}) 正在进行初始化，跳过...")
                            return False
                        else:
                            logger.info(f"发现过期的锁文件 (PID: {stored_pid})，重新获取锁")

                # 尝试删除过期的锁文件
                lock_file_path.unlink()

            except (ValueError, IndexError, FileNotFoundError) as e:
                logger.warning(f"读取锁文件失败，尝试重新创建: {e}")
                if lock_file_path.exists():
                    lock_file_path.unlink()

        # 创建新的锁文件，包含PID和时间戳
        current_pid = str(os.getpid())
        current_time = str(time.time())
        lock_content = f"{current_pid}:{current_time}"

        # 使用原子操作创建锁文件
        with open(lock_file_path, 'w') as f:
            f.write(lock_content)

        # 短暂等待后验证锁文件仍然是我们创建的
        time.sleep(0.1)
        if lock_file_path.exists():
            verify_content = lock_file_path.read_text().strip()
            if verify_content.startswith(current_pid):
                logger.info(f"成功获取启动锁 (PID: {current_pid})")
                return True
            else:
                logger.warning("锁文件被其他进程抢占，获取锁失败")
                return False
        else:
            logger.warning("锁文件创建后消失，获取锁失败")
            return False

    except Exception as e:
        logger.error(f"获取启动锁时出错: {e}")
        return False


def _release_startup_lock():
    """释放启动锁"""
    lock_file_path = Path(__file__).parent / ".startup_lock"

    try:
        if lock_file_path.exists():
            # 验证锁文件是否属于当前进程
            try:
                lock_content = lock_file_path.read_text().strip()
                current_pid = str(os.getpid())
                if lock_content.startswith(current_pid):
                    lock_file_path.unlink()
                    logger.info(f"成功释放启动锁 (PID: {current_pid})")
                else:
                    logger.info("锁文件不属于当前进程，无需释放")
            except Exception as e:
                logger.warning(f"验证锁文件时出错，强制删除: {e}")
                lock_file_path.unlink()
        else:
            logger.info("锁文件不存在，无需释放")
    except Exception as e:
        logger.error(f"释放启动锁时出错: {e}")


async def _initialize_system_services():
    """初始化系统服务，包括向量数据库训练、元数据同步、可观测服务

    这个方法确保在多worker环境下只运行一次
    """
    if not _acquire_startup_lock():
        logger.info("跳过系统服务初始化，由其他worker处理")
        return

    try:
        logger.info("=== 开始系统服务初始化（仅此worker执行） ===")

        # 初始化向量数据库训练服务和元数据同步
        with get_db_session() as db:
            vector_training_service = VectorTrainingService(db)

            # 异步执行向量数据库训练
            import asyncio
            asyncio.create_task(_train_vector_database_async(vector_training_service))

            logger.info("向量数据库训练服务初始化完成，开始后台训练...")

            # 执行元数据同步
            metadata_sync_service = MetadataSyncService(db)
            sync_result = metadata_sync_service.sync_metadata()
            if sync_result["success"]:
                logger.info("元数据同步完毕")
            else:
                logger.error(f"元数据同步失败: {sync_result.get('error', 'Unknown error')}")

        logger.info("=== 系统服务初始化完成 ===")

    except Exception as e:
        logger.error(f"系统服务初始化失败: {e}", exc_info=True)
        raise
    finally:
        # 在初始化完成后立即释放锁，允许其他worker继续启动
        _release_startup_lock()


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
        # 初始化异步 Playwright 浏览器（每个worker都需要）
        logger.info("初始化异步 Playwright 浏览器...")
        from services.agents.fine_report_tools import get_async_browser_context
        await get_async_browser_context()  # 初始化异步浏览器并建立登录会话
        logger.info("异步 Playwright 浏览器初始化完成")

        # 初始化查询引擎服务（每个worker都需要）
        query_engine = get_query_engine()
        logger.info(f"查询引擎初始化完成")

        # 初始化异步查询服务（每个worker都需要）
        async_query_service = get_async_query_service()
        logger.info("异步查询服务初始化完成")
        
        # 初始化可观测性服务（外部追踪）
        initialize_observability()

        # 初始化系统服务（向量数据库训练、元数据同步）
        # 这些服务在多worker环境下只需要运行一次
        await _initialize_system_services()

        # 启动实时指标调度器
        try:
            from services.fraudhunter.wide_table_service.realtime_scheduler import realtime_scheduler
            realtime_scheduler.start()
            logger.info("实时指标调度器已启动")
        except Exception as e:
            logger.error(f"实时指标调度器启动失败: {e}", exc_info=True)
            # 不影响主应用启动

        from services.agents.agent_service import agent_service
        async with agent_service.lifespan():
            logger.info("=== 淘沙分析平台启动成功 ===")
            yield

    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise

    # 关闭时的清理
    logger.info("=== 淘沙分析平台关闭中 ===")
    try:
        # 关闭实时指标调度器
        try:
            from services.fraudhunter.wide_table_service.realtime_scheduler import realtime_scheduler
            realtime_scheduler.shutdown()
            logger.info("实时指标调度器已关闭")
        except Exception as e:
            logger.error(f"实时指标调度器关闭失败: {e}", exc_info=True)

        # 清理异步 Playwright 浏览器（每个worker都需要清理）
        logger.info("清理异步 Playwright 浏览器...")
        from services.agents.fine_report_tools import cleanup_async_browser
        await cleanup_async_browser()
        logger.info("异步 Playwright 浏览器已清理")

        # 关闭查询引擎连接（每个worker都需要关闭）
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

# 注册 API 路由
app.include_router(nlquey_router, prefix=api_prefix)
app.include_router(metadata_router, prefix=api_prefix)
app.include_router(user_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)

# 注册 FraudHunter 路由
fraudhunter_prefix = f"{api_prefix}/fraudhunter"
app.include_router(indicator_task_router, prefix=fraudhunter_prefix)
app.include_router(indicator_router, prefix=fraudhunter_prefix)
app.include_router(fraudhunter_task_router, prefix=fraudhunter_prefix)
app.include_router(wide_table_router, prefix=fraudhunter_prefix)

# API 根路径信息
@app.get(f"{api_prefix}/", tags=["API信息"])
async def api_root():
    """API 根路径信息"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "api_prefix": api_prefix
    }

# 配置前端静态文件（SPA 支持）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dist), html=True),
        name="frontend"
    )
    logger.info(f"前端静态文件已挂载: {frontend_dist}")
else:
    logger.warning(f"前端静态文件目录不存在: {frontend_dist}")
    logger.warning("请先运行: cd frontend && npm run build")

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

    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=50020,
        workers=settings.workers,
        reload=settings.debug,
        reload_excludes=["database/*", "*.log", "__pycache__/*"] if settings.debug else None,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()