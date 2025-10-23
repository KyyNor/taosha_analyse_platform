"""
向量存储抽象基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class VectorStore(ABC):
    """向量存储抽象基类

    定义向量库的统一接口，支持 ChromaDB、Qdrant 等多种实现
    """

    @abstractmethod
    def add(self,
            documents: List[str],
            metadatas: List[Dict] = None,
            ids: List[str] = None) -> List[str]:
        """添加文档到向量库

        Args:
            documents: 文档内容列表
            metadatas: 文档元数据列表，与 documents 一一对应
            ids: 文档ID列表，如果为None则自动生成

        Returns:
            添加成功的文档ID列表

        Raises:
            ValueError: 参数验证失败时抛出
        """
        pass

    @abstractmethod
    def search(self,
               query: str,
               top_k: int = 5,
               filters: Dict = None,
               allowed_ids: List[str] = None) -> List[Dict]:
        """搜索相似文档

        Args:
            query: 查询文本
            top_k: 返回结果数量，默认5
            filters: 过滤条件，键值对形式
                   例如: {"type": "table", "is_available": 0}
            allowed_ids: 限制搜索的文档ID列表，仅返回这些ID的文档
                        用于基于表选择的精准过滤

        Returns:
            搜索结果列表，每个结果包含：
            {
                "id": "文档ID",
                "content": "文档内容",
                "score": 0.95,  # 相似度分数，0-1之间
                "metadata": {...}  # 文档元数据
            }

        Raises:
            ValueError: 查询参数错误时抛出
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        """删除文档

        Args:
            ids: 要删除的文档ID列表

        Raises:
            ValueError: ID不存在时抛出
        """
        pass

    @abstractmethod
    def update(self,
               ids: List[str],
               documents: List[str],
               metadatas: List[Dict] = None):
        """更新文档

        Args:
            ids: 文档ID列表
            documents: 更新后的文档内容列表
            metadatas: 更新后的元数据列表

        Raises:
            ValueError: 参数验证失败或ID不存在时抛出
        """
        pass

    @abstractmethod
    def clear(self):
        """清空所有数据

        注意：此操作不可恢复
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """获取向量库中的文档总数

        Returns:
            文档总数
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """检查向量库连接状态

        Returns:
            True 表示连接正常，False 表示连接异常
        """
        pass
