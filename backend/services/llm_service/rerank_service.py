"""
Rerank服务 - 基于LocalAI的文档重排序服务
"""

import requests
from typing import List, Tuple, Dict, Any, Optional
from utils.logger import logger
from utils.config import settings


class RerankService:
    """基于LocalAI的文档重排序服务

    通过HTTP API调用LocalAI的reranker功能
    """

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        """初始化Rerank服务

        Args:
            base_url: LocalAI服务的基础URL
            api_key: API密钥（LocalAI通常不需要）
            model: 使用的重排序模型名称
        """
        self.base_url = base_url or settings.embedding_base_url
        self.api_key = api_key or settings.embedding_api_key or "not-needed"
        self.model = model or settings.embedding_reranker_model

        if not self.base_url:
            raise ValueError("Rerank base URL is required")

        if not self.model:
            raise ValueError("Rerank model is required")

        try:
            logger.info(f"初始化LocalAI Rerank服务: {self.base_url}")
            logger.info(f"Rerank模型: {self.model}")

            # 测试服务可用性
            if not self.health_check():
                logger.warning("LocalAI Rerank服务可能不可用")
            else:
                logger.info("LocalAI Rerank服务初始化完成")

        except Exception as e:
            logger.error(f"LocalAI Rerank服务初始化失败: {e}")
            # Rerank服务失败不阻止系统启动，只记录警告
            logger.warning("系统将在没有重排序功能的情况下运行")

    def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Tuple[int, float]]:
        """对文档进行重排序

        Args:
            query: 查询文本
            documents: 文档文本列表
            top_k: 返回前K个结果，None表示返回所有

        Returns:
            包含(文档索引, 重排序分数)的元组列表，按分数降序排列
        """
        if not documents:
            return []

        if not self.base_url or not self.model:
            logger.warning("Rerank服务未正确配置，返回原始排序")
            return [(i, 1.0) for i in range(len(documents))]

        try:
            url = f"{self.base_url.rstrip('/')}/rerank"

            headers = {
                "Content-Type": "application/json",
            }

            # 只有当API密钥存在且不为空时才添加Authorization头
            if self.api_key and self.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_k": top_k if top_k else len(documents)
            }

            logger.debug(f"发送rerank请求: {url}, 文档数: {len(documents)}")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            # 解析响应
            if "results" in result:
                rerank_results = []
                for item in result["results"]:
                    doc_index = item.get("index", 0)
                    relevance_score = item.get("relevance_score", 0.0)
                    rerank_results.append((doc_index, relevance_score))

                # 按分数降序排序
                rerank_results.sort(key=lambda x: x[1], reverse=True)

                logger.debug(f"Rerank完成，返回 {len(rerank_results)} 个结果")
                return rerank_results
            else:
                logger.warning(f"Rerank响应格式异常: {result}")
                # 返回原始排序
                return [(i, 1.0) for i in range(len(documents))]

        except requests.exceptions.RequestException as e:
            logger.error(f"Rerank请求失败: {e}")
            # 返回原始排序
            return [(i, 1.0) for i in range(len(documents))]
        except Exception as e:
            logger.error(f"Rerank处理失败: {e}")
            # 返回原始排序
            return [(i, 1.0) for i in range(len(documents))]

    def rerank_with_metadata(self, query: str, documents: List[Dict[str, Any]],
                           content_field: str = "content", top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """对包含元数据的文档进行重排序

        Args:
            query: 查询文本
            documents: 包含元数据的文档列表
            content_field: 文档内容字段名
            top_k: 返回前K个结果

        Returns:
            重排序后的文档列表，按分数降序排列
        """
        if not documents:
            return []

        # 提取文档内容
        contents = []
        for doc in documents:
            if isinstance(doc, dict) and content_field in doc:
                contents.append(doc[content_field])
            elif isinstance(doc, str):
                contents.append(doc)
            else:
                contents.append(str(doc))

        # 进行重排序
        rerank_results = self.rerank(query, contents, top_k)

        # 重新组织文档
        reranked_docs = []
        for doc_index, score in rerank_results:
            if doc_index < len(documents):
                doc = documents[doc_index].copy() if isinstance(documents[doc_index], dict) else {"content": documents[doc_index]}
                doc["rerank_score"] = score
                reranked_docs.append(doc)

        return reranked_docs

    def health_check(self) -> bool:
        """检查LocalAI Rerank服务健康状态

        Returns:
            服务是否健康
        """
        try:
            # 尝试获取可用模型列表来测试连接
            url = f"{self.base_url.rstrip('/')}/models"

            headers = {}
            if self.api_key and self.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                models = response.json()
                # 检查reranker模型是否存在
                if "data" in models:
                    model_ids = [model.get("id", "") for model in models["data"]]
                    return any(self.model.lower() in model_id.lower() for model_id in model_ids)

            return False

        except Exception as e:
            logger.debug(f"Rerank服务健康检查失败: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """获取可用的重排序模型列表

        Returns:
            可用模型名称列表
        """
        try:
            url = f"{self.base_url.rstrip('/')}/models"

            headers = {}
            if self.api_key and self.api_key != "not-needed":
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            models = response.json()
            if "data" in models:
                return [model.get("id", "") for model in models["data"]]

            return []

        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return []


# 全局缓存实例
_rerank_service = None


def get_rerank_service() -> RerankService:
    """获取全局Rerank服务实例

    Returns:
        RerankService实例
    """
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service