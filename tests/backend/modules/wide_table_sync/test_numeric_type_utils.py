import sys
from pathlib import Path
import importlib.util

import pandas as pd

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

_module_path = (
    _backend_root
    / "services"
    / "fraudhunter"
    / "wide_table_service"
    / "numeric_type_utils.py"
)
_spec = importlib.util.spec_from_file_location("numeric_type_utils", _module_path)
numeric_type_utils = importlib.util.module_from_spec(_spec)
sys.modules["numeric_type_utils"] = numeric_type_utils
_spec.loader.exec_module(numeric_type_utils)

NumericConversionStats = numeric_type_utils.NumericConversionStats
WideTableNumericTypeHelper = numeric_type_utils.WideTableNumericTypeHelper


class TestWideTableNumericTypeHelper:
    def test_is_numeric_meta_true_for_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is True

    def test_is_numeric_meta_true_for_uppercase_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "NUMERIC"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is True

    def test_is_numeric_meta_false_for_non_numeric(self):
        meta = {"indicator_code": "i_name", "data_type": "string"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is False

    def test_pg_type_for_numeric_is_double_precision(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, []) == "DOUBLE PRECISION"

    def test_pg_type_for_non_numeric_keeps_existing_varchar_behavior(self):
        meta = {"indicator_code": "i_name", "data_type": "string"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, []) == "varchar(1000)"

    def test_pg_type_for_long_text_stays_text(self):
        meta = {"indicator_code": "i_desc", "data_type": "string"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, ["i_desc"]) == "text"

    def test_numeric_indicator_codes_returns_only_numeric_codes(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
            "3": {"indicator_code": "i_rate", "data_type": "NUMERIC"},
            "4": {"data_type": "numeric"},
        }
        assert WideTableNumericTypeHelper.numeric_indicator_codes(metadata) == ["i_amt", "i_rate"]

    def test_spark_numeric_safe_cast_expression_handles_blank_and_invalid_values(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_amt", "data_type": "numeric"}
        )
        assert "CASE" in expr
        assert "TRIM(CAST(i_amt AS STRING)) = ''" in expr
        assert "RLIKE" in expr
        assert "CAST(TRIM(CAST(i_amt AS STRING)) AS DOUBLE)" in expr
        assert "ELSE CAST(NULL AS DOUBLE)" in expr
        assert "AS i_amt" in expr

    def test_spark_non_numeric_expression_passes_column_through(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_name", "data_type": "string"}
        )
        assert expr == "i_name"

    def test_spark_select_expressions_mixes_numeric_and_text(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }
        expressions = WideTableNumericTypeHelper.spark_select_expressions(metadata)
        assert expressions[0].endswith("AS i_amt")
        assert expressions[1] == "i_name"

    def test_convert_numeric_dataframe_columns_turns_blank_invalid_to_null(self):
        df = pd.DataFrame(
            {
                "target_id": ["a", "b", "c", "d"],
                "i_amt": ["12.5", "", "  ", "not-a-number"],
                "i_name": ["x", "y", "z", "w"],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted is not df
        assert df["i_amt"].tolist() == ["12.5", "", "  ", "not-a-number"]
        assert converted["i_amt"].dtype == "float64"
        assert converted["i_amt"].tolist()[0] == 12.5
        assert pd.isna(converted["i_amt"].tolist()[1])
        assert pd.isna(converted["i_amt"].tolist()[2])
        assert pd.isna(converted["i_amt"].tolist()[3])
        assert converted["i_name"].tolist() == ["x", "y", "z", "w"]
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=2, invalid_count=1)
        ]

    def test_convert_numeric_dataframe_columns_counts_null_blank_and_invalid(self):
        df = pd.DataFrame(
            {
                "i_amt": [None, "1", "1e3", ".5", "-2.25", "bad"],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted["i_amt"].tolist()[1:5] == [1.0, 1000.0, 0.5, -2.25]
        assert pd.isna(converted["i_amt"].tolist()[0])
        assert pd.isna(converted["i_amt"].tolist()[5])
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=1, invalid_count=1)
        ]

    def test_numeric_conversion_stats_equality(self):
        assert NumericConversionStats("i_amt", 1, 2) == NumericConversionStats("i_amt", 1, 2)
        assert NumericConversionStats("i_amt", 1, 2) != NumericConversionStats("i_amt", 2, 1)
