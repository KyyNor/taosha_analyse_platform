"""Utilities for typed numeric FraudHunter wide-table columns."""

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


NUMERIC_REGEX_SPARK = r"^-?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$"
NUMERIC_REGEX_PANDAS = r"^-?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"
NUMERIC_PATTERN_PANDAS = re.compile(NUMERIC_REGEX_PANDAS)


@dataclass(frozen=True)
class NumericConversionStats:
    indicator_code: str
    blank_count: int
    invalid_count: int


class WideTableNumericTypeHelper:
    """Centralizes numeric physical-type behavior for wide-table generation."""

    @staticmethod
    def is_numeric_meta(meta: Dict[str, Any]) -> bool:
        return str(meta.get("data_type") or "").lower() == "numeric"

    @staticmethod
    def pg_type_for_indicator(meta: Dict[str, Any], long_text_indicator_list: Iterable[str]) -> str:
        indicator_code = meta.get("indicator_code")
        if WideTableNumericTypeHelper.is_numeric_meta(meta):
            return "DOUBLE PRECISION"
        if indicator_code in set(long_text_indicator_list):
            return "text"
        return "varchar(1000)"

    @staticmethod
    def numeric_indicator_codes(indicator_metadata: Dict[Any, Dict[str, Any]]) -> List[str]:
        return [
            meta.get("indicator_code")
            for meta in indicator_metadata.values()
            if meta.get("indicator_code") and WideTableNumericTypeHelper.is_numeric_meta(meta)
        ]

    @staticmethod
    def spark_select_expression(meta: Dict[str, Any]) -> str:
        code = meta.get("indicator_code")
        if not code:
            raise ValueError("indicator_code is required")

        if not WideTableNumericTypeHelper.is_numeric_meta(meta):
            return code

        value_sql = f"TRIM(CAST({code} AS STRING))"
        return (
            "CASE "
            f"WHEN {code} IS NULL OR {value_sql} = '' THEN CAST(NULL AS DOUBLE) "
            f"WHEN {value_sql} RLIKE '{NUMERIC_REGEX_SPARK}' THEN CAST({value_sql} AS DOUBLE) "
            "ELSE CAST(NULL AS DOUBLE) "
            f"END AS {code}"
        )

    @staticmethod
    def spark_select_expressions(indicator_metadata: Dict[Any, Dict[str, Any]]) -> List[str]:
        return [
            WideTableNumericTypeHelper.spark_select_expression(meta)
            for meta in indicator_metadata.values()
            if meta.get("indicator_code")
        ]

    @staticmethod
    def convert_numeric_dataframe_columns(
        df: pd.DataFrame,
        indicator_metadata: Dict[Any, Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, List[NumericConversionStats]]:
        converted = df.copy()
        stats: List[NumericConversionStats] = []

        for code in WideTableNumericTypeHelper.numeric_indicator_codes(indicator_metadata):
            if code not in converted.columns:
                continue

            raw = converted[code]
            as_text = raw.astype("string")
            stripped = as_text.str.strip()
            blank_mask = raw.isna() | stripped.fillna("").eq("")
            valid_mask = stripped.str.fullmatch(NUMERIC_PATTERN_PANDAS).fillna(False)
            numeric_values = pd.to_numeric(stripped.where(valid_mask), errors="coerce")
            invalid_mask = ~blank_mask & ~valid_mask

            converted[code] = numeric_values.astype("float64")
            stats.append(
                NumericConversionStats(
                    indicator_code=code,
                    blank_count=int(blank_mask.sum()),
                    invalid_count=int(invalid_mask.sum()),
                )
            )

        return converted, stats
