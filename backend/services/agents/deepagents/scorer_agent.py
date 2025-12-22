"""
评分与总结智能体

阅读分析问题和完整分析过程，给出三项评分和改进建议。
使用普通 LangChain ReAct Agent，不使用 deepagents 框架。
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from services.llm_service.base_llm_service import BaseLLMService
from services.agents.tools.deepagents.session_reader_tool import (
    read_session_info,
    read_session_report,
    read_session_llm_output,
    get_session_data
)
from models import SessionLocal
from repositories.deepagents import AnalysisScoreRepository
from utils.logger import logger


# 评分智能体系统提示词
SCORER_PROMPT = """你是淘沙分析平台的分析质量评审专家。

## 任务
阅读数据分析智能体的完整分析过程，给出专业评分和改进建议。

## 评分维度

### 1. 分析过程评分 (0-100分)
评估标准：
- 工具选择是否恰当（选用了正确的工具解决问题）
- 参数设置是否合理（SQL查询条件、时间范围等）
- 代码逻辑是否正确（Python代码无明显错误）
- 数据处理是否规范（数据清洗、转换、聚合正确）
- 分析步骤是否完整（没有遗漏关键步骤）

扣分项示例：
- SQL 语法错误 -10分
- 选错分析工具 -15分
- 代码执行失败 -20分
- 数据处理遗漏 -10分

### 2. 分析报告评分 (0-100分)
评估标准：
- 报告结构是否完整（背景、方法、结果、结论四个部分）
- 图表使用是否恰当（该用图表展示的数据使用了图表）
- 数值单位是否规范（大数字使用万/亿等合理单位）
- 可视化是否直观清晰（图表类型选择正确）
- 格式排版是否专业（标题层级、段落结构清晰）

扣分项示例：
- 缺少分析结论 -20分
- 应该用图表但只用了文字 -15分
- 数字未做单位转换（如直接显示10000000元） -10分
- 报告结构混乱 -15分

### 3. 分析结论评分 (0-100分)
评估标准：
- 是否直接回答了用户问题（核心问题得到解答）
- 结论是否有数据支撑（每个结论都有数据来源）
- 是否有遗漏的分析角度（考虑了主要影响因素）
- 建议是否具有可操作性（给出了具体的行动建议）

扣分项示例：
- 未回答核心问题 -30分
- 结论缺乏数据支撑 -20分
- 遗漏重要分析维度 -15分
- 建议过于笼统 -10分

## 输出格式
请严格按照以下 JSON 格式输出：
```json
{
    "process_score": {
        "score": 85,
        "reasons": ["使用了正确的SQL查询工具", "数据处理逻辑清晰"],
        "deductions": ["部分查询参数可以优化"]
    },
    "report_score": {
        "score": 80,
        "reasons": ["报告结构完整", "使用了柱状图展示趋势"],
        "deductions": ["数字单位未做转换", "缺少图表标题"]
    },
    "conclusion_score": {
        "score": 90,
        "reasons": ["直接回答了用户问题", "结论有数据支撑"],
        "deductions": ["可增加更多维度的分析"]
    },
    "overall_score": 85,
    "improvement_suggestions": [
        {
            "category": "prompt",
            "suggestion": "在系统提示中增加数值单位规范要求",
            "priority": "high"
        },
        {
            "category": "tool",
            "suggestion": "增加数据校验工具，确保查询结果的完整性",
            "priority": "medium"
        },
        {
            "category": "code",
            "suggestion": "代码中增加异常处理逻辑",
            "priority": "low"
        }
    ]
}
```

注意：
- 每项评分必须在 0-100 之间
- overall_score 是三项评分的加权平均（过程40%、报告30%、结论30%）
- improvement_suggestions 的 category 必须是: prompt/tool/code/other
- priority 必须是: high/medium/low
"""


class ScorerAgent:
    """评分与总结智能体"""

    def __init__(self):
        """初始化评分智能体"""
        self.llm_service = BaseLLMService()
        self.agent = None

        logger.info("ScorerAgent 初始化完成")

    def create_agent(self) -> None:
        """创建 Agent 实例"""
        try:
            tools = [
                read_session_info,
                read_session_report,
                read_session_llm_output,
            ]

            self.agent = create_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt=SCORER_PROMPT,
            )

            logger.info("ScorerAgent Agent 创建成功")

        except Exception as e:
            logger.error(f"ScorerAgent Agent 创建失败: {e}")
            raise

    def evaluate_session(self, session_id: str) -> Dict[str, Any]:
        """评估分析会话

        Args:
            session_id: 分析会话ID

        Returns:
            包含评分结果的字典
        """
        if not self.agent:
            self.create_agent()

        start_time = datetime.now()

        # 构建用户消息
        user_message = f"""请评估分析会话 {session_id}。

请按以下步骤操作：
1. 使用 read_session_info 工具获取会话基本信息
2. 使用 read_session_llm_output 工具读取完整的分析过程
3. 使用 read_session_report 工具读取生成的分析报告
4. 根据评分标准给出三项评分和改进建议

请确保输出格式符合要求的 JSON 结构。"""

        try:
            # 执行 Agent
            result = self.agent.invoke({
                "messages": [HumanMessage(content=user_message)]
            })

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 提取 AI 输出
            ai_output = self._extract_ai_output(result)

            # 解析评分 JSON
            scores_data = self._parse_scores_json(ai_output)

            logger.info(f"评分完成，耗时: {duration:.2f}秒")

            return {
                "success": True,
                "session_id": session_id,
                "process_score": scores_data.get("process_score", {}),
                "report_score": scores_data.get("report_score", {}),
                "conclusion_score": scores_data.get("conclusion_score", {}),
                "overall_score": scores_data.get("overall_score", 0),
                "improvement_suggestions": scores_data.get("improvement_suggestions", []),
                "raw_output": ai_output,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"评分失败: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
            }

    def evaluate_and_save(self, session_id: str) -> Dict[str, Any]:
        """评估分析会话并保存评分结果到数据库

        Args:
            session_id: 分析会话ID

        Returns:
            包含评分结果的字典
        """
        # 执行评估
        result = self.evaluate_session(session_id)

        if not result.get("success"):
            return result

        # 保存到数据库
        try:
            db = SessionLocal()
            try:
                score_repo = AnalysisScoreRepository(db)

                process_score = result.get("process_score", {})
                report_score = result.get("report_score", {})
                conclusion_score = result.get("conclusion_score", {})

                score_repo.save_scores(
                    session_id=session_id,
                    process_score=process_score.get("score", 0),
                    process_reasons=process_score.get("reasons", []),
                    process_deductions=process_score.get("deductions", []),
                    report_score=report_score.get("score", 0),
                    report_reasons=report_score.get("reasons", []),
                    report_deductions=report_score.get("deductions", []),
                    conclusion_score=conclusion_score.get("score", 0),
                    conclusion_reasons=conclusion_score.get("reasons", []),
                    conclusion_deductions=conclusion_score.get("deductions", []),
                    overall_score=result.get("overall_score", 0),
                    improvement_suggestions=result.get("improvement_suggestions", []),
                    scorer_model=self.llm_service.model_name if hasattr(self.llm_service, 'model_name') else None
                )

                result["saved_to_db"] = True
                logger.info(f"评分结果已保存到数据库: {session_id}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"保存评分结果失败: {e}")
            result["saved_to_db"] = False
            result["save_error"] = str(e)

        return result

    def _extract_ai_output(self, result: Dict[str, Any]) -> str:
        """从结果中提取 AI 输出"""
        try:
            messages = result.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        return str(msg.content)
            return ""
        except Exception as e:
            logger.warning(f"提取 AI 输出失败: {e}")
            return ""

    def _parse_scores_json(self, output: str) -> Dict[str, Any]:
        """从 AI 输出中解析评分 JSON

        Args:
            output: AI 输出文本

        Returns:
            解析后的评分数据
        """
        try:
            # 尝试直接解析
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 结构
        brace_match = re.search(r"\{[\s\S]*\}", output)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("无法解析评分 JSON，返回默认结构")
        return {
            "process_score": {"score": 0, "reasons": [], "deductions": ["无法解析评分"]},
            "report_score": {"score": 0, "reasons": [], "deductions": ["无法解析评分"]},
            "conclusion_score": {"score": 0, "reasons": [], "deductions": ["无法解析评分"]},
            "overall_score": 0,
            "improvement_suggestions": []
        }


# 便捷函数
def create_scorer_agent() -> ScorerAgent:
    """创建评分智能体实例"""
    agent = ScorerAgent()
    agent.create_agent()
    return agent
