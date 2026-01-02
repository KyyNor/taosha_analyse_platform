#!/usr/bin/env python3
"""
Token权限管理系统集成测试脚本

测试系统的核心功能：
1. 数据库连接和表创建
2. JWT token生成和验证
3. 权限验证流程
4. API接口基本功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import logger
from models.db_base import create_tables, get_db_session
from services.token_service import TokenService, UserInfo
from services.permission_service import PermissionService, LoginRecordService, EntityService
from services.page_discovery_service import PageDiscoveryService
from sqlalchemy import text


async def test_database_connection():
    """测试数据库连接和表创建"""
    logger.info("=== 测试数据库连接和表创建 ===")
    
    try:
        # 创建数据库表
        create_tables()
        logger.info("✅ 数据库表创建成功")
        
        # 测试数据库连接
        with get_db_session() as db:
            # 简单查询测试
            result = db.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                logger.info("✅ 数据库连接测试成功")
                return True
            else:
                logger.error("❌ 数据库连接测试失败")
                return False
                
    except Exception as e:
        logger.error(f"❌ 数据库测试失败: {e}")
        return False


async def test_token_service():
    """测试JWT token服务"""
    logger.info("=== 测试JWT Token服务 ===")
    
    try:
        token_service = TokenService()
        
        # 测试数据 - 创建UserInfo对象
        from datetime import datetime
        test_user_info = UserInfo(
            user_id="test_user_001",
            user_name="测试用户",
            branch_no="TEST_DEPT",
            branch_name="测试部门",
            role_id_list=["TEST_ROLE", "USER"],
            access_time=datetime.now()
        )
        
        # 生成token
        token = token_service.generate_token(test_user_info)
        logger.info(f"✅ Token生成成功: {token[:50]}...")
        
        # 验证token
        user_info = token_service.decode_token(token)
        if user_info and user_info.user_id == test_user_info.user_id:
            logger.info("✅ Token验证成功")
            logger.info(f"   用户ID: {user_info.user_id}")
            logger.info(f"   用户名: {user_info.user_name}")
            logger.info(f"   部门: {user_info.branch_name}")
            logger.info(f"   角色: {user_info.role_id_list}")
            return True
        else:
            logger.error("❌ Token验证失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ Token服务测试失败: {e}")
        return False


async def test_page_sync():
    """测试页面同步功能"""
    logger.info("=== 测试页面同步功能 ===")
    
    try:
        with get_db_session() as db:
            page_service = PageDiscoveryService(db)
            
            # 同步页面配置
            count = page_service.sync_pages_from_config()
            logger.info(f"✅ 页面同步成功，处理了 {count} 个页面")
            
            # 验证页面数据
            pages = page_service.get_all_pages_from_config()
            if pages and len(pages) > 0:
                logger.info(f"✅ 页面配置加载成功，共 {len(pages)} 个页面")
                
                # 显示前几个页面
                for i, page in enumerate(pages[:3]):
                    logger.info(f"   页面 {i+1}: {page['name']} ({page['path']})")
                
                return True
            else:
                logger.error("❌ 页面配置为空")
                return False
                
    except Exception as e:
        logger.error(f"❌ 页面同步测试失败: {e}")
        return False


async def test_permission_service():
    """测试权限服务"""
    logger.info("=== 测试权限服务 ===")
    
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            
            # 测试创建测试实体
            from models.permission_models import EntityType
            import time
            unique_code = f"TEST_DEPT_{int(time.time())}"
            test_dept = entity_service.create_entity(
                code=unique_code,
                name="测试部门001",
                entity_type=EntityType.DEPARTMENT,  # 使用枚举值
                description="集成测试用的测试部门"
            )
            logger.info(f"✅ 测试部门创建成功: {test_dept.name} ({test_dept.code})")
            
            # 测试获取实体列表
            departments = entity_service.get_entities_by_type(EntityType.DEPARTMENT)
            if departments and len(departments) > 0:
                logger.info(f"✅ 部门列表获取成功，共 {len(departments)} 个部门")
                return True
            else:
                logger.error("❌ 部门列表为空")
                return False
                
    except Exception as e:
        logger.error(f"❌ 权限服务测试失败: {e}")
        return False


async def test_login_record_service():
    """测试登录记录服务"""
    logger.info("=== 测试登录记录服务 ===")
    
    try:
        with get_db_session() as db:
            login_service = LoginRecordService(db)
            
            # 测试记录登录
            test_login_data = {
                "user_id": "test_user_002",
                "user_name": "测试用户002",
                "branch_no": "TEST_DEPT",
                "branch_name": "测试部门",
                "role_id_list": ["TEST_ROLE"]
            }
            
            record = login_service.record_login(**test_login_data)
            logger.info(f"✅ 登录记录创建成功: {record.user_name}")
            
            # 测试获取登录记录
            retrieved_record = login_service.get_last_login(test_login_data["user_id"])
            if retrieved_record and retrieved_record.user_id == test_login_data["user_id"]:
                logger.info("✅ 登录记录查询成功")
                return True
            else:
                logger.error("❌ 登录记录查询失败")
                return False
                
    except Exception as e:
        logger.error(f"❌ 登录记录服务测试失败: {e}")
        return False


async def test_api_imports():
    """测试API路由导入"""
    logger.info("=== 测试API路由导入 ===")
    
    try:
        # 测试导入所有权限管理相关的API路由
        from api.entity_routes import router as entity_router
        from api.permission_routes import router as permission_router
        from api.login_record_routes import router as login_record_router
        
        logger.info("✅ 权限管理API路由导入成功")
        
        # 测试导入改造后的API路由
        from api.fraudhunter.indicator_routes import router as indicator_router
        from api.fraudhunter.indicator_task_routes import router as indicator_task_router
        from api.fraudhunter.model_routes import risk_control_model_router
        from api.metadata_routes import router as metadata_router
        
        logger.info("✅ 改造后的API路由导入成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API路由导入测试失败: {e}")
        return False


async def run_integration_tests():
    """运行所有集成测试"""
    logger.info("🚀 开始Token权限管理系统集成测试")
    logger.info("=" * 60)
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("数据库连接", test_database_connection),
        ("JWT Token服务", test_token_service),
        ("页面同步功能", test_page_sync),
        ("权限服务", test_permission_service),
        ("登录记录服务", test_login_record_service),
        ("API路由导入", test_api_imports),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name}测试异常: {e}")
            test_results.append((test_name, False))
        
        logger.info("-" * 40)
    
    # 汇总测试结果
    logger.info("📊 集成测试结果汇总")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("-" * 40)
    logger.info(f"总计: {len(test_results)} 项测试")
    logger.info(f"通过: {passed} 项")
    logger.info(f"失败: {failed} 项")
    
    if failed == 0:
        logger.info("🎉 所有集成测试通过！系统集成成功！")
        return True
    else:
        logger.error(f"⚠️  有 {failed} 项测试失败，请检查系统配置")
        return False


if __name__ == "__main__":
    # 运行集成测试
    success = asyncio.run(run_integration_tests())
    
    # 设置退出码
    sys.exit(0 if success else 1)