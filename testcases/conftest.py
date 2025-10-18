"""
pytest全局配置和fixtures
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import duckdb

# 添加后端路径到Python路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from models.db_base import Base
from utils.logger import logger


# ============== 数据库Fixtures ==============

@pytest.fixture(scope="session")
def temp_duckdb():
    """创建临时DuckDB数据库"""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
        db_path = f.name

    # 创建测试数据
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER,
            name VARCHAR,
            email VARCHAR,
            age INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER,
            user_id INTEGER,
            amount DECIMAL(10, 2),
            order_date DATE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER,
            name VARCHAR,
            category VARCHAR,
            price DECIMAL(10, 2)
        )
    """)

    # 插入样本数据
    conn.execute("INSERT INTO users VALUES (1, '张三', 'zhangsan@example.com', 25)")
    conn.execute("INSERT INTO users VALUES (2, '李四', 'lisi@example.com', 30)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 100.00, '2024-01-01')")
    conn.execute("INSERT INTO orders VALUES (2, 2, 200.00, '2024-01-02')")
    conn.execute("INSERT INTO products VALUES (1, '产品A', '类别1', 99.99)")
    conn.execute("INSERT INTO products VALUES (2, '产品B', '类别2', 199.99)")
    conn.commit()
    conn.close()

    yield db_path

    # 清理
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="function")
def test_db():
    """创建临时SQLite元数据数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 创建引擎和会话
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    # 清理
    session.close()
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def db_session(test_db):
    """提供数据库会话fixture"""
    return test_db


# ============== Mock Fixtures ==============

@pytest.fixture
def mock_openai_api():
    """Mock OpenAI API"""
    with patch('services.nlquery_service.nl2sql_service.OpenAI') as mock:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="SELECT * FROM users;"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def mock_embedding_service():
    """Mock Embedding服务"""
    with patch('services.vanna_service.local_embedding_service.LocalEmbeddingService') as mock:
        mock_instance = Mock()
        mock_instance.embed.return_value = [0.1] * 768  # 模拟768维向量
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_vanna_service():
    """Mock Vanna服务"""
    with patch('services.vanna_service.taosha_vanna_service.TaoshaVannaService') as mock:
        mock_instance = Mock()
        mock_instance.generate_sql.return_value = "SELECT * FROM users WHERE id = 1;"
        mock_instance.train.return_value = True
        mock.return_value = mock_instance
        yield mock


# ============== 配置和环境Fixtures ==============

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """设置测试环境"""
    # 设置日志级别
    os.environ["TAOSHA_LOG_LEVEL"] = "INFO"
    logger.info("测试环境初始化完成")
    yield
    logger.info("测试环境清理完成")


@pytest.fixture
def mock_settings():
    """Mock设置对象"""
    with patch('utils.config.settings') as mock:
        mock.app_name = "Taosha Test Platform"
        mock.app_version = "0.1.0"
        mock.debug = True
        mock.duckdb_path = ":memory:"
        mock.database_dir = Path(tempfile.gettempdir())
        mock.chromadb_path = str(Path(tempfile.gettempdir()) / "chromadb_test")
        mock.log_level = "INFO"
        mock.taosha_db_type = "sqlite"
        yield mock


# ============== 标记Hooks ==============

def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "requires_db: 需要数据库的测试")


# ============== 测试输出Hooks ==============

def pytest_runtest_logreport(report):
    """自定义测试报告"""
    if report.when == "call":
        if report.outcome == "failed":
            logger.error(f"测试失败: {report.nodeid}")
        elif report.outcome == "passed":
            logger.debug(f"测试通过: {report.nodeid}")
