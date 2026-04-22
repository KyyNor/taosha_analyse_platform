"""
backend/domain/wide_table/version_delta.py
==========================================

Domain 层：宽表版本之间指标的差异计算

职责
----
接收当前版本和新版本的 metadata 字典，计算以下三类列差异：
- static_cols  ：版本号未变，可直接 COPY（速度最快，利用 PG INSERT...SELECT）
- changed_cols ：版本号已升，需 Spark PIVOT + UPDATE 重建
- new_cols     ：新版中独有的指标，等同 changed_cols 的待遇

使用约束
--------
本模块为纯领域逻辑，无 IO，无外部依赖，可放心在任意测试中使用。
使用时，调用方负责确保 dict 的 key/value 形态符合接口约定（见下方 docstring）。
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class VersionDelta:
    """两版本之间完整列差异的持有结构。"""
    static_cols: List[str] = field(default_factory=list)
    changed_cols: List[str] = field(default_factory=list)
    new_cols: List[str] = field(default_factory=list)

    @property
    def is_unchanged(self) -> bool:
        """返回 True 时，增量同步应跳过（status: skipped）。"""
        return not (self.changed_cols or self.new_cols)

    @property
    def has_any_change(self) -> bool:
        return bool(self.changed_cols or self.new_cols)

    @property
    def deferred_cols(self) -> List[str]:
        """static 以外的其余列，都需要 PIVOT 重建（changed + new）。"""
        return self.changed_cols + self.new_cols


class WideTableComparator:
    """
    领域逻辑：将 current_metadata 和 target_metadata 转化为 VersionDelta。

    设计原则
    --------
    1. 完全无 IO（不使用 DB、文件、网络、外部服务）
    2. 参数和返回值均为 Plain Old Python Objects（POPO，dataclass）
    3. 确定性强：相同输入在任何时候、任何线程下得到相同结果
    4. 可逆推：given 一个 VersionDelta，我们可以还原出等价的 current 和 target
    """

    @staticmethod
    def diff(
        current_metadata: Dict[int, dict],
        target_metadata: Dict[int, dict],
    ) -> VersionDelta:
        """
        将两版指标的 metadata 字典对比，产出三列分类。

        入参约束
        ---------
        current_metadata: {
            indicator_id(int): {
                "version": int,                          # 必须
                "indicator_code": str,                    # 必须
                ...其他字段不影响分类结果...
            },
            ...
        }
        target_metadata: 同上（通常来自即将上线的版本）

        返回值
        ------
        VersionDelta(static_cols=[], changed_cols=[], new_cols=[])

        分类规则
        --------
        new     — 该 indicator_id 在 target 中存在、在 current 中不存在
        changed — 两版均存在，但 version 值不相同（即发生了版本升级）
        static  — 两版均存在，且 version 值完全一致（可复用，无需重建）

        示例
        -----
        >>> current = {1: {"version": 1, "indicator_code": "A"}}
        >>> target  = {1: {"version": 2, "indicator_code": "A"}}
        >>> delta = WideTableComparator.diff(current, target)
        >>> delta.changed_cols
        ['A']
        >>> delta.is_unchanged
        False

        >>> current, target = {}, {}
        >>> delta = WideTableComparator.diff(current, target)
        >>> delta.is_unchanged
        True
        """
        changed: List[str] = []
        new: List[str] = []
        static: List[str] = []

        all_keys = set(current_metadata.keys()) | set(target_metadata.keys())
        for k in all_keys:
            cur_meta = current_metadata.get(k, {})
            tgt_meta = target_metadata.get(k, {})
            cur_ver = cur_meta.get("version")
            tgt_ver = tgt_meta.get("version")
            code = (tgt_meta or cur_meta).get("indicator_code")

            if k not in current_metadata:
                # target 有但 current 无 → 新增指标
                new.append(code)
            elif cur_ver == tgt_ver:
                # 两版 version 相等 → 静态度，可 COPY
                static.append(code)
            else:
                # version 不同 → 发生变化，需要重建
                changed.append(code)

        return VersionDelta(
            static_cols=static,
            changed_cols=changed,
            new_cols=new,
        )