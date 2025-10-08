"""
查询引擎工厂
根据配置创建和管理查询引擎实例
"""
from typing import Dict, Any, Optional
from enum import Enum

from .base_engine import BaseQueryEngine
from .duckdb_engine import DuckDBQueryEngine
from .mysql_engine import MySQLQueryEngine
from utils.logger import get_logger
from utils.exceptions import QueryEngineException, ConfigurationException
from config.settings import get_settings

logger = get_logger(__name__)


class EngineType(str, Enum):
    """查询引擎类型枚举"""
    DUCKDB = "duckdb"
    MYSQL = "mysql"


class QueryEngineFactory:
    """查询引擎工厂类"""
    
    _instances: Dict[str, BaseQueryEngine] = {}
    
    @classmethod
    def create_engine(
        self, 
        engine_type: str, 
        config: Dict[str, Any],
        instance_name: str = "default"
    ) -> BaseQueryEngine:
        """
        创建查询引擎实例
        
        Args:
            engine_type: 引擎类型
            config: 引擎配置
            instance_name: 实例名称
            
        Returns:
            查询引擎实例
        """
        try:
            # 检查是否已存在实例
            if instance_name in self._instances:
                logger.info(f"返回已存在的查询引擎实例: {instance_name}")
                return self._instances[instance_name]
            
            # 根据类型创建引擎
            if engine_type == EngineType.DUCKDB:
                engine = DuckDBQueryEngine(config)
            elif engine_type == EngineType.MYSQL:
                engine = MySQLQueryEngine(config)
            else:
                raise QueryEngineException(f"不支持的查询引擎类型: {engine_type}")
            
            # 缓存实例
            self._instances[instance_name] = engine
            
            logger.info(f"创建查询引擎实例成功: {engine_type} ({instance_name})")
            return engine
            
        except Exception as e:
            logger.error(f"创建查询引擎失败: {e}")
            raise QueryEngineException(f"创建查询引擎失败: {e}")
    
    @classmethod
    def get_engine(self, instance_name: str = "default") -> Optional[BaseQueryEngine]:
        """
        获取查询引擎实例
        
        Args:
            instance_name: 实例名称
            
        Returns:
            查询引擎实例，如果不存在返回None
        """
        return self._instances.get(instance_name)
    
    @classmethod
    def remove_engine(self, instance_name: str = "default") -> bool:
        """
        移除查询引擎实例
        
        Args:
            instance_name: 实例名称
            
        Returns:
            是否成功移除
        """
        try:
            if instance_name in self._instances:
                engine = self._instances[instance_name]
                # 异步断开连接需要在异步上下文中处理
                del self._instances[instance_name]
                logger.info(f"移除查询引擎实例: {instance_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"移除查询引擎实例失败: {e}")
            return False
    
    @classmethod
    async def close_all_engines(self):
        """关闭所有查询引擎实例"""
        try:
            for instance_name, engine in self._instances.items():
                try:
                    await engine.disconnect()
                    logger.info(f"关闭查询引擎: {instance_name}")
                except Exception as e:
                    logger.error(f"关闭查询引擎失败 {instance_name}: {e}")
            
            self._instances.clear()
            logger.info("所有查询引擎已关闭")
            
        except Exception as e:
            logger.error(f"关闭查询引擎失败: {e}")
    
    @classmethod
    def list_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有查询引擎实例
        
        Returns:
            实例信息字典
        """
        engines_info = {}
        
        for instance_name, engine in self._instances.items():
            engines_info[instance_name] = {
                "engine_type": engine.__class__.__name__,
                "is_connected": engine.is_connected,
                "config": {k: v for k, v in engine.config.items() if 'password' not in k.lower()}
            }
        
        return engines_info
    
    @classmethod
    def get_supported_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取支持的查询引擎信息
        
        Returns:
            支持的引擎信息
        """
        return {
            EngineType.DUCKDB: {
                "name": "DuckDB",
                "description": "轻量级分析数据库，适用于开发和测试",
                "features": [
                    "内存数据库支持",
                    "文件数据库支持", 
                    "SQL分析功能",
                    "JSON支持",
                    "Parquet支持"
                ],
                "use_cases": ["开发环境", "测试环境", "小数据量分析"]
            },
            EngineType.MYSQL: {
                "name": "MySQL",
                "description": "流行的关系型数据库，适用于生产环境",
                "features": [
                    "ACID事务支持",
                    "连接池管理",
                    "查询优化",
                    "表统计信息",
                    "索引优化"
                ],
                "use_cases": ["生产环境", "大数据量处理", "高并发场景"]
            }
        }


def get_query_engine(instance_name: str = "default") -> BaseQueryEngine:
    """
    获取查询引擎实例（如果不存在则创建默认实例）
    
    Args:
        instance_name: 实例名称
        
    Returns:
        查询引擎实例
    """
    # 尝试获取现有实例
    engine = QueryEngineFactory.get_engine(instance_name)
    
    if engine is None:
        # 创建默认实例
        settings = get_settings()
        
        try:
            # 获取查询引擎配置
            engine_config = settings.get_query_engine_config()
            engine_type = engine_config.get("type")
            
            if not engine_type:
                raise ConfigurationException("查询引擎类型未配置")
            
            # 创建引擎实例
            engine = QueryEngineFactory.create_engine(
                engine_type=engine_type,
                config=engine_config,
                instance_name=instance_name
            )
            
            logger.info(f"创建默认查询引擎实例: {engine_type}")
            
        except Exception as e:
            logger.error(f"创建默认查询引擎失败: {e}")
            raise QueryEngineException(f"创建默认查询引擎失败: {e}")
    
    return engine


async def initialize_default_engine() -> BaseQueryEngine:
    """
    初始化默认查询引擎并建立连接
    
    Returns:
        初始化后的查询引擎实例
    """
    try:
        engine = get_query_engine()
        
        # 建立连接
        if not engine.is_connected:
            await engine.connect()
        
        # 如果是DuckDB，创建示例数据
        if isinstance(engine, DuckDBQueryEngine):
            await engine.create_sample_data()
        
        logger.info("默认查询引擎初始化完成")
        return engine
        
    except Exception as e:
        logger.error(f"初始化默认查询引擎失败: {e}")
        raise QueryEngineException(f"初始化默认查询引擎失败: {e}")


async def health_check_engines() -> Dict[str, Dict[str, Any]]:
    """
    检查所有查询引擎的健康状态
    
    Returns:
        健康检查结果
    """
    health_status = {}
    
    for instance_name, engine in QueryEngineFactory._instances.items():
        try:
            # 测试连接
            is_healthy = await engine.test_connection()
            
            health_status[instance_name] = {
                "status": "healthy" if is_healthy else "unhealthy",
                "engine_type": engine.__class__.__name__,
                "is_connected": engine.is_connected,
                "last_check": "now"
            }
            
        except Exception as e:
            health_status[instance_name] = {
                "status": "error",
                "engine_type": engine.__class__.__name__,
                "is_connected": False,
                "error": str(e),
                "last_check": "now"
            }
    
    return health_status