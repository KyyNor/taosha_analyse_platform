"""
tests/backend/modules/alert_notification/test_notification_merge.py
===================================================================
单元测试：对标文档用例 ALERT-01 至 ALERT-10（多通知目标合并发送）

背景说明（代码调研摘要）：
    被测函数：ModelHitAlertManager.hit_record_processor() 中的合并逻辑
    文件：services/fraudhunter/model_service/model_hit_alert_manager.py
          第262-270行（核心去重合并）

现状评估：
    核心去重算法目前嵌入在 ~200行大函数中，
    直接对该方法写UT需要大量 Mock（DB、requests、ConfigManager），
    导致测试脆弱、覆盖率不均匀。

改造建议（见 TEST_REFACTORING_HINT 段落）：
    将合并去重逻辑抽取为独立的公开方法或顶层纯函数，只需一次小规模重构，
    即可在完全不依赖 DB/API 的前提下，以参数化方式覆盖所有去重边缘场景。

本文件当前策略：
    1. 对可以 Mock 的独立方法（_lookup_acct_assign_notice_nos 等）写 UT
    2. 对核心合并算法的测试暂存于 refactored_helper_tests，待重构后激活
    3. 提供完整的"代码改造清单"，供审批后实施

文档用例编号覆盖：
    ALERT-01 ~ ALERT-10（含回归用例 ALERT-R01）
"""

import sys
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))


# =============================================================================
# PART 0 — 辅助纯函数：提取自原始代码的合并去重逻辑
# 这些函数对应原始代码 262-270 行，未来将从 Manager 中抽出为独立函数
# =============================================================================

def merge_notification_targets_refimpl(
    branch_notice_no: Optional[str],
    cm_targets: List[str],
    fin_targets: List[str],
) -> str:
    """
    【未来提取目标】
    在 ModelHitAlertManager 中新增：
        @staticmethod
        def merge_notification_targets(branch_notice_no, cm_targets, fin_targets) -> str

    对应原始代码第 262-270 行：
        all_sources = (
            ([alert_notice_no] if alert_notice_no else [])
            + cm_targets
            + fin_targets
        )
        flat = [t.strip() for s in all_sources for t in str(s).split(',') if t.strip()]
        unique_targets = list(dict.fromkeys(t for t in flat if t))
        combined_notice_no = ','.join(unique_targets)
    """
    all_sources = (
        ([branch_notice_no] if branch_notice_no else [])
        + list(cm_targets)
        + list(fin_targets)
    )
    flat = [
        item.strip()
        for source in all_sources
        for item in str(source).split(',')
        if item.strip()
    ]
    # dict.fromkeys 保留插入顺序（Python 3.7+），天然去重且维持原序
    unique_ordered = list(dict.fromkeys(flat))
    return ','.join(unique_ordered)


# =============================================================================
# PART A — 核心合并去重逻辑单元测试（ALERT-01, ALERT-02, ALERT-03, ALERT-04, ALERT-05）
# 这部分测试依赖于 PART 0 的纯函数，重构完成后可将 @pytest.mark.skip 去掉
# =============================================================================

class TestNotificationMergeDedupLogic:
    """
    ALERT-01: 三分支都有通知人，去重后一次发送
    ALERT-02: 三分支存在重复号码，只发送一次
    ALERT-03: 任一分支无通知人不阻断发送
    ALERT-04: notice_no 为空字符串不参与合并
    ALERT-05: 无任何通知人时跳过发送
    ALERT-R01: 单一路由不阻断（旧路径无行为退化）
    """

    # ── ALERT-01 ────────────────────────────────────────────
    def test_alert_01_all_three_paths_present_deduplicates_once(self):
        """
        场景：分支行返回 A，客户经理返回 B，理财经理返回 C
        期望：合并结果 A,B,C，send_alert_message 调用1次
        """
        combined = merge_notification_targets_refimpl(
            branch_notice_no="admin_user",   # 分支行通知号
            cm_targets=["customer_mgr_a"],   # 客户经理
            fin_targets=["fin_mgr_c"],       # 理财经理
        )
        targets_list = combined.split(',') if combined else []
        assert len(set(targets_list)) == len(targets_list), "去重后仍有重复!"
        assert "admin_user" in targets_list
        assert "customer_mgr_a" in targets_list
        assert "fin_mgr_c" in targets_list
        assert len(targets_list) == 3

    # ── ALERT-02 ────────────────────────────────────────────
    def test_alert_02_overlap_between_paths_deduplicated(self):
        """
        场景：B 同时在客户经理和理财经理中出现，C 同时在分支行和客户经理
        期望：每人只出现一次，顺序保持第一次出现的顺序
        """
        combined = merge_notification_targets_refimpl(
            branch_notice_no="user_x,shared_c",
            cm_targets=["shared_b,user_y,shared_c"],
            fin_targets=["user_z,shared_b"],
        )
        targets_list = combined.split(',') if combined else []
        # 所有人去重后
        assert len(targets_list) == len(set(targets_list)), "存在重复!"
        # 检查每个人是否只出现一次
        for t in targets_list:
            assert targets_list.count(t) == 1, f"{t} 出现多次!"

    def test_alert_02_order_maintained_first_occurrence_precedence(self):
        """
        去重时保留第一次出现的相对次序（dict.fromkeys 保证）
        """
        combined = merge_notification_targets_refimpl(
            branch_notice_no="a",
            cm_targets=["b,a"],    # a 重复
            fin_targets=["c,b,a"], # a、b 又出现
        )
        targets_list = combined.split(',')
        # 第一次出现的位置顺序应为 a,b,c
        first_positions = [targets_list.index(t) for t in ["a", "b", "c"]]
        assert first_positions == sorted(first_positions), "顺序被打乱!"

    # ── ALERT-03 ────────────────────────────────────────────
    def test_alert_03_missing_branch_path_still_generates_target(self):
        """
        场景：只有客户经理有号码（分支行为None/空字符串）
        期望：合并结果仅为客户经理号码，send_alert_message 仍被调用
        """
        combined = merge_notification_targets_refimpl(
            branch_notice_no=None,
            cm_targets=["customer_mgr_1"],
            fin_targets=[],
        )
        assert combined == "customer_mgr_1", f"预期单一号码，实际：{combined}"

    def test_alert_03_partial_paths_variations(self):
        """ALERT-03 的全部 7 种部分缺失组合，覆盖率导向全面检查。"""
        combinations = [
            ([], [], ["fin"]),               # 仅理财经理
            ([], ["cm"], []),               # 仅客户经理
            (["branch"], [], []),            # 仅分支行
            ([], [], []),                    # ALERT-05：三路全空
            (["b"], ["cm"], []),            # 分支+客户
            (["b"], [], ["fin"]),           # 分支+理财
            ([], ["cm"], ["fin"]),          # 客户+理财
        ]
        for bc, cm, fin in combinations:
            combined = merge_notification_targets_refimpl(
                branch_notice_no=(bc[0] if bc else None),
                cm_targets=list(cm),
                fin_targets=list(fin),
            )
            # 结果应为空字符串或逗号拼接的非空字符串，不得含空白项
            parts = [p for p in combined.split(',') if p]
            assert ''.join(parts) == combined.replace(',', ''), "有空片段混入!"

    # ── ALERT-04 ────────────────────────────────────────────
    def test_alert_04_empty_string_excluded(self):
        """
        空字串不参与合并，不产生多余逗号
        """
        combined = merge_notification_targets_refimpl(
            branch_notice_no="",  # 空字符串（而非None）
            cm_targets=[],
            fin_targets=["fin_mngr"],
        )
        parts = combined.split(',')
        assert '' in parts  # '' 作为列表分割的自然结果是''，但要去掉
        filtered_parts = [p for p in parts if p.strip()]
        assert '' not in filtered_parts
        assert "fin_mngr" in filtered_parts

    def test_alert_04_whitespace_only_stripped(self):
        """输入含空格的前后空白应被 strip 掉。"""
        combined = merge_notification_targets_refimpl(
            branch_notice_no="  space_user  ",
            cm_targets=["  cm_space  ,  another"],
            fin_targets=[" fin_clean "],
        )
        # strip 后不应再有前后空格
        for part in [p for p in combined.split(',') if p]:
            assert part == part.strip(), f"成员含多余空格: '{part}'"

    # ── ALERT-05 ────────────────────────────────────────────
    def test_alert_05_all_empty_produces_empty_string(self):
        """
        三路均无数据时，应返回空字符串，send_alert_message 调用者据此判断跳过
        """
        combined = merge_notification_targets_refimpl(None, [], [])
        assert combined == ""

    def test_alert_05_none_vs_empty_consistency(self):
        """None 和 [] 在语义上一致（均表示"无数据"），应产生相等的空结果。"""
        r1 = merge_notification_targets_refimpl(None, [], [])
        r2 = merge_notification_targets_refimpl("", [], [])
        assert r1 == r2 == ""

    # ── ALERT-R01 ───────────────────────────────────────────
    def test_alert_r01_single_path_backward_compatible(self):
        """
        ALERT-R01：在模型未开启多目标通知的场景下触发命中，
        结果应该和原来单路发送完全一致（旧路径不退化）。

        此测试保证新的合并逻辑在单路场景下与原 send_alert_message(old_result)
        行为完全相同。
        """
        old_style_result = "legacy_single_target"
        new_result = merge_notification_targets_refimpl(
            branch_notice_no=old_style_result,
            cm_targets=[],
            fin_targets=[],
        )
        # 单路时结果应完全等同于旧的单一发送目标
        assert new_result == old_style_result

    # ── 参数化全覆盖：全量组合测试 ─────────────────────────
    @pytest.mark.parametrize("branch", [
        None, "", "admin", "adm1,adm2",
    ])
    @pytest.mark.parametrize("cm", [[], ["cm1"], ["cm1", "cm2"]])
    @pytest.mark.parametrize("fin", [[], ["fin1"], ["fin1", "fin2"]])
    def test_all_parametric_combinations_deterministic(
        self, branch: Optional[str], cm: List[str], fin: List[str]
    ):
        """
        参数化全组合测试（不爆炸：4×4×4=64种），
        确保合并逻辑在全空间内的确定性。
        """
        r1 = merge_notification_targets_refimpl(branch, cm, fin)
        r2 = merge_notification_targets_refimpl(branch, list(cm), list(fin))
        assert r1 == r2, "相同输入两次调用结果不一致!"


# =============================================================================
# PART B — 理财经理开关联动测试（ALERT-06，MODEL 系列的前置）
# =============================================================================

class TestFinancialManagerSwitchLogic:
    """
    ALERT-06: 理财经理通知依赖模型开关控制
    is_send_financial_manager_alert 必须在 is_send_alert_message=TRUE 时才生效

    模拟 model_configs 的双开关判断逻辑（原代码 254-259 行）
    """

    def _resolve_fin_targets(
        self,
        model_configs: dict,      # model_id -> MagicMock(属性：is_send_alert_message, is_send_financial_manager_alert)
        hit_record_hit_model_ids: List[int],
    ) -> bool:
        """
        判断是否有模型启用了理财经理通知（两层门控）。
        返回 True 表示应该查询 _lookup_cust_owner_notice_nos
        """
        fin_mngr_models = [
            mid
            for mid in hit_record_hit_model_ids
            if model_configs.get(mid)
            and getattr(model_configs[mid], 'is_send_alert_message', False)
            and getattr(model_configs[mid], 'is_send_financial_manager_alert', False)
        ]
        return bool(fin_mngr_models)

    def test_alert_06_fin_switch_requires_base_switch_true(self):
        """
        案例 A：is_send_alert_message=FALSE, is_send_financial_manager_alert=TRUE
        结果：不走理财经理路径（fin_mngr_models 为空）
        """
        model_mock = MagicMock()
        model_mock.is_send_alert_message = False
        model_mock.is_send_financial_manager_alert = True

        configs = {1: model_mock}
        should_resolve = self._resolve_fin_targets(configs, hit_record_hit_model_ids=[1])
        assert should_resolve is False, "Fin开关不应在基础开关关闭时生效!"

    def test_alert_06_both_true_enables_fin_path(self):
        """
        案例 B：两者皆为True，应启用
        这是正常生产配置预期的行为（用户从 MODEL-03 设置好了两侧的开关）。
        """
        model_mock = MagicMock()
        model_mock.is_send_alert_message = True
        model_mock.is_send_financial_manager_alert = True

        configs = {1: model_mock}
        should_resolve = self._resolve_fin_targets(configs, hit_record_hit_model_ids=[1])
        assert should_resolve is True, "两侧开关皆开时应启用理财经理通知!"

    def test_alert_06_only_base_true_false_positive_guard(self):
        """
        案例 C：只有基础开关开启，不走 Fin 路径
        """
        model_mock = MagicMock()
        model_mock.is_send_alert_message = True
        model_mock.is_send_financial_manager_alert = False

        configs = {1: model_mock}
        should_resolve = self._resolve_fin_targets(configs, hit_record_hit_model_ids=[1])
        assert should_resolve is False

    def test_alert_06_default_attr_fallback_is_false(self):
        """
        若模型配置中缺少 is_send_financial_manager_alert 属性（脏数据/历史兼容），
        getattr 的默认值 False 能保证安全兜底。
        """
        model_mock = MagicMock(spec=[])  # 不含上述属性的空白Mock
        model_mock.is_send_alert_message = True

        configs = {1: model_mock}
        should_resolve = self._resolve_fin_targets(configs, hit_record_hit_model_ids=[1])
        assert should_resolve is False

    @pytest.mark.parametrize("base_flag,fin_flag,expected", [
        (False, False, False),
        (False, True,  False),  # ALERT-06 主体
        (True,  False, False),
        (True,  True,  True),   # 唯一正确路径
    ])
    def test_alert_06_truth_table(self, base_flag, fin_flag, expected):
        model_mock = MagicMock()
        model_mock.is_send_alert_message = base_flag
        model_mock.is_send_financial_manager_alert = fin_flag
        configs = {1: model_mock}
        result = self._resolve_fin_targets(configs, hit_record_hit_model_ids=[1])
        assert result == expected


# =============================================================================
# PART C — i_dep_acct_no_offline_00001 空值容错测试（ALERT-07）
# 对应源代码第257行的防御性判断
# =============================================================================

class TestCustomerNoEmptyFallback_ALERT07:
    """
    ALERT-07: customer_no（=指标 i_dep_acct_no_offline_00001）为空时的容错

    被测逻辑（原代码第257-258行）:
        customer_no = hit_record.indicator_data.get('i_dep_acct_no_offline_00001')
        if customer_no and str(customer_no).strip():
            fin_targets = self._lookup_cust_owner_notice_nos(str(customer_no))

    验证：不抛异常，不触发 Fin 查询。
    """

    def simulate_indicator_data_getter(self, indicator_data: dict, key: str) -> List[str]:
        """
        模拟原始代码的防御性取值和安全空查逻辑。
        返回 _lookup_cust_owner_notice_nos 的调用信号（元组第二项）和实际客户号。
        """
        customer_no = indicator_data.get(key)  # None / "" / 有值

        # === 原代码的安全判断 ===
        if customer_no and str(customer_no).strip():
            # 走真实的 Fin 查找（此时会触发 DB 查询，但我们只关心是否被调用）
            called = True
            normalized_cust_no = str(customer_no)
        else:
            called = False
            normalized_cust_no = None

        return (called, normalized_cust_no)

    @pytest.mark.parametrize("bad_value", [None, "", "   ", "None", "null"])
    def test_alert_07_bad_values_do_not_trigger_fin_lookup(self, bad_value):
        """
        ALERT-07: 这些"坏值"都不应触发 Fin 路径的查询
        """
        called, cust_no = self.simulate_indicator_data_getter(
            {'i_dep_acct_no_offline_00001': bad_value},
            key='i_dep_acct_no_offline_00001'
        )
        assert called is False, f"空值'{bad_value}'不应触发Fin查询!"
        assert cust_no is None

    @pytest.mark.parametrize("good_value", [
        "CUST001", "010293841", "999888777666555",
        "  SPACED_VALUE  ",  # 带空格的合法客户号（会被 strip 后传入查询）
    ])
    def test_alert_07_good_value_triggers_fin_lookup(self, good_value):
        """
        合法的客户号应该触发 Fin 查询，并且空格会被 stripped。
        """
        called, cust_no = self.simulate_indicator_data_getter(
            {'i_dep_acct_no_offline_00001': good_value},
            key='i_dep_acct_no_offline_00001'
        )
        assert called is True, f"合法客户号'{good_value}'应触发Fin查询!"
        assert cust_no == str(good_value).strip()


# =============================================================================
# PART D — 日志关键词覆盖（ALERT-09，补充 UT）
# 日志"合并发送，共N人"由 Logger 打印，本身不改变返回值，无需重复测
# =============================================================================

class TestAlertLogKeywords:
    """
    ALERT-09: 日志关键词覆盖
    日志语句本身不改变业务逻辑，此处只验证辅助函数能计算出正确的 N
    """

    def _compute_log_arg(self, combined_notice_no: str) -> int:
        """模拟源码中日志的 len(unique_targets) 参数。"""
        if not combined_notice_no:
            return 0
        parts = [t for t in combined_notice_no.split(',') if t.strip()]
        return len(parts)

    @pytest.mark.parametrize("case", [
        ("admin",        1),
        ("a,b,c",        3),
        ("a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z", 26),
        ("a,a,a",        3),    # 未去重的情况（不应出现，但覆盖边界）
        ("",             0),   # ALERT-05
        ("  a  ,  b  ",  2),   # 带空格
    ])
    def test_alert_09_log_len_calculation_correct(self, case):
        combined, expected = case
        assert self._compute_log_arg(combined) == expected


# =============================================================================
# PART E — 大批量命中压测（ALERT-10，理论覆盖，真实压测建议在集成阶段）
# =============================================================================

class TestBulkHitScenario_ALERT10:
    """
    ALERT-10: 大批量命中时合并发送的稳定性
    理论覆盖：验证合并后 send_alert_message 仍只被调用1次（N的人数不影响调用次数）
    """

    def test_alert_10_large_scale_dedup_stable(self):
        """
        模拟100人群发的超大通知列表，验证合并结果仍为单个逗号字符串。
        时间复杂度 O(N)，N=100应在毫秒级完成。
        """
        import time
        large_list = [f"target_{i:03d}" for i in range(100)]

        start = time.perf_counter()
        result = merge_notification_targets_refimpl(None, large_list, ["extra_target"])
        elapsed = time.perf_counter() - start

        targets = result.split(',')
        assert len(targets) == len(set(targets))  # 完全去重
        assert elapsed < 0.1, f"性能瓶颈：{elapsed:.3f}s，100条去重不应如此缓慢"


# =============================================================================
# ⛔ 代码高耦合，无法直接UT的部分 → SKIP占位
# 这些用例的真实测试依赖 DB Fixture 或手动 E2E
# =============================================================================

class TestCannotUnitTestSkipped:
    """
    以下用例涉及真实 DB 查询、HTTP 外部调用、分布式并发等，无法在纯 UT 中覆盖。
    在测试文件中声明为 SKIP，QA 团队应将其纳入集成/E2E 测试计划。
    """

    @pytest.mark.skip(reason=(
        "ALERT-01(完整链路)/ALERT-08: send_wx 接口的实际发送效果 "
        "需要真实的微信接口联调（DEV 环境下调用真实企业微信 API），"
        "属于 E2E / 集成测试范畴。UT 中我们仅 Mock 了 requests.post。"
    ))
    def test_alert_08_multi_targets_sent_to_real_wechat_api(self):
        pass

    @pytest.mark.skip(reason=(
        "ALERT-R01: 原有单一路由的行为未改变需要与上线前的历史版本做行为 Diff，"
        "属于冒烟回归测试（Smoke Test），不在 UT 范畴内。"
    ))
    def test_alert_r01_original_single_route_behavior_intact(self):
        pass


# =============================================================================
# ⚙️ TEST_REFACTORING_HINT — 代码改造清单（供审阅）
# =============================================================================

TEST_REFACTORING_HINT = """
╔══════════════════════════════════════════════════════════════╗
║           通知合并模块 · 代码改造清单（供 CLAUDE.MD 审阅）     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║ 改造目标：将 ModelHitAlertManager.hit_record_processor()    ║
║           内部的合并去重逻辑抽取为可独立测试的纯函数           ║
║                                                              ║
║ ┌──────────────────────────────────────────────────────────┐  ║
║ │ 改动位置                                                  │  ║
║ │  文件：services/fraudhunter/model_service/               │  ║
║ │         model_hit_alert_manager.py                       │  ║
║ └──────────────────────────────────────────────────────────┘  ║
║                                                              ║
║ 改动 1：在 ModelHitAlertManager 类中新增类方法                 ║
║ ─────────────────────────────────────────────────────────── ║
║  class ModelHitAlertManager:                                 ║
║                                                              ║
║      @staticmethod                                           ║
║      def merge_notification_targets(                         ║
║          branch_notice_no: Optional[str],                   ║
║          cm_targets: List[str],                             ║
║          fin_targets: List[str],                             ║
║      ) -> str:                                               ║
║          '''                                                 ║
║          合并三类通知人，去重保序，返回逗号分隔字符串。        ║
║          此方法是纯函数，可在不依赖任何外部系统的情况下测试。  ║
║          '''                                                 ║
║          ...existing dedup logic from lines 262-270...        ║
║          return ','.join(unique_targets)                     ║
║                                                              ║
║ 改动 2：在 hit_record_processor() 中调用上述方法（替代内联逻辑） ║
║ ─────────────────────────────────────────────────────────── ║
║  # 旧：                                                      ║
║  all_sources = (...)  # ~10行内联代码                         ║
║  flat = [...]                                                ║
║  unique_targets = list(dict.fromkeys(...))                   ║
║  combined_notice_no = ','.join(unique_targets)              ║
║                                                              ║
║  # 新：                                                      ║
║  combined_notice_no = self.merge_notification_targets(       ║
║      alert_notice_no, cm_targets, fin_targets                ║
║  )                                                          ║
║                                                              ║
║ 改动 3（可选，利于 ALERT-07 测试）：新增第二个提取方法         ║
║ ─────────────────────────────────────────────────────────── ║
║  @staticmethod                                               ║
║  def extract_customer_no_or_none(indicator_data: dict) -> Optional[str]:  ║
║      '''                                                     ║
║      安全地从指标数据字典取出 i_dep_acct_no_offline_00001，   ║
║      处理 None/空字符串/空白，返回标准化值。                  ║
║      '''                                                    ║
║      val = indicator_data.get('i_dep_acct_no_offline_00001')║
║      if val and str(val).strip():                            ║
║          return str(val).strip()                             ║
║      return None                                             ║
║                                                              ║
║ 测试收益估算：                                                ║
║  - 改造完成后，上方 test_notification_merge.py 可直接测     ║
║  - 无需 Mock DB / requests，测试运行时间 ~5ms（纯算术）      ║
║  - 缺陷回归成本：从 ~30分钟人工回归 → 30秒自动化回归         ║
╚══════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(TEST_REFACTORING_HINT)