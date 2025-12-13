"""
告警管控记录API路由测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date

from main import app
from models.db_base import get_db, Base
from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_alert_control.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# 创建测试表
Base.metadata.create_all(bind=engine)

client = TestClient(app)


class TestAlertControlRecordRoutes:
    """告警管控记录API路由测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 清理测试数据
        db = TestingSessionLocal()
        try:
            db.query(FraudHunterModelAlertControlRecord).delete()
            db.query(FraudHunterModelHitRecord).delete()
            db.commit()
        finally:
            db.close()

    def create_test_data(self):
        """创建测试数据"""
        db = TestingSessionLocal()
        try:
            # 创建命中记录
            hit_record = FraudHunterModelHitRecord(
                account_id="test_account_001",
                hit_time=datetime(2024, 12, 12, 10, 30, 0),
                hit_model_ids=[1, 2],
                hit_model_names=["测试模型A", "测试模型B"],
                indicator_data={"score": 85, "risk_level": "high"}
            )
            db.add(hit_record)
            db.flush()

            # 创建告警管控记录
            alert_record = FraudHunterModelAlertControlRecord(
                hit_record_id=hit_record.id,
                account_id="test_account_001",
                record_date=date(2024, 12, 12),
                model_id=1,
                model_name="测试模型A",
                alert_status="sent",
                alert_message="账户 test_account_001 在 2024-12-12 10:30:00，因命中测试模型A模型，触发告警",
                alert_person="system",
                alert_time=datetime(2024, 12, 12, 10, 30, 5),
                control_status="not_configured"
            )
            db.add(alert_record)
            db.commit()
            
            return hit_record.id, alert_record.id
        finally:
            db.close()

    def test_list_alert_control_records_empty(self):
        """测试获取空的告警管控记录列表"""
        response = client.get("/api/fraudhunter/alert-control-records")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["records"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_alert_control_records_with_data(self):
        """测试获取有数据的告警管控记录列表"""
        # 创建测试数据
        hit_record_id, alert_record_id = self.create_test_data()
        
        response = client.get("/api/fraudhunter/alert-control-records")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["records"]) == 1
        
        record = data["records"][0]
        assert record["account_id"] == "test_account_001"
        assert record["model_name"] == "测试模型A"
        assert record["alert_status"] == "sent"

    def test_list_alert_control_records_with_filters(self):
        """测试带筛选条件的告警管控记录列表"""
        # 创建测试数据
        self.create_test_data()
        
        # 测试账号筛选
        response = client.get("/api/fraudhunter/alert-control-records?account_id=test_account_001")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        
        # 测试不存在的账号
        response = client.get("/api/fraudhunter/alert-control-records?account_id=nonexistent")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        
        # 测试日期筛选
        response = client.get("/api/fraudhunter/alert-control-records?start_date=2024-12-12&end_date=2024-12-12")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_get_alert_control_record_detail(self):
        """测试获取告警管控记录详情"""
        # 创建测试数据
        hit_record_id, alert_record_id = self.create_test_data()
        
        response = client.get(f"/api/fraudhunter/alert-control-records/{alert_record_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查记录信息
        assert data["record"]["account_id"] == "test_account_001"
        assert data["record"]["model_name"] == "测试模型A"
        
        # 检查关联的命中记录
        assert data["hit_record"]["account_id"] == "test_account_001"
        assert data["hit_record"]["indicator_data"]["score"] == 85

    def test_get_alert_control_record_detail_not_found(self):
        """测试获取不存在的告警管控记录详情"""
        response = client.get("/api/fraudhunter/alert-control-records/999999")
        
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    def test_export_alert_control_records_csv(self):
        """测试导出CSV格式的告警管控记录"""
        # 创建测试数据
        self.create_test_data()
        
        response = client.post("/api/fraudhunter/alert-control-records/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        # 检查CSV内容
        content = response.content.decode('utf-8-sig')
        assert "test_account_001" in content
        assert "测试模型A" in content

    def test_export_alert_control_records_excel(self):
        """测试导出Excel格式的告警管控记录"""
        # 创建测试数据
        self.create_test_data()
        
        response = client.post("/api/fraudhunter/alert-control-records/export?format=excel")
        
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert len(response.content) > 0

    def test_export_alert_control_records_invalid_format(self):
        """测试导出无效格式"""
        response = client.post("/api/fraudhunter/alert-control-records/export?format=pdf")
        
        assert response.status_code == 400
        assert "不支持的导出格式" in response.json()["detail"]

    def test_get_alert_control_statistics(self):
        """测试获取告警管控统计"""
        # 创建测试数据
        self.create_test_data()
        
        response = client.get("/api/fraudhunter/alert-control-records/statistics/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_records" in data
        assert "alert_statistics" in data
        assert "control_statistics" in data
        assert data["alert_statistics"]["sent_alerts"] == 1
        assert data["control_statistics"]["executed_controls"] == 0

    def test_pagination(self):
        """测试分页功能"""
        # 创建多条测试数据
        db = TestingSessionLocal()
        try:
            for i in range(25):
                hit_record = FraudHunterModelHitRecord(
                    account_id=f"test_account_{i:03d}",
                    hit_time=datetime(2024, 12, 12, 10, 30, i),
                    hit_model_ids=[1],
                    hit_model_names=["测试模型"],
                    indicator_data={"score": 50 + i}
                )
                db.add(hit_record)
                db.flush()

                alert_record = FraudHunterModelAlertControlRecord(
                    hit_record_id=hit_record.id,
                    account_id=f"test_account_{i:03d}",
                    record_date=date(2024, 12, 12),
                    model_id=1,
                    model_name="测试模型",
                    alert_status="sent",
                    control_status="not_configured"
                )
                db.add(alert_record)
            
            db.commit()
        finally:
            db.close()
        
        # 测试第一页
        response = client.get("/api/fraudhunter/alert-control-records?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["records"]) == 10
        assert data["page"] == 1
        assert data["total_pages"] == 3
        
        # 测试第二页
        response = client.get("/api/fraudhunter/alert-control-records?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 10
        assert data["page"] == 2
        
        # 测试最后一页
        response = client.get("/api/fraudhunter/alert-control-records?page=3&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 5
        assert data["page"] == 3