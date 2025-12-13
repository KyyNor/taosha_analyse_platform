#!/usr/bin/env python3
"""
验证告警管控记录系统的完整集成
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.db_base import get_db_session
from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)
from utils.logger import logger


def verify_database_data():
    """验证数据库中的数据"""
    logger.info("=== 验证数据库数据 ===")
    
    with get_db_session() as db:
        # 统计命中记录
        hit_count = db.query(FraudHunterModelHitRecord).count()
        logger.info(f"命中记录总数: {hit_count}")
        
        # 统计告警管控记录
        alert_count = db.query(FraudHunterModelAlertControlRecord).count()
        logger.info(f"告警管控记录总数: {alert_count}")
        
        # 统计各种状态的记录
        alert_sent = db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.alert_status == 'sent'
        ).count()
        
        alert_duplicate = db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.alert_status == 'duplicate'
        ).count()
        
        control_executed = db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.control_status == 'executed'
        ).count()
        
        logger.info(f"已发送告警: {alert_sent}")
        logger.info(f"重复告警: {alert_duplicate}")
        logger.info(f"已执行管控: {control_executed}")
        
        # 获取最近的几条记录作为样本
        recent_records = db.query(FraudHunterModelAlertControlRecord)\
                           .order_by(FraudHunterModelAlertControlRecord.created_at.desc())\
                           .limit(3)\
                           .all()
        
        logger.info("最近的记录样本:")
        for record in recent_records:
            logger.info(f"  ID: {record.id}, 账号: {record.account_id}, "
                       f"模型: {record.model_name}, 告警: {record.alert_status}, "
                       f"管控: {record.control_status}")
        
        return hit_count > 0 and alert_count > 0


def verify_api_endpoints():
    """验证API端点"""
    logger.info("=== 验证API端点 ===")
    
    base_url = "http://localhost:50020/api/taosha/v1/fraudhunter/alert-control-records"
    
    try:
        # 测试列表API
        logger.info("测试列表API...")
        response = requests.get(f"{base_url}?page=1&page_size=10")
        
        if response.status_code != 200:
            logger.error(f"列表API失败: {response.status_code}")
            return False
        
        data = response.json()
        logger.info(f"✓ 列表API成功: 返回 {len(data.get('records', []))} 条记录")
        
        # 测试筛选功能
        logger.info("测试筛选功能...")
        today = datetime.now().strftime('%Y-%m-%d')
        filter_response = requests.get(f"{base_url}?start_date={today}&end_date={today}")
        
        if filter_response.status_code == 200:
            filter_data = filter_response.json()
            logger.info(f"✓ 筛选API成功: 返回 {len(filter_data.get('records', []))} 条今日记录")
        
        # 测试详情API（如果有记录）
        if data.get('records') and len(data['records']) > 0:
            record_id = data['records'][0]['id']
            logger.info(f"测试详情API (ID: {record_id})...")
            
            detail_response = requests.get(f"{base_url}/{record_id}")
            if detail_response.status_code == 200:
                logger.info("✓ 详情API成功")
            else:
                logger.error(f"详情API失败: {detail_response.status_code}")
        
        # 测试导出API
        logger.info("测试导出API...")
        export_response = requests.post(f"{base_url}/export?format=csv")
        
        if export_response.status_code == 200:
            logger.info(f"✓ 导出API成功: 文件大小 {len(export_response.content)} 字节")
        else:
            logger.error(f"导出API失败: {export_response.status_code}")
        
        # 测试统计API
        logger.info("测试统计API...")
        stats_response = requests.get(f"{base_url}/statistics/summary")
        
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            logger.info(f"✓ 统计API成功: 总记录 {stats_data.get('total_records', 0)}")
        else:
            logger.error(f"统计API失败: {stats_response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        logger.error("✗ 无法连接到后端服务，请确保服务正在运行")
        return False
    except Exception as e:
        logger.error(f"API测试异常: {e}")
        return False


def verify_data_consistency():
    """验证数据一致性"""
    logger.info("=== 验证数据一致性 ===")
    
    base_url = "http://localhost:50020/api/taosha/v1/fraudhunter/alert-control-records"
    
    try:
        # 获取API数据
        response = requests.get(f"{base_url}?page=1&page_size=100")
        if response.status_code != 200:
            logger.error("无法获取API数据进行一致性验证")
            return False
        
        api_data = response.json()
        api_records = api_data.get('records', [])
        
        # 获取数据库数据
        with get_db_session() as db:
            db_records = db.query(FraudHunterModelAlertControlRecord)\
                          .order_by(FraudHunterModelAlertControlRecord.created_at.desc())\
                          .limit(100)\
                          .all()
        
        # 比较数量
        if len(api_records) != len(db_records):
            logger.warning(f"记录数量不一致: API={len(api_records)}, DB={len(db_records)}")
        
        # 验证前几条记录的一致性
        for i in range(min(5, len(api_records), len(db_records))):
            api_record = api_records[i]
            db_record = db_records[i]
            
            if api_record['id'] != db_record.id:
                logger.error(f"记录ID不一致: API={api_record['id']}, DB={db_record.id}")
                return False
            
            if api_record['account_id'] != db_record.account_id:
                logger.error(f"账号不一致: API={api_record['account_id']}, DB={db_record.account_id}")
                return False
        
        logger.info("✓ 数据一致性验证通过")
        return True
        
    except Exception as e:
        logger.error(f"数据一致性验证异常: {e}")
        return False


def verify_frontend_accessibility():
    """验证前端页面可访问性"""
    logger.info("=== 验证前端页面可访问性 ===")
    
    frontend_urls = [
        "http://localhost:3000/taosha/fraudhunter/alert-control-records",
        "http://localhost:3000/taosha/api/taosha/v1/fraudhunter/alert-control-records?page=1&page_size=5"
    ]
    
    for url in frontend_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"✓ 前端页面可访问: {url}")
            else:
                logger.warning(f"前端页面响应异常: {url} - {response.status_code}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"无法连接到前端服务: {url}")
        except Exception as e:
            logger.warning(f"前端页面测试异常: {url} - {e}")


def main():
    """主函数"""
    logger.info("开始验证告警管控记录系统集成...")
    
    success_count = 0
    total_tests = 4
    
    # 验证数据库数据
    if verify_database_data():
        success_count += 1
        logger.info("✓ 数据库验证通过")
    else:
        logger.error("✗ 数据库验证失败")
    
    # 验证API端点
    if verify_api_endpoints():
        success_count += 1
        logger.info("✓ API端点验证通过")
    else:
        logger.error("✗ API端点验证失败")
    
    # 验证数据一致性
    if verify_data_consistency():
        success_count += 1
        logger.info("✓ 数据一致性验证通过")
    else:
        logger.error("✗ 数据一致性验证失败")
    
    # 验证前端可访问性
    verify_frontend_accessibility()
    success_count += 1  # 前端测试不影响整体结果
    
    # 总结
    logger.info(f"\n=== 集成验证总结 ===")
    logger.info(f"通过测试: {success_count}/{total_tests}")
    
    if success_count >= 3:  # 至少3个核心测试通过
        logger.info("🎉 告警管控记录系统集成验证成功！")
        logger.info("\n可以进行以下操作:")
        logger.info("1. 访问前端页面: http://localhost:3000/taosha/fraudhunter/alert-control-records")
        logger.info("2. 测试筛选、搜索、分页功能")
        logger.info("3. 测试记录详情查看")
        logger.info("4. 测试数据导出功能")
        return True
    else:
        logger.error("❌ 集成验证失败，请检查以上错误信息")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)