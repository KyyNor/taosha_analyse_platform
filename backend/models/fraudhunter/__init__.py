"""
FraudHunter模块数据库模型
"""

from .indicator import (
    FraudHunterIndicatorTask,
    FraudHunterIndicatorTaskHistory,
    FraudHunterIndicatorDefinition,
    FraudHunterIndicatorHistory,
    FraudHunterSequenceCounter,
)
from .risk_control_model import (
    FraudHunterModelDefinition,
    FraudHunterModelHistory,
)
from .dry_run_task import (
    FraudHunterDryRunExecution,
)
from .wide_table import (
    FraudHunterIndicatorRunProgress,
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
)
from .model_execution_tracking import (
    FraudHunterModelExecution,
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord,
    FraudHunterSystemConfig,
)
from .alert_notify_targets import (
    FraudHunterAlertAcctAssign,
    FraudHunterAlertCustOwner,
)

__all__ = [
    'FraudHunterIndicatorTask',
    'FraudHunterIndicatorTaskHistory',
    'FraudHunterIndicatorDefinition',
    'FraudHunterIndicatorHistory',
    'FraudHunterModelDefinition',
    'FraudHunterModelHistory',
    'FraudHunterDryRunExecution',
    'FraudHunterSequenceCounter',
    'FraudHunterIndicatorRunProgress',
    'FraudHunterWideTableVersion',
    'FraudHunterWideTableSnapshot',
    'FraudHunterModelExecution',
    'FraudHunterModelHitRecord',
    'FraudHunterModelAlertControlRecord',
    'FraudHunterSystemConfig',
    'FraudHunterAlertAcctAssign',
    'FraudHunterAlertCustOwner',
]
