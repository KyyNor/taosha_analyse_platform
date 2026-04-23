"""
告警管控记录API路由

提供告警管控记录的查询、详情和导出功能的API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from urllib.parse import quote
import io

from models.db_base import get_db
from middleware.auth_middleware import get_current_user
from services.token_service import UserInfo
from schemas.fraudhunter.alert_control_record import (
    AlertControlFilters,
    PaginationParams,
    AlertControlRecordResponse,
    AlertControlListResponse,
    AlertControlRecordDetailResponse,
    TrendRequest,
    TrendResponse,
    AlertControlListRequest,
    AlertControlExportRequest,
)
from services.fraudhunter.model_service.model_hit_alert_manager import ModelHitAlertManager
from utils.logger import logger


router = APIRouter(prefix="/alert-control-records", tags=["告警管控记录"])


@router.post(
    "",
    response_model=AlertControlListResponse,
    summary="获取告警管控记录列表"
)
async def list_alert_control_records(
    body: AlertControlListRequest,

    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取告警管控记录列表，支持分页和多条件筛选

    查询参数:
    - page: 页码（默认1）
    - page_size: 每页数量（默认20，最大1000）
    - start_date: 开始日期，格式 YYYY-MM-DD
    - end_date: 结束日期，格式 YYYY-MM-DD
    - account_id: 精确匹配账号ID
    - model_ids: 模型ID列表（多选，精确匹配）
    - model_name: 模糊匹配模型名称
    - alert_status: 告警状态筛选
    - control_status: 管控状态筛选
    - search: 搜索关键词，会在账号、模型名称、告警消息中搜索

    返回:
    - records: 告警管控记录列表
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页数量
    - total_pages: 总页数

    状态说明:
    - not_configured: 未配置（模型未启用告警/管控）
    - sent: 已发送（告警已发送）
    - executed: 已执行（管控已执行）
    - duplicate: 重复（当天已告警/管控过）
    """
    try:
        # 验证状态参数
        valid_alert_statuses = ["not_configured", "sent", "duplicate"]
        valid_control_statuses = ["not_configured", "executed", "duplicate"]

        if body.alert_status and body.alert_status not in valid_alert_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的告警状态: {body.alert_status}，支持的状态: {', '.join(valid_alert_statuses)}"
            )

        if body.control_status and body.control_status not in valid_control_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的管控状态: {body.control_status}，支持的状态: {', '.join(valid_control_statuses)}"
            )

        # 验证日期格式
        if body.start_date:
            try:
                datetime.strptime(body.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的开始日期格式: {body.start_date}，请使用 YYYY-MM-DD 格式"
                )

        if body.end_date:
            try:
                datetime.strptime(body.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的结束日期格式: {body.end_date}，请使用 YYYY-MM-DD 格式"
                )

        # 构建筛选条件
        filters = AlertControlFilters(
            start_date=body.start_date,
            end_date=body.end_date,
            account_id=body.account_id,
            model_ids=body.model_ids,
            model_name=body.model_name,
            alert_status=body.alert_status,
            control_status=body.control_status,
            search=body.search,
            hide_inactive=body.hide_inactive
        )

        # 构建分页参数
        pagination = PaginationParams(
            page=body.page,
            page_size=body.page_size
        )

        # 查询记录
        manager = ModelHitAlertManager(db)
        result = manager.get_alert_control_records(filters, pagination)

        logger.info(
            f"查询告警管控记录: user={current_user.user_id}, branch_no={current_user.branch_no}, "
            f"page={body.page}, page_size={body.page_size}, "
            f"total={result.total}, filters={filters.model_dump(exclude_none=True)}"
        )
        
        return result

    except Exception as e:
        logger.error(f"获取告警管控记录列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取告警管控记录列表失败: {str(e)}"
        )


@router.get(
    "/{record_id}",
    response_model=AlertControlRecordDetailResponse,
    summary="获取告警管控记录详情"
)
async def get_alert_control_record_detail(
    record_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的告警管控记录详情

    参数:
    - record_id: 告警管控记录ID

    返回:
    - record: 告警管控记录基本信息
    - hit_record: 关联的命中记录详情（包含指标数据）

    详情包含:
    - 基本信息：记录ID、账号、日期、模型信息
    - 告警信息：告警状态、消息、告警人、告警时间
    - 管控信息：管控状态、管控时间、管控流水号
    - 关联命中记录：命中时间、指标数据、命中模型列表
    """
    try:
        manager = ModelHitAlertManager(db)
        detail = manager.get_alert_control_record_detail(record_id)
        
        if not detail:
            raise HTTPException(
                status_code=404,
                detail=f"告警管控记录不存在: {record_id}"
            )
        
        logger.info(f"获取告警管控记录详情: record_id={record_id}")
        
        return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警管控记录详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取告警管控记录详情失败: {str(e)}"
        )


@router.post(
    "/export",
    summary="导出告警管控记录为Excel"
)
async def export_alert_control_records(
    body: AlertControlExportRequest,

    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    导出告警管控记录为Excel文件

    参数:
    - 筛选参数与列表查询相同

    返回:
    - Excel文件下载响应

    导出内容包含:
    - ID、账号、记录日期、模型信息
    - 告警状态、告警消息、告警人、告警时间
    - 管控状态、管控时间、管控流水号
    - 创建时间、更新时间

    注意:
    - 导出会包含所有符合筛选条件的记录，请注意数据量
    """
    try:
        # 验证状态参数
        valid_alert_statuses = ["not_configured", "sent", "duplicate"]
        valid_control_statuses = ["not_configured", "executed", "duplicate"]

        if body.alert_status and body.alert_status not in valid_alert_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的告警状态: {body.alert_status}，支持的状态: {', '.join(valid_alert_statuses)}"
            )

        if body.control_status and body.control_status not in valid_control_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的管控状态: {body.control_status}，支持的状态: {', '.join(valid_control_statuses)}"
            )

        # 验证日期格式
        if body.start_date:
            try:
                datetime.strptime(body.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的开始日期格式: {body.start_date}，请使用 YYYY-MM-DD 格式"
                )

        if body.end_date:
            try:
                datetime.strptime(body.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的结束日期格式: {body.end_date}，请使用 YYYY-MM-DD 格式"
                )

        # 构建筛选条件
        filters = AlertControlFilters(
            start_date=body.start_date,
            end_date=body.end_date,
            account_id=body.account_id,
            model_ids=body.model_ids,
            model_name=body.model_name,
            alert_status=body.alert_status,
            control_status=body.control_status,
            search=body.search,
            hide_inactive=body.hide_inactive
        )

        # 导出数据
        manager = ModelHitAlertManager(db)
        file_content = manager.export_alert_control_records(filters)

        # 设置文件名和响应头
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alert_control_records_{timestamp}.xlsx"
        # 使用RFC 5987格式支持Unicode文件名
        encoded_filename = quote(filename)

        logger.info(
            f"导出告警管控记录: user={current_user.user_id}, branch_no={current_user.branch_no}, "
            f"size={len(file_content)} bytes, "
            f"filters={filters.model_dump(exclude_none=True)}"
        )

        # 返回文件流响应
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出告警管控记录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"导出告警管控记录失败: {str(e)}"
        )


@router.get(
    "/statistics/summary",
    summary="获取告警管控统计摘要"
)
async def get_alert_control_statistics(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    获取告警管控记录的统计摘要

    参数:
    - start_date: 统计开始日期
    - end_date: 统计结束日期

    返回:
    - total_records: 总记录数
    - alert_statistics: 告警统计
      - total_alerts: 总告警数
      - sent_alerts: 已发送告警数
      - duplicate_alerts: 重复告警数
    - control_statistics: 管控统计
      - total_controls: 总管控数
      - executed_controls: 已执行管控数
      - duplicate_controls: 重复管控数
    - daily_statistics: 按日期统计（最近7天）

    用于前端展示统计图表和概览信息
    """
    try:
        # 构建筛选条件
        filters = AlertControlFilters(
            start_date=start_date,
            end_date=end_date
        )
        
        manager = ModelHitAlertManager(db)
        
        # 获取基础统计（使用现有的查询方法）
        # 注意：这里使用一个大的page_size来获取所有记录进行统计
        # 在实际生产环境中，应该在数据库层面进行聚合查询以提高性能
        pagination = PaginationParams(page=1, page_size=10000)
        result = manager.get_alert_control_records(filters, pagination)
        
        # 计算统计数据
        total_records = result.total
        
        # 告警统计
        alert_sent = sum(1 for r in result.records if r.alert_status == 'sent')
        alert_duplicate = sum(1 for r in result.records if r.alert_status == 'duplicate')
        alert_total = alert_sent + alert_duplicate
        
        # 管控统计
        control_executed = sum(1 for r in result.records if r.control_status == 'executed')
        control_duplicate = sum(1 for r in result.records if r.control_status == 'duplicate')
        control_total = control_executed + control_duplicate
        
        statistics = {
            "total_records": total_records,
            "alert_statistics": {
                "total_alerts": alert_total,
                "sent_alerts": alert_sent,
                "duplicate_alerts": alert_duplicate
            },
            "control_statistics": {
                "total_controls": control_total,
                "executed_controls": control_executed,
                "duplicate_controls": control_duplicate
            },
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
        logger.info(f"获取告警管控统计: {statistics}")
        
        return statistics

    except Exception as e:
        logger.error(f"获取告警管控统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取告警管控统计失败: {str(e)}"
        )


@router.post(
    "/history/trend",
    response_model=TrendResponse,
    summary="获取模型命中账户数历史趋势"
)
async def get_model_history_trend(
    body: TrendRequest,

    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取模型命中账户数的历史趋势（面积折线图数据源）。

    **去重口径**：`COUNT(DISTINCT account_id)` — 同一个账户同一天命中同一模型计一次，
    不同模型互不受影响。

    **支持的粒度**：
    - `day`：按自然日分组，横轴标签形如 "2024-01-15"
    - `week`：按 ISO 所在周分组，横轴标签形如 "2024-W03"
    - `month`：按自然月分组，横轴标签形如 "2024-01"

    **约束**：时间跨度不允许超过 180 天。

    返回的 series 每一项代表"某模型在某一时间刻度上命中的独立账户数"。
    前端可据此绘制多条折线，面积图。
    """
    start_date = body.start_date
    end_date = body.end_date
    granularity = body.granularity
    model_ids = body.model_ids

    valid_granularities = {"day", "week", "month"}
    if granularity not in valid_granularities:
        raise HTTPException(
            status_code=400,
            detail=f"无效的粒度: {granularity}，支持的粒度: {', '.join(valid_granularities)}"
        )

    try:
        manager = ModelHitAlertManager(db)
        result = manager.get_history_trend(body)

        logger.info(
            f"[get_model_history_trend] user={current_user.user_id}, "
            f"start={start_date}, end={end_date}, granularity={granularity}, "
            f"model_count={len(model_ids) if model_ids else 'all_online'}, "
            f"total_points={result.total_points}, series_len={len(result.series)}"
        )

        return result

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"获取模型历史趋势失败: {str(e)}")