"""
Qdrant 向量存储实现（支持内存模式和远程模式）
"""

import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from services.vector_store.base import VectorStore
from utils.logger import logger
from utils.config import settings


class QdrantStore(VectorStore):
    """Qdrant 向量存储实现

    支持内存模式和远程模式
    """

    def __init__(self,
                 embedding_func,
                 collection_name: str = "taosha_knowledge",
                 embedding_dimension: int = 1024,
                 mode: str = "memory",
                 url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 verify: bool = True,
                 grpc_port: int = 6334,
                 prefer_grpc: bool = False):
        """初始化 Qdrant 存储

        Args:
            embedding_func: Embedding 函数实例
            collection_name: 集合名称
            embedding_dimension: Embedding 维度
            mode: 运行模式，"memory" 或 "remote"
            url: 远程Qdrant服务器URL（远程模式必需）
            api_key: 远程Qdrant API密钥（可选）
            timeout: 连接超时时间（秒）
            verify: 是否验证HTTPS证书
            grpc_port: gRPC端口
            prefer_grpc: 是否优先使用gRPC
        """
        self.embedding_func = embedding_func
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.mode = mode
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.verify = verify
        self.grpc_port = grpc_port
        self.prefer_grpc = prefer_grpc

        try:
            # 根据模式初始化客户端
            if mode == "memory":
                logger.info("初始化 Qdrant (内存模式)")
                self.client = QdrantClient(":memory:")
            elif mode == "remote":
                if not url:
                    raise ValueError("远程模式需要提供URL")
                
                logger.info(f"初始化 Qdrant (远程模式): {url}")
                client_kwargs = {
                    "url": url,
                    "timeout": timeout,
                    "verify": verify
                }
                
                if api_key:
                    client_kwargs["api_key"] = api_key
                
                if prefer_grpc:
                    client_kwargs["prefer_grpc"] = True
                    client_kwargs["grpc_port"] = grpc_port
                
                self.client = QdrantClient(**client_kwargs)
            else:
                raise ValueError(f"不支持的Qdrant模式: {mode}，支持的模式: memory, remote")

            # 检查集合是否已存在，如果不存在则创建
            try:
                self.client.get_collection(collection_name)
                logger.info(f"找到已有的 Qdrant 集合: {collection_name}")
            except Exception:
                # 集合不存在，创建新集合
                logger.info(f"创建新的 Qdrant 集合: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dimension,
                        distance=Distance.COSINE
                    )
                )

            logger.info(f"Qdrant 初始化完成，集合名: {collection_name}，模式: {mode}")

        except Exception as e:
            logger.error(f"Qdrant 初始化失败: {e}")
            raise RuntimeError(f"Qdrant 初始化失败: {e}")

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
            # 计算文档的 embedding
            embeddings = self.embedding_func.embed_documents(documents)

            # 转换 ID 为整数（Qdrant 需要）
            numeric_ids = []
            id_mapping = {}
            for idx, doc_id in enumerate(ids):
                numeric_id = hash(doc_id) & 0x7fffffff  # 转换为正整数
                numeric_ids.append(numeric_id)
                id_mapping[numeric_id] = doc_id

            # 构建 Point 对象
            points = []
            for numeric_id, embedding, document, metadata in zip(
                numeric_ids, embeddings, documents, metadatas
            ):
                # 将文档内容添加到元数据中
                metadata_with_content = {
                    **metadata,
                    "content": document,
                    "original_id": ids[numeric_ids.index(numeric_id)]
                }

                point = PointStruct(
                    id=numeric_id,
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
               top_k: int = 5,
               filters: Dict = None,
               allowed_ids: List[str] = None) -> List[Dict]:
        """搜索相似文档

        支持基于 vector_id 的精准过滤，只在 allowed_ids 范围内返回结果
        """

        if not query:
            raise ValueError("查询文本不能为空")

        if top_k <= 0:
            raise ValueError(f"top_k 必须大于 0，当前值: {top_k}")

        try:
            # 计算查询的 embedding
            query_embedding = self.embedding_func.embed_query(query)

            # 构建查询过滤条件
            query_filter = None
            if filters:
                # Qdrant 的过滤条件格式较复杂，这里先简化处理
                # 实际使用时可能需要更复杂的过滤逻辑
                pass

            # 执行搜索
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter
            )

            # 转换结果格式
            output = []
            for result in results:
                payload = result.payload or {}
                content = payload.pop("content", "")
                original_id = payload.pop("original_id", str(result.id))

                # 如果指定了 allowed_ids，进行过滤
                if allowed_ids and original_id not in allowed_ids:
                    continue

                output.append({
                    "id": original_id,
                    "content": content,
                    "score": result.score,  # Qdrant 的 cosine 距离已经是相似度
                    "metadata": payload
                })

            logger.debug(f"搜索查询: {query[:50]}... 返回 {len(output)} 结果（过滤后）")
            return output

        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            raise RuntimeError(f"搜索失败: {e}")

    def delete(self, ids: List[str]):
        """删除文档"""

        if not ids:
            return

        try:
            # 将字符串ID转换为数字ID
            numeric_ids = [hash(doc_id) & 0x7fffffff for doc_id in ids]

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=numeric_ids
            )

            logger.info(f"从 Qdrant 删除 {len(ids)} 个文档")

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise RuntimeError(f"删除失败: {e}")

    def update(self,
               ids: List[str],
               documents: List[str],
               metadatas: List[Dict] = None):
        """更新文档"""

        if not ids:
            return

        # 验证参数
        if len(ids) != len(documents):
            raise ValueError(f"ID数量({len(ids)})与文档数量({len(documents)})不匹配")

        if metadatas and len(metadatas) != len(documents):
            raise ValueError(f"文档数量({len(documents)})与元数据数量({len(metadatas)})不匹配")

        if metadatas is None:
            metadatas = [{} for _ in documents]

        try:
            # 先删除旧文档，再添加新文档
            self.delete(ids)
            self.add(documents, metadatas, ids)

            logger.info(f"更新 Qdrant 中 {len(ids)} 个文档")

        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            raise RuntimeError(f"更新失败: {e}")

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
            return True

        except Exception as e:
            logger.error(f"Qdrant 健康检查失败: {e}")
            return False
