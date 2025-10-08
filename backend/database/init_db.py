"""
数据库初始化脚本
"""
import asyncio
import json
from pathlib import Path
from sqlalchemy import text
from utils.database import db_manager
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = db_manager
        self.base_dir = Path(__file__).parent
    
    async def initialize_database(self):
        """初始化数据库"""
        try:
            logger.info("开始初始化数据库...")
            
            # 初始化数据库连接
            await self.db_manager.initialize()
            
            # 执行初始化脚本
            if self.settings.DATABASE_TYPE == "sqlite":
                await self._init_sqlite()
            elif self.settings.DATABASE_TYPE == "mysql":
                await self._init_mysql()
            else:
                raise ValueError(f"不支持的数据库类型: {self.settings.DATABASE_TYPE}")
            
            # 插入初始数据
            await self._insert_initial_data()
            
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _init_sqlite(self):
        """初始化 SQLite 数据库"""
        logger.info("执行 SQLite 初始化脚本...")
        
        script_path = self.base_dir / "init_sqlite.sql"
        if not script_path.exists():
            logger.warning(f"SQLite 初始化脚本不存在: {script_path}")
            return
        
        # 读取SQL脚本
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句（按分号分割）
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        async with self.db_manager.get_session() as session:
            for sql_stmt in sql_statements:
                if sql_stmt:
                    try:
                        await session.execute(text(sql_stmt))
                        logger.debug(f"执行SQL成功: {sql_stmt[:100]}...")
                    except Exception as e:
                        logger.warning(f"执行SQL失败: {e}, SQL: {sql_stmt[:100]}...")
            
            await session.commit()
        
        logger.info("SQLite 初始化脚本执行完成")
    
    async def _init_mysql(self):
        """初始化 MySQL 数据库"""
        logger.info("执行 MySQL 初始化脚本...")
        
        script_path = self.base_dir / "init_mysql.sql"
        if not script_path.exists():
            logger.warning(f"MySQL 初始化脚本不存在: {script_path}")
            return
        
        # 读取SQL脚本
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句（按分号分割，但要考虑存储过程等复合语句）
        sql_statements = self._split_mysql_statements(sql_content)
        
        async with self.db_manager.get_session() as session:
            for sql_stmt in sql_statements:
                if sql_stmt:
                    try:
                        await session.execute(text(sql_stmt))
                        logger.debug(f"执行SQL成功: {sql_stmt[:100]}...")
                    except Exception as e:
                        logger.warning(f"执行SQL失败: {e}, SQL: {sql_stmt[:100]}...")
            
            await session.commit()
        
        logger.info("MySQL 初始化脚本执行完成")
    
    def _split_mysql_statements(self, sql_content: str) -> list:
        """分割MySQL SQL语句"""
        statements = []
        current_statement = ""
        in_delimiter = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--') or line.startswith('#'):
                continue
            
            # 处理DELIMITER语句
            if line.upper().startswith('DELIMITER'):
                in_delimiter = not in_delimiter
                continue
            
            current_statement += line + '\n'
            
            # 检查语句结束
            if not in_delimiter and line.endswith(';'):
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
        
        # 处理最后一个语句
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    async def _insert_initial_data(self):
        """插入初始数据"""
        logger.info("开始插入初始数据...")
        
        try:
            # 插入默认系统配置
            await self._insert_system_configs()
            
            # 插入默认用户和角色
            await self._insert_default_users()
            
            # 插入示例数据主题
            await self._insert_sample_themes()
            
            logger.info("初始数据插入完成")
            
        except Exception as e:
            logger.error(f"插入初始数据失败: {e}")
            # 初始数据插入失败不应该阻止应用启动
            if not self.settings.DEBUG:
                raise
    
    async def _insert_system_configs(self):
        """插入系统配置"""
        configs = [
            {
                'config_key': 'system.name',
                'config_value': '淘沙分析平台',
                'config_type': 'system',
                'config_description': '系统名称'
            },
            {
                'config_key': 'system.version',
                'config_value': '1.0.0',
                'config_type': 'system',
                'config_description': '系统版本'
            },
            {
                'config_key': 'query.max_result_rows',
                'config_value': '1000',
                'config_type': 'system',
                'config_description': '查询结果最大行数'
            },
            {
                'config_key': 'query.timeout_seconds',
                'config_value': '30',
                'config_type': 'system',
                'config_description': '查询超时时间(秒)'
            }
        ]
        
        async with self.db_manager.get_session() as session:
            for config in configs:
                # 检查配置是否已存在
                result = await session.execute(
                    text("SELECT id FROM sys_config WHERE config_key = :key"),
                    {"key": config['config_key']}
                )
                if not result.fetchone():
                    await session.execute(
                        text("""
                            INSERT INTO sys_config 
                            (config_key, config_value, config_type, config_description, created_by)
                            VALUES (:key, :value, :type, :description, 1)
                        """),
                        {
                            "key": config['config_key'],
                            "value": config['config_value'],
                            "type": config['config_type'],
                            "description": config['config_description']
                        }
                    )
            
            await session.commit()
        
        logger.info("系统配置插入完成")
    
    async def _insert_default_users(self):
        """插入默认用户和角色"""
        # 这里可以插入默认的管理员用户
        # 注意：生产环境中应该通过安全的方式创建管理员账户
        
        async with self.db_manager.get_session() as session:
            # 检查是否已有用户
            result = await session.execute(text("SELECT COUNT(*) as count FROM sys_user"))
            user_count = result.fetchone()[0]
            
            if user_count == 0:
                logger.info("创建默认管理员用户...")
                
                # 插入默认角色
                await session.execute(
                    text("""
                        INSERT INTO sys_role (role_code, role_name, role_description, is_system, created_by)
                        VALUES ('admin', '系统管理员', '拥有系统所有权限', 1, 1)
                    """)
                )
                
                await session.execute(
                    text("""
                        INSERT INTO sys_role (role_code, role_name, role_description, is_system, created_by)
                        VALUES ('user', '普通用户', '基础查询权限', 1, 1)
                    """)
                )
                
                # 插入默认用户
                await session.execute(
                    text("""
                        INSERT INTO sys_user (username, nickname, password_hash, is_active, created_by)
                        VALUES ('admin', '系统管理员', 'temp_password_hash', 1, 1)
                    """)
                )
                
                # 分配角色
                await session.execute(
                    text("""
                        INSERT INTO sys_user_role (user_id, role_id, created_by)
                        VALUES (1, 1, 1)
                    """)
                )
                
                await session.commit()
                logger.info("默认用户创建完成")
    
    async def _insert_sample_themes(self):
        """插入示例数据主题"""
        themes = [
            {
                'theme_name': '公共数据',
                'theme_description': '所有用户都可以访问的公共数据',
                'is_public': True
            },
            {
                'theme_name': '业务数据',
                'theme_description': '核心业务数据，需要相应权限才能访问',
                'is_public': False
            }
        ]
        
        async with self.db_manager.get_session() as session:
            for theme in themes:
                # 检查主题是否已存在
                result = await session.execute(
                    text("SELECT id FROM metadata_data_theme WHERE theme_name = :name"),
                    {"name": theme['theme_name']}
                )
                if not result.fetchone():
                    await session.execute(
                        text("""
                            INSERT INTO metadata_data_theme 
                            (theme_name, theme_description, is_public, created_by)
                            VALUES (:name, :description, :is_public, 1)
                        """),
                        {
                            "name": theme['theme_name'],
                            "description": theme['theme_description'],
                            "is_public": theme['is_public']
                        }
                    )
            
            await session.commit()
        
        logger.info("示例数据主题插入完成")


async def main():
    """主函数：执行数据库初始化"""
    initializer = DatabaseInitializer()
    await initializer.initialize_database()


if __name__ == "__main__":
    asyncio.run(main())