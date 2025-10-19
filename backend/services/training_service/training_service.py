"""
训练服务 - 管理SQL训练数据和Vanna模型训练
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from utils.logger import logger
from repositories.training_repository import (
    TrainingDataRepository,
    TrainingSessionRepository,
    TrainingMetricsRepository,
    SQLValidationResultRepository
)


class TrainingService:
    """训练数据和会话管理服务"""

    def __init__(self, db: Session):
        """初始化训练服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.training_repo = TrainingDataRepository(db)
        self.session_repo = TrainingSessionRepository(db)
        self.metrics_repo = TrainingMetricsRepository(db)
        self.validation_repo = SQLValidationResultRepository(db)

        logger.info("TrainingService 初始化完成")

    # ========== 训练数据管理 ==========

    def add_training_data(self,
                         question: str,
                         sql: str,
                         category: str = "general",
                         difficulty: str = "medium",
                         tags: str = "",
                         source: str = "manual",
                         created_by: str = "system") -> Optional[Dict[str, Any]]:
        """添加训练数据

        Args:
            question: 自然语言问题
            sql: 对应的SQL语句
            category: 查询分类
            difficulty: 难度等级
            tags: 标签
            source: 数据来源
            created_by: 创建者

        Returns:
            创建的训练数据字典或None
        """
        try:
            logger.info(f"添加训练数据: category={category}, difficulty={difficulty}")

            training_data = self.training_repo.create(
                question=question,
                sql=sql,
                category=category,
                difficulty=difficulty,
                tags=tags,
                source=source,
                created_by=created_by,
                quality_score=0.5,  # 初始质量评分
                is_verified=False
            )

            return {
                "id": training_data.id,
                "question": training_data.question,
                "sql": training_data.sql,
                "category": training_data.category,
                "difficulty": training_data.difficulty,
                "created_at": training_data.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"添加训练数据失败: {e}")
            return None

    def batch_import_training_data(self, data_list: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量导入训练数据

        Args:
            data_list: 训练数据列表，每个元素包含：
                - question: 自然语言问题
                - sql: SQL语句
                - category: 分类（可选）
                - difficulty: 难度（可选）

        Returns:
            导入统计字典
        """
        try:
            logger.info(f"批量导入训练数据: {len(data_list)} 条")

            success_count = 0
            failed_count = 0
            errors = []

            for idx, data in enumerate(data_list):
                try:
                    question = data.get("question", "")
                    sql = data.get("sql", "")

                    if not question or not sql:
                        failed_count += 1
                        errors.append(f"行 {idx + 1}: 问题或SQL为空")
                        continue

                    result = self.add_training_data(
                        question=question,
                        sql=sql,
                        category=data.get("category", "general"),
                        difficulty=data.get("difficulty", "medium"),
                        tags=data.get("tags", ""),
                        source="imported"
                    )

                    if result:
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    failed_count += 1
                    errors.append(f"行 {idx + 1}: {str(e)}")

            logger.info(f"批量导入完成: 成功={success_count}, 失败={failed_count}")

            return {
                "total": len(data_list),
                "success": success_count,
                "failed": failed_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"批量导入训练数据失败: {e}")
            return {"total": len(data_list), "success": 0, "failed": len(data_list), "errors": [str(e)]}

    def get_training_data(self, training_id: int) -> Optional[Dict[str, Any]]:
        """获取训练数据

        Args:
            training_id: 训练数据ID

        Returns:
            训练数据字典或None
        """
        try:
            training_data = self.training_repo.get_by_id(training_id)
            if not training_data:
                return None

            return {
                "id": training_data.id,
                "question": training_data.question,
                "sql": training_data.sql,
                "category": training_data.category,
                "difficulty": training_data.difficulty,
                "tags": training_data.tags,
                "quality_score": training_data.quality_score,
                "is_verified": training_data.is_verified,
                "usage_count": training_data.usage_count,
                "success_count": training_data.success_count,
                "source": training_data.source,
                "created_at": training_data.created_at.isoformat(),
                "updated_at": training_data.updated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"获取训练数据失败: {e}")
            return None

    def update_training_data(self, training_id: int, **kwargs) -> bool:
        """更新训练数据

        Args:
            training_id: 训练数据ID
            **kwargs: 更新的字段

        Returns:
            是否成功
        """
        try:
            self.training_repo.update(training_id, **kwargs)
            logger.info(f"更新训练数据 {training_id} 成功")
            return True
        except Exception as e:
            logger.error(f"更新训练数据失败: {e}")
            return False

    def delete_training_data(self, training_id: int) -> bool:
        """删除训练数据

        Args:
            training_id: 训练数据ID

        Returns:
            是否成功
        """
        try:
            self.training_repo.delete(training_id)
            self.db.flush()  # 确保删除被提交到数据库
            logger.info(f"删除训练数据 {training_id} 成功")
            return True
        except Exception as e:
            logger.error(f"删除训练数据失败: {e}")
            return False

    def verify_training_data(self, training_id: int, notes: str = "") -> bool:
        """验证训练数据

        Args:
            training_id: 训练数据ID
            notes: 验证备注

        Returns:
            是否成功
        """
        try:
            self.training_repo.update(
                training_id,
                is_verified=True,
                verification_notes=notes
            )
            logger.info(f"验证训练数据 {training_id} 成功")
            return True
        except Exception as e:
            logger.error(f"验证训练数据失败: {e}")
            return False

    def search_training_data(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索训练数据

        Args:
            keyword: 搜索关键字
            limit: 返回数量限制

        Returns:
            训练数据列表
        """
        try:
            results = self.training_repo.search_by_question(keyword, limit)
            return [
                {
                    "id": r.id,
                    "question": r.question,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "is_verified": r.is_verified
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"搜索训练数据失败: {e}")
            return []

    def get_training_data_statistics(self) -> Dict[str, Any]:
        """获取训练数据统计信息

        Returns:
            统计信息字典
        """
        try:
            stats = self.training_repo.get_statistics()
            logger.info(f"训练数据统计: {stats}")
            return stats
        except Exception as e:
            logger.error(f"获取训练数据统计失败: {e}")
            return {}

    # ========== 训练会话管理 ==========

    def create_training_session(self,
                               session_name: str,
                               session_type: str = "manual",
                               notes: str = "",
                               created_by: str = "system") -> Optional[Dict[str, Any]]:
        """创建训练会话

        Args:
            session_name: 会话名称
            session_type: 会话类型（manual/auto/scheduled）
            notes: 会话备注
            created_by: 创建者

        Returns:
            创建的会话字典或None
        """
        try:
            logger.info(f"创建训练会话: {session_name}")

            session = self.session_repo.create(
                session_name=session_name,
                session_type=session_type,
                status="pending",
                notes=notes,
                created_by=created_by
            )

            return {
                "id": session.id,
                "name": session.session_name,
                "status": session.status,
                "created_at": session.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"创建训练会话失败: {e}")
            return None

    def start_training_session(self, session_id: int) -> bool:
        """启动训练会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        try:
            self.session_repo.update_session_progress(session_id, status="running")
            logger.info(f"启动训练会话 {session_id} 成功")
            return True
        except Exception as e:
            logger.error(f"启动训练会话失败: {e}")
            return False

    def complete_training_session(self,
                                 session_id: int,
                                 success_rate: float = 0.0,
                                 avg_confidence: float = 0.0,
                                 training_time: float = 0.0) -> bool:
        """完成训练会话

        Args:
            session_id: 会话ID
            success_rate: 成功率
            avg_confidence: 平均置信度
            training_time: 训练耗时

        Returns:
            是否成功
        """
        try:
            self.session_repo.complete_session(
                session_id,
                success_rate=success_rate,
                avg_confidence=avg_confidence,
                training_time=training_time
            )
            logger.info(f"完成训练会话 {session_id} 成功")
            return True
        except Exception as e:
            logger.error(f"完成训练会话失败: {e}")
            return False

    def get_training_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """获取训练会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典或None
        """
        try:
            return self.session_repo.get_session_summary(session_id)
        except Exception as e:
            logger.error(f"获取训练会话失败: {e}")
            return None

    def get_recent_training_sessions(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的训练会话

        Args:
            days: 天数范围
            limit: 返回数量限制

        Returns:
            会话列表
        """
        try:
            sessions = self.session_repo.get_recent_sessions(days, limit)
            return [
                {
                    "id": s.id,
                    "name": s.session_name,
                    "status": s.status,
                    "success_rate": s.success_rate,
                    "created_at": s.created_at.isoformat()
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"获取最近训练会话失败: {e}")
            return []

    # ========== 验证结果管理 ==========

    def record_validation_result(self,
                                training_data_id: Optional[int],
                                original_sql: str,
                                executed_sql: str,
                                is_valid: bool = False,
                                validation_message: str = "",
                                error_message: str = "",
                                execution_time_ms: float = 0.0,
                                row_count: int = 0,
                                execution_status: str = "success") -> Optional[Dict[str, Any]]:
        """记录SQL验证结果

        Args:
            training_data_id: 关联的训练数据ID
            original_sql: 原始SQL
            executed_sql: 执行的SQL
            is_valid: 是否有效
            validation_message: 验证信息
            error_message: 错误信息
            execution_time_ms: 执行耗时
            row_count: 返回行数
            execution_status: 执行状态

        Returns:
            验证结果字典或None
        """
        try:
            result = self.validation_repo.create(
                training_data_id=training_data_id,
                original_sql=original_sql,
                executed_sql=executed_sql,
                is_valid=is_valid,
                validation_message=validation_message,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
                row_count=row_count,
                execution_status=execution_status
            )

            return {
                "id": result.id,
                "is_valid": result.is_valid,
                "execution_status": result.execution_status,
                "execution_time_ms": result.execution_time_ms,
                "row_count": result.row_count
            }

        except Exception as e:
            logger.error(f"记录验证结果失败: {e}")
            return None

    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息

        Returns:
            统计信息字典
        """
        try:
            stats = self.validation_repo.get_validation_statistics()
            logger.info(f"验证统计: {stats}")
            return stats
        except Exception as e:
            logger.error(f"获取验证统计失败: {e}")
            return {}

    def get_failed_validations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取验证失败的记录

        Args:
            limit: 返回数量限制

        Returns:
            失败记录列表
        """
        try:
            results = self.validation_repo.get_failed_validations(limit)
            return [
                {
                    "id": r.id,
                    "original_sql": r.original_sql,
                    "error_message": r.error_message,
                    "created_at": r.created_at.isoformat()
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"获取验证失败的记录失败: {e}")
            return []
