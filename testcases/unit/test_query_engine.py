"""
查询引擎服务单元测试

测试DuckDB和查询引擎工厂的功能
"""

import pytest
import pandas as pd
import duckdb
from unittest.mock import Mock, patch

from services.query_engine.duckdb_service import DuckDBService
from services.query_engine.base import QueryEngineFactory


class TestDuckDBService:
    """DuckDB服务测试"""

    def test_duckdb_service_init(self, temp_duckdb):
        """测试DuckDB服务初始化"""
        service = DuckDBService(temp_duckdb)

        assert service.db_path == temp_duckdb
        assert service.conn is not None
        assert isinstance(service.conn, duckdb.DuckDBPyConnection)

    def test_duckdb_service_init_with_default_path(self, mock_settings):
        """测试使用默认路径初始化"""
        with patch('services.query_engine.duckdb_service.settings.duckdb_path', ':memory:'):
            service = DuckDBService()
            assert service.db_path == ':memory:'
            assert service.conn is not None

    def test_duckdb_service_connection_error(self):
        """测试连接错误处理"""
        with patch('duckdb.connect', side_effect=Exception("连接失败")):
            with pytest.raises(Exception, match="连接失败"):
                DuckDBService()

    def test_execute_query_success(self, temp_duckdb):
        """测试成功执行SQL查询"""
        service = DuckDBService(temp_duckdb)

        # 测试SELECT查询
        result = service.execute_query("SELECT 1 as test_col")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['test_col'] == 1

        # 测试查询表数据
        result = service.execute_query("SELECT * FROM users")
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1
        assert 'name' in result.columns

    def test_execute_query_empty_result(self, temp_duckdb):
        """测试查询返回空结果"""
        service = DuckDBService(temp_duckdb)
        result = service.execute_query("SELECT * FROM users WHERE id = -1")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_execute_query_syntax_error(self, temp_duckdb):
        """测试SQL语法错误"""
        service = DuckDBService(temp_duckdb)

        with pytest.raises(Exception):  # DuckDB会抛出ParserError
            service.execute_query("INVALID SQL SYNTAX")

    def test_execute_query_table_not_found(self, temp_duckdb):
        """测试表不存在错误"""
        service = DuckDBService(temp_duckdb)

        with pytest.raises(Exception):  # DuckDB会抛出CatalogError
            service.execute_query("SELECT * FROM non_existent_table")

    def test_get_tables_success(self, temp_duckdb):
        """测试获取表列表"""
        service = DuckDBService(temp_duckdb)

        tables = service.get_tables()
        assert isinstance(tables, list)
        assert len(tables) >= 3  # 应该至少有users, orders, products表
        assert 'users' in tables
        assert 'orders' in tables
        assert 'products' in tables

    def test_get_tables_empty_database(self):
        """测试空数据库的表列表"""
        service = DuckDBService(':memory:')
        tables = service.get_tables()
        assert isinstance(tables, list)
        assert len(tables) == 0

    def test_get_table_schema_success(self, temp_duckdb):
        """测试获取表结构"""
        service = DuckDBService(temp_duckdb)

        schema = service.get_table_schema('users')
        assert isinstance(schema, dict)
        assert schema['table_name'] == 'users'
        assert 'row_count' in schema
        assert 'columns' in schema

        # 检查列信息
        columns = schema['columns']
        assert len(columns) >= 3  # id, name, email列
        column_names = [col['name'] for col in columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'email' in column_names

    def test_get_table_schema_not_found(self, temp_duckdb):
        """测试获取不存在表的结构"""
        service = DuckDBService(temp_duckdb)

        schema = service.get_table_schema('non_existent_table')
        assert 'error' in schema
        assert isinstance(schema['error'], str)

    def test_close_connection(self, temp_duckdb):
        """测试关闭连接"""
        service = DuckDBService(temp_duckdb)

        # 连接应该是打开的
        assert service.conn is not None

        # 关闭连接
        service.close()

        # 验证连接已关闭（DuckDB没有直接的连接状态检查，所以只能检查对象）
        assert service.conn.closed is True

    def test_close_connection_when_already_closed(self, temp_duckdb):
        """测试重复关闭连接"""
        service = DuckDBService(temp_duckdb)

        service.close()
        # 再次关闭不应该出错
        service.close()  # 不应该抛出异常

    def test_complex_query(self, temp_duckdb):
        """测试复杂查询"""
        service = DuckDBService(temp_duckdb)

        # 测试JOIN查询
        result = service.execute_query("""
            SELECT u.name, o.amount
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.age > 20
            ORDER BY o.amount DESC
        """)

        assert isinstance(result, pd.DataFrame)
        if len(result) > 0:
            assert 'name' in result.columns
            assert 'amount' in result.columns

    def test_aggregate_query(self, temp_duckdb):
        """测试聚合查询"""
        service = DuckDBService(temp_duckdb)

        # 测试聚合函数
        result = service.execute_query("""
            SELECT
                COUNT(*) as total_count,
                AVG(age) as avg_age,
                MAX(age) as max_age
            FROM users
        """)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'total_count' in result.columns
        assert 'avg_age' in result.columns
        assert 'max_age' in result.columns

    def test_insert_and_query(self, temp_duckdb):
        """测试插入和查询"""
        service = DuckDBService(temp_duckdb)

        # 创建临时表
        service.execute_query("""
            CREATE TEMPORARY TABLE test_insert (
                id INTEGER,
                name VARCHAR,
                value DECIMAL
            )
        """)

        # 插入数据
        service.execute_query("""
            INSERT INTO test_insert VALUES
                (1, 'test1', 10.5),
                (2, 'test2', 20.3)
        """)

        # 查询数据
        result = service.execute_query("SELECT * FROM test_insert ORDER BY id")
        assert len(result) == 2
        assert result.iloc[0]['name'] == 'test1'
        assert result.iloc[1]['value'] == 20.3


class TestQueryEngineFactory:
    """查询引擎工厂测试"""

    def test_create_duckdb_service(self, temp_duckdb):
        """测试创建DuckDB服务"""
        service = QueryEngineFactory.create_service("duckdb", db_path=temp_duckdb)

        assert isinstance(service, DuckDBService)
        assert service.db_path == temp_duckdb
        assert service.conn is not None

    def test_create_duckdb_service_default(self):
        """测试创建默认DuckDB服务"""
        with patch('services.query_engine.base.settings.duckdb_path', ':memory:'):
            service = QueryEngineFactory.create_service("duckdb")
            assert isinstance(service, DuckDBService)

    def test_create_duckdb_service_with_kwargs(self):
        """测试创建DuckDB服务时传递参数"""
        with patch('services.query_engine.base.settings.duckdb_path', ':memory:'):
            service = QueryEngineFactory.create_service(
                "duckdb",
                db_path=":memory:"
            )
            assert isinstance(service, DuckDBService)

    def test_create_unsupported_service(self):
        """测试创建不支持的查询引擎"""
        with pytest.raises(ValueError, match="不支持的查询引擎服务类型"):
            QueryEngineFactory.create_service("unsupported_db")

    def test_create_service_case_insensitive(self, temp_duckdb):
        """测试服务类型大小写不敏感"""
        service1 = QueryEngineFactory.create_service("DuckDB", db_path=temp_duckdb)
        service2 = QueryEngineFactory.create_service("duckdb", db_path=temp_duckdb)

        assert isinstance(service1, DuckDBService)
        assert isinstance(service2, DuckDBService)

    def test_create_spark_service(self):
        """测试创建Spark服务（仅验证接口，不实际导入）"""
        # 注意：这需要实际的Spark实现才能工作
        # 目前只是测试工厂是否会尝试创建Spark服务
        try:
            # 如果Spark模块不存在，会抛出ImportError
            service = QueryEngineFactory.create_service("spark")
            assert hasattr(service, 'execute_query')
        except ImportError:
            # 如果没有Spark实现，这是正常的
            pytest.skip("Spark SQL服务未实现")


class TestQueryEngineIntegration:
    """查询引擎集成测试"""

    def test_multiple_queries_same_service(self, temp_duckdb):
        """测试在同一服务实例上执行多个查询"""
        service = DuckDBService(temp_duckdb)

        # 执行多个查询
        result1 = service.execute_query("SELECT COUNT(*) as count FROM users")
        result2 = service.execute_query("SELECT * FROM orders")
        result3 = service.execute_query("SELECT name, email FROM users WHERE age > 20")

        assert isinstance(result1, pd.DataFrame)
        assert isinstance(result2, pd.DataFrame)
        assert isinstance(result3, pd.DataFrame)

        # 验证每个查询都成功执行
        assert len(result1) == 1
        assert 'count' in result1.columns

    def test_database_connection_persistence(self, temp_duckdb):
        """测试数据库连接的持久性"""
        service1 = DuckDBService(temp_duckdb)
        service2 = DuckDBService(temp_duckdb)

        # 两个服务实例应该能访问同一个数据库
        tables1 = service1.get_tables()
        tables2 = service2.get_tables()

        assert set(tables1) == set(tables2)

    def test_concurrent_access(self, temp_duckdb):
        """测试并发访问（简单的顺序测试）"""
        service = DuckDBService(temp_duckdb)

        # 模拟多个查询快速执行
        queries = [
            "SELECT * FROM users",
            "SELECT * FROM orders",
            "SELECT * FROM products",
            "SELECT COUNT(*) FROM users",
            "SELECT MAX(amount) FROM orders"
        ]

        results = []
        for query in queries:
            result = service.execute_query(query)
            results.append(result)

        # 验证所有查询都成功
        assert len(results) == len(queries)
        for result in results:
            assert isinstance(result, pd.DataFrame)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
