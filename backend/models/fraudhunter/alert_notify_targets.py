"""
FraudHunter 告警通知目标关联模型

- FraudHunterAlertAcctAssign: 账号 → 客户经理通知号对应表
- FraudHunterAlertCustOwner:  客户号 → 理财经理通知号对应表
"""

from sqlalchemy import Column, String, Date, DateTime, PrimaryKeyConstraint
from datetime import datetime
from models.db_base import Base


class FraudHunterAlertAcctAssign(Base):
    """账号与客户经理通知号对应表

    用于客户经理场景：命中后根据 account_id 查出对应的客户经理通知号，
    再通过 sendwx 接口发送告警。

    notice_no 支持逗号拼接多账号（如 "user1,user2"），lookup 时会拆解去重。
    每个 account_id 唯一（UNIQUE），一条数据代表一个账号的全部客户经理。
    """
    __tablename__ = "fraudhunter_alert_acct_assign"

    acct_no = Column(String(64), nullable=False, unique=True, comment='账号标识')
    notice_no = Column(String(512), nullable=True, comment='客户经理通知号（逗号拼接，多个去重发送）')
    etl_date = Column(Date, nullable=True, comment='数据日期')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        PrimaryKeyConstraint('acct_no'),
        {'comment': '账号与客户经理通知号对应表'},
    )


class FraudHunterAlertCustOwner(Base):
    """客户号与理财经理通知号对应表

    用于理财经理场景：命中后根据 customer_no（宽表字段 i_dep_acct_no_offline_00001）
    查出对应的理财经理通知号，再通过 sendwx 接口发送告警。

    notice_no 支持逗号拼接多账号（如 "fm1,fm2"），lookup 时会拆解去重。
    每个 customer_no 唯一（UNIQUE），一条数据代表一个客户号的主要理财经理。
    """
    __tablename__ = "fraudhunter_alert_cust_owner"

    cust_no = Column(String(64), nullable=False, unique=True, comment='客户号（宽表 i_dep_acct_no_offline_00001）')
    notice_no = Column(String(512), nullable=True, comment='理财经理通知号（逗号拼接，多个去重发送）')
    etl_date = Column(Date, nullable=True, comment='数据日期')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        PrimaryKeyConstraint('cust_no'),
        {'comment': '客户号与理财经理通知号对应表'},
    )