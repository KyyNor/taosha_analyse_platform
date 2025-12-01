"""
LangGraph 状态持久化服务
"""
from typing import Any, Dict, Optional, AsyncIterator
from sqlalchemy import desc

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.json import JsonPlusSerializer

from backend.models.db_base import get_db_session
from backend.models.agent_chat_models import AgentCheckpoint
from utils.logger import logger

class DatabaseCheckpointSaver(BaseCheckpointSaver):
    """
    基于 SQLAlchemy 的 CheckpointSaver implementation.
    用于将 LangGraph 的状态保存到数据库中。
    """
    
    def __init__(self, serializer: Optional[SerializerProtocol] = None):
        super().__init__(serializer=serializer or JsonPlusSerializer())

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """获取检查点"""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with get_db_session() as db:
            query = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.thread_id == thread_id,
                AgentCheckpoint.checkpoint_ns == checkpoint_ns
            )
            
            if checkpoint_id:
                query = query.filter(AgentCheckpoint.checkpoint_id == checkpoint_id)
            else:
                # 获取最新的
                query = query.order_by(desc(AgentCheckpoint.checkpoint_id))

            record = query.first()
            
            if record:
                # 反序列化
                checkpoint = self.serde.loads(record.checkpoint)
                metadata = record.metadata_ or {}
                parent_checkpoint_id = record.parent_checkpoint_id
                
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    } if parent_checkpoint_id else None,
                )
            
        return None

    def list(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """列出检查点"""
        pass

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """保存检查点"""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        # 序列化
        serialized_checkpoint = self.serde.dumps(checkpoint)
        
        try:
            with get_db_session() as db:
                existing = db.query(AgentCheckpoint).filter(
                    AgentCheckpoint.thread_id == thread_id,
                    AgentCheckpoint.checkpoint_ns == checkpoint_ns,
                    AgentCheckpoint.checkpoint_id == checkpoint_id
                ).first()

                if not existing:
                    new_record = AgentCheckpoint(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        parent_checkpoint_id=parent_checkpoint_id,
                        checkpoint=serialized_checkpoint,
                        metadata_=metadata
                    )
                    db.add(new_record)
                    logger.debug(f"Saved checkpoint: {thread_id} - {checkpoint_id}")
                else:
                    existing.checkpoint = serialized_checkpoint
                    existing.metadata_ = metadata
                    logger.debug(f"Updated checkpoint: {thread_id} - {checkpoint_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }
