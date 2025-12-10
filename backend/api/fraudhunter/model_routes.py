"""
FraudHunter模型管理API路由

版本: v2.1.0 (支持高级操作符和历史回测)

提供规则验证、SQL预览、运行时评估、历史回测和预警管控模型CRUD的API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from models.db_base import get_db
from schemas.fraudhunter.rule import (
    RuleConfig,
    RuleValidationResult,
    SQLPreviewResult,
    RuleEvaluationResult
)
from schemas.fraudhunter.risk_control_model import (
    RiskControlModelCreate,
    RiskControlModelUpdate,
    RiskControlModelResponse,
    RiskControlModelListResponse,
    RiskControlModelPublishRequest,
    ModelBacktestRequest,
    ModelBacktestResponse,
    ModelOnlineRequest,
    ModelOnlineResponse
)
from services.fraudhunter.model_service.rule_engine import RuleEngine
from services.fraudhunter.model_service import RiskControlModelManager
from utils.logger import logger


router = APIRouter(prefix="/models", tags=["模型管理"])
risk_control_model_router = APIRouter(prefix="/risk-control-models", tags=["预警管控模型"])


@router.post(
    "/validate-rule",
    response_model=RuleValidationResult,
    summary="验证规则配置"
)
async def validate_rule_config(
    rule_config: RuleConfig,
    db: Session = Depends(get_db)
):
    """
    验证规则配置的完整性和正确性

    验证内容：
    - 检查指标是否存在
    - 验证操作符与数据类型兼容性
    - 检查规则结构完整性
    - 验证正则表达式语法（regexp/not regexp）
    - 验证多值数组格式（in/not in）
    - 提供规则优化建议

    参数:
    - logic: 根逻辑操作符（AND/OR）
    - rules: 规则列表（支持嵌套）

    返回:
    - valid: 是否验证通过
    - errors: 错误信息列表
    - warnings: 警告信息列表
    - extracted_indicators: 提取到的指标编码列表
    """
    try:
        rule_engine = RuleEngine(db)
        validation_result = rule_engine.validate_rule_config(rule_config)

        logger.info(
            f"规则验证完成: valid={validation_result.valid}, "
            f"errors={len(validation_result.errors)}, "
            f"warnings={len(validation_result.warnings)}, "
            f"indicators={len(validation_result.extracted_indicators)}"
        )

        return validation_result

    except Exception as e:
        logger.error(f"规则验证失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"规则验证失败: {str(e)}"
        )


@router.post(
    "/preview-sql",
    response_model=SQLPreviewResult,
    summary="预览规则SQL表达式"
)
async def preview_rule_sql(
    rule_config: RuleConfig,
    db: Session = Depends(get_db)
):
    """
    生成规则的Spark SQL WHERE子句

    将可视化规则配置转换为Spark SQL表达式，用于在大数据平台上执行规则筛选。

    支持的SQL语法：
    - 基础比较: >, >=, <, <=, =, !=
    - 集合操作: IN, NOT IN
    - 正则匹配: REGEXP, NOT REGEXP ...

    示例输出:
    ```sql
    (i_login_cnt_7d > 10 AND (i_device_change_cnt >= 3 OR i_user_status IN ('suspended', 'banned')))
    ```

    参数:
    - rule_config: 规则配置

    返回:
    - sql_expression: SQL WHERE子句
    - extracted_indicators: 提取到的指标列表
    - rule_summary: 规则摘要信息
    - warnings: 警告信息
    """
    try:
        rule_engine = RuleEngine(db)

        # 先验证规则
        validation_result = rule_engine.validate_rule_config(rule_config)
        if not validation_result.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "规则验证失败，无法生成SQL",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
            )

        # 生成SQL表达式
        sql_expression = rule_engine.generate_sql_expression(rule_config, use_display_name=True)

        # 获取规则摘要
        summary = rule_engine.get_rule_summary(rule_config)

        logger.info(f"生成SQL成功，长度: {len(sql_expression)}")

        return SQLPreviewResult(
            sql_expression=sql_expression,
            extracted_indicators=validation_result.extracted_indicators,
            rule_summary=summary,
            warnings=validation_result.warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成SQL失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"生成SQL失败: {str(e)}"
        )


@router.post(
    "/evaluate-rule",
    response_model=RuleEvaluationResult,
    summary="运行时评估规则"
)
async def evaluate_rule_runtime(
    rule_config: RuleConfig,
    indicator_values: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    在运行时评估规则是否命中

    用于测试规则是否会命中给定的指标值。支持所有操作符类型：
    - 基础比较: >, >=, <, <=, =, !=
    - 集合操作: in, not in
    - 正则匹配: regexp, not regexp

    参数:
    - rule_config: 规则配置
    - indicator_values: 指标值字典，格式 {"i_login_cnt_7d": 15, "i_user_status": "suspended", ...}

    返回:
    - is_hit: 规则是否命中
    - indicator_values: 输入的指标值

    示例请求:
    ```json
    {
      "rule_config": {
        "logic": "AND",
        "rules": [
          {
            "type": "condition",
            "indicator": "i_login_cnt_7d",
            "operator": ">",
            "value": 10
          },
          {
            "type": "condition",
            "indicator": "i_user_status",
            "operator": "in",
            "value": ["suspended", "banned"]
          }
        ]
      },
      "indicator_values": {
        "i_login_cnt_7d": 15,
        "i_user_status": "suspended"
      }
    }
    ```
    """
    try:
        rule_engine = RuleEngine(db)

        # 验证规则
        validation_result = rule_engine.validate_rule_config(rule_config)
        if not validation_result.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "规则验证失败",
                    "errors": validation_result.errors
                }
            )

        # 执行评估
        is_hit = rule_engine.evaluate_rule(rule_config, indicator_values)

        logger.info(
            f"规则评估完成: is_hit={is_hit}, "
            f"indicators={list(indicator_values.keys())}"
        )

        return RuleEvaluationResult(
            is_hit=is_hit,
            indicator_values=indicator_values
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"规则评估失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"规则评估失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查"
)
async def health_check():
    """
    检查规则引擎服务健康状态

    返回:
    - status: 服务状态
    - version: 规则引擎版本
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "supported_operators": {
            "comparison": [">", ">=", "<", "<=", "=", "!="],
            "set": ["in", "not in"],
            "pattern": ["regexp", "not regexp"]
        }
    }


# ==================== 预警管控模型CRUD端点 ====================

@risk_control_model_router.post(
    "",
    response_model=RiskControlModelResponse,
    summary="创建预警管控模型"
)
async def create_risk_control_model(
    model_data: RiskControlModelCreate,
    db: Session = Depends(get_db)
):
    """
    创建新的预警管控模型

    参数:
    - model_code: 模型编码（唯一）
    - model_name: 模型名称
    - description: 模型描述
    - rule_config: 规则配置JSON
    - is_send_alert_message: 是否发送告警消息
    - alert_message_target: 告警消息目标
    - is_acct_control: 是否账户控制

    返回:
    - 创建的预警管控模型完整信息
    """
    try:
        manager = RiskControlModelManager(db)
        model = manager.create_risk_control_model(model_data, created_by="system")
        return model

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建预警管控模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建预警管控模型失败: {str(e)}")


@risk_control_model_router.get(
    "",
    response_model=RiskControlModelListResponse,
    summary="获取预警管控模型列表"
)
async def list_risk_control_models(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    model_code: Optional[str] = Query(None, description="模型编码筛选（模糊匹配）"),
    db: Session = Depends(get_db)
):
    """
    获取预警管控模型列表，支持分页和筛选

    查询参数:
    - page: 页码（默认1）
    - page_size: 每页数量（默认20，最大100）
    - status: 状态筛选（draft/testing/online/offline/archived）
    - model_code: 模型编码筛选（模糊匹配）

    返回:
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页数量
    - items: 预警管控模型列表
    """
    try:
        manager = RiskControlModelManager(db)
        items, total = manager.list_risk_control_models(
            page=page,
            page_size=page_size,
            status=status,
            model_code=model_code
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    except Exception as e:
        logger.error(f"获取预警管控模型列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取预警管控模型列表失败: {str(e)}")


@risk_control_model_router.get(
    "/{model_id}",
    response_model=RiskControlModelResponse,
    summary="获取预警管控模型详情"
)
async def get_risk_control_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的预警管控模型详情

    参数:
    - model_id: 模型ID

    返回:
    - 预警管控模型完整信息
    """
    try:
        manager = RiskControlModelManager(db)
        model = manager.get_risk_control_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail=f"预警管控模型不存在: {model_id}")

        return model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取预警管控模型详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取预警管控模型详情失败: {str(e)}")


@risk_control_model_router.put(
    "/{model_id}",
    response_model=RiskControlModelResponse,
    summary="更新预警管控模型"
)
async def update_risk_control_model(
    model_id: int,
    model_data: RiskControlModelUpdate,
    db: Session = Depends(get_db)
):
    """
    更新预警管控模型配置

    参数:
    - model_id: 模型ID
    - 更新字段（所有字段可选）

    返回:
    - 更新后的预警管控模型信息
    """
    try:
        manager = RiskControlModelManager(db)
        model = manager.update_risk_control_model(model_id, model_data, updated_by="system")
        return model

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新预警管控模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新预警管控模型失败: {str(e)}")


@risk_control_model_router.delete(
    "/{model_id}",
    summary="删除预警管控模型"
)
async def delete_risk_control_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    删除预警管控模型（级联删除历史记录）

    参数:
    - model_id: 模型ID

    返回:
    - 删除成功消息
    """
    try:
        manager = RiskControlModelManager(db)
        manager.delete_risk_control_model(model_id)
        return {"message": f"预警管控模型 {model_id} 已删除"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除预警管控模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除预警管控模型失败: {str(e)}")


@risk_control_model_router.post(
    "/{model_id}/publish",
    response_model=RiskControlModelResponse,
    summary="发布预警管控模型"
)
async def publish_risk_control_model(
    model_id: int,
    publish_data: RiskControlModelPublishRequest,
    db: Session = Depends(get_db)
):
    """
    发布预警管控模型到指定版本

    参数:
    - model_id: 模型ID
    - version: 要发布的版本号
    - change_description: 变更说明（可选）

    返回:
    - 发布后的预警管控模型信息
    """
    try:
        manager = RiskControlModelManager(db)
        model = manager.publish_risk_control_model(
            model_id,
            publish_data.version,
            updated_by="system",
            change_description=publish_data.change_description
        )
        return model

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发布预警管控模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发布预警管控模型失败: {str(e)}")


@risk_control_model_router.post(
    "/{model_id}/archive",
    response_model=RiskControlModelResponse,
    summary="归档预警管控模型"
)
async def archive_risk_control_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    归档预警管控模型

    参数:
    - model_id: 模型ID

    返回:
    - 归档后的预警管控模型信息
    """
    try:
        manager = RiskControlModelManager(db)
        model = manager.archive_risk_control_model(model_id, updated_by="system")
        return model

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"归档预警管控模型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档预警管控模型失败: {str(e)}")


# ==================== 模型执行端点 ====================

@risk_control_model_router.post(
    "/{model_id}/backtest",
    response_model=ModelBacktestResponse,
    summary="提交模型历史回测任务"
)
async def submit_model_backtest(
    model_id: int,
    backtest_data: ModelBacktestRequest,
    db: Session = Depends(get_db)
):
    """
    提交模型历史回测任务

    根据指定的日期范围，对每天执行模型回测。回测SQL会联接当天的宽表（实时指标）
    和前一天的宽表（离线指标）进行模型条件匹配。

    任务提交后后台异步执行，可通过试运行任务列表查看进度。

    参数:
    - model_id: 模型ID
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)

    返回:
    - success: 提交是否成功
    - message: 提示消息
    - execution_id: 任务执行ID（可用于查询进度）

    注意:
    - 如果某天的宽表文件不存在，该日期会被跳过并产生警告
    - 目前只支持 dep_acct_no 对象类型的宽表
    """
    try:
        manager = RiskControlModelManager(db)

        execution_id = await manager.submit_backtest_task(
            model_id=model_id,
            start_date=backtest_data.start_date,
            end_date=backtest_data.end_date,
            created_by="system"
        )

        return ModelBacktestResponse(
            success=True,
            message=f"历史回测任务已提交，日期范围: {backtest_data.start_date} 至 {backtest_data.end_date}",
            execution_id=execution_id
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交模型历史回测任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交模型历史回测任务失败: {str(e)}")


@risk_control_model_router.post(
    "/{model_id}/online",
    response_model=ModelOnlineResponse,
    summary="模型上线执行（预留）"
)
async def execute_model_online(
    model_id: int,
    online_data: ModelOnlineRequest = None,
    db: Session = Depends(get_db)
):
    """
    将模型部署到生产环境执行（功能待实现）

    此功能将在后续版本中完善，包括：
    - 验证模型状态（必须是online状态）
    - 生成生产环境SQL
    - 部署到DolphinScheduler
    - 配置定时任务

    参数:
    - model_id: 模型ID
    - schedule_cron: 调度CRON表达式（可选）
    - description: 上线说明（可选）

    返回:
    - success: 上线是否成功
    - message: 提示消息
    - workflow_code: DolphinScheduler工作流编码
    """
    try:
        manager = RiskControlModelManager(db)
        manager.execute_online(model_id, updated_by="system")

        # 如果execute_online没有抛出NotImplementedError，返回成功
        return ModelOnlineResponse(
            success=True,
            message="模型上线成功",
            workflow_code=None
        )

    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"模型上线执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"模型上线执行失败: {str(e)}")
