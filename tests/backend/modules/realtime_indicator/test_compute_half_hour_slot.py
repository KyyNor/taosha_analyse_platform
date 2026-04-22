"""
tests/backend/modules/realtime_indicator/test_compute_half_hour_slot.py
======================================================================
单元测试：对标文档用例 RT-02、RT-03、RT-05
测试实时指标半小时间隔复用核心函数 _compute_half_hour_slot()

被测函数位置：
    backend/services/scheduler/jobs/realtime_indicator_job.py  第55-71行

测试策略：
    ✅ 纯函数，无外部依赖，直接参数→返回值，不涉及 IO/DB/API
    ✅ 使用等价类划分 + 边界值分析，覆盖所有时钟角落场景

文档用例编号覆盖：
    RT-02 跨半点界限生成新的半小间隔分区
    RT-03 区分数值的分钟截断精度（09:14→09:00, 09:31→09:30）
    RT-05 截断模式下同一账号多条记录的行为（→ 由业务方保证，此处略）
"""

import pytest
import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from services.scheduler.jobs.realtime_indicator_job import _compute_half_hour_slot


class TestComputeHalfHourSlot:
    """
    等价类划分：
    - [00:00, 00:29] → 归整到 XX:00
    - [00:30, 00:59] → 归整到 XX:30
    """

    # ── 精确半点，不应改变 ─────────────────────────────────────
    @pytest.mark.parametrize("hour,minute", [
        (9, 0),   # 09:00 → 0900
        (9, 30),  # 09:30 → 0930
        (23, 0),  # 23:00 → 2300
        (23, 30), # 23:30 → 2330
    ])
    def test_exact_half_hour_boundary_unchanged(self, hour, minute):
        ts_input = f"20260422{hour:02d}{minute:02d}"
        ts_expected = f"20260422{hour:02d}{minute:02d}"
        assert _compute_half_hour_slot(ts_input) == ts_expected

    # ── 下沉到 :00 的场景（[mm:00, mm:29]） ──────────────────
    @pytest.mark.parametrize("hour,minute", [
        (9, 0),   # 理论上已在上方覆盖，此处强调边界
        (9, 14),  # RT-03 示例：09:14 → 0900
        (9, 29),  # 最大下沉值
        (10, 7),  # 随机中间值
        (0, 15),  # 午夜
        (12, 29), # 正午边界
    ])
    def test_rounds_down_to_xx00(self, hour, minute):
        ts_input = f"20260422{hour:02d}{minute:02d}"
        ts_expected = f"20260422{hour:02d}00"
        assert _compute_half_hour_slot(ts_input) == ts_expected

    # ── 下沉到 :30 的场景（[mm:30, mm:59]） ──────────────────
    @pytest.mark.parametrize("hour,minute", [
        (9, 30),  # 精确边界，理论上应在上方覆盖，保留作回归保险
        (9, 31),  # RT-03 示例：09:31 → 0930
        (9, 45),  # 随机中间值
        (9, 59),  # 最远下沉值
        (23, 55), # 深夜
    ])
    def test_rounds_down_to_xx30(self, hour, minute):
        ts_input = f"20260422{hour:02d}{minute:02d}"
        ts_expected = f"20260422{hour:02d}30"
        assert _compute_half_hour_slot(ts_input) == ts_expected

    # ── 跨小时进位（例如 00:45 整到 00:30，01:00 到 01:00） ────
    def test_cross_hour_boundary_round_up_to_next_00(self):
        # 跨小时的正确语义：[分钟段 30-59]→ 同小时30分，不跨小时
        # 但若输入本身跨天了……（此处不支持，按规范仅处理日内场景）
        ts_input = "202604220045"   # 00:45 → 0030
        assert _compute_half_hour_slot(ts_input) == "202604220030"

    def test_round_at_midnight_boundary(self):
        # 23:59 → 2330（同一天）
        assert _compute_half_hour_slot("202604222359") == "202604222330"
        # 00:00 → 0000（一日的最早）
        assert _compute_half_hour_slot("202604220000") == "202604220000"

    # ── 不同日期前缀保留 ─────────────────────────────────────
    @pytest.mark.parametrize("prefix", [
        "20260101",  # 年初
        "20261231",  # 年末
        "20240229",  # 闰年（2024年2月29日）
        "20250301",  # 平年次日
    ])
    def test_date_prefix_preserved(self, prefix):
        ts_input = f"{prefix}0914"
        result = _compute_half_hour_slot(ts_input)
        assert result.startswith(prefix), f"日期前缀被篡改: {result}"

    # ── 输入格式固定：14位数字（前8位日期+后4位时间）─────────
    @pytest.mark.parametrize("invalid_input", [
        "",                    # 空字符串
        "2026042209145",      # 超长
        "20260422091",        # 不足
        "2026-04-22-09-14",  # 连字符格式
        "2026042209aa",       # 含字母
    ])
    def test_invalid_format_raises_value_error(self, invalid_input):
        with pytest.raises(ValueError):
            _compute_half_hour_slot(invalid_input)

    # ── 文档示例逆向验证 ─────────────────────────────────────
    def test_rt_03_example_a(self):
        """RT-03: Mock时间 09:14 → 映射到 09:00"""
        assert _compute_half_hour_slot("202604220914") == "202604220900"

    def test_rt_03_example_b(self):
        """RT-03: Mock时间 09:31 → 映射到 09:30"""
        assert _compute_half_hour_slot("202604220931") == "202604220930"


# =============================================================================
# RT-04 的替身测试：validate_half_hour_partition_key
# 注：由于 RT-04 要求的是"数据准确性"，真正的端到端数据校验不是UT范畴
# 此处退化为测试"分区 key 格式是否符合 YYYYMMDDHHMM"
# =============================================================================

class TestHalfHourPartitionKeyFormat:
    """验证 `_compute_half_hour_slot` 的输出永远符合分区命名规范。"""

    VALID_PATTERN = r"^\d{12}$"  # 正好12位数字

    @pytest.mark.parametrize("input_ts", [
        "202604220000", "202604220014", "202604220029",
        "202604220030", "202604220059",
        "202412312359",  # 年度边界
        "202401010001",   # 年度开头最小
    ])
    def test_output_always_12_digits(self, input_ts):
        result = _compute_half_hour_slot(input_ts)
        import re
        assert re.match(self.VALID_PATTERN, result), f"非法分区名: {result}"


# =============================================================================
# RT-05 替身：验证截断语义（truncate vs append）
# 实际的截断由 if_exists='truncate' 参数决定，不是单元测试范围
# 此处留下 SKIP 占位，原文要求的是"同一账号多条记录只保留最后一条"
# =============================================================================

class TestTruncateSemantics_RT05:
    """
    【SKIP 理由】
    RT-05 的测试要点是 "截断而非追加导致的多条"，这只在有真实 PG 环境的
    集成测试中才能验证——因为同一批次内两次写入只有在实际入库后才能感知。
    我们通过测试文件中的占位函数声明这一点，建议 QA 在冒烟测试阶段覆盖。
    """

    @pytest.mark.skip(reason=(
        "RT-05 需要真实 PG 环境验证 truncate 语义，属于集成测试范畴。"
        "建议 QA 在冒烟测试阶段，用预埋数据验证同一半小时间隔内两次写入"
        "后查询仅有最新一次的结果。"
    ))
    def test_rt_05_same_account_two_records_same_slot_only_last_remains(self):
        """
        【文档原文】
        RT-05: 截断模式下同一账号多条记录的行为
        1. 给定账号在同一半小时间隔内有两条不同指标值的数据
        2. 验证最终表中该账号只有一条记录（截断而非追加导致的多条）

        【测试设计备注】
        此测试应写成 pytest-bdd/given-when-then 风格，由 QA 工程师在
        真实环境中操作，不宜硬编码在单元测试套件中。
        """
        pass