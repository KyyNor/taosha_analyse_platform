import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from domain.wide_table.version_delta import VersionDelta, WideTableComparator


class TestVersionDelta:
    def test_mixed_static_changed_new_removed_columns(self):
        current = {
            1: {"version": 1, "indicator_code": "i_static"},
            2: {"version": 1, "indicator_code": "i_changed"},
            3: {"version": 1, "indicator_code": "i_removed"},
        }
        target = {
            1: {"version": 1, "indicator_code": "i_static"},
            2: {"version": 2, "indicator_code": "i_changed"},
            4: {"version": 1, "indicator_code": "i_new"},
        }

        delta = WideTableComparator.diff(current, target)

        assert isinstance(delta, VersionDelta)
        assert delta.static_cols == ["i_static"]
        assert delta.changed_cols == ["i_changed"]
        assert delta.new_cols == ["i_new"]
        assert delta.removed_cols == ["i_removed"]
        assert delta.deferred_cols == ["i_changed", "i_new"]
        assert delta.has_any_change is True

    def test_only_removed_columns_count_as_change(self):
        current = {
            1: {"version": 1, "indicator_code": "i_removed"},
            2: {"version": 1, "indicator_code": "i_static"},
        }
        target = {
            2: {"version": 1, "indicator_code": "i_static"},
        }

        delta = WideTableComparator.diff(current, target)

        assert delta.static_cols == ["i_static"]
        assert delta.changed_cols == []
        assert delta.new_cols == []
        assert delta.removed_cols == ["i_removed"]
        assert delta.has_any_change is True
        assert delta.deferred_cols == []

    def test_unchanged_columns_have_no_change(self):
        current = {1: {"version": 1, "indicator_code": "i_same"}}
        target = {1: {"version": 1, "indicator_code": "i_same"}}

        delta = WideTableComparator.diff(current, target)

        assert delta.static_cols == ["i_same"]
        assert delta.changed_cols == []
        assert delta.new_cols == []
        assert delta.removed_cols == []
        assert delta.has_any_change is False
