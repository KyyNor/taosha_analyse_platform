"""告警管控记录机构号筛选请求契约测试。"""

import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from schemas.fraudhunter.alert_control_record import (
    AlertControlExportRequest,
    AlertControlFilters,
    AlertControlListRequest,
)


def test_branch_no_is_accepted_by_list_request_and_filters():
    request = AlertControlListRequest(branch_no="110026")
    filters = AlertControlFilters(branch_no=request.branch_no)

    assert request.branch_no == "110026"
    assert filters.model_dump(exclude_none=True)["branch_no"] == "110026"


def test_branch_no_is_accepted_by_export_request_and_filters():
    request = AlertControlExportRequest(branch_no="110026", format="excel")
    filters = AlertControlFilters(branch_no=request.branch_no)

    assert request.branch_no == "110026"
    assert filters.model_dump(exclude_none=True)["branch_no"] == "110026"
