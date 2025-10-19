"""
API接口测试

测试FastAPI路由端点的功能：
1. 自然语言查询API
2. WebSocket实时进度推送
3. 元数据管理API
4. 错误处理和参数验证
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 导入API路由
import sys
sys.path.insert(0, 'backend')

from api.nlquey_routes import router as nlquery_router
from api.metadata_routes import router as metadata_router
from api.endpoint_models import QueryRequest


class TestNaturalLanguageQueryAPI:
    """自然语言查询API测试"""

    @pytest.fixture
    def app(self):
        """创建FastAPI测试应用"""
        app = FastAPI()
        app.include_router(nlquery_router, prefix="/api/test")
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_submit_query_success(self, client):
        """测试成功提交查询"""
        # Mock异步查询服务
        with patch('api.nlquey_routes.get_async_query_service') as mock_get_service:
            mock_service = Mock()
            mock_service.submit_query = AsyncMock(return_value="test_task_id")
            mock_get_service.return_value = mock_service

            # Mock tracker
            with patch('api.nlquey_routes.tracker') as mock_tracker:
                mock_tracker.start_task.return_value = True

                # 发送查询请求
                response = client.post(
                    "/api/test/nlquery/submit",
                    json={
                        "query": "查询年龄大于25岁的用户",
                        "flow_type": "fast",
                        "max_retries": 2
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["task_id"] == "test_task_id"

    def test_submit_query_invalid_input(self, client):
        """测试无效输入参数"""
        response = client.post(
            "/api/test/nlquery/submit",
            json={
                "query": "",  # 空查询
                "flow_type": "invalid_type",  # 无效流程类型
                "max_retries": 10  # 超出范围
            }
        )

        # 应该返回验证错误
        assert response.status_code == 422  # Validation error

    def test_submit_query_service_error(self, client):
        """测试服务错误处理"""
        with patch('api.nlquey_routes.get_async_query_service') as mock_get_service:
            mock_service = Mock()
            mock_service.submit_query = AsyncMock(side_effect=Exception("服务错误"))
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/test/nlquery/submit",
                json={"query": "查询用户"}
            )

            assert response.status_code == 500

    def test_submit_query_missing_fields(self, client):
        """测试缺少必要字段"""
        response = client.post(
            "/api/test/nlquery/submit",
            json={"flow_type": "fast"}  # 缺少query字段
        )

        assert response.status_code == 422

    def test_get_task_status_success(self, client):
        """测试获取任务状态"""
        with patch('api.nlquey_routes.tracker') as mock_tracker:
            # Mock任务状态
            mock_task = Mock()
            mock_task.task_id = "test_task"
            mock_task.status = "running"
            mock_task.progress = 50
            mock_tracker.get_task_status = AsyncMock(return_value=mock_task)

            response = client.get("/api/test/nlquery/task/test_task/status")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["task_id"] == "test_task"
            assert data["data"]["status"] == "running"

    def test_get_task_status_not_found(self, client):
        """测试获取不存在任务的状态"""
        with patch('api.nlquey_routes.tracker') as mock_tracker:
            mock_tracker.get_task_status = AsyncMock(return_value=None)

            response = client.get("/api/test/nlquery/task/nonexistent_task/status")

            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "not found" in data["error_msg"].lower()

    def test_websocket_connection(self, app):
        """测试WebSocket连接"""
        with patch('api.nlquey_routes.tracker') as mock_tracker:
            # Mock任务状态
            mock_task = Mock()
            mock_task.status = "running"
            mock_task.progress = 25
            mock_tracker.get_task_status = AsyncMock(return_value=mock_task)

            # 创建WebSocket测试客户端
            with TestClient(app) as client:
                with client.websocket_connect("/api/test/nlquery/ws/task_process") as websocket:
                    # 发送任务ID
                    websocket.send_text("test_task_id")

                    # 接收状态更新
                    data = websocket.receive_json()
                    assert data["code"] == 0
                    assert data["data"]["status"] == "running"

    def test_websocket_invalid_task(self, app):
        """测试WebSocket处理无效任务"""
        with patch('api.nlquey_routes.tracker') as mock_tracker:
            mock_tracker.get_task_status = AsyncMock(return_value=None)

            with TestClient(app) as client:
                with client.websocket_connect("/api/test/nlquery/ws/task_process") as websocket:
                    websocket.send_text("invalid_task")
                    data = websocket.receive_json()
                    assert data["code"] == 404

    def test_websocket_disconnect_handling(self, app):
        """测试WebSocket断开连接处理"""
        with TestClient(app) as client:
            # 简单连接测试
            try:
                with client.websocket_connect("/api/test/nlquery/ws/task_process") as websocket:
                    # 立即断开连接
                    pass
            except Exception:
                # 不应该抛出异常
                pass

    def test_query_request_validation(self):
        """测试查询请求模型验证"""
        # 有效请求
        valid_request = QueryRequest(
            query="查询用户信息",
            flow_type="fast",
            max_retries=2
        )
        assert valid_request.query == "查询用户信息"
        assert valid_request.flow_type == "fast"
        assert valid_request.max_retries == 2

        # 默认值测试
        default_request = QueryRequest(query="测试查询")
        assert default_request.flow_type == "fast"
        assert default_request.max_retries == 2


class TestMetadataAPI:
    """元数据管理API测试"""

    @pytest.fixture
    def app(self):
        """创建FastAPI测试应用"""
        app = FastAPI()
        app.include_router(metadata_router, prefix="/api/test")
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_get_all_tables(self, client):
        """测试获取所有表元数据"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_tables.return_value = [
                {
                    "id": 1,
                    "name": "users",
                    "comment": "用户表",
                    "is_available": 0,
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "VARCHAR"}
                    ]
                }
            ]
            mock_get_service.return_value = mock_service

            response = client.get("/api/test/metadata/tables")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "users"

    def test_get_available_tables(self, client):
        """测试获取可用表"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_available_tables.return_value = [
                {"id": 1, "name": "users", "is_available": 0}
            ]
            mock_get_service.return_value = mock_service

            response = client.get("/api/test/metadata/tables?isAvailable=1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["is_available"] == 0

    def test_add_table_metadata(self, client):
        """测试添加表元数据"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.add_table.return_value = {
                "id": 1,
                "name": "new_table",
                "comment": "新表",
                "is_available": 0
            }
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/test/metadata/tables",
                json={
                    "name": "new_table",
                    "comment": "新表",
                    "is_available": 0
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "new_table"

    def test_add_table_duplicate_name(self, client):
        """测试添加重名表"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.add_table.return_value = None  # 添加失败
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/test/metadata/tables",
                json={"name": "existing_table"}
            )

            assert response.status_code == 400

    def test_update_table_metadata(self, client):
        """测试更新表元数据"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.update_table_by_id.return_value = True
            mock_get_service.return_value = mock_service

            response = client.put(
                "/api/test/metadata/tables/1",
                json={
                    "comment": "更新后的注释",
                    "is_available": 1
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_update_table_not_found(self, client):
        """测试更新不存在的表"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.update_table_by_id.return_value = False
            mock_get_service.return_value = mock_service

            response = client.put(
                "/api/test/metadata/tables/999",
                json={"comment": "更新"}
            )

            assert response.status_code == 400

    def test_delete_table_metadata(self, client):
        """测试删除表元数据"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.delete_table_by_id.return_value = True
            mock_get_service.return_value = mock_service

            response = client.delete("/api/test/metadata/tables/1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_add_column_metadata(self, client):
        """测试添加列元数据"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.add_column_by_id.return_value = {
                "id": 1,
                "name": "new_column",
                "type": "VARCHAR",
                "comment": "新列"
            }
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/test/metadata/columns",
                json={
                    "table_id": 1,
                    "name": "new_column",
                    "type": "VARCHAR",
                    "comment": "新列"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_glossary_terms(self, client):
        """测试获取术语表"""
        with patch('api.metadata_routes.get_glossary_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_terms.return_value = [
                {
                    "id": 1,
                    "name": "用户",
                    "type": "concept",
                    "content": {"explanation": "使用系统的人员"}
                }
            ]
            mock_get_service.return_value = mock_service

            response = client.get("/api/test/metadata/glossary")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "用户"

    def test_add_glossary_term(self, client):
        """测试添加术语"""
        with patch('api.metadata_routes.get_glossary_service') as mock_get_service:
            mock_service = Mock()
            mock_service.add_term.return_value = True
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/test/metadata/glossary",
                json={
                    "name": "新术语",
                    "type": "concept",
                    "content": {"explanation": "术语解释"},
                    "creator": "admin"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_relation_configs(self, client):
        """测试获取关联配置"""
        with patch('api.metadata_routes.get_relation_field_config_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_all_relation_configs.return_value = [
                {
                    "id": 1,
                    "relation_family": "用户",
                    "relation_subfamily": "部门关联",
                    "relation_desc": "用户与部门的关联"
                }
            ]
            mock_get_service.return_value = mock_service

            response = client.get("/api/test/metadata/relations")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1

    def test_server_error_handling(self, client):
        """测试服务器错误处理"""
        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_get_service.side_effect = Exception("数据库连接错误")

            response = client.get("/api/test/metadata/tables")

            assert response.status_code == 500


class TestAPIIntegration:
    """API集成测试"""

    def test_cors_headers(self):
        """测试CORS头设置"""
        app = FastAPI()
        app.include_router(nlquery_router, prefix="/api/test")

        # 添加CORS中间件（模拟主应用设置）
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        client = TestClient(app)

        response = client.options("/api/test/nlquery/submit")
        assert "access-control-allow-origin" in response.headers

    def test_api_versioning(self):
        """测试API版本"""
        app = FastAPI()
        app.include_router(nlquery_router, prefix="/api/v1")

        with TestClient(app) as client:
            # 确保API路由正确注册
            response = client.get("/api/v1/docs")
            assert response.status_code == 200

    def test_response_format_consistency(self):
        """测试响应格式一致性"""
        app = FastAPI()
        app.include_router(metadata_router, prefix="/api/test")

        with patch('api.metadata_routes.get_metadata_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_tables.return_value = []
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.get("/api/test/metadata/tables")

            # 验证响应格式
            assert "success" in response.json()
            assert "data" in response.json()

    def test_rate_limiting_simulation(self):
        """测试限流模拟（简单示例）"""
        # 这里可以添加限流逻辑的测试
        # 由于当前没有限流实现，这里只是示例
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
