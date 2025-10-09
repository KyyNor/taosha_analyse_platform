"""
API路由定义
"""

import time
from typing import List
from utils.logger import logger, get_logger, LoggerMixin
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from api.endpoint_models import (
    QueryRequest, QueryResponse, TableInfo, 
    DatabaseStatus, SystemStatus, ErrorResponse
)
from services import (
    get_nl2sql_service, get_query_engine,
    get_metadata_service, get_glossary_service
)
from services.async_query_service import get_async_query_service
from utils.config import settings


# 创建路由器
router = APIRouter()

@router.post("/query")
async def process_natural_language_query(request: QueryRequest):
    """
    异步处理自然语言查询

    接收自然语言输入，返回任务ID，查询在后台异步执行
    """
    try:
        logger.info(f"接收查询请求: {request.query}")

        # 获取异步查询服务
        async_query_service = get_async_query_service()

        # 提交异步任务
        operator = "api_user"  # 实际应用中应该从认证信息中获取
        task_id = await async_query_service.submit_query(
            user_input=request.query,
            operator=operator,
            flow_type=request.flow_type,
            max_retries=request.max_retries
        )

        logger.info(f"异步任务已创建: {task_id}")

        # 返回任务ID
        return {
            "success": True,
            "task_id": task_id,
            "message": "查询任务已提交，正在后台处理"
        }

    except Exception as e:
        error_message = f"查询提交失败: {str(e)}"
        logger.error(error_message, exc_info=True)

        # 返回错误响应
        return {
            "success": False,
            "error": error_message
        }

@router.get("/tables", response_model=List[TableInfo])
async def get_tables():
    """
    获取所有数据表信息
    """
    try:
        db_service = get_query_engine()
        metadata_service = get_metadata_service()
        
        # 从数据库获取表列表
        table_names = db_service.get_tables()
        
        tables_info = []
        for table_name in table_names:
            # 获取表结构信息
            schema = db_service.get_table_schema(table_name)
            
            # 获取元数据中的表注释
            table_metadata = metadata_service.get_table_info(table_name)
            comment = table_metadata.get('comment', '') if table_metadata else ''
            
            table_info = TableInfo(
                table_name=table_name,
                comment=comment,
                row_count=schema.get('row_count', 0),
                columns=schema.get('columns', [])
            )
            tables_info.append(table_info)
        
        logger.info(f"成功获取 {len(tables_info)} 个表信息")
        return tables_info

    except Exception as e:
        logger.error(f"获取表信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表信息失败: {str(e)}")

@router.get("/table/{table_name}", response_model=TableInfo)
async def get_table_info(table_name: str):
    """
    获取指定表的详细信息
    """
    try:
        db_service = get_query_engine()
        metadata_service = get_metadata_service()

        # 检查表是否存在
        table_names = db_service.get_tables()
        if table_name not in table_names:
            raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

        # 获取表结构
        schema = db_service.get_table_schema(table_name)

        # 获取元数据中的表注释
        table_metadata = metadata_service.get_table_info(table_name)
        comment = table_metadata.get('comment', '') if table_metadata else ''

        table_info = TableInfo(
            table_name=table_name,
            comment=comment,
            row_count=schema.get('row_count', 0),
            columns=schema.get('columns', [])
        )

        logger.info(f"成功获取表 {table_name} 的详细信息")
        return table_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表 {table_name} 信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表信息失败: {str(e)}")

@router.get("/query/{task_id}")
async def get_query_result(task_id: str):
    """
    获取查询任务结果
    """
    try:
        async_query_service = get_async_query_service()
        result = await async_query_service.get_task_result(task_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")

        logger.info(f"成功获取任务 {task_id} 的结果")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务 {task_id} 结果失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")

@router.get("/query")
async def get_all_queries():
    """
    获取所有查询任务列表
    """
    try:
        async_query_service = get_async_query_service()
        tasks = await async_query_service.get_all_tasks()

        logger.info(f"成功获取 {len(tasks)} 个查询任务")
        return tasks

    except Exception as e:
        logger.error(f"获取查询任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取查询任务列表失败: {str(e)}")
