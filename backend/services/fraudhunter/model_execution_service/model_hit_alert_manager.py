"""
模型命中与告警管理器
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from dataclasses import dataclass
import csv
import io
import pandas as pd

from models.fraudhunter.model_execution_tracking import (
    FraudHunterHitRecord,
    FraudHunterAlertControlRecord
)
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from schemas.fraudhunter.alert_control_record import (
    AlertControlFilters,
    PaginationParams,
    AlertControlRecordResponse,
    AlertControlListResponse,
    HitRecordResponse,
    AlertControlRecordDetailResponse
)
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
                        [model_name],
                        has_control=model_def.is_acct_control if model_def else False
                    )
                else:
                    # 首次告警
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = self._format_alert_message(
                        hit_record.account_id, 
                        hit_record.hit_time, 
                        [model_name],
                        has_control=model_def.is_acct_control if model_def else False
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

    def _format_alert_message(self, account_id: str, hit_time: datetime, model_names: List[str], has_control: bool = False) -> str:
        """格式化告警消息
        
        Args:
            account_id: 账号ID
            hit_time: 命中时间
            model_names: 模型名称列表
            has_control: 是否包含管控模型
            
        Returns:
            格式化的告警消息
        """
        model_list = "、".join(model_names)
        time_str = hit_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if has_control:
            return f"账户 {account_id} 在 {time_str}，因命中{model_list}模型，触发告警及管控"
        else:
            return f"账户 {account_id} 在 {time_str}，因命中{model_list}模型，触发告警"

    def get_alert_control_records(
        self, 
        filters: AlertControlFilters, 
        pagination: PaginationParams
    ) -> AlertControlListResponse:
        """查询告警管控记录列表
        
        Args:
            filters: 筛选条件
            pagination: 分页参数
            
        Returns:
            告警管控记录列表响应
        """
        # 构建基础查询
        query = self.db.query(FraudHunterAlertControlRecord)
        
        # 应用筛选条件
        query = self._apply_filters(query, filters)
        
        # 计算总数
        total = query.count()
        
        # 应用分页
        offset = (pagination.page - 1) * pagination.page_size
        records = query.order_by(FraudHunterAlertControlRecord.created_at.desc())\
                      .offset(offset)\
                      .limit(pagination.page_size)\
                      .all()
        
        # 转换为响应格式
        record_responses = [
            AlertControlRecordResponse.from_orm(record) 
            for record in records
        ]
        
        # 计算总页数
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return AlertControlListResponse(
            records=record_responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages
        )

    def get_alert_control_record_detail(self, record_id: int) -> Optional[AlertControlRecordDetailResponse]:
        """获取告警管控记录详情
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录详情，如果不存在返回None
        """
        # 查询告警管控记录
        alert_record = self.db.query(FraudHunterAlertControlRecord)\
                             .filter(FraudHunterAlertControlRecord.id == record_id)\
                             .first()
        
        if not alert_record:
            return None
        
        # 查询关联的命中记录
        hit_record = self.db.query(FraudHunterHitRecord)\
                           .filter(FraudHunterHitRecord.id == alert_record.hit_record_id)\
                           .first()
        
        if not hit_record:
            return None
        
        return AlertControlRecordDetailResponse(
            record=AlertControlRecordResponse.from_orm(alert_record),
            hit_record=HitRecordResponse.from_orm(hit_record)
        )

    def export_alert_control_records(
        self, 
        filters: AlertControlFilters, 
        format: str = "csv"
    ) -> bytes:
        """导出告警管控记录
        
        Args:
            filters: 筛选条件
            format: 导出格式，支持 'csv' 或 'excel'
            
        Returns:
            导出的文件内容（字节）
            
        Raises:
            ValueError: 如果格式不支持
        """
        if format not in ["csv", "excel"]:
            raise ValueError(f"不支持的导出格式: {format}")
        
        # 查询所有符合条件的记录
        query = self.db.query(FraudHunterAlertControlRecord)
        query = self._apply_filters(query, filters)
        records = query.order_by(FraudHunterAlertControlRecord.created_at.desc()).all()
        
        # 准备导出数据
        export_data = []
        for record in records:
            export_data.append({
                'ID': record.id,
                '账号': record.account_id,
                '记录日期': record.record_date.strftime('%Y-%m-%d'),
                '模型ID': record.model_id,
                '模型名称': record.model_name,
                '告警状态': self._get_status_display(record.alert_status),
                '告警消息': record.alert_message or '',
                '告警人': record.alert_person or '',
                '告警时间': record.alert_time.strftime('%Y-%m-%d %H:%M:%S') if record.alert_time else '',
                '管控状态': self._get_status_display(record.control_status),
                '管控时间': record.control_time.strftime('%Y-%m-%d %H:%M:%S') if record.control_time else '',
                '管控流水号': record.control_serial_number or '',
                '创建时间': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '更新时间': record.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        if format == "csv":
            return self._export_to_csv(export_data)
        else:  # excel
            return self._export_to_excel(export_data)

    def _apply_filters(self, query, filters: AlertControlFilters):
        """应用筛选条件到查询
        
        Args:
            query: SQLAlchemy查询对象
            filters: 筛选条件
            
        Returns:
            应用筛选条件后的查询对象
        """
        # 日期范围筛选
        if filters.start_date:
            try:
                start_date = datetime.strptime(filters.start_date, "%Y-%m-%d").date()
                query = query.filter(FraudHunterAlertControlRecord.record_date >= start_date)
            except ValueError:
                logger.warning(f"无效的开始日期格式: {filters.start_date}")
        
        if filters.end_date:
            try:
                end_date = datetime.strptime(filters.end_date, "%Y-%m-%d").date()
                query = query.filter(FraudHunterAlertControlRecord.record_date <= end_date)
            except ValueError:
                logger.warning(f"无效的结束日期格式: {filters.end_date}")
        
        # 账号筛选
        if filters.account_id:
            query = query.filter(FraudHunterAlertControlRecord.account_id == filters.account_id)
        
        # 模型筛选
        if filters.model_id:
            query = query.filter(FraudHunterAlertControlRecord.model_id == filters.model_id)
        
        if filters.model_name:
            query = query.filter(FraudHunterAlertControlRecord.model_name.like(f"%{filters.model_name}%"))
        
        # 状态筛选
        if filters.alert_status:
            query = query.filter(FraudHunterAlertControlRecord.alert_status == filters.alert_status)
        
        if filters.control_status:
            query = query.filter(FraudHunterAlertControlRecord.control_status == filters.control_status)
        
        # 搜索关键词
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    FraudHunterAlertControlRecord.account_id.like(search_term),
                    FraudHunterAlertControlRecord.model_name.like(search_term),
                    FraudHunterAlertControlRecord.alert_message.like(search_term)
                )
            )
        
        return query

    def _get_status_display(self, status: str) -> str:
        """获取状态的显示文本
        
        Args:
            status: 状态值
            
        Returns:
            显示文本
        """
        status_map = {
            'not_configured': '未配置',
            'sent': '已发送',
            'duplicate': '重复',
            'executed': '已执行'
        }
        return status_map.get(status, status)

    def _export_to_csv(self, data: List[Dict[str, Any]]) -> bytes:
        """导出为CSV格式
        
        Args:
            data: 要导出的数据
            
        Returns:
            CSV文件内容（字节）
        """
        if not data:
            return b""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        # 转换为字节并使用UTF-8编码
        csv_content = output.getvalue()
        return csv_content.encode('utf-8-sig')  # 使用BOM以便Excel正确识别中文

    def _export_to_excel(self, data: List[Dict[str, Any]]) -> bytes:
        """导出为Excel格式
        
        Args:
            data: 要导出的数据
            
        Returns:
            Excel文件内容（字节）
        """
        if not data:
            # 返回空的Excel文件
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='告警管控记录', index=False)
        
        return output.getvalue()

    def _generate_control_serial_number(self) -> str:
        """生成管控流水号
        
        Returns:
            管控流水号
        """
        # 简化实现，使用时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"CTRL{timestamp}"