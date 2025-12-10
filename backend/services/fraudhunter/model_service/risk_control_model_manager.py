"""
预警管控模型定义管理服务
"""

from typing import List, Optional, Set, Dict, Any
from sqlalchemy.orm import Session
import json
from models.fraudhunter.risk_control_model import (
    FraudHunterModelDefinition,
    FraudHunterModelHistory
)
from schemas.fraudhunter.risk_control_model import (
    RiskControlModelCreate,
    RiskControlModelUpdate
)
from schemas.fraudhunter.rule import RuleConfig
from .rule_engine import RuleEngine
from .model_executor import model_executor
from services.fraudhunter.dry_run_task_service import dry_run_task_manager
from services.fraudhunter.sequence_service import SequenceManager
from utils.logger import logger


class RiskControlModelManager:
    """预警管控模型定义管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.rule_engine = RuleEngine(db)
        self.sequence_manager = SequenceManager(db)

    # ==================== CRUD操作 ====================

    def create_risk_control_model(
        self,
        model_data: RiskControlModelCreate,
        created_by: str
    ) -> FraudHunterModelDefinition:
        """创建预警管控模型

        Args:
            model_data: 模型创建数据
            created_by: 创建人

        Returns:
            创建的模型对象

        Raises:
            ValueError: 如果model_code已存在或rule_config验证失败
        """
        # 如果未提供编码，自动生成
        if not model_data.model_code:
            model_data.model_code = self.sequence_manager.generate_model_code()
            logger.info(f"自动生成模型编码: {model_data.model_code}")
        else:
            # 如果提供了编码，验证唯一性
            existing = self.db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.model_code == model_data.model_code
            ).first()

            if existing:
                raise ValueError(f"模型编码已存在: {model_data.model_code}")

        # 验证rule_config
        validation_result = self.rule_engine.validate_rule_config(model_data.rule_config)
        if not validation_result.valid:
            raise ValueError(f"规则配置验证失败: {', '.join(validation_result.errors)}")

        # 生成offline_model_sql
        offline_sql = ""

        # 提取indicator_codes
        indicator_codes = validation_result.extracted_indicators
        indicator_codes_json = json.dumps(indicator_codes, ensure_ascii=False)

        # 创建模型记录
        db_model = FraudHunterModelDefinition(
            **model_data.model_dump(exclude={'rule_config'}),
            rule_config=model_data.rule_config.model_dump(),
            offline_model_sql=offline_sql,
            realtime_model_sql="",  # 暂不实现
            indicator_codes=indicator_codes_json,
            created_by=created_by,
            status='draft',
            current_version=1,
            latest_version=1
        )

        self.db.add(db_model)
        self.db.flush()

        # 创建版本历史
        self._create_version_history(db_model, 'create', '初始创建', created_by)

        self.db.commit()
        self.db.refresh(db_model)

        logger.info(f"创建预警管控模型成功: {db_model.model_code}, ID={db_model.id}")
        return db_model

    def get_risk_control_model(self, model_id: int) -> Optional[FraudHunterModelDefinition]:
        """获取预警管控模型

        Args:
            model_id: 模型ID

        Returns:
            模型对象或None
        """
        return self.db.query(FraudHunterModelDefinition).filter(
            FraudHunterModelDefinition.id == model_id
        ).first()

    def get_risk_control_model_by_code(self, model_code: str) -> Optional[FraudHunterModelDefinition]:
        """根据编码获取预警管控模型

        Args:
            model_code: 模型编码

        Returns:
            模型对象或None
        """
        return self.db.query(FraudHunterModelDefinition).filter(
            FraudHunterModelDefinition.model_code == model_code
        ).first()

    def list_risk_control_models(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        model_code: Optional[str] = None
    ) -> tuple[List[FraudHunterModelDefinition], int]:
        """获取预警管控模型列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            model_code: 编码筛选（模糊匹配）

        Returns:
            (模型列表, 总数)
        """
        query = self.db.query(FraudHunterModelDefinition)

        # 状态筛选
        if status:
            query = query.filter(FraudHunterModelDefinition.status == status)

        # 编码筛选（模糊匹配）
        if model_code:
            query = query.filter(FraudHunterModelDefinition.model_code.like(f"%{model_code}%"))

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterModelDefinition.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def update_risk_control_model(
        self,
        model_id: int,
        model_data: RiskControlModelUpdate,
        updated_by: str
    ) -> FraudHunterModelDefinition:
        """更新预警管控模型

        Args:
            model_id: 模型ID
            model_data: 更新数据
            updated_by: 更新人

        Returns:
            更新后的模型对象

        Raises:
            ValueError: 如果模型不存在或rule_config验证失败
        """
        db_model = self.get_risk_control_model(model_id)
        if not db_model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        # 准备更新数据
        update_data = model_data.model_dump(exclude_unset=True, exclude={'rule_config'})

        # 如果更新了rule_config，需要重新验证和生成SQL
        if model_data.rule_config is not None:
            # 验证规则配置
            validation_result = self.rule_engine.validate_rule_config(model_data.rule_config)
            if not validation_result.valid:
                raise ValueError(f"规则配置验证失败: {', '.join(validation_result.errors)}")

            # 重新生成SQL
            update_data['offline_model_sql'] = ""
            update_data['realtime_model_sql'] = ""

            # 重新提取indicator_codes
            indicator_codes = validation_result.extracted_indicators
            update_data['indicator_codes'] = json.dumps(indicator_codes, ensure_ascii=False)

            # 保存rule_config
            update_data['rule_config'] = model_data.rule_config.model_dump()

        # 更新字段
        for key, value in update_data.items():
            setattr(db_model, key, value)

        db_model.updated_by = updated_by
        db_model.latest_version += 1

        # 创建版本历史
        self._create_version_history(db_model, 'update', '更新配置', updated_by)

        self.db.commit()
        self.db.refresh(db_model)

        logger.info(f"更新预警管控模型成功: {db_model.model_code}, 新版本={db_model.latest_version}")
        return db_model

    def publish_risk_control_model(
        self,
        model_id: int,
        version: int,
        updated_by: str,
        change_description: Optional[str] = None
    ) -> FraudHunterModelDefinition:
        """发布预警管控模型

        Args:
            model_id: 模型ID
            version: 要发布的版本号
            updated_by: 更新人
            change_description: 变更说明

        Returns:
            发布后的模型对象

        Raises:
            ValueError: 如果模型不存在或版本号无效
        """
        db_model = self.get_risk_control_model(model_id)
        if not db_model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        # 验证版本号
        if version > db_model.latest_version:
            raise ValueError(f"版本号不存在: {version}")

        # 更新发布版本
        db_model.current_version = version
        db_model.status = 'online'
        db_model.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(
            db_model,
            'publish',
            change_description or f'发布版本{version}',
            updated_by
        )

        self.db.commit()
        self.db.refresh(db_model)

        logger.info(f"发布预警管控模型成功: {db_model.model_code}, 版本: {version}")
        return db_model

    def archive_risk_control_model(
        self,
        model_id: int,
        updated_by: str
    ) -> FraudHunterModelDefinition:
        """归档预警管控模型

        Args:
            model_id: 模型ID
            updated_by: 更新人

        Returns:
            归档后的模型对象

        Raises:
            ValueError: 如果模型不存在
        """
        db_model = self.get_risk_control_model(model_id)
        if not db_model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        db_model.status = 'archived'
        db_model.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(db_model, 'archive', '归档模型', updated_by)

        self.db.commit()
        self.db.refresh(db_model)

        logger.info(f"归档预警管控模型成功: {db_model.model_code}")
        return db_model

    def delete_risk_control_model(self, model_id: int) -> None:
        """删除预警管控模型（级联删除历史记录）

        Args:
            model_id: 模型ID

        Raises:
            ValueError: 如果模型不存在
        """
        db_model = self.get_risk_control_model(model_id)
        if not db_model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        model_code = db_model.model_code
        self.db.delete(db_model)
        self.db.commit()

        logger.info(f"删除预警管控模型成功: {model_code}")

    # ==================== 版本历史 ====================

    def _create_version_history(
        self,
        model: FraudHunterModelDefinition,
        change_type: str,
        change_description: str,
        created_by: str
    ) -> None:
        """创建版本历史记录

        Args:
            model: 模型对象
            change_type: 变更类型（create/update/publish/archive）
            change_description: 变更说明
            created_by: 创建人
        """
        history = FraudHunterModelHistory(
            model_id=model.id,
            version=model.latest_version,
            model_code=model.model_code,
            model_name=model.model_name,
            description=model.description,
            rule_config=model.rule_config,
            indicator_codes=model.indicator_codes,
            generated_code=model.offline_model_sql,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by
        )
        self.db.add(history)
        self.db.flush()

    def get_risk_control_model_history(
        self,
        model_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[FraudHunterModelHistory], int]:
        """获取预警管控模型版本历史

        Args:
            model_id: 模型ID
            page: 页码
            page_size: 每页数量

        Returns:
            (历史记录列表, 总数)
        """
        query = self.db.query(FraudHunterModelHistory).filter(
            FraudHunterModelHistory.model_id == model_id
        )

        total = query.count()

        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterModelHistory.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    # ==================== 模型执行 ====================

    async def submit_backtest_task(
        self,
        model_id: int,
        start_date: str,
        end_date: str,
        created_by: str
    ) -> str:
        """提交模型历史回测任务

        Args:
            model_id: 模型ID
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            created_by: 创建人

        Returns:
            execution_id: 任务执行ID

        Raises:
            ValueError: 如果模型不存在
        """
        # 验证模型存在
        model = self.get_risk_control_model(model_id)
        if not model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        logger.info(f"提交模型历史回测任务: {model.model_code}, 日期范围: {start_date} 至 {end_date}")

        # 提交异步任务
        execution_id = await dry_run_task_manager.submit_task(
            db=self.db,
            task_type='model_backtest',
            task_id=model_id,
            task_func=model_executor.execute_backtest,
            created_by=created_by,
            task_name=model.model_name,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"模型历史回测任务已提交: {execution_id}")
        return execution_id

    def execute_online(
        self,
        model_id: int,
        updated_by: str
    ) -> Dict[str, Any]:
        """模型上线执行（占位方法，后续完善）

        将模型部署到生产环境执行

        Args:
            model_id: 模型ID
            updated_by: 操作人

        Returns:
            执行结果

        Raises:
            ValueError: 如果模型不存在
            NotImplementedError: 功能待实现
        """
        # 验证模型存在
        model = self.get_risk_control_model(model_id)
        if not model:
            raise ValueError(f"预警管控模型不存在: {model_id}")

        # TODO: 实现模型上线逻辑
        # 1. 验证模型状态（必须是online状态）
        # 2. 生成生产环境SQL
        # 3. 部署到DolphinScheduler
        # 4. 配置定时任务
        # 5. 更新模型执行状态

        logger.info(f"模型上线执行（待实现）: {model.model_code}")

        raise NotImplementedError("模型上线功能尚未实现，后续版本将完善此功能")
