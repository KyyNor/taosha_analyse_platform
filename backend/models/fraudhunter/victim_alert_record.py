"""
FraudHunter 受害人预警记录
"""

from datetime import datetime

from sqlalchemy import Column, BigInteger, String, Text, DateTime, Date, JSON, Index, UniqueConstraint

from models.db_base import Base


class FraudHunterVictimAlertRecord(Base):
    """受害人预警记录表：实时任务命中受害人模型后写入，由 DS 任务发送给下游服务"""
    __tablename__ = "fraudhunter_victim_alert_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    alert_id = Column(String(32), nullable=False, comment='告警ID：md5(账号+命中模型ID+告警时间)')
    account_id = Column(String(64), nullable=False, comment='账号')
    hit_model_ids = Column(JSON, nullable=False, comment='命中模型ID列表')
    hit_model_names = Column(JSON, nullable=False, comment='命中模型名称列表')
    hit_time = Column(DateTime, nullable=False, comment='命中时间（告警管控记录的告警时间）')
    record_date = Column(Date, nullable=False, comment='记录日期')
    status = Column(String(16), nullable=False, default='new', comment='状态：new 新建/sent 已发送/error 异常')
    message = Column(Text, comment='信息：异常时记录错误内容')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        UniqueConstraint('alert_id', name='uk_fh_victim_alert_id'),
        # 同一账号同一记录日期只记录一次
        UniqueConstraint('account_id', 'record_date', name='uk_fh_victim_account_date'),
        Index('idx_fh_victim_record_date', 'record_date'),
        Index('idx_fh_victim_status', 'status'),
        {'comment': '受害人预警记录表'}
    )

    def __repr__(self):
        return (f"<FraudHunterVictimAlertRecord(alert_id='{self.alert_id}', account_id='{self.account_id}', "
                f"record_date='{self.record_date}', status='{self.status}')>")
