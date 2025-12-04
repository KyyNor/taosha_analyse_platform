"""
Qdrant 向量存储实现
"""

import uuid
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.http.models import MatchAny, FieldCondition, Filter, MatchText
from qdrant_client.models import Distance, VectorParams, PointStruct, TextIndexParams, TokenizerType

from utils.config import settings
from utils.logger import logger
from services.llm_service.embedding_service import get_embedding_service
from services.llm_service.rerank_service import get_rerank_service


class QdrantVectorStore():
    """Qdrant 向量存储实现

    支持内存模式和远程模式
    """


    def __init__(self):
        """初始化 Qdrant 存储
        """
        self.collection_name = settings.vector_store_collection_name
        self.qdrant_url = settings.qdrant_url
        self.qdrant_api_key = settings.qdrant_api_key
        self.qdrant_timeout = settings.qdrant_timeout

        try:
            # 根据模式初始化客户端
            if not self.qdrant_url:
                raise ValueError("请配置Qdrant向量数据库URL")

            logger.info(f"初始化 Qdrant : {self.qdrant_url}")
            client_kwargs = {
                "url": self.qdrant_url,
                "timeout": self.qdrant_timeout,
            }

            if self.qdrant_api_key:
                client_kwargs["api_key"] = self.qdrant_api_key

            self.client = QdrantClient(**client_kwargs)

            # 初始化Embedding和Rerank服务
            self.embedding_service = get_embedding_service()
            self.rerank_service = get_rerank_service()

            # 获取嵌入维度
            self.embedding_dimension = self.embedding_service.embedding_dimension

            # 检查集合是否已存在，如果不存在则创建
            try:
                self.client.get_collection(self.collection_name)
                logger.info(f"找到已有的 Qdrant 集合: {self.collection_name}")
            except Exception:
                # 集合不存在，创建新集合
                logger.info(f"创建新的 Qdrant 集合: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )

            # 创建全文索引
            self._setup_fulltext_indexes()

            logger.info(f"Qdrant 初始化完成，集合名: {self.collection_name}")

        except Exception as e:
            logger.error(f"Qdrant 初始化失败: {e}")
            raise RuntimeError(f"Qdrant 初始化失败: {e}")

    def _setup_fulltext_indexes(self):
        """设置全文索引

        为payload中的文本字段创建全文索引，支持中文分词
        """
        try:
            # 为content字段创建全文索引（主要文档内容）
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="content",
                field_schema=TextIndexParams(
                    type="text",
                    tokenizer=TokenizerType.WORD,  # 使用word分词器，支持中文
                    min_token_len=1,               # 最小token长度（支持中文单字）
                    max_token_len=20,              # 最大token长度
                    lowercase=True                 # 转换为小写
                )
            )
            logger.info("已为 'content' 字段创建全文索引")

        except Exception as e:
            # 索引可能已存在，不影响使用
            logger.debug(f"设置全文索引时出现提示: {e}")

    def add(self,
            documents: List[str],
            metadatas: List[Dict] = None,
            ids: List[str] = None) -> List[str]:
        """添加文档到向量库"""

        if not documents:
            return []

        # 验证参数
        if metadatas and len(metadatas) != len(documents):
            raise ValueError(f"文档数量({len(documents)})与元数据数量({len(metadatas)})不匹配")

        if ids and len(ids) != len(documents):
            raise ValueError(f"文档数量({len(documents)})与ID数量({len(ids)})不匹配")

        # 生成 ID 和 Embedding
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        try:
            # 生成嵌入向量
            embeddings = self.embedding_service.embed_documents(documents)

            # 构建 Point 对象
            points = []
            for _id, document, metadata, embedding in zip(
                ids, documents, metadatas, embeddings
            ):
                # 将文档内容添加到元数据中
                metadata_with_content = {
                    **metadata,
                    "content": document,
                    "id": _id
                }

                point = PointStruct(
                    id=_id,
                    vector=embedding,
                    payload=metadata_with_content
                )
                points.append(point)

            # 批量插入到 Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            logger.info(f"向 Qdrant 添加 {len(documents)} 个文档")
            return ids

        except Exception as e:
            logger.error(f"添加文档到 Qdrant 失败: {e}")
            raise RuntimeError(f"添加文档失败: {e}")

    def search(self,
               query: str,
               top_k: int = 10,
               rerank_top_k: int = None,
               filters: Filter = None,
               score_threshold: float = None,
               allowed_ids: List[str] = None,
               search_mode: str = "vector_only") -> List[Dict]:
        """搜索相似文档

        支持基于 vector_id 的精准过滤，只在 allowed_ids 范围内返回结果

        Args:
            query: 查询文本
            top_k: 最终返回结果数量
            rerank_top_k: 重排序前的候选数量（默认为top_k*2）
            filters: 过滤条件
            score_threshold: 分数阈值
            allowed_ids: 允许的ID列表
            search_mode: 搜索模式，支持 "vector_only"(纯向量)、"fulltext_only"(纯全文)、"hybrid"(混合)
        """

        if not query:
            raise ValueError("查询文本不能为空")

        if top_k <= 0:
            raise ValueError(f"top_k 必须大于 0，当前值: {top_k}")

        if rerank_top_k is None or rerank_top_k < top_k:
            rerank_top_k = top_k * 2

        try:
            # 根据搜索模式选择不同的搜索策略
            if search_mode == "vector_only":
                # 纯向量搜索（原有逻辑）
                results = self._vector_search(
                    query, rerank_top_k, filters, score_threshold, allowed_ids
                )
            elif search_mode == "fulltext_only":
                # 纯全文检索
                results = self._fulltext_search(
                    query, rerank_top_k, filters, allowed_ids
                )
            elif search_mode == "hybrid":
                # 混合搜索
                results = self._hybrid_search(
                    query, rerank_top_k, filters, score_threshold, allowed_ids
                )
            else:
                raise ValueError(f"不支持的搜索模式: {search_mode}，支持的模式: vector_only, fulltext_only, hybrid")

            # 提取文档内容和元数据
            documents_with_metadata = []
            for hit in results.points:
                documents_with_metadata.append({
                    "content": hit.payload["content"],
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": hit.payload
                })

            # 使用reranker重新排序
            reranked_documents = self.rerank_service.rerank_with_metadata(
                query=query,
                documents=documents_with_metadata,
                content_field="content",
                top_k=top_k
            )

            # 格式化返回结果
            final_result = []
            for doc in reranked_documents:
                final_result.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "score": doc.get("score", 0.0),
                    "rerank_score": doc.get("rerank_score", 0.0),
                    "metadata": doc.get("metadata", {})
                })

            logger.debug(f"搜索查询 ({search_mode}): {query[:50]}... 返回 {len(final_result)} 结果（重排序后）")
            return final_result

        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            raise RuntimeError(f"搜索失败: {e}")

    def _vector_search(self,
                      query: str,
                      limit: int,
                      filters: Filter = None,
                      score_threshold: float = None,
                      allowed_ids: List[str] = None):
        """纯向量搜索（原有逻辑）"""
        if filters is None:
            filters = Filter()

        if allowed_ids:
            filters = Filter(
                must=[FieldCondition(key="id", match=MatchAny(any=allowed_ids))]
            )

        # 生成查询向量
        query_embedding = self.embedding_service.embed_query(query)

        # 执行向量搜索
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
            query_filter=filters,
            score_threshold=score_threshold,
        )

        return results

    def _fulltext_search(self,
                        query: str,
                        limit: int,
                        filters: Filter = None,
                        allowed_ids: List[str] = None):
        """纯全文检索

        使用Qdrant的全文搜索功能进行精确关键词匹配
        """
        if filters is None:
            filters = Filter(must=[])
        else:
            # 确保filters有must属性
            if not hasattr(filters, 'must') or filters.must is None:
                filters.must = []
            else:
                # 复制filters避免修改原对象
                filters = Filter(must=list(filters.must) if filters.must else [])

        # 添加全文搜索条件
        fulltext_condition = FieldCondition(
            key="content",
            match=MatchText(text=query)
        )
        filters.must.append(fulltext_condition)

        # 添加ID过滤
        if allowed_ids:
            filters.must.append(
                FieldCondition(key="id", match=MatchAny(any=allowed_ids))
            )

        # 使用scroll API进行全文检索
        scroll_result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filters,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        # 包装为与query_points相同的格式
        class SearchResult:
            def __init__(self, points):
                self.points = points

        # 为每个结果添加默认分数（全文搜索没有分数）
        points = scroll_result[0] if scroll_result else []
        for point in points:
            point.score = 1.0  # 全文匹配给予固定分数

        return SearchResult(points)

    def _hybrid_search(self,
                      query: str,
                      limit: int,
                      filters: Filter = None,
                      score_threshold: float = None,
                      allowed_ids: List[str] = None):
        """混合搜索（推荐）

        结合向量搜索和全文检索：
        1. 分别执行向量搜索和全文检索
        2. 合并结果（ID去重）
        3. 对同时命中的结果进行分数加权
        4. 按分数排序返回
        """
        # 1. 执行向量搜索
        vector_results = self._vector_search(
            query, limit, filters, score_threshold, allowed_ids
        )

        # 2. 执行全文检索
        fulltext_results = self._fulltext_search(
            query, limit, filters, allowed_ids
        )

        # 3. 合并结果（使用ID去重）
        combined_points = {}

        # 添加向量搜索结果
        for point in vector_results.points:
            combined_points[point.id] = point

        # 合并全文搜索结果
        for point in fulltext_results.points:
            if point.id in combined_points:
                # ID已存在，说明同时命中向量和关键词，增强分数
                combined_points[point.id].score = combined_points[point.id].score * 1.5
                logger.debug(f"混合搜索：文档 {point.id} 同时命中向量和全文，分数提升")
            else:
                # 新结果，添加进去（使用较低的分数，表示只有关键词匹配）
                point.score = 0.5  # 只有全文匹配的结果给予较低分数
                combined_points[point.id] = point

        # 4. 按分数排序
        sorted_points = sorted(
            combined_points.values(),
            key=lambda p: p.score,
            reverse=True
        )[:limit]

        logger.debug(
            f"混合搜索：向量结果 {len(vector_results.points)} 个，"
            f"全文结果 {len(fulltext_results.points)} 个，"
            f"合并后 {len(sorted_points)} 个"
        )

        # 包装为SearchResult
        class SearchResult:
            def __init__(self, points):
                self.points = points

        return SearchResult(sorted_points)

    def delete(self, ids: List[str]):
        """删除文档"""

        if not ids:
            return

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )

            logger.info(f"从 Qdrant 删除 {len(ids)} 个文档")

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise RuntimeError(f"删除失败: {e}")


    def clear(self):
        """清空所有数据"""

        try:
            # 删除并重新创建集合
            self.client.delete_collection(self.collection_name)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=Distance.COSINE
                )
            )

            logger.warning(f"已清空 Qdrant 集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            raise RuntimeError(f"清空失败: {e}")

    def count(self) -> int:
        """获取文档总数"""

        try:
            collection_info = self.client.get_collection(self.collection_name)
            count = collection_info.points_count
            logger.debug(f"Qdrant 集合 {self.collection_name} 包含 {count} 个文档")
            return count

        except Exception as e:
            logger.error(f"获取文档数失败: {e}")
            return 0

    def health_check(self) -> bool:
        """检查连接状态"""

        try:
            # 尝试获取集合信息
            self.client.get_collection(self.collection_name)

            # 检查embedding和rerank服务
            embedding_health = self.embedding_service.health_check()
            rerank_health = self.rerank_service.health_check()

            if not embedding_health:
                logger.warning("Embedding服务健康检查失败")

            if not rerank_health:
                logger.warning("Rerank服务健康检查失败")

            return embedding_health  # 至少embedding服务需要正常工作

        except Exception as e:
            logger.error(f"Qdrant 健康检查失败: {e}")
            return False


# 全局缓存实例
qdrant_vector_store = QdrantVectorStore()
