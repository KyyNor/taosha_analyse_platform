"""
API路由定义
"""

import time
from typing import List
from loguru import logger
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from api.models import (
    QueryRequest, QueryResponse, TableInfo, 
    DatabaseStatus, SystemStatus, ErrorResponse
)
from services import (
    get_nl2sql_service, get_database_service, 
    get_metadata_service, get_glossary_service
)
from config import settings


# 创建路由器
router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest):
    """
    处理自然语言查询
    
    接收自然语言输入，返回SQL查询和执行结果
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # 获取NL2SQL服务
        nl2sql_service = get_nl2sql_service()
        
        # 处理查询
        result = nl2sql_service.process_query(
            user_input=request.query,
            max_retries=request.max_retries
        )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 构建响应
        response = QueryResponse(
            success=result['success'],
            user_input=result['user_input'],
            is_clear=result['is_clear'],
            sql_query=result['sql_query'],
            data=result['data'],
            row_count=result.get('row_count'),
            error=result['error'],
            retry_count=result['retry_count'],
            execution_time=execution_time,
            logs=result['logs']
        )
        
        logger.info(f"Query processed successfully in {execution_time:.2f}s")
        return response
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_message = f"查询处理失败: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        # 返回错误响应
        return QueryResponse(
            success=False,
            user_input=request.query,
            is_clear=False,
            sql_query="",
            data=None,
            row_count=None,
            error=error_message,
            retry_count=0,
            execution_time=execution_time,
            logs=[]
        )

@router.get("/tables", response_model=List[TableInfo])
async def get_tables():
    """
    获取所有数据表信息
    """
    try:
        db_service = get_database_service()
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
        
        logger.info(f"Retrieved {len(tables_info)} tables")
        return tables_info
        
    except Exception as e:
        logger.error(f"Failed to get tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表信息失败: {str(e)}")

@router.get("/table/{table_name}", response_model=TableInfo)
async def get_table_info(table_name: str):
    """
    获取指定表的详细信息
    """
    try:
        db_service = get_database_service()
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
        
        logger.info(f"Retrieved info for table: {table_name}")
        return table_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table info for {table_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表信息失败: {str(e)}")

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    获取系统状态信息
    """
    try:
        db_service = get_database_service()
        metadata_service = get_metadata_service()
        glossary_service = get_glossary_service()
        
        # 获取数据库状态
        table_names = db_service.get_tables()
        tables_info = []
        
        for table_name in table_names:
            schema = db_service.get_table_schema(table_name)
            table_metadata = metadata_service.get_table_info(table_name)
            comment = table_metadata.get('comment', '') if table_metadata else ''
            
            table_info = TableInfo(
                table_name=table_name,
                comment=comment,
                row_count=schema.get('row_count', 0),
                columns=schema.get('columns', [])
            )
            tables_info.append(table_info)
        
        database_status = DatabaseStatus(
            database_type="DuckDB",
            tables=tables_info,
            total_tables=len(tables_info)
        )
        
        # 获取元数据和术语表版本
        metadata = metadata_service.get_metadata()
        glossary = glossary_service.get_glossary()
        
        status = SystemStatus(
            app_name=settings.app_name,
            version=settings.app_version,
            status="running",
            database=database_status,
            metadata_version=metadata.get('version', 'unknown'),
            glossary_version=glossary.get('version', 'unknown'),
            uptime="运行中"  # 简化实现
        )
        
        logger.info("System status retrieved successfully")
        return status
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.get("/metadata/reload")
async def reload_metadata():
    """
    重新加载元数据和术语表
    """
    try:
        metadata_service = get_metadata_service()
        glossary_service = get_glossary_service()
        
        # 强制重新加载
        metadata_changed = metadata_service.reload_if_changed()
        glossary_changed = glossary_service.reload_if_changed()
        
        result = {
            "success": True,
            "metadata_reloaded": metadata_changed,
            "glossary_reloaded": glossary_changed,
            "message": "元数据和术语表重新加载完成"
        }
        
        logger.info(f"Metadata reload: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to reload metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新加载元数据失败: {str(e)}")

@router.get("/health")
async def health_check():
    """
    健康检查接口
    """
    try:
        # 简单的健康检查：尝试获取数据库连接
        db_service = get_database_service()
        tables = db_service.get_tables()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database_tables": len(tables)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="服务不可用")

