"""
FraudHunter模型管理API路由

版本: v2.0.0 (支持高级操作符)

提供规则验证、SQL预览和运行时评估的API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from models.db_base import get_db
from schemas.fraudhunter.rule import (
    RuleConfig,
    RuleValidationResult,
    SQLPreviewResult,
    RuleEvaluationResult
)
from services.fraudhunter.model_service.rule_engine import RuleEngine
from utils.logger import logger


router = APIRouter(prefix="/models", tags=["模型管理"])


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
    - output: 输出配置

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
        sql_expression = rule_engine.generate_sql_expression(rule_config)

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
    - output: 规则命中时的输出配置（未命中时为None）

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
        ],
        "output": {
          "risk_level": "high",
          "risk_score": 85,
          "action": "review"
        }
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
            indicator_values=indicator_values,
            output=rule_config.output.model_dump() if is_hit else None
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
