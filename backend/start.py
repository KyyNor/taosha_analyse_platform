"""
系统启动脚本
用于启动淘沙分析平台
"""
import asyncio
import uvicorn
from pathlib import Path

from main import app
from scripts.init_permissions import InitPermissionData
from utils.logger import get_logger

logger = get_logger(__name__)


async def init_system():
    """系统初始化"""
    try:
        logger.info("开始系统初始化...")
        
        # 初始化权限数据
        init_data = InitPermissionData()
        await init_data.run_init()
        
        logger.info("系统初始化完成")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}", exc_info=True)
        raise


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 淘沙分析平台启动中...")
    logger.info("=" * 60)
    
    # 运行系统初始化
    asyncio.run(init_system())
    
    # 启动服务
    logger.info("启动FastAPI服务...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()