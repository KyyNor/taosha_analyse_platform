"""
简化的查询API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import uuid
from datetime import datetime

router = APIRouter()

# 请求模型
class QueryRequest(BaseModel):
    user_question: str
    theme_id: Optional[int] = None
    table_ids: Optional[List[int]] = None
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    code: int = 0
    message: str = "查询任务已创建"
    data: Dict[str, Any]

# 模拟任务存储
MOCK_TASKS = {}

@router.post("/submit", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    """提交查询请求"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建模拟任务
        task = {
            "task_id": task_id,
            "user_question": request.user_question,
            "theme_id": request.theme_id,
            "table_ids": request.table_ids or [],
            "status": "processing",
            "current_step": "正在分析查询需求...",
            "progress_percentage": 0.1,
            "generated_sql": None,
            "sql_confidence": None,
            "result": None,
            "error_message": None,
            "error_details": None,
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "查询任务已创建",
                    "details": None
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 存储任务
        MOCK_TASKS[task_id] = task
        
        # 启动异步处理任务（模拟）
        asyncio.create_task(process_query_task(task_id))
        
        return QueryResponse(
            data={
                "task_id": task_id,
                "status": "processing",
                "message": "查询任务已创建，正在处理中..."
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交查询失败: {str(e)}")

@router.get("/status/{task_id}")
async def get_query_task(task_id: str):
    """获取查询任务状态"""
    if task_id not in MOCK_TASKS:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = MOCK_TASKS[task_id]
    return {
        "code": 0,
        "message": "获取成功",
        "data": task
    }

@router.delete("/cancel/{task_id}")
async def cancel_query_task(task_id: str):
    """取消查询任务"""
    if task_id not in MOCK_TASKS:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = MOCK_TASKS[task_id]
    if task["status"] in ["completed", "failed", "cancelled"]:
        return {
            "code": 0,
            "message": "任务已完成，无法取消",
            "data": {"task_id": task_id, "status": task["status"]}
        }
    
    # 取消任务
    task["status"] = "cancelled"
    task["current_step"] = "任务已取消"
    task["updated_at"] = datetime.now().isoformat()
    
    return {
        "code": 0,
        "message": "任务已取消",
        "data": {"task_id": task_id, "status": "cancelled"}
    }

async def process_query_task(task_id: str):
    """异步处理查询任务（模拟）"""
    if task_id not in MOCK_TASKS:
        return
    
    task = MOCK_TASKS[task_id]
    
    try:
        # 模拟处理步骤
        steps = [
            ("正在解析自然语言查询...", 0.2),
            ("正在生成SQL语句...", 0.4),
            ("正在验证SQL语法...", 0.6),
            ("正在执行查询...", 0.8),
            ("正在处理查询结果...", 0.9),
        ]
        
        for step_name, progress in steps:
            if task["status"] == "cancelled":
                return
                
            task["current_step"] = step_name
            task["progress_percentage"] = progress
            task["updated_at"] = datetime.now().isoformat()
            
            # 添加日志
            task["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": step_name,
                "details": None
            })
            
            # 模拟处理时间
            await asyncio.sleep(1)
        
        if task["status"] == "cancelled":
            return
        
        # 生成模拟SQL和结果
        user_question = task["user_question"]
        
        # 根据问题生成相应的SQL
        if "销售" in user_question or "订单" in user_question:
            sql = """SELECT 
    DATE(order_date) as date,
    COUNT(*) as order_count,
    SUM(total_amount) as total_sales
FROM orders 
WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(order_date)
ORDER BY date DESC"""
            
            result = {
                "columns": ["日期", "订单数量", "销售金额"],
                "rows": [
                    ["2024-10-08", 45, 12580.50],
                    ["2024-10-07", 38, 9750.30],
                    ["2024-10-06", 52, 15230.80],
                    ["2024-10-05", 41, 11420.60],
                    ["2024-10-04", 33, 8790.40]
                ],
                "total_count": 5,
                "execution_time_ms": 234
            }
        else:
            sql = f"""-- 根据查询需求生成的SQL
-- 查询: {user_question}
SELECT * FROM your_table 
WHERE condition = 'your_condition'
LIMIT 10"""
            
            result = {
                "columns": ["示例列1", "示例列2", "示例列3"],
                "rows": [
                    ["数据1", "数据2", "数据3"],
                    ["数据4", "数据5", "数据6"]
                ],
                "total_count": 2,
                "execution_time_ms": 156
            }
        
        # 完成任务
        task["status"] = "completed"
        task["current_step"] = "查询完成"
        task["progress_percentage"] = 1.0
        task["generated_sql"] = sql
        task["sql_confidence"] = 0.85
        task["result"] = result
        task["updated_at"] = datetime.now().isoformat()
        
        # 添加完成日志
        task["logs"].append({
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "查询执行完成",
            "details": f"返回 {result['total_count']} 条记录"
        })
        
    except Exception as e:
        # 处理错误
        task["status"] = "failed"
        task["current_step"] = "查询失败"
        task["error_message"] = str(e)
        task["error_details"] = f"处理查询时发生错误: {str(e)}"
        task["updated_at"] = datetime.now().isoformat()
        
        # 添加错误日志
        task["logs"].append({
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "message": "查询执行失败",
            "details": str(e)
        })