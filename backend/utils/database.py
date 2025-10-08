"""
数据库连接管理模块
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
from pathlib import Path

from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

# 创建基础模型类
Base = declarative_base()


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session_maker = None
    
    async def initialize(self):
        """初始化数据库连接"""
        try:
            database_url = self.settings.get_database_url()
            logger.info(f"正在连接数据库: {database_url.split('@')[0] if '@' in database_url else database_url}")
            
            # 创建异步引擎
            self.engine = create_async_engine(
                database_url,
                echo=self.settings.DEBUG,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # 创建会话工厂
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 测试数据库连接
            await self._test_connection()
            
            # 创建表结构
            await self._create_tables()
            
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _test_connection(self):
        """测试数据库连接"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            raise
    
    async def _create_tables(self):
        """创建数据库表结构"""
        try:
            # 暂时跳过模型导入，只创建基础表结构
            # from models import metadata_models, nlquery_models, system_models
            
            async with self.engine.begin() as conn:
                # 创建所有表
                await conn.run_sync(Base.metadata.create_all)
                logger.info("数据库表结构创建完成")
                
        except Exception as e:
            logger.error(f"创建数据库表结构失败: {e}")
            # 在开发环境中，表结构创建失败不应该阻止应用启动
            if self.settings.DEBUG:
                logger.warning("开发环境下忽略表结构创建错误")
            else:
                raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not self.async_session_maker:
            raise RuntimeError("数据库未初始化")
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("数据库连接已关闭")


# 全局数据库管理器实例
db_manager = DatabaseManager()


async def get_async_db():
    """
    简化的数据库会话获取函数
    用于依赖注入
    """
    # 暂时返回 None，避免复杂的数据库初始化
    return None


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入函数，获取数据库会话
    """
    # 暂时返回 None，避免复杂的数据库初始化
    return None


class QueryEngineManager:
    """查询引擎管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine_config = self.settings.get_query_engine_config()
        self.connection = None
    
    async def initialize(self):
        """初始化查询引擎"""
        try:
            if self.engine_config["type"] == "duckdb":
                await self._init_duckdb()
            elif self.engine_config["type"] == "mysql":
                await self._init_mysql()
            else:
                raise ValueError(f"不支持的查询引擎类型: {self.engine_config['type']}")
            
            logger.info(f"查询引擎初始化完成: {self.engine_config['type']}")
            
        except Exception as e:
            logger.error(f"查询引擎初始化失败: {e}")
            raise
    
    async def _init_duckdb(self):
        """初始化 DuckDB 引擎"""
        try:
            import duckdb
            
            # 确保数据库文件目录存在
            db_path = Path(self.engine_config["path"])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建 DuckDB 连接
            self.connection = duckdb.connect(str(db_path))
            
            # 测试连接
            result = self.connection.execute("SELECT 1").fetchone()
            if result[0] != 1:
                raise Exception("DuckDB 连接测试失败")
            
            logger.info(f"DuckDB 连接成功: {db_path}")
            
        except ImportError:
            logger.error("DuckDB 未安装，请运行: pip install duckdb")
            raise
        except Exception as e:
            logger.error(f"DuckDB 初始化失败: {e}")
            raise
    
    async def _init_mysql(self):
        """初始化 MySQL 引擎"""
        try:
            import aiomysql
            
            # 创建 MySQL 连接池
            self.connection = await aiomysql.create_pool(
                host=self.engine_config["host"],
                port=self.engine_config["port"],
                user=self.engine_config["user"],
                password=self.engine_config["password"],
                db=self.engine_config["database"],
                charset='utf8mb4',
                autocommit=True,
                maxsize=10,
                minsize=1,
            )
            
            # 测试连接
            async with self.connection.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    if result[0] != 1:
                        raise Exception("MySQL 连接测试失败")
            
            logger.info(f"MySQL 连接成功: {self.engine_config['host']}:{self.engine_config['port']}")
            
        except ImportError:
            logger.error("aiomysql 未安装，请运行: pip install aiomysql")
            raise
        except Exception as e:
            logger.error(f"MySQL 初始化失败: {e}")
            raise
    
    async def execute_query(self, sql: str, params=None):
        """执行查询"""
        try:
            if self.engine_config["type"] == "duckdb":
                return await self._execute_duckdb_query(sql, params)
            elif self.engine_config["type"] == "mysql":
                return await self._execute_mysql_query(sql, params)
            else:
                raise ValueError(f"不支持的查询引擎类型: {self.engine_config['type']}")
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
    
    async def _execute_duckdb_query(self, sql: str, params=None):
        """执行 DuckDB 查询"""
        try:
            if params:
                result = self.connection.execute(sql, params)
            else:
                result = self.connection.execute(sql)
            
            # 获取列名
            columns = [desc[0] for desc in result.description] if result.description else []
            
            # 获取数据
            rows = result.fetchall()
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
        except Exception as e:
            logger.error(f"DuckDB 查询执行失败: {e}")
            raise
    
    async def _execute_mysql_query(self, sql: str, params=None):
        """执行 MySQL 查询"""
        try:
            async with self.connection.acquire() as conn:
                async with conn.cursor() as cursor:
                    if params:
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)
                    
                    # 获取列名
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # 获取数据
                    rows = await cursor.fetchall()
                    
                    return {
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows)
                    }
        except Exception as e:
            logger.error(f"MySQL 查询执行失败: {e}")
            raise
    
    async def close(self):
        """关闭查询引擎连接"""
        try:
            if self.connection:
                if self.engine_config["type"] == "duckdb":
                    self.connection.close()
                elif self.engine_config["type"] == "mysql":
                    self.connection.close()
                    await self.connection.wait_closed()
                
                logger.info("查询引擎连接已关闭")
        except Exception as e:
            logger.error(f"关闭查询引擎连接失败: {e}")


# 全局查询引擎管理器实例
query_engine_manager = QueryEngineManager()