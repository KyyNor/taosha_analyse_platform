"""
ChromaDB 向量存储实现
"""

import uuid
from typing import List, Dict, Optional
import chromadb

from services.vector_store.base import VectorStore
from utils.logger import logger


class ChromaDBStore(VectorStore):
    """ChromaDB 向量存储实现"""

    def __init__(self,
                 embedding_func,
                 collection_name: str = "taosha_knowledge",
                 persist_dir: str = None):
        """初始化 ChromaDB 存储

        Args:
            embedding_func: Embedding 函数实例
            collection_name: 集合名称
            persist_dir: 持久化目录，如果为None则使用内存模式
        """
        self.embedding_func = embedding_func
        self.collection_name = collection_name

        try:
            # 使用新的 Chroma API
            # 注意：不传 embedding_function，改用 data parameterization
            logger.info(f"初始化 ChromaDB")

            if persist_dir:
                # 持久化模式
                logger.info(f"持久化模式: {persist_dir}")
                self.client = chromadb.PersistentClient(path=persist_dir)
            else:
                # 内存模式
                logger.info("内存模式")
                self.client = chromadb.EphemeralClient()

            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"ChromaDB 初始化完成，集合名: {collection_name}")

        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise RuntimeError(f"ChromaDB 初始化失败: {e}")

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

        # 生成 ID
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # 填充元数据（ChromaDB 要求 metadata 不能为空）
        if metadatas is None:
            metadatas = [{"index": i} for i in range(len(documents))]
        else:
            # 确保每个 metadata 不为空
            metadatas = [m if m else {"index": i} for i, m in enumerate(metadatas)]

        try:
            # 计算 embeddings
            embeddings = self.embedding_func.embed_documents(documents)

            # ChromaDB 添加文档（新API）
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"向 ChromaDB 添加 {len(documents)} 个文档")
            return ids

        except Exception as e:
            logger.error(f"添加文档到 ChromaDB 失败: {e}")
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

            # 构建查询参数
            where = None
            if filters:
                where = filters

            # 执行查询（新API）
            # 注意：如果提供 allowed_ids，ChromaDB 的 query 会在这些 IDs 范围内检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                ids=allowed_ids if allowed_ids else None,  # 精准过滤：仅在指定IDs范围内查询
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # 转换结果格式
            output = []
            if results and results["ids"] and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results["documents"][0]
                distances = results["distances"][0]
                metadatas = results["metadatas"][0]

                for doc_id, content, distance, metadata in zip(ids, documents, distances, metadatas):
                    # ChromaDB 的距离是 cosine distance，转换为相似度 (1 - distance)
                    score = 1 - distance if distance is not None else 0

                    output.append({
                        "id": doc_id,
                        "content": content,
                        "score": score,
                        "metadata": metadata or {}
                    })

            logger.debug(f"搜索查询: {query[:50]}... 返回 {len(output)} 结果")
            return output

        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            raise RuntimeError(f"搜索失败: {e}")

    def delete(self, ids: List[str]):
        """删除文档"""

        if not ids:
            return

        try:
            self.collection.delete(ids=ids)
            logger.info(f"从 ChromaDB 删除 {len(ids)} 个文档")

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

        # 填充元数据
        if metadatas is None:
            metadatas = [{} for _ in documents]

        try:
            # ChromaDB 的更新实现为：删除旧文档，添加新文档
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"更新 ChromaDB 中 {len(ids)} 个文档")

        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            raise RuntimeError(f"更新失败: {e}")

    def clear(self):
        """清空所有数据"""

        try:
            # 先删除集合
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass  # 集合不存在也没关系

            # 重新获取或创建集合（不传 embedding_function）
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            logger.warning(f"已清空 ChromaDB 集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            raise RuntimeError(f"清空失败: {e}")

    def count(self) -> int:
        """获取文档总数"""

        try:
            count = self.collection.count()
            logger.debug(f"ChromaDB 集合 {self.collection_name} 包含 {count} 个文档")
            return count

        except Exception as e:
            logger.error(f"获取文档数失败: {e}")
            return 0

    def health_check(self) -> bool:
        """检查连接状态"""

        try:
            # 尝试获取集合计数
            self.collection.count()
            return True

        except Exception as e:
            logger.error(f"ChromaDB 健康检查失败: {e}")
            return False
