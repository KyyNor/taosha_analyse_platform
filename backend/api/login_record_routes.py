"""
登录记录API路由
提供用户登录记录查询接口
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from models.db_base import get_db_session
from models.permission_models import SystemLoginRecord
from services.permission_service import LoginRecordService
from middleware.auth_middleware import require_admin_role, get_current_user
from services.token_service import UserInfo
from utils.logger import logger

router = APIRouter(prefix="/login-records", tags=["登录记录"])


# Pydantic模型定义
class LoginRecordResponse(BaseModel):
    """登录记录响应模型"""
    user_id: str
    user_name: str
    branch_no: str
    branch_name: str
    role_id_list: List[str]
    role_name_list: List[str]
    is_admin: bool = False  # 是否为管理员（根据部门和角色的is_admin字段判断）
    last_login_time: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class LoginRecordListResponse(BaseModel):
    """登录记录列表响应模型"""
    records: List[LoginRecordResponse]
    total: int
    page: int
    page_size: int


class LoginRecordSummaryResponse(BaseModel):
    """登录记录摘要响应模型"""
    total_users: int
    active_users_today: int
    active_users_week: int
    active_users_month: int
    latest_login_time: Optional[str]
    most_active_department: Optional[str]
    most_active_role: Optional[str]


# API路由定义
@router.get("", response_model=LoginRecordListResponse)
async def list_login_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    branch_no: Optional[str] = Query(None, description="部门编号过滤"),
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    获取用户登录记录列表
    
    需要管理员权限
    支持分页和过滤
    """
    try:
        with get_db_session() as db:
            from services.permission_service import PermissionService

            login_service = LoginRecordService(db)
            permission_service = PermissionService(db)

            # 构建查询
            query = db.query(SystemLoginRecord)

            # 应用过滤条件
            if user_id:
                query = query.filter(SystemLoginRecord.user_id.like(f"%{user_id}%"))

            if branch_no:
                query = query.filter(SystemLoginRecord.branch_no == branch_no)

            # 获取总数
            total = query.count()

            # 应用分页和排序
            records = query.order_by(SystemLoginRecord.last_login_time.desc())\
                          .offset((page - 1) * page_size)\
                          .limit(page_size)\
                          .all()

            # 转换响应格式
            record_responses = []
            for record in records:
                # 计算每个用户是否为管理员
                is_admin = permission_service.is_admin_user(
                    record.branch_no,
                    record.role_id_list
                )

                record_responses.append(
                    LoginRecordResponse(
                        user_id=record.user_id,
                        user_name=record.user_name,
                        branch_no=record.branch_no,
                        branch_name=record.branch_name,
                        role_id_list=record.role_id_list,
                        role_name_list=record.role_name_list,
                        is_admin=is_admin,
                        last_login_time=record.last_login_time.isoformat(),
                        created_at=record.created_at.isoformat(),
                        updated_at=record.updated_at.isoformat()
                    )
                )
            
            return LoginRecordListResponse(
                records=record_responses,
                total=total,
                page=page,
                page_size=page_size
            )
            
    except Exception as e:
        logger.error(f"获取登录记录列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取登录记录列表失败"
        )


@router.get("/{user_id}", response_model=LoginRecordResponse)
async def get_user_login_record(
    user_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    获取指定用户的登录记录
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            from services.permission_service import PermissionService

            login_service = LoginRecordService(db)
            permission_service = PermissionService(db)

            record = login_service.get_last_login(user_id)

            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"用户 {user_id} 的登录记录不存在"
                )

            # 计算用户是否为管理员
            is_admin = permission_service.is_admin_user(
                record.branch_no,
                record.role_id_list
            )

            return LoginRecordResponse(
                user_id=record.user_id,
                user_name=record.user_name,
                branch_no=record.branch_no,
                branch_name=record.branch_name,
                role_id_list=record.role_id_list,
                role_name_list=record.role_name_list,
                is_admin=is_admin,
                last_login_time=record.last_login_time.isoformat(),
                created_at=record.created_at.isoformat(),
                updated_at=record.updated_at.isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户登录记录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户登录记录失败"
        )


@router.get("/current/info", response_model=LoginRecordResponse)
async def get_current_user_login_record(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    获取当前用户的登录记录

    用户可以查看自己的登录记录
    """
    try:
        with get_db_session() as db:
            from services.permission_service import PermissionService

            login_service = LoginRecordService(db)
            permission_service = PermissionService(db)

            record = login_service.get_last_login(current_user.user_id)

            if not record:
                # 如果没有记录，创建一个基于当前token信息的记录
                record = login_service.record_login(
                    user_id=current_user.user_id,
                    user_name=current_user.user_name,
                    branch_no=current_user.branch_no,
                    branch_name=current_user.branch_name,
                    role_id_list=current_user.role_id_list
                )

            # 计算用户是否为管理员（基于实体的is_admin字段）
            is_admin = permission_service.is_admin_user(
                record.branch_no,
                record.role_id_list
            )

            return LoginRecordResponse(
                user_id=record.user_id,
                user_name=record.user_name,
                branch_no=record.branch_no,
                branch_name=record.branch_name,
                role_id_list=record.role_id_list,
                role_name_list=record.role_name_list,
                is_admin=is_admin,
                last_login_time=record.last_login_time.isoformat(),
                created_at=record.created_at.isoformat(),
                updated_at=record.updated_at.isoformat()
            )

    except Exception as e:
        logger.error(f"获取当前用户登录记录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取当前用户登录记录失败"
        )


@router.get("/summary/stats", response_model=LoginRecordSummaryResponse)
async def get_login_summary(
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    获取登录记录统计摘要
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            from datetime import datetime, timedelta
            from sqlalchemy import func, desc
            
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # 总用户数
            total_users = db.query(SystemLoginRecord).count()
            
            # 今日活跃用户数
            active_users_today = db.query(SystemLoginRecord)\
                .filter(SystemLoginRecord.last_login_time >= today)\
                .count()
            
            # 本周活跃用户数
            active_users_week = db.query(SystemLoginRecord)\
                .filter(SystemLoginRecord.last_login_time >= week_ago)\
                .count()
            
            # 本月活跃用户数
            active_users_month = db.query(SystemLoginRecord)\
                .filter(SystemLoginRecord.last_login_time >= month_ago)\
                .count()
            
            # 最新登录时间
            latest_record = db.query(SystemLoginRecord)\
                .order_by(desc(SystemLoginRecord.last_login_time))\
                .first()
            latest_login_time = latest_record.last_login_time.isoformat() if latest_record else None
            
            # 最活跃的部门（本月）
            most_active_dept_result = db.query(
                SystemLoginRecord.branch_name,
                func.count(SystemLoginRecord.user_id).label('count')
            ).filter(SystemLoginRecord.last_login_time >= month_ago)\
             .group_by(SystemLoginRecord.branch_name)\
             .order_by(desc('count'))\
             .first()
            
            most_active_department = most_active_dept_result[0] if most_active_dept_result else None
            
            # 最活跃的角色（本月）- 这里简化处理，取第一个角色
            most_active_role_result = db.query(SystemLoginRecord)\
                .filter(SystemLoginRecord.last_login_time >= month_ago)\
                .order_by(desc(SystemLoginRecord.last_login_time))\
                .first()
            
            most_active_role = None
            if most_active_role_result and most_active_role_result.role_name_list:
                most_active_role = most_active_role_result.role_name_list[0]
            
            return LoginRecordSummaryResponse(
                total_users=total_users,
                active_users_today=active_users_today,
                active_users_week=active_users_week,
                active_users_month=active_users_month,
                latest_login_time=latest_login_time,
                most_active_department=most_active_department,
                most_active_role=most_active_role
            )
            
    except Exception as e:
        logger.error(f"获取登录统计摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取登录统计摘要失败"
        )


@router.get("/departments/stats")
async def get_department_login_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    获取各部门登录统计
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 按部门统计登录用户数
            dept_stats = db.query(
                SystemLoginRecord.branch_no,
                SystemLoginRecord.branch_name,
                func.count(SystemLoginRecord.user_id).label('user_count'),
                func.max(SystemLoginRecord.last_login_time).label('latest_login')
            ).filter(SystemLoginRecord.last_login_time >= start_date)\
             .group_by(SystemLoginRecord.branch_no, SystemLoginRecord.branch_name)\
             .order_by(func.count(SystemLoginRecord.user_id).desc())\
             .all()
            
            stats = [
                {
                    "branch_no": stat.branch_no,
                    "branch_name": stat.branch_name,
                    "user_count": stat.user_count,
                    "latest_login": stat.latest_login.isoformat() if stat.latest_login else None
                }
                for stat in dept_stats
            ]
            
            return {
                "stats": stats,
                "total_departments": len(stats),
                "period_days": days
            }
            
    except Exception as e:
        logger.error(f"获取部门登录统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门登录统计失败"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_login_record(
    user_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    删除用户登录记录
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            record = db.query(SystemLoginRecord)\
                .filter(SystemLoginRecord.user_id == user_id)\
                .first()
            
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"用户 {user_id} 的登录记录不存在"
                )
            
            db.delete(record)
            db.flush()
            
            logger.info(f"管理员 {admin_user.user_id} 删除了用户 {user_id} 的登录记录")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户登录记录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户登录记录失败"
        )