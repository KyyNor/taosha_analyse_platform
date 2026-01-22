"""
淘沙分析平台 - FastAPI主应用
"""
import asyncio, platform, os
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


from contextlib import asynccontextmanager
from pathlib import Path
from utils.logger import logger
from filelock import FileLock, Timeout

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.config import settings
from api.metadata_routes import router as metadata_router
from api.user_routes import router as user_router
from api.agents_routes import router as agents_router
from api.deepagents_routes import router as deepagents_router
from api.entity_routes import router as entity_router
from api.permission_routes import router as permission_router
from api.login_record_routes import router as login_record_router
from api.fraudhunter import (
    indicator_task_router,
    indicator_router,
    task_router as fraudhunter_task_router,
    model_router,
    risk_control_model_router,
    wide_table_router,
    alert_control_record_router,
    system_config_router,
    indicator_query_router
)
from services.query_engine import get_query_engine
from models.db_base import get_db_session
from services.tracking_service.observability_service import initialize_observability

# 全局变量：实时数据消费者实例
_realtime_consumer = None

# 全局变量：启动锁实例（服务运行期间持续持有）
_startup_lock = None


async def _run_realtime_consumer(consumer):
    """运行实时数据消费者（后台任务）

    Args:
        consumer: RealtimeDataConsumer实例
    """
    try:
        await consumer.start()
    except Exception as e:
        logger.error(f"实时数据消费服务运行异常: {e}", exc_info=True)


async def _start_scheduler_service():
    """启动统一调度服务（每个worker都会执行，通过任务分片决定注册哪些任务）

    这个函数在启动锁保护之外执行，所有worker都会运行
    通过 PID 取模和任务组配置实现任务分片
    """
    try:
        from services.scheduler import scheduler_service
        from services.scheduler.jobs import (
            sync_all_wide_tables_job,
            generate_realtime_wide_table_job,
            metadata_sync_job,
            fine_report_sync_job,
            vector_training_job
        )

        # 计算当前worker应该运行的任务
        pid = os.getpid()
        worker_count = settings.workers
        worker_index = pid % worker_count
        

        # 定义默认任务组（二维数组）
        default_task_groups = [
            ['offline_wide_table_sync'],                          # 组0：离线宽表同步
            ['generate_realtime_wide_table_job', 'metadata_sync'],  # 组1：实时宽表生成 + 元数据同步
            ['fine_report_sync'],                                 # 组2：FineReport同步
            ['vector_training', 'postgres_data_cleanup']         # 组3：向量训练 + 数据清理
        ]

        # 获取当前worker分配的任务（轮询算法）
        assigned_tasks = []
        for group_idx, group in enumerate(default_task_groups):
            # 使用组索引取模决定该组归属哪个worker（轮询分配）
            target_worker = group_idx % worker_count
            if target_worker == worker_index:
                assigned_tasks.extend(group)

        logger.info(f"Worker {worker_index}/{worker_count} (PID:{os.getpid()}) 负责运行任务: {assigned_tasks}")

        # 定义所有可注册的任务
        jobs_to_register = [
            ('offline_wide_table_sync', sync_all_wide_tables_job,
             settings.scheduler_offline_wide_table_sync, '离线指标宽表同步'),
            ('generate_realtime_wide_table_job', generate_realtime_wide_table_job,
             settings.scheduler_model_runner_interval, '实时指标宽表生成'),
            ('metadata_sync', metadata_sync_job,
             settings.scheduler_metadata_sync_interval, '元数据同步'),
            ('fine_report_sync', fine_report_sync_job,
             settings.scheduler_fine_report_sync_interval, 'FineReport报表同步'),
            ('vector_training', vector_training_job,
             settings.scheduler_vector_training_interval, '向量数据库训练'),
        ]

        registered_count = 0
        for job_id, job_func, interval, job_name in jobs_to_register:
            # 检查任务是否在当前worker的分配列表中
            if job_id not in assigned_tasks:
                logger.info(f"跳过任务 {job_name}（未分配给当前worker）")
                continue

            scheduler_service.add_interval_job(
                func=job_func,
                seconds=interval,
                job_id=job_id,
                job_name=job_name
            )
            registered_count += 1

        # PostgreSQL数据清理任务
        if settings.fraudhunter_realtime_data_enabled:
            from services.scheduler.jobs.postgres_data_cleanup_job import postgres_data_cleanup_job
            job_id = 'postgres_data_cleanup'

            if job_id in assigned_tasks:
                scheduler_service.add_cron_job(
                    func=postgres_data_cleanup_job,
                    cron=settings.scheduler_postgres_data_cleanup_cron,
                    job_id=job_id,
                    job_name='PostgreSQL数据清理'
                )
                registered_count += 1
            else:
                logger.info(f"跳过任务 PostgreSQL数据清理（未分配给当前worker）")

        # 启动调度器
        scheduler_service.start()

        logger.info(f"统一调度服务已启动（当前worker注册{registered_count}个任务）")
    except Exception as e:
        logger.error(f"统一调度服务启动失败: {e}", exc_info=True)


async def _initialize_system_services():
    """初始化系统服务，包括向量数据库训练、元数据同步、可观测服务、PySpark

    使用 filelock 确保在多worker环境下只运行一次，锁在服务运行期间持续持有
    """
    global _startup_lock, _realtime_consumer

    lock_file_path = Path(__file__).parent / ".startup_lock"

    # 尝试获取锁（非阻塞模式）
    # timeout=0 表示立即返回，不等待
    try:
        _startup_lock = FileLock(str(lock_file_path), timeout=0)
        _startup_lock.acquire()
        logger.info(f"成功获取启动锁 (PID: {os.getpid()})")
    except Timeout:
        logger.info("检测到其他worker正在进行初始化，跳过...")
        return
    except Exception as e:
        logger.error(f"获取启动锁时出错: {e}", exc_info=True)
        return

    try:
        logger.info("=== 开始系统服务初始化（仅此worker执行） ===")

        # 启动实时数据服务（如果配置启用）
        if settings.fraudhunter_realtime_data_enabled:
            try:
                from services.fraudhunter.model_service import RealtimeDataConsumer

                _realtime_consumer = RealtimeDataConsumer()

                # 创建后台任务
                asyncio.create_task(_run_realtime_consumer(_realtime_consumer))

                logger.info("实时数据消费服务已启动")

            except Exception as e:
                # 启动异常不影响其他功能，只记录错误
                logger.error(f"实时数据消费服务启动失败: {e}", exc_info=True)

        logger.info("=== 系统服务初始化完成 ===")
        logger.info("启动锁将在服务运行期间持续持有，应用关闭时释放")

    except Exception as e:
        logger.error(f"系统服务初始化失败: {e}", exc_info=True)
        # 初始化失败时释放锁，允许其他worker尝试
        try:
            if _startup_lock is not None:
                _startup_lock.release()
                _startup_lock = None
                logger.info("初始化失败，已释放启动锁")
        except Exception as release_error:
            logger.error(f"释放启动锁失败: {release_error}", exc_info=True)
        raise
    # 注意：成功初始化后不释放锁，锁将一直持有到应用关闭



@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    logger.info("=== 淘沙分析平台启动中 ===")

    try:
        # 初始化异步 Playwright 浏览器（每个worker都需要）
        if not settings.fine_report_disable_browser_init:
            logger.info("初始化异步 Playwright 浏览器...")
            from services.agents.tools.fine_report_tools import get_async_browser_context
            await get_async_browser_context()  # 初始化异步浏览器并建立登录会话
            logger.info("异步 Playwright 浏览器初始化完成")
        else:
            logger.info("浏览器初始化已禁用，跳过异步 Playwright 浏览器初始化")

        # 初始化查询引擎服务（每个worker都需要）
        query_engine = get_query_engine()
        logger.info(f"查询引擎初始化完成")
        
        # 初始化可观测性服务（外部追踪）
        initialize_observability()

        # 初始化数据库表和页面同步
        try:
            logger.info("初始化数据库表...")
            from models.db_base import create_tables
            create_tables()
            
            logger.info("同步页面配置到数据库...")
            from services.page_discovery_service import PageDiscoveryService
            with get_db_session() as db:
                page_service = PageDiscoveryService(db)
                page_service.sync_pages_on_startup()
            
            logger.info("数据库初始化和页面同步完成")
        except Exception as e:
            logger.error(f"数据库初始化或页面同步失败: {e}", exc_info=True)
            # 不影响系统启动，继续运行

        # 初始化系统服务（实时数据消费者等单例服务）
        # 这些服务在多worker环境下只需要运行一次（使用启动锁保护）
        await _initialize_system_services()

        # 启动统一调度服务（所有worker都会启动，通过任务分片决定注册哪些任务）
        await _start_scheduler_service()

        # 启动 DeepAgents 任务执行器（每个 worker 都需要启动）
        try:
            from services.agents.deepagents import get_task_runner
            deepagents_runner = get_task_runner()
            deepagents_runner.start()
            logger.info("DeepAgents 任务执行器已启动")
        except Exception as e:
            logger.error(f"DeepAgents 任务执行器启动失败: {e}", exc_info=True)

        logger.info("=== 淘沙分析平台启动成功 ===")
        yield

    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise

    # 关闭时的清理
    logger.info("=== 淘沙分析平台关闭中 ===")
    try:
        # 停止 DeepAgents 任务执行器
        try:
            from services.agents.deepagents import get_task_runner
            deepagents_runner = get_task_runner()
            deepagents_runner.stop()
            logger.info("DeepAgents 任务执行器已停止")
        except Exception as e:
            logger.error(f"DeepAgents 任务执行器停止失败: {e}", exc_info=True)

        # 关闭统一调度服务
        try:
            from services.scheduler import scheduler_service
            scheduler_service.shutdown()
            logger.info("统一调度服务已关闭")
        except Exception as e:
            logger.error(f"统一调度服务关闭失败: {e}", exc_info=True)

        # 停止实时数据消费者
        if settings.fraudhunter_realtime_data_enabled and _realtime_consumer is not None:
            try:
                await _realtime_consumer.stop()
                logger.info("实时数据消费服务已停止")
            except Exception as e:
                logger.error(f"停止实时数据消费服务失败: {e}", exc_info=True)

        # 清理异步 Playwright 浏览器（每个worker都需要清理）
        if not settings.fine_report_disable_browser_init:
            logger.info("清理异步 Playwright 浏览器...")
            from services.agents.tools.fine_report_tools import cleanup_async_browser
            await cleanup_async_browser()
            logger.info("异步 Playwright 浏览器已清理")
        else:
            logger.info("浏览器初始化已禁用，跳过异步 Playwright 浏览器清理")

        # 关闭查询引擎连接（每个worker都需要关闭）
        query_engine = get_query_engine()
        query_engine.close()
        logger.info("查询引擎连接已关闭")

        # 释放启动锁（仅在持有锁的worker中执行）
        global _startup_lock
        if _startup_lock is not None:
            try:
                _startup_lock.release()
                logger.info("启动锁已释放")
            except Exception as e:
                logger.error(f"释放启动锁失败: {e}", exc_info=True)
            finally:
                _startup_lock = None

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
app.include_router(metadata_router, prefix=api_prefix)
app.include_router(user_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)
app.include_router(deepagents_router, prefix=api_prefix)

# 注册权限管理路由
app.include_router(entity_router, prefix=api_prefix)
app.include_router(permission_router, prefix=api_prefix)
app.include_router(login_record_router, prefix=api_prefix)

# 注册 FraudHunter 路由
fraudhunter_prefix = f"{api_prefix}/fraudhunter"
app.include_router(indicator_task_router, prefix=fraudhunter_prefix)
app.include_router(indicator_router, prefix=fraudhunter_prefix)
app.include_router(fraudhunter_task_router, prefix=fraudhunter_prefix)
app.include_router(model_router, prefix=fraudhunter_prefix)  # 模型管理（规则引擎）
app.include_router(risk_control_model_router, prefix=fraudhunter_prefix)  # 预警管控模型
app.include_router(wide_table_router, prefix=fraudhunter_prefix)
app.include_router(alert_control_record_router, prefix=fraudhunter_prefix)  # 告警管控记录
app.include_router(system_config_router, prefix=fraudhunter_prefix)  # 系统配置
app.include_router(indicator_query_router, prefix=fraudhunter_prefix)  # 指标数据查询

# API 根路径信息
@app.get(f"{api_prefix}/", tags=["API信息"])
async def api_root():
    """API 根路径信息"""
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