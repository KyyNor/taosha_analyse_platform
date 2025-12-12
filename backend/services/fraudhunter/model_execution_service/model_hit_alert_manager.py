"""
模型命中与告警管理器
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from dataclasses import dataclass

from models.fraudhunter.model_execution_tracking import (
    FraudHunterHitRecord,
    FraudHunterAlertControlRecord
)
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from utils.logger import logger


@dataclass
class ModelHit:
    """模型命中信息"""
    model_id: int
    model_name: str


class ModelHitAlertManager:
    """模型命中与告警管理器"""

    def __init__(self, db: Session):
        self.db = db

    def create_hit_record(
        self,
        account_id: str,
        hit_models: List[ModelHit],
        indicator_data: Dict[str, Any],
        hit_time: datetime
    ) -> FraudHunterHitRecord:
        """创建命中记录
        
        Args:
            account_id: 账号标识
            hit_models: 命中的模型列表
            indicator_data: 指标数据
            hit_time: 命中时间
            
        Returns:
            创建的命中记录
            
        Raises:
            ValueError: 如果参数无效
        """
        if not account_id:
            raise ValueError("账号ID不能为空")
        
        if not hit_models:
            raise ValueError("命中模型列表不能为空")
            
        if not indicator_data:
            raise ValueError("指标数据不能为空")
            
        # 提取模型ID和名称列表
        hit_model_ids = [model.model_id for model in hit_models]
        hit_model_names = [model.model_name for model in hit_models]
        
        # 创建命中记录
        hit_record = FraudHunterHitRecord(
            account_id=account_id,
            hit_time=hit_time,
            hit_model_ids=hit_model_ids,
            hit_model_names=hit_model_names,
            indicator_data=indicator_data
        )
        
        self.db.add(hit_record)
        self.db.flush()  # 获取ID但不提交事务
        
        logger.info(f"创建命中记录: account_id={account_id}, models={hit_model_ids}, hit_time={hit_time}")
        
        return hit_record

    def hit_record_processor(self, hit_record: FraudHunterHitRecord) -> List[FraudHunterAlertControlRecord]:
        """处理命中记录，生成告警管控记录
        
        Args:
            hit_record: 命中记录
            
        Returns:
            生成的告警管控记录列表
        """
        alert_control_records = []
        record_date = hit_record.hit_time.date()
        
        # 为每个命中的模型创建告警管控记录
        for i, model_id in enumerate(hit_record.hit_model_ids):
            model_name = hit_record.hit_model_names[i]
            
            # 获取模型配置
            model_def = self.db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.id == model_id
            ).first()
            
            # 创建告警管控记录
            alert_control_record = FraudHunterAlertControlRecord(
                hit_record_id=hit_record.id,
                account_id=hit_record.account_id,
                record_date=record_date,
                model_id=model_id,
                model_name=model_name
            )
            
            # 设置告警状态和消息
            if model_def and model_def.is_send_alert_message:
                # 检查是否重复告警
                duplicate_alerts = self.check_duplicate_alert(
                    hit_record.account_id, 
                    [model_id], 
                    record_date
                )
                
                if duplicate_alerts.get(model_id, False):
                    # 重复告警
                    alert_control_record.alert_status = 'duplicate'
                    alert_control_record.alert_message = self._format_alert_message(
                        hit_record.account_id, 
                        hit_record.hit_time, 
                        [model_name]
                    )
                else:
                    # 首次告警
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = self._format_alert_message(
                        hit_record.account_id, 
                        hit_record.hit_time, 
                        [model_name]
                    )
                    alert_control_record.alert_person = 'system'
                    alert_control_record.alert_time = datetime.now()
            else:
                alert_control_record.alert_status = 'not_configured'
            
            # 设置管控状态
            if model_def and model_def.is_acct_control:
                # 检查是否重复管控
                duplicate_control = self.check_duplicate_control(
                    hit_record.account_id, 
                    record_date
                )
                
                if duplicate_control:
                    # 重复管控
                    alert_control_record.control_status = 'duplicate'
                else:
                    # 首次管控
                    alert_control_record.control_status = 'executed'
                    alert_control_record.control_time = datetime.now()
                    alert_control_record.control_serial_number = self._generate_control_serial_number()
            else:
                alert_control_record.control_status = 'not_configured'
            
            self.db.add(alert_control_record)
            alert_control_records.append(alert_control_record)
        
        self.db.flush()
        
        logger.info(f"处理命中记录完成: hit_record_id={hit_record.id}, 生成{len(alert_control_records)}条告警管控记录")
        
        return alert_control_records

    def check_duplicate_alert(
        self, 
        account_id: str, 
        model_ids: List[int], 
        date: date
    ) -> Dict[int, bool]:
        """检查重复告警
        
        Args:
            account_id: 账号ID
            model_ids: 模型ID列表
            date: 检查日期
            
        Returns:
            模型ID到是否重复的映射
        """
        duplicate_map = {}
        
        for model_id in model_ids:
            # 查询当天是否已有该模型的告警记录
            existing_alert = self.db.query(FraudHunterAlertControlRecord).filter(
                FraudHunterAlertControlRecord.account_id == account_id,
                FraudHunterAlertControlRecord.model_id == model_id,
                FraudHunterAlertControlRecord.record_date == date,
                FraudHunterAlertControlRecord.alert_status.in_(['sent', 'duplicate'])
            ).first()
            
            duplicate_map[model_id] = existing_alert is not None
        
        return duplicate_map

    def check_duplicate_control(self, account_id: str, date: date) -> bool:
        """检查重复管控
        
        Args:
            account_id: 账号ID
            date: 检查日期
            
        Returns:
            是否重复管控
        """
        # 查询当天是否已有管控记录
        existing_control = self.db.query(FraudHunterAlertControlRecord).filter(
            FraudHunterAlertControlRecord.account_id == account_id,
            FraudHunterAlertControlRecord.record_date == date,
            FraudHunterAlertControlRecord.control_status.in_(['executed', 'duplicate'])
        ).first()
        
        return existing_control is not None

    def send_alert_message(self, alert_records: List[FraudHunterAlertControlRecord]) -> None:
        """发送告警消息（留空实现）
        
        Args:
            alert_records: 需要发送告警的记录列表
        """
        for record in alert_records:
            if record.alert_status == 'sent':
                # 这里是留空实现，实际应该调用外部告警服务
                logger.info(f"发送告警消息: {record.alert_message}")

    def process_alert_control(self, alert_records: List[FraudHunterAlertControlRecord]) -> None:
        """处理告警管控（留空实现）
        
        Args:
            alert_records: 需要处理管控的记录列表
        """
        for record in alert_records:
            if record.control_status == 'executed':
                # 这里是留空实现，实际应该调用外部管控服务
                logger.info(f"执行管控操作: account_id={record.account_id}, serial_number={record.control_serial_number}")

    def _format_alert_message(self, account_id: str, hit_time: datetime, model_names: List[str]) -> str:
        """格式化告警消息
        
        Args:
            account_id: 账号ID
            hit_time: 命中时间
            model_names: 模型名称列表
            
        Returns:
            格式化的告警消息
        """
        model_list = "、".join(model_names)
        time_str = hit_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 判断是否包含管控模型（简化实现，实际应该查询模型配置）
        has_control = any("管控" in name for name in model_names)
        
        if has_control:
            return f"账户 {account_id} 在 {time_str}，因命中{model_list}模型，触发告警及管控"
        else:
            return f"账户 {account_id} 在 {time_str}，因命中{model_list}模型，触发告警"

    def _generate_control_serial_number(self) -> str:
        """生成管控流水号
        
        Returns:
            管控流水号
        """
        # 简化实现，使用时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"CTRL{timestamp}"