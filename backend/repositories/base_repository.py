"""
通用Repository基类
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from models.base import get_db_session
from utils.logger import logger

# 泛型类型变量
T = TypeVar('T')


class BaseRepository(Generic[T]):
    """通用Repository基类"""

    def __init__(self, model_class: Type[T]):
        """
        初始化Repository

        Args:
            model_class: SQLAlchemy模型类
        """
        self.model_class = model_class

    def create(self, **kwargs) -> T:
        """
        创建新记录

        Args:
            **kwargs: 模型字段参数

        Returns:
            创建的模型实例
        """
        try:
            with get_db_session() as db:
                instance = self.model_class(**kwargs)
                db.add(instance)
                db.flush()  # 确保获取到ID
                db.refresh(instance)  # 刷新实例，获取数据库生成的值
                # 将实例状态设置为持久化，避免会话关闭后访问出错
                db.expunge(instance)  # 从会话中分离实例
                logger.info(f"创建 {self.model_class.__name__} 记录成功: ID={instance.id}")
                return instance
        except SQLAlchemyError as e:
            logger.error(f"创建 {self.model_class.__name__} 记录失败: {e}")
            raise

    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据ID获取记录

        Args:
            id: 记录ID

        Returns:
            模型实例或None
        """
        try:
            with get_db_session() as db:
                return db.query(self.model_class).filter(self.model_class.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"获取 {self.model_class.__name__} 记录失败: {e}")
            raise

    def get_all(self, **filters) -> List[T]:
        """
        获取所有记录

        Args:
            **filters: 过滤条件

        Returns:
            模型实例列表
        """
        try:
            with get_db_session() as db:
                query = db.query(self.model_class)

                # 应用过滤条件
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)

                return query.all()
        except SQLAlchemyError as e:
            logger.error(f"获取 {self.model_class.__name__} 记录列表失败: {e}")
            raise

    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        更新记录

        Args:
            id: 记录ID
            **kwargs: 更新字段

        Returns:
            更新后的模型实例或None
        """
        try:
            with get_db_session() as db:
                instance = db.query(self.model_class).filter(self.model_class.id == id).first()
                if instance:
                    for key, value in kwargs.items():
                        if hasattr(instance, key):
                            setattr(instance, key, value)
                    db.flush()
                    db.refresh(instance)
                    db.expunge(instance)  # 从会话中分离实例
                    logger.info(f"更新 {self.model_class.__name__} 记录成功: ID={id}")
                    return instance
                return None
        except SQLAlchemyError as e:
            logger.error(f"更新 {self.model_class.__name__} 记录失败: {e}")
            raise

    def delete(self, id: int) -> bool:
        """
        删除记录

        Args:
            id: 记录ID

        Returns:
            是否删除成功
        """
        try:
            with get_db_session() as db:
                instance = db.query(self.model_class).filter(self.model_class.id == id).first()
                if instance:
                    db.delete(instance)
                    logger.info(f"删除 {self.model_class.__name__} 记录成功: ID={id}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"删除 {self.model_class.__name__} 记录失败: {e}")
            raise

    def count(self, **filters) -> int:
        """
        统计记录数量

        Args:
            **filters: 过滤条件

        Returns:
            记录数量
        """
        try:
            with get_db_session() as db:
                query = db.query(self.model_class)

                # 应用过滤条件
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)

                return query.count()
        except SQLAlchemyError as e:
            logger.error(f"统计 {self.model_class.__name__} 记录数量失败: {e}")
            raise

    def exists(self, **filters) -> bool:
        """
        检查记录是否存在

        Args:
            **filters: 过滤条件

        Returns:
            是否存在
        """
        try:
            with get_db_session() as db:
                query = db.query(self.model_class)

                # 应用过滤条件
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)

                return query.first() is not None
        except SQLAlchemyError as e:
            logger.error(f"检查 {self.model_class.__name__} 记录存在性失败: {e}")
            raise

    def get_paginated(self, page: int = 1, page_size: int = 20, **filters) -> Dict[str, Any]:
        """
        分页获取记录

        Args:
            page: 页码
            page_size: 每页数量
            **filters: 过滤条件

        Returns:
            包含分页信息的字典
        """
        try:
            with get_db_session() as db:
                query = db.query(self.model_class)

                # 应用过滤条件
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)

                # 计算总数
                total = query.count()

                # 应用分页
                offset = (page - 1) * page_size
                items = query.offset(offset).limit(page_size).all()

                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
        except SQLAlchemyError as e:
            logger.error(f"分页获取 {self.model_class.__name__} 记录失败: {e}")
            raise