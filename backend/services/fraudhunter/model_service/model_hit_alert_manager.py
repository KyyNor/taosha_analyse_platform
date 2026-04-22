"""
模型命中与告警管理器
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, String, Integer, text
from dataclasses import dataclass
import pandas as pd
import requests
import json

from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.alert_notify_targets import (
    FraudHunterAlertAcctAssign,
    FraudHunterAlertCustOwner,
)
from schemas.fraudhunter.alert_control_record import (
    AlertControlFilters,
    PaginationParams,
    AlertControlRecordResponse,
    AlertControlListResponse,
    HitRecordResponse,
    AlertControlRecordDetailResponse,
    TrendRequest,
    TrendPoint,
    TrendResponse,
)
from services.fraudhunter.system_config_service import SystemConfigManager
from utils.logger import logger
from utils.excel_exporter import create_excel_exporter
from utils.config import settings


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
        self.control_api_url = settings.fraudhunter_alert_control_control_api_url
        self.message_api_url = settings.fraudhunter_alert_control_message_api_url
        # 系统配置管理器
        self.config_manager = SystemConfigManager(db)

    def create_hit_record(
        self,
        account_id: str,
        branch_no: Optional[str],
        hit_models: List[ModelHit],
        indicator_data: Dict[str, Any],
        hit_time: datetime,
        execution_id: Optional[int] = None
    ) -> FraudHunterModelHitRecord:
        """创建命中记录

        Args:
            account_id: 账号标识
            branch_no: 部门编号（4位数字）
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
            branch_no=branch_no,
            hit_time=hit_time,
            hit_model_ids=hit_model_ids,
            hit_model_names=hit_model_names,
            indicator_data=indicator_data
        )

        self.db.add(hit_record)
        self.db.flush()  # 获取ID但不提交事务

        logger.debug(f"创建命中记录: account_id={account_id}, branch_no={branch_no}, models={hit_model_ids}, hit_time={hit_time}, execution_id={execution_id}")

        return hit_record

    def hit_record_processor(
        self,
        hit_record: FraudHunterModelHitRecord,
        cust_type: str,
        is_whitelist: bool = False
    ) -> FraudHunterModelAlertControlRecord:
        """处理命中记录，生成告警管控记录

        Args:
            hit_record: 命中记录
            is_whitelist: 是否为白名单账号

        Returns:
            生成的告警管控记录
        """
        record_date = hit_record.hit_time.date()

        # 创建一条告警管控记录，包含所有命中的模型
        alert_control_record = FraudHunterModelAlertControlRecord(
            execution_id=hit_record.execution_id,
            hit_record_id=hit_record.id,
            account_id=hit_record.account_id,
            branch_no=hit_record.branch_no,
            record_date=record_date,
            hit_model_ids=hit_record.hit_model_ids,
            hit_model_names=hit_record.hit_model_names
        )

        # 如果是白名单账号，直接设置状态为whitelist，不触发告警和管控
        if is_whitelist:
            alert_control_record.alert_status = 'whitelist'
            alert_control_record.control_status = 'whitelist'
            self.db.add(alert_control_record)
            self.db.flush()
            logger.info(
                f"白名单账号跳过告警管控: hit_record_id={hit_record.id}, "
                f"account_id={hit_record.account_id}"
            )
            return alert_control_record

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
                control_resp = self._call_control_api(hit_record.account_id, account_type=cust_type)

                if control_resp:
                    # 管控接口调用成功，从响应中提取流水号
                    control_serial_number = control_resp.get('body', {}).get('tranFlwNo', '000000')
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

                # 从配置获取告警通知人（支持按机构号获取）
                alert_notice_no = self._get_branch_alert_recipients(
                    branch_no=hit_record.branch_no
                )

                # ========== 【合并】收集所有通知人，去重，一次发送 ==========
                # 1. 客户经理通知号（跟随 is_send_alert_message，无额外开关）
                cm_targets = self._lookup_acct_assign_notice_nos(hit_record.account_id)

                # 2. 理财经理通知号（需 is_send_alert_message=True AND is_send_financial_manager_alert=True）
                fin_targets: List[str] = []
                fin_mngr_models = [
                    mid for mid in hit_record.hit_model_ids
                    if model_configs.get(mid)
                    and model_configs[mid].is_send_alert_message
                    and getattr(model_configs[mid], 'is_send_financial_manager_alert', False)
                ]
                if fin_mngr_models:
                    customer_no = hit_record.indicator_data.get('i_dep_acct_no_offline_00001')
                    if customer_no and str(customer_no).strip():
                        fin_targets = self._lookup_cust_owner_notice_nos(str(customer_no))

                # 3. 合并去重：调用领域层的纯合路去重函数
                combined_notice_no = self.merge_notification_targets(
                    branch_notice_no=alert_notice_no,
                    cm_targets=cm_targets,
                    fin_targets=fin_targets,
                )

                # 4. 单次发送，无人或为空字串则跳过
                send_success = False
                if combined_notice_no:
                    send_success = self.send_alert_message(
                        notice_no=combined_notice_no,
                        notice=alert_message
                    )
                    final_targets_list = combined_notice_no.split(",") if combined_notice_no else []
                    logger.info(
                        f"{'成功' if send_success else '失败'}（合并发送，共{len(final_targets_list)}人）: "
                        f"targets={final_targets_list}"
                    )

                # 5. 记录结果，兼容原有状态字段
                if send_success:
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = alert_message
                    alert_control_record.alert_person = 'system'
                    alert_control_record.alert_time = datetime.now()
                else:
                    # 消息发送失败（非 00000 响应码），但仍记录消息内容
                    alert_control_record.alert_status = 'sent'
                    alert_control_record.alert_message = alert_message
                    alert_control_record.alert_person = 'system'
                    alert_control_record.alert_time = datetime.now()
                    logger.warning(f"消息发送失败（合并发送，共{len(unique_targets)}人）: account_id={hit_record.account_id}")
                # ===========================================================================
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

        if alert_control_record.alert_status != "duplicate" or alert_control_record.control_status != "duplicate":
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
        from datetime import timedelta
        date_range = [date - timedelta(days=i) for i in range(1)]  # 今天、昨天、前天

        alert_records = self.db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.account_id == account_id,
            FraudHunterModelAlertControlRecord.record_date.in_(date_range),
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
        from datetime import timedelta
        date_range = [date - timedelta(days=i) for i in range(1)]  # 今天 , 应要求改为只当天不重复预警，后续还是会预警

        existing_control = self.db.query(FraudHunterModelAlertControlRecord).filter(
            FraudHunterModelAlertControlRecord.account_id == account_id,
            FraudHunterModelAlertControlRecord.record_date.in_(date_range),
            FraudHunterModelAlertControlRecord.control_status.in_(['executed', 'duplicate'])
        ).first()
        
        return existing_control is not None

    @staticmethod
    def merge_notification_targets(
        branch_notice_no: Optional[str],
        cm_targets: List[str],
        fin_targets: List[str],
    ) -> str:
        """
        将三种来源的通知号合并，去重后返回逗号分隔字符串。

        适用场景
        --------
        命中告警时，向分支行通知号（系统配置）、客户经理通知号（AcctAssign表）、
        理财经理通知号（CustOwner表）三类目标合并后，一次调用 send_alert_message()。
        本方法保证：
        1. 空字符串（branch_notice_no=""）和 None 不产生多余逗号
        2. 三路中出现的重复手机号/人名只出现一次
        3. 保持第一次出现的相对顺序（insertion-order deduplication）

        参数
        ----
        branch_notice_no : 分支行通知号，可能是逗号拼接字符串、全局配置值、空字符串、None
        cm_targets       : 客户经理通知号列表，元素可以是逗号拼接字符串
        fin_targets      : 理财经理通知号列表，元素可以是逗号拼接字符串

        返回值
        -------
        逗号分隔的去重字符串，形如 "张三,李四,王五" 或空字符串 ""

        示例
        -----
        >>> merge_notification_targets('admin,A', ['B','A'], ['C','B'])
        'admin,A,B,C'

        >>> merge_notification_targets('', ['A'], [])
        'A'

        >>> merge_notification_targets(None, [], [])
        ''

        本方法为纯函数，无 IO，请勿在其中引入 DB/Settings/全局变量等隐式依赖。
        """
        all_sources = (
            ([branch_notice_no] if branch_notice_no else [])
            + list(cm_targets)
            + list(fin_targets)
        )
        flat = [
            item.strip()
            for source in all_sources
            for item in str(source).split(",")
            if item.strip()
        ]
        # Python 3.7+: dict 保证 insertion-order，正是"去重保序"的语义需求
        unique_ordered = list(dict.fromkeys(flat))
        return ",".join(unique_ordered)

    def _lookup_acct_assign_notice_nos(self, acct_no: str) -> List[str]:
        """查询账号对应的客户经理通知号列表

        支持 notice_no 逗号拼接，返回去重后的列表。

        Args:
            acct_no: 账号

        Returns:
            去重后的通知号列表（不含空值），无结果时返回空列表
        """
        record = self.db.query(FraudHunterAlertAcctAssign).filter(
            FraudHunterAlertAcctAssign.acct_no == acct_no
        ).first()

        if not record or not record.notice_no:
            logger.debug(f"未找到客户经理通知目标: acct_no={acct_no}")
            return []

        targets = [
            t.strip() for t in str(record.notice_no).split(',')
            if t.strip()
        ]
        logger.debug(f"找到客户经理通知目标: acct_no={acct_no}, targets={targets}")
        return targets

    def _lookup_cust_owner_notice_nos(self, cust_no: str) -> List[str]:
        """查询客户号对应的理财经理通知号列表

        支持 notice_no 逗号拼接，返回去重后的列表。

        Args:
            cust_no: 客户号

        Returns:
            去重后的通知号列表（不含空值），无结果时返回空列表
        """
        record = self.db.query(FraudHunterAlertCustOwner).filter(
            FraudHunterAlertCustOwner.cust_no == cust_no
        ).first()

        if not record or not record.notice_no:
            logger.debug(f"未找到理财经理通知目标: cust_no={cust_no}")
            return []

        targets = [
            t.strip() for t in str(record.notice_no).split(',')
            if t.strip()
        ]
        logger.debug(f"找到理财经理通知目标: cust_no={cust_no}, targets={targets}")
        return targets

    def _call_control_api(self, account_id: str, account_type: str = "01") -> Optional[Dict[str, Any]]:
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
            from utils.common_utils import getacctno
            full_account_id = getacctno(account_id)

            data = {
                "iibs": {
                    "req": {
                        "body": {
                            "acctNo": full_account_id,
                            "acctType": account_type,
                            "resAbs": "武汉分行监测系统"
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

            logger.info(f"管控接口调用成功: account_id={account_id}, full_account_id={full_account_id}, response={resp_data}")
            return resp_data

        except Exception as e:
            logger.error(f"管控接口调用失败: account_id={account_id}, error={str(e)}")
            return None

    def _get_related_branch_nos(self, branch_no: str) -> List[str]:
        """获取当前用户有权查看的所有机构号

        根据机构号层级映射配置，获取用户有权限查看的所有机构号：
        1. 包含用户自己的机构号
        2. 包含所有映射到该机构号的下级机构号（branch_no_lay2 == branch_no）

        Args:
            branch_no: 用户的部门编号

        Returns:
            相关的机构号列表
        """
        related_branch_nos = [branch_no]

        # 获取 branch_no_lay 配置
        branch_no_lay_config = self.config_manager.get_config_value(
            'branch_no_lay',
            default=[]
        )

        # 反向查找：找到所有 branch_no_lay2 等于当前用户 branch_no 的原始 branch_no
        if branch_no_lay_config:
            for item in branch_no_lay_config:
                if item.get('branch_no_lay2') == branch_no:
                    original_branch_no = item.get('branch_no')
                    if original_branch_no and original_branch_no not in related_branch_nos:
                        related_branch_nos.append(original_branch_no)
                        logger.debug(f"机构号权限映射: user_branch_no={branch_no}, include_child_branch_no={original_branch_no}")

        logger.debug(f"用户 {branch_no} 可查看的机构号列表: {related_branch_nos}")
        return related_branch_nos

    def _get_branch_alert_recipients(self, branch_no: Optional[str]) -> str:
        """获取分支机构的告警提醒人列表

        处理流程：
        1. 从 branch_no_lay 配置获取原始 branch_no 到 branch_no_lay2 的映射
        2. 从 branch_alert_notice_no 配置获取 branch_no_lay2 对应的提醒人列表
        3. 与全局 alert_notice_no 合并去重

        Args:
            branch_no: 原始部门编号

        Returns:
            逗号分隔的提醒人列表
        """
        # 获取全局默认提醒人
        global_alert_no = self.config_manager.get_config_value(
            'alert_notice_no',
            default='whwangzeqi'
        )

        # 如果没有 branch_no，直接返回全局提醒人
        if not branch_no:
            return global_alert_no

        # 1. 获取 branch_no 映射配置
        # 格式: [{'branch_no':'1151','branch_no_lay2':'1150'},{...}]
        branch_no_lay_config = self.config_manager.get_config_value(
            'branch_no_lay',
            default=[]
        )

        # 2. 查找映射后的 branch_no_lay2
        mapped_branch_no = None
        if branch_no_lay_config:
            for item in branch_no_lay_config:
                if item.get('branch_no') == branch_no:
                    mapped_branch_no = item.get('branch_no_lay2')
                    logger.debug(f"机构号映射: {branch_no} -> {mapped_branch_no}")
                    break

        # 如果没有找到映射，使用原始 branch_no
        if not mapped_branch_no:
            mapped_branch_no = branch_no

        # 3. 获取机构级提醒人配置
        # 格式: [{'机构号':'1150','提醒人':'whxxxxz'},{...}]
        branch_alert_config = self.config_manager.get_config_value(
            'branch_alert_notice_no',
            default=[]
        )

        # 4. 收集该机构的提醒人
        branch_recipients = []
        if branch_alert_config:
            for item in branch_alert_config:
                if item.get('机构号') == mapped_branch_no:
                    recipient = item.get('提醒人', '')
                    if recipient:
                        branch_recipients.append(recipient)

        # 5. 合并全局提醒人和机构提醒人，去重
        all_recipients = set()
        # 添加全局提醒人（可能是逗号分隔的）
        if global_alert_no:
            all_recipients.update(r.strip() for r in global_alert_no.split(',') if r.strip())
        # 添加机构提醒人
        all_recipients.update(branch_recipients)

        final_recipients = ','.join(sorted(all_recipients))
        logger.debug(
            f"提醒人列表: branch_no={branch_no}, mapped_branch_no={mapped_branch_no}, "
            f"branch_recipients={branch_recipients}, global={global_alert_no}, "
            f"final={final_recipients}"
        )

        return final_recipients

    def send_alert_message(self, notice_no: str, notice: str) -> bool:
        """发送告警消息

        Args:
            notice_no: 通知编号（账号ID，可能是逗号分隔的多个账号）
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

        使用系统配置中的消息模板，支持变量替换：
        - {account_id}: 账号ID
        - {time}: 命中时间
        - {model_list}: 模型名称列表
        - {control_serial_number}: 管控流水号

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

        # 默认模板
        default_template_with_control = (
            "【武汉分行监测系统】账号：{account_id} 在 {time} 触发 {model_list} 模型，"
            "已采取暂停非柜面管控措施，管控流水号为：{control_serial_number},请在2小时内核实。"
        )
        default_template_without_control = (
            "【武汉分行监测系统】账号：{account_id} 在 {time} 触发 {model_list} 模型告警。"
        )

        if control_serial_number:
            # 从配置获取带管控的消息模板
            template = self.config_manager.get_config_value(
                'alert_message_template_with_control',
                default=default_template_with_control
            )
            # 变量替换
            return template.format(
                account_id=account_id,
                time=time_str,
                model_list=model_list,
                control_serial_number=control_serial_number
            )
        else:
            # 从配置获取不带管控的消息模板
            template = self.config_manager.get_config_value(
                'alert_message_template_without_control',
                default=default_template_without_control
            )
            # 变量替换
            return template.format(
                account_id=account_id,
                time=time_str,
                model_list=model_list
            )

    def get_alert_control_records(
        self,
        filters: AlertControlFilters,
        pagination: PaginationParams,
        current_user_branch_no: Optional[str] = None
    ) -> AlertControlListResponse:
        """查询告警管控记录列表

        Args:
            filters: 筛选条件
            pagination: 分页参数
            current_user_branch_no: 当前用户的部门编号（用于权限过滤）

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
        filters: AlertControlFilters,
        current_user_branch_no: Optional[str] = None
    ) -> bytes:
        """导出告警管控记录为Excel

        Args:
            filters: 筛选条件
            current_user_branch_no: 当前用户的部门编号（用于权限过滤）

        Returns:
            导出的Excel文件内容（字节）
        """
        # 查询所有符合条件的记录
        query = self.db.query(FraudHunterModelAlertControlRecord)

        query = self._apply_filters(query, filters)
        records = query.order_by(FraudHunterModelAlertControlRecord.created_at.desc()).limit(5000).all()

        # 准备导出数据
        export_data = []
        logger.info(f"export records len : {len(records)}")
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
        if filters.model_ids:
            # 使用 JSON_CONTAINS 精确检查数组中是否包含指定的 model_ids
            # 避免模糊匹配导致的误匹配（如查找 2 时匹配到 12）
            # 使用 OR 逻辑：命中任意一个模型即可
            conditions = []
            for model_id in filters.model_ids:
                conditions.append(
                    func.json_contains(
                        FraudHunterModelAlertControlRecord.hit_model_ids,
                        f'{model_id}'
                    ) == True
                )
            query = query.filter(or_(*conditions))

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

        # 隐藏无效记录（告警和管控均为重复或未配置）
        if filters.hide_inactive:
            inactive_statuses = ['duplicate', 'not_configured']
            # 过滤条件：至少有一个状态是有效的（sent 或 executed）
            query = query.filter(
                or_(
                    ~FraudHunterModelAlertControlRecord.alert_status.in_(inactive_statuses),
                    ~FraudHunterModelAlertControlRecord.control_status.in_(inactive_statuses)
                )
            )

        return query

    def get_history_trend(
        self,
        req: TrendRequest,
        current_user_branch_no: Optional[str] = None,
    ) -> TrendResponse:
        """获取模型命中账户数的日/周/月历史趋势

        Args:
            req: 趋势请求参数（起止日期、粒度、模型ID列表）
            current_user_branch_no: 当前用户机构号（用于权限过滤）

        Returns:
            TrendResponse，含 series（时间刻度 × 模型 的去重账户数列表）
        """
        try:
            req_start = datetime.strptime(req.start_date, "%Y-%m-%d").date()
            req_end = datetime.strptime(req.end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"日期格式无效，应为 YYYY-MM-DD，当前值不合法: {e}")

        span_days = (req_end - req_start).days
        if span_days < 0:
            raise ValueError("开始日期不能晚于结束日期")
        if span_days > 180:
            raise ValueError("时间跨度不能超过180天")

        # ---- 确定待查询的模型列表 ----------------------------------------
        model_query = self.db.query(
            FraudHunterModelDefinition.id,
            FraudHunterModelDefinition.name
        ).filter(FraudHunterModelDefinition.status == "online")

        if req.model_ids:
            model_query = model_query.filter(FraudHunterModelDefinition.id.in_(req.model_ids))

        models = {mid: mname for mid, mname in model_query.all()}
        if not models:
            return TrendResponse(series=[], total_points=0, meta={"msg": "无可用模型"})

        # ---- 日期表达式（根据粒度）---------------------------------------
        tbl = FraudHunterModelAlertControlRecord
        if req.granularity == "week":
            date_expr = func.date_format(tbl.record_date, "%Y-W%v")
        elif req.granularity == "month":
            date_expr = func.date_format(tbl.record_date, "%Y-%m")
        else:  # day
            date_expr = func.date_format(tbl.record_date, "%Y-%m-%d")

        # ---- 逐模型构造 WHERE 条件，拼成 OR ------------------------------
        model_predicates = []
        for mid in models.keys():
            cond = func.json_contains(
                tbl.hit_model_ids,
                func.cast(text(str(mid)), Integer)
            )
            model_predicates.append(cond)

        if not model_predicates:
            return TrendResponse(series=[], total_points=0, meta={"msg": "无有效模型条件"})
        combined_predicate = or_(*model_predicates)

        # ---- 构建基查询 -------------------------------------------------
        query = (
            self.db.query(
                date_expr.label("date_point"),
                func.max(func.cast(tbl.hit_model_ids, String)).label("_model_ids"),
                func.count(func.distinct(tbl.account_id)).label("distinct_account_count"),
            )
            .filter(tbl.record_date.between(req_start, req_end))
            .filter(combined_predicate)
        )

        query = (
            query
            .group_by(date_expr)
            .order_by(date_expr)
        )

        raw_rows = query.all()

        # ---- 解析结果，按 date_point × model_id 展开 --------------------
        series: List[TrendPoint] = []
        for row in raw_rows:
            dp = row.date_point
            ids_str = row._model_ids
            if not ids_str:
                continue
            hit_model_ids_on_day: List[int] = []
            try:
                hit_model_ids_on_day = json.loads(ids_str) if isinstance(ids_str, str) else (ids_str or [])
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

            for mid in hit_model_ids_on_day:
                if mid in models and dp:
                    series.append(
                        TrendPoint(
                            date_point=str(dp),
                            model_id=mid,
                            model_name=models[mid],
                            distinct_account_count=row.distinct_account_count or 0,
                        )
                    )

        logger.info(
            f"[get_history_trend] granularity={req.granularity}, "
            f"models={list(models.keys())}, points={len(raw_rows)}, "
            f"expanded_series={len(series)}"
        )

        return TrendResponse(
            series=series,
            total_points=len(raw_rows),
            meta={"span_days": span_days, "model_count": len(models)},
        )

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
            'executed': '已执行',
            'whitelist': '白名单'
        }
        return status_map.get(status, status)
