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

from utils.config import settings
from api.nlquey_routes import router as nlquey_router
from api.metadata_routes import router as metadata_router
from api.user_routes import router as user_router
from api.agents_routes import router as agents_router
from api.deepagents_routes import router as deepagents_router
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


async def _run_realtime_consumer(consumer):
    """运行实时数据消费者（后台任务）

    Args:
        consumer: RealtimeDataConsumer实例
    """
    try:
        await consumer.start()
    except Exception as e:
        logger.error(f"实时数据消费服务运行异常: {e}", exc_info=True)


async def _initialize_pyspark():
    """初始化PySpark服务（如果配置启用）
    
    PySpark初始化是耗时操作，使用线程池执行避免阻塞事件循环
    """
    import asyncio
    
    if not getattr(settings, 'pyspark_enabled', False):
        logger.info("PySpark未启用，跳过初始化")
        return
    
    try:
        logger.info("正在初始化PySpark服务...")
        
        def _init_pyspark():
            from utils.spark_utils import pyspark_service
            return pyspark_service.initialize()
        
        # 在线程池中初始化PySpark
        success = await asyncio.to_thread(_init_pyspark)
        
        if success:
            from utils.spark_utils import pyspark_service
            status = pyspark_service.get_status()
            logger.info(f"PySpark服务初始化成功: {status}")
        else:
            logger.warning("PySpark服务初始化失败，将使用JDBC模式")
            
    except Exception as e:
        logger.error(f"PySpark初始化异常: {e}", exc_info=True)
        logger.warning("将回退到JDBC模式进行Spark查询")


async def _shutdown_pyspark():
    """关闭PySpark服务"""
    if not getattr(settings, 'pyspark_enabled', False):
        return
    
    try:
        logger.info("正在关闭PySpark服务...")
        from utils.spark_utils import pyspark_service
        pyspark_service.shutdown()
        logger.info("PySpark服务已关闭")
    except Exception as e:
        logger.error(f"关闭PySpark服务失败: {e}", exc_info=True)


async def _initialize_system_services():
    """初始化系统服务，包括向量数据库训练、元数据同步、可观测服务、PySpark

    这个方法确保在多worker环境下只运行一次
    """
    if not _acquire_startup_lock():
        logger.info("跳过系统服务初始化，由其他worker处理")
        return

    try:
        logger.info("=== 开始系统服务初始化（仅此worker执行） ===")

        # 初始化PySpark服务（如果配置启用）
        await _initialize_pyspark()


        # 启动实时数据服务（如果配置启用）
        # 注意：在启动锁保护内启动，确保只有一个worker执行
        if settings.fraudhunter_realtime_data_enabled:
            try:
                from services.fraudhunter.model_service import RealtimeDataConsumer

                # 全局保存consumer引用（用于关闭时停止）
                global _realtime_consumer
                _realtime_consumer = RealtimeDataConsumer()

                # 创建后台任务
                asyncio.create_task(_run_realtime_consumer(_realtime_consumer))

                logger.info("实时数据消费服务已启动")

            except Exception as e:
                # 启动异常不影响其他功能，只记录错误
                logger.error(f"实时数据消费服务启动失败: {e}", exc_info=True)

        # 启动统一调度服务（在启动锁保护下，确保单进程）
        try:
            from services.scheduler import scheduler_service
            from services.scheduler.jobs import (
                sync_all_wide_tables_job,
                generate_realtime_wide_table_job,
                metadata_sync_job,
                fine_report_sync_job,
                vector_training_job
            )

            # 注册离线宽表同步任务
            scheduler_service.add_interval_job(
                func=sync_all_wide_tables_job,
                seconds=settings.scheduler_offline_wide_table_sync,
                job_id='offline_wide_table_sync',
                job_name='离线指标宽表同步'
            )

            # 注册实时指标生成任务
            scheduler_service.add_interval_job(
                func=generate_realtime_wide_table_job,
                seconds=settings.scheduler_model_runner_interval,
                job_id='generate_realtime_wide_table_job',
                job_name='实时指标宽表生成'
            )

            # 注册元数据同步任务
            scheduler_service.add_interval_job(
                func=metadata_sync_job,
                seconds=settings.scheduler_metadata_sync_interval,
                job_id='metadata_sync',
                job_name='元数据同步'
            )

            # 注册FineReport报表同步任务
            scheduler_service.add_interval_job(
                func=fine_report_sync_job,
                seconds=settings.scheduler_fine_report_sync_interval,
                job_id='fine_report_sync',
                job_name='FineReport报表同步'
            )

            # 注册向量数据库训练任务
            scheduler_service.add_interval_job(
                func=vector_training_job,
                seconds=settings.scheduler_vector_training_interval,
                job_id='vector_training',
                job_name='向量数据库训练'
            )

            # 添加实时数据清理任务
            if settings.fraudhunter_realtime_data_enabled:
                from services.scheduler.jobs.realtime_data_cleanup_job import cleanup_realtime_data
                scheduler_service.add_cron_job(
                    func=cleanup_realtime_data,
                    cron='0 2 * * *',  # 每日凌晨2点
                    job_id='realtime_data_cleanup',
                    job_name='实时数据清理'
                )

            # 启动调度器
            scheduler_service.start()

            logger.info("统一调度服务已启动（仅此worker执行）")
        except Exception as e:
            logger.error(f"统一调度服务启动失败: {e}", exc_info=True)
            # 不影响系统服务初始化

        logger.info("=== 系统服务初始化完成 ===")

    except Exception as e:
        logger.error(f"系统服务初始化失败: {e}", exc_info=True)
        raise
    finally:
        # 在初始化完成后立即释放锁，允许其他worker继续启动
        _release_startup_lock()



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

        # 初始化系统服务（向量数据库训练、元数据同步）
        # 这些服务在多worker环境下只需要运行一次
        await _initialize_system_services()

        # 启动 DeepAgents 任务执行器（每个 worker 都需要启动）
        try:
            from services.agents.deepagents import get_task_runner
            deepagents_runner = get_task_runner()
            deepagents_runner.start()
            logger.info("DeepAgents 任务执行器已启动")
        except Exception as e:
            logger.error(f"DeepAgents 任务执行器启动失败: {e}", exc_info=True)

        from services.agents.agent_service import agent_service
        async with agent_service.lifespan():
            logger.info("=== 淘沙分析平台启动成功 ===")
            yield
        # logger.info("=== 淘沙分析平台启动成功 ===")
        # yield

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

        # 关闭PySpark服务
        await _shutdown_pyspark()

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
app.include_router(deepagents_router, prefix=api_prefix)

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