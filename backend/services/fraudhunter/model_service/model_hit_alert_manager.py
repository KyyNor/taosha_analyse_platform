"""
模型命中与告警管理器
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, String
from dataclasses import dataclass
import pandas as pd
import requests

from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
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
from utils.excel_exporter import create_excel_exporter
from utils.config import config_manager


@dataclass
class ModelHit:
    """模型命中信息"""
    model_id: int
    model_name: str


class ModelHitAlertManager:
    """模型命中与告警管理器"""

    def __init__(self, db: Session):
        self.db = db
        # 从配置加载接口URL
        self.control_api_url = config_manager.get("fraudhunter.alert_control.control_api_url")
        self.message_api_url = config_manager.get("fraudhunter.alert_control.message_api_url")

    def create_hit_record(
        self,
        account_id: str,
        hit_models: List[ModelHit],
        indicator_data: Dict[str, Any],
        hit_time: datetime,
        execution_id: Optional[int] = None
    ) -> FraudHunterModelHitRecord:
        """创建命中记录

        Args:
            account_id: 账号标识
            hit_models: 命中的模型列表
            indicator_data: 指标数据
            hit_time: 命中时间
            execution_id: 执行记录ID（可选）

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
        hit_record = FraudHunterModelHitRecord(
            execution_id=execution_id,
            account_id=account_id,
            hit_time=hit_time,
            hit_model_ids=hit_model_ids,
            hit_model_names=hit_model_names,
            indicator_data=indicator_data
        )

        self.db.add(hit_record)
        self.db.flush()  # 获取ID但不提交事务

        logger.info(f"创建命中记录: account_id={account_id}, models={hit_model_ids}, hit_time={hit_time}, execution_id={execution_id}")

        return hit_record

    def hit_record_processor(self, hit_record: FraudHunterModelHitRecord) -> FraudHunterModelAlertControlRecord:
        """处理命中记录，生成告警管控记录

        Args:
            hit_record: 命中记录

        Returns:
            生成的告警管控记录
        """
        record_date = hit_record.hit_time.date()

        # 创建一条告警管控记录，包含所有命中的模型
        alert_control_record = FraudHunterModelAlertControlRecord(
            execution_id=hit_record.execution_id,
            hit_record_id=hit_record.id,
            account_id=hit_record.account_id,
            record_date=record_date,
            hit_model_ids=hit_record.hit_model_ids,
            hit_model_names=hit_record.hit_model_names
        )

        # 获取所有命中模型的配置
        model_configs = {}
        for model_id in hit_record.hit_model_ids:
            model_def = self.db.query(FraudHunterModelDefinition).filter(
                FraudHunterModelDefinition.id == model_id
            ).first()
            if model_def:
                model_configs[model_id] = model_def

        # 管控流水号
        control_serial_number = None

        # 处理管控逻辑：检查是否有任何模型需要管控
        needs_control = any(
            model_configs.get(model_id) and model_configs[model_id].is_acct_control
            for model_id in hit_record.hit_model_ids
        )

        if needs_control:
            # 检查该账号当日是否已有管控记录
            duplicate_control = self.check_duplicate_control(
                hit_record.account_id,
                record_date
            )

            if duplicate_control:
                # 重复管控
                alert_control_record.control_status = 'duplicate'
            else:
                # 首次管控，调用管控接口
                control_resp = self._call_control_api(hit_record.account_id)

                if control_resp:
                    # 管控接口调用成功，从响应中提取流水号
                    control_serial_number = control_resp.get('body', {}).get('serialNumber', '000000')
                    alert_control_record.control_status = 'executed'
                    alert_control_record.control_time = datetime.now()
                    alert_control_record.control_serial_number = control_serial_number
                else:
                    # 管控接口调用失败，使用默认流水号
                    control_serial_number = '000000'
                    alert_control_record.control_status = 'executed'
                    alert_control_record.control_time = datetime.now()
                    alert_control_record.control_serial_number = control_serial_number
                    logger.warning(f"管控接口调用失败，使用默认流水号: account_id={hit_record.account_id}")
        else:
            alert_control_record.control_status = 'not_configured'

        # 处理告警逻辑：检查是否有模型需要发送告警
        # 1. 找出所有需要发送告警的模型
        models_need_alert = [
            model_id for model_id in hit_record.hit_model_ids
            if model_configs.get(model_id) and model_configs[model_id].is_send_alert_message
        ]

        if models_need_alert:
            # 2. 查询该账号当日已发送告警的模型ID
            alerted_model_ids = self.get_alerted_model_ids(
                hit_record.account_id,
                record_date
            )

            # 3. 找出需要发送但尚未发送的模型
            models_to_alert = [
                model_id for model_id in models_need_alert
                if model_id not in alerted_model_ids
            ]

            if models_to_alert:
                # 有模型需要发送告警
                # 获取需要发送告警的模型名称
                alert_model_names = [
                    hit_record.hit_model_names[i]
                    for i, model_id in enumerate(hit_record.hit_model_ids)
                    if model_id in models_to_alert
                ]

                # 生成告警消息
                alert_message = self._format_alert_message(
                    hit_record.account_id,
                    hit_record.hit_time,
                    alert_model_names,
                    control_serial_number=control_serial_number
                )

                # 调用消息提醒接口
                send_success = self.send_alert_message(
                    notice_no="whwangzeqi", # todo 
                    notice=alert_message
                )

                if send_success:
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = alert_message
                    alert_control_record.alert_person = 'system'
                    alert_control_record.alert_time = datetime.now()
                else:
                    # 消息发送失败，但仍记录消息内容
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = alert_message
                    alert_control_record.alert_person = 'system'
                    alert_control_record.alert_time = datetime.now()
                    logger.warning(f"消息发送失败，但已记录告警信息: account_id={hit_record.account_id}")
            else:
                # 所有需要告警的模型都已发送过
                alert_control_record.alert_status = 'duplicate'
                # 生成消息内容（用于记录）
                alert_model_names = [
                    hit_record.hit_model_names[i]
                    for i, model_id in enumerate(hit_record.hit_model_ids)
                    if model_id in models_need_alert
                ]
                alert_control_record.alert_message = self._format_alert_message(
                    hit_record.account_id,
                    hit_record.hit_time,
                    alert_model_names,
                    control_serial_number=control_serial_number
                )
        else:
            alert_control_record.alert_status = 'not_configured'

        self.db.add(alert_control_record)
        self.db.flush()

        logger.info(f"处理命中记录完成: hit_record_id={hit_record.id}, account_id={hit_record.account_id}, "
                   f"alert_status={alert_control_record.alert_status}, control_status={alert_control_record.control_status}")

        return alert_control_record

    def get_alerted_model_ids(self, account_id: str, date: date) -> List[int]:
        """获取该账号当日已发送告警的模型ID列表

        Args:
            account_id: 账号ID
            date: 检查日期

        Returns:
            已发送告警的模型ID列表
        """
        # 查询当天该账号的所有告警记录
        alert_records = self.db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.account_id == account_id,
            FraudHunterModelAlertControlRecord.record_date == date,
            FraudHunterModelAlertControlRecord.alert_status.in_(['sent', 'duplicate'])
        ).all()

        # 收集所有已发送告警的模型ID
        alerted_model_ids = set()
        for record in alert_records:
            if record.hit_model_ids:
                alerted_model_ids.update(record.hit_model_ids)

        return list(alerted_model_ids)

    def check_duplicate_control(self, account_id: str, date: date) -> bool:
        """检查重复管控
        
        Args:
            account_id: 账号ID
            date: 检查日期
            
        Returns:
            是否重复管控
        """
        # 查询当天是否已有管控记录
        existing_control = self.db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.account_id == account_id,
            FraudHunterModelAlertControlRecord.record_date == date,
            FraudHunterModelAlertControlRecord.control_status.in_(['executed', 'duplicate'])
        ).first()
        
        return existing_control is not None

    def _call_control_api(self, account_id: str, account_type: str = "1") -> Optional[Dict[str, Any]]:
        """调用管控接口

        Args:
            account_id: 账号ID
            account_type: 账号类型，默认为"1"

        Returns:
            管控接口响应，如果失败返回None
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "iibs": {
                    "req": {
                        "body": {
                            "acctNo": account_id,
                            "acctType": account_type,
                            "resAbs": "淘沙实时管控模型"
                        }
                    }
                }
            }

            response = requests.post(
                url=self.control_api_url,
                json=data,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            resp_data = result.get('iibs', {}).get('resp')

            logger.info(f"管控接口调用成功: account_id={account_id}, response={resp_data}")
            return resp_data

        except Exception as e:
            logger.error(f"管控接口调用失败: account_id={account_id}, error={str(e)}")
            return None

    def send_alert_message(self, notice_no: str, notice: str) -> bool:
        """发送告警消息

        Args:
            notice_no: 通知编号（账号ID）
            notice: 通知内容

        Returns:
            发送是否成功
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "noticeNo": notice_no,
                "notice": notice
            }

            response = requests.post(
                url=self.message_api_url,
                json=data,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            resp_code = result.get("body", {}).get("respCode")
            resp_msg = result.get("body", {}).get("respMsg")

            if resp_code == "00000":
                logger.info(f"消息发送成功: notice_no={notice_no}")
                return True
            else:
                logger.warning(f"消息发送失败: notice_no={notice_no}, code={resp_code}, msg={resp_msg}")
                return False

        except Exception as e:
            logger.error(f"消息发送异常: notice_no={notice_no}, error={str(e)}")
            return False


    def _format_alert_message(
        self,
        account_id: str,
        hit_time: datetime,
        model_names: List[str],
        control_serial_number: Optional[str] = None
    ) -> str:
        """格式化告警消息

        Args:
            account_id: 账号ID
            hit_time: 命中时间
            model_names: 模型名称列表
            control_serial_number: 管控流水号（可选）

        Returns:
            格式化的告警消息
        """
        model_list = ",".join(model_names)
        time_str = hit_time.strftime("%Y-%m-%d %H:%M:%S")

        if control_serial_number:
            # 需要管控的消息格式
            return f"【武汉分行监测系统】账号：{account_id} 在 {time_str} 触发 {model_list} 模型，已采取暂停非柜面管控措施，管控流水号为：{control_serial_number},请在2小时内核实。"
        else:
            # 不需要管控的消息格式
            return f"【武汉分行监测系统】账号：{account_id} 在 {time_str} 触发 {model_list} 模型告警。"

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
        query = self.db.query(FraudHunterModelAlertControlRecord)
        
        # 应用筛选条件
        query = self._apply_filters(query, filters)
        
        # 计算总数
        total = query.count()
        
        # 应用分页
        offset = (pagination.page - 1) * pagination.page_size
        records = query.order_by(FraudHunterModelAlertControlRecord.created_at.desc())\
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
        alert_record = self.db.query(FraudHunterModelAlertControlRecord)\
                             .filter(FraudHunterModelAlertControlRecord.id == record_id)\
                             .first()
        
        if not alert_record:
            return None
        
        # 查询关联的命中记录
        hit_record = self.db.query(FraudHunterModelHitRecord)\
                           .filter(FraudHunterModelHitRecord.id == alert_record.hit_record_id)\
                           .first()
        
        if not hit_record:
            return None
        
        return AlertControlRecordDetailResponse(
            record=AlertControlRecordResponse.from_orm(alert_record),
            hit_record=HitRecordResponse.from_orm(hit_record)
        )

    def export_alert_control_records(
        self,
        filters: AlertControlFilters
    ) -> bytes:
        """导出告警管控记录为Excel

        Args:
            filters: 筛选条件

        Returns:
            导出的Excel文件内容（字节）
        """
        # 查询所有符合条件的记录
        query = self.db.query(FraudHunterModelAlertControlRecord)
        query = self._apply_filters(query, filters)
        records = query.order_by(FraudHunterModelAlertControlRecord.created_at.desc()).all()

        # 准备导出数据
        export_data = []
        for record in records:
            # 将JSON数组转换为逗号分隔的字符串
            model_ids_str = ','.join(map(str, record.hit_model_ids)) if record.hit_model_ids else ''
            model_names_str = ','.join(record.hit_model_names) if record.hit_model_names else ''

            export_data.append({
                'ID': record.id,
                '账号': record.account_id,
                '记录日期': record.record_date.strftime('%Y-%m-%d'),
                '模型ID': model_ids_str,
                '模型名称': model_names_str,
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

        # 转换为DataFrame
        df = pd.DataFrame(export_data) if export_data else pd.DataFrame()

        # 使用Excel导出器
        exporter = create_excel_exporter()
        output = exporter.export_single_sheet(df, sheet_name="告警管控记录")

        return output.getvalue()

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
                query = query.filter(FraudHunterModelAlertControlRecord.record_date >= start_date)
            except ValueError:
                logger.warning(f"无效的开始日期格式: {filters.start_date}")
        
        if filters.end_date:
            try:
                end_date = datetime.strptime(filters.end_date, "%Y-%m-%d").date()
                query = query.filter(FraudHunterModelAlertControlRecord.record_date <= end_date)
            except ValueError:
                logger.warning(f"无效的结束日期格式: {filters.end_date}")
        
        # 账号筛选
        if filters.account_id:
            query = query.filter(FraudHunterModelAlertControlRecord.account_id == filters.account_id)
        
        # 模型筛选（JSON数组包含检查）
        if filters.model_id:
            # 使用JSON_CONTAINS检查数组中是否包含指定的model_id
            # 注意：这里使用cast将JSON转为文本进行模糊匹配，兼容性更好
            query = query.filter(
                func.cast(FraudHunterModelAlertControlRecord.hit_model_ids, String).like(f'%{filters.model_id}%')
            )

        if filters.model_name:
            # 检查JSON数组中是否包含指定的模型名称
            query = query.filter(
                func.cast(FraudHunterModelAlertControlRecord.hit_model_names, String).like(f"%{filters.model_name}%")
            )

        # 状态筛选
        if filters.alert_status:
            query = query.filter(FraudHunterModelAlertControlRecord.alert_status == filters.alert_status)

        if filters.control_status:
            query = query.filter(FraudHunterModelAlertControlRecord.control_status == filters.control_status)

        # 搜索关键词
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    FraudHunterModelAlertControlRecord.account_id.like(search_term),
                    func.cast(FraudHunterModelAlertControlRecord.hit_model_names, String).like(search_term),
                    FraudHunterModelAlertControlRecord.alert_message.like(search_term)
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
