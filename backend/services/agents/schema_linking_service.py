"""
Schema Linking智能筛选服务

两阶段Schema筛选流程：
1. 向量检索召回候选表（top_k=10）
2. LLM精确筛选最相关表（top_k=3-5）

使用Few-Shot提示提高筛选准确性。
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from utils.logger import LoggerMixin
from utils.config import settings
from models.prompt_templates import SchemaLinkingTemplates
from repositories.metadata_repository import MetadataTableRepository


class SchemaLinkingResult:
    """Schema Linking结果"""

    def __init__(
        self,
        selected_tables: List[str],
        reasoning: str,
        candidate_count: int,
        use_fallback: bool = False
    ):
        self.selected_tables = selected_tables
        self.reasoning = reasoning
        self.candidate_count = candidate_count
        self.use_fallback = use_fallback

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "selected_tables": self.selected_tables,
            "reasoning": self.reasoning,
            "candidate_count": self.candidate_count,
            "use_fallback": self.use_fallback
        }


class SchemaLinkingService(LoggerMixin):
    """Schema Linking智能筛选服务

    使用两阶段筛选流程：
    1. 向量检索召回候选表
    2. LLM精确筛选最相关表
    """

    # 配置参数
    DEFAULT_CANDIDATE_TOP_K = 10  # 向量检索召回数量
    DEFAULT_SELECTED_TOP_K = 5    # LLM筛选最大数量
    MIN_SELECTED_TABLES = 1       # 最少选择表数量
    MAX_TOKENS = 2000             # LLM最大token数

    def __init__(self, db: Session, llm_service=None):
        """初始化Schema Linking服务

        Args:
            db: 数据库会话
            llm_service: LLM服务（可选，用于测试）
        """
        self.db = db
        self.table_repo = MetadataTableRepository(db)

        # 向量存储（延迟初始化）
        self.vector_store = None
        self._init_vector_store()

        # LLM服务（如果提供）
        self.llm_service = llm_service

        # 缓存（避免重复筛选）
        self._cache: Dict[str, SchemaLinkingResult] = {}

    def _init_vector_store(self):
        """初始化向量存储（处理Qdrant未配置的情况）"""
        try:
            from services.vector_store.qdrant_vector_store import qdrant_vector_store
            self.vector_store = qdrant_vector_store
            self.logger.info("向量存储初始化成功")
        except Exception as e:
            self.logger.warning(f"向量存储初始化失败: {e}，向量检索功能将不可用")
            self.vector_store = None

    async def select_relevant_tables(
        self,
        question: str,
        candidate_top_k: int = DEFAULT_CANDIDATE_TOP_K,
        selected_top_k: int = DEFAULT_SELECTED_TOP_K,
        use_cache: bool = True,
        force_fallback: bool = False
    ) -> SchemaLinkingResult:
        """选择相关表（两阶段筛选）

        Args:
            question: 用户问题
            candidate_top_k: 候选表数量
            selected_top_k: 选择的表数量
            use_cache: 是否使用缓存
            force_fallback: 强制使用降级策略

        Returns:
            SchemaLinkingResult
        """
        # 检查缓存
        cache_key = f"{question}:{candidate_top_k}:{selected_top_k}"
        if use_cache and cache_key in self._cache:
            self.logger.debug(f"从缓存获取Schema Linking结果: {cache_key}")
            return self._cache[cache_key]

        try:
            # 第一阶段：向量检索召回候选表
            self.logger.info(f"第一阶段：向量检索召回候选表（top_k={candidate_top_k}）")
            candidate_results = await self._vector_retrieve_candidate_tables(
                question,
                top_k=candidate_top_k
            )

            if not candidate_results:
                self.logger.warning("向量检索未找到候选表")
                return SchemaLinkingResult(
                    selected_tables=[],
                    reasoning="向量检索未找到相关表",
                    candidate_count=0,
                    use_fallback=True
                )

            self.logger.info(f"向量检索召回 {len(candidate_results)} 个候选表")

            # 如果强制降级或没有LLM服务，直接返回向量检索结果
            if force_fallback or not self.llm_service:
                self.logger.info("使用降级策略：直接返回向量检索结果")
                result = SchemaLinkingResult(
                    selected_tables=[r["table_name"] for r in candidate_results[:selected_top_k]],
                    reasoning=f"向量检索召回的前{min(selected_top_k, len(candidate_results))}个表",
                    candidate_count=len(candidate_results),
                    use_fallback=True
                )
                if use_cache:
                    self._cache[cache_key] = result
                return result

            # 第二阶段：LLM精确筛选
            self.logger.info(f"第二阶段：LLM精确筛选（max_k={selected_top_k}）")
            result = await self._llm_filter_tables(
                question,
                candidate_results,
                max_selected=selected_top_k
            )

            # 缓存结果
            if use_cache:
                self._cache[cache_key] = result

            return result

        except Exception as e:
            self.logger.error(f"Schema Linking筛选失败: {e}")
            # 降级：返回向量检索结果
            self.logger.info("使用降级策略：返回向量检索结果")
            return SchemaLinkingResult(
                selected_tables=[],
                reasoning=f"Schema Linking失败: {str(e)}",
                candidate_count=0,
                use_fallback=True
            )

    async def _vector_retrieve_candidate_tables(
        self,
        question: str,
        top_k: int = 10
    ) -> List[Dict]:
        """向量检索候选表

        Args:
            question: 用户问题
            top_k: 召回数量

        Returns:
            候选表列表，每个元素包含表名、schema摘要、分数等信息
        """
        try:
            # 检查向量存储是否可用
            if not self.vector_store:
                self.logger.warning("向量存储不可用，无法进行向量检索")
                return []

            # 使用向量存储检索相关表
            search_results = self.vector_store.search(
                query_text=question,
                collection_name="table",  # 表向量集合
                limit=top_k
            )

            if not search_results:
                return []

            # 解析搜索结果
            candidates = []
            for result in search_results:
                metadata = result.get("metadata", {})
                table_name = metadata.get("table_name", "")
                score = result.get("score", 0.0)

                if table_name:
                    candidates.append({
                        "table_name": table_name,
                        "score": score,
                        "summary": result.get("payload", ""),  # Schema摘要
                        "metadata": metadata
                    })

            self.logger.info(f"向量检索召回 {len(candidates)} 个候选表")
            return candidates

        except Exception as e:
            self.logger.error(f"向量检索失败: {e}")
            return []

    async def _llm_filter_tables(
        self,
        question: str,
        candidate_tables: List[Dict],
        max_selected: int = 5
    ) -> SchemaLinkingResult:
        """使用LLM筛选最相关的表

        Args:
            question: 用户问题
            candidate_tables: 候选表列表
            max_selected: 最大选择数量

        Returns:
            SchemaLinkingResult
        """
        try:
            # 构建候选表描述
            candidate_descriptions = []
            for idx, table in enumerate(candidate_tables, 1):
                table_name = table["table_name"]
                summary = table.get("summary", "")

                # 提取关键信息（避免上下文过长）
                description = self._extract_table_description(table_name, summary)
                candidate_descriptions.append(f"{idx}. {description}")

            candidate_text = "\n".join(candidate_descriptions)

            # 获取Few-Shot模板
            template = SchemaLinkingTemplates.get_template(use_simple=False)
            prompt = template.format(
                question=question,
                candidate_tables=candidate_text
            )

            # 调用LLM
            self.logger.debug(f"LLM筛选提示词长度: {len(prompt)} 字符")
            response = await self._call_llm_async(prompt)

            # 解析LLM响应
            result = self._parse_llm_response(response, candidate_tables)

            # 验证结果
            if not result["selected_tables"]:
                self.logger.warning("LLM未选择任何表，使用向量检索top 3")
                result["selected_tables"] = [
                    t["table_name"] for t in candidate_tables[:3]
                ]
                result["use_fallback"] = True

            return SchemaLinkingResult(
                selected_tables=result["selected_tables"],
                reasoning=result["reasoning"],
                candidate_count=len(candidate_tables),
                use_fallback=result.get("use_fallback", False)
            )

        except Exception as e:
            self.logger.error(f"LLM筛选失败: {e}")
            # 降级：返回向量检索top 3
            return SchemaLinkingResult(
                selected_tables=[t["table_name"] for t in candidate_tables[:3]],
                reasoning=f"LLM筛选失败: {str(e)}，使用向量检索top 3",
                candidate_count=len(candidate_tables),
                use_fallback=True
            )

    def _extract_table_description(self, table_name: str, summary: str) -> str:
        """从Schema摘要中提取表描述（避免上下文过长）

        Args:
            table_name: 表名
            summary: 完整Schema摘要

        Returns:
            简化的表描述
        """
        # 提取表注释和关键字段
        lines = summary.split('\n')

        description_parts = [f"**{table_name}**:"]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 表注释
            if "表注释：" in line or "表描述:" in line:
                description_parts.append(line)

            # 字段信息（限制数量）
            if line.startswith(("1.", "2.", "3.", "4.", "5.")):
                # 只保留前5个字段的描述
                description_parts.append(line)

            # 关键字段标记
            if "关键字段" in line:
                description_parts.append(line)

        # 限制长度
        full_description = " ".join(description_parts)
        if len(full_description) > 300:
            # 截断到300字符
            full_description = full_description[:297] + "..."

        return full_description

    async def _call_llm_async(self, prompt: str) -> str:
        """异步调用LLM

        Args:
            prompt: 提示词

        Returns:
            LLM响应
        """
        try:
            if not self.llm_service:
                raise ValueError("LLM服务未配置")

            # 假设LLM服务支持异步调用
            if asyncio.iscoroutinefunction(self.llm_service.generate):
                response = await self.llm_service.generate(
                    prompt=prompt,
                    max_tokens=self.MAX_TOKENS,
                    temperature=0.1  # 低温度，更确定性的输出
                )
            else:
                # 同步LLM，在线程池中运行
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.llm_service.generate(
                        prompt=prompt,
                        max_tokens=self.MAX_TOKENS,
                        temperature=0.1
                    )
                )

            return response

        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise

    def _parse_llm_response(self, response: str, candidate_tables: List[Dict]) -> Dict:
        """解析LLM响应

        Args:
            response: LLM响应文本
            candidate_tables: 候选表列表（用于验证）

        Returns:
            解析结果字典
        """
        try:
            # 尝试解析JSON响应
            # 提取JSON代码块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            # 解析JSON
            result = json.loads(json_str)

            # 验证表名
            selected_tables = result.get("selected_tables", [])
            valid_table_names = {t["table_name"] for t in candidate_tables}

            # 过滤无效表名
            valid_tables = [t for t in selected_tables if t in valid_table_names]

            if len(valid_tables) != len(selected_tables):
                self.logger.warning(
                    f"LLM返回的部分表名不在候选表中，已过滤: "
                    f"{set(selected_tables) - valid_table_names}"
                )

            return {
                "selected_tables": valid_tables,
                "reasoning": result.get("reasoning", "未提供理由"),
                "use_fallback": False
            }

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            # 尝试从文本中提取表名
            return self._extract_tables_from_text(response, candidate_tables)

        except Exception as e:
            self.logger.error(f"解析LLM响应失败: {e}")
            return {
                "selected_tables": [],
                "reasoning": f"解析失败: {str(e)}",
                "use_fallback": True
            }

    def _extract_tables_from_text(self, text: str, candidate_tables: List[Dict]) -> Dict:
        """从文本中提取表名（降级策略）

        Args:
            text: LLM响应文本
            candidate_tables: 候选表列表

        Returns:
            解析结果字典
        """
        valid_table_names = {t["table_name"] for t in candidate_tables}
        found_tables = []

        for table_name in valid_table_names:
            if table_name in text:
                found_tables.append(table_name)

        return {
            "selected_tables": found_tables,
            "reasoning": "从文本中提取表名",
            "use_fallback": True
        }

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self.logger.info("Schema Linking缓存已清空")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys())
        }
