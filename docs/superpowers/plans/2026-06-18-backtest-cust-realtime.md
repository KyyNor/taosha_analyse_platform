# 回测支持客户(cust_no)实时指标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让模型历史回测(`model_executor.py`)支持引用客户(cust_no)实时指标的模型，补上缺失的 `cust_realtime_indicator` LEFT JOIN，使回测能正常取值、产出命中记录。

**Architecture:** 仅改 `model_executor.py`。新增两个纯静态方法(`_build_cust_realtime_join_clause` / `_uses_cust_realtime_indicator`)承载可独立验证的逻辑；`_generate_backtest_sql` 新增可选参数拼接客户实时 JOIN；`execute_backtest` 取当天客户宽表快照、按"模型是否引用客户实时指标"做条件降级。SELECT 与别名映射(`rule_engine.build_indicator_alias_mapping`)已就绪，不动。

**Tech Stack:** Python 3.11 / SQLAlchemy 2.0 / FastAPI / pytest(本地复本单测)。

**关键约束(影响测试方式):** 本环境 `backend/config/config.yaml` 不存在(gitignore)、`pytest` 未安装，且 `import services.*` 会触发 `services/__init__.py` 热切导入链(config 读文件 → logger 初始化 → `DuckDBService(QueryEngineService, LoggerMixin)` metaclass 冲突)，无法直接 import 测生产代码。因此沿用项目既有约定(见 `tests/backend/modules/realtime_indicator/test_compute_half_hour_slot.py`、`tests/backend/modules/alert_notification/test_notification_merge.py`)：**纯逻辑用本地复本单测**，端到端 SQL/回测验证走手动清单。仅装 `pytest` 即可跑复本测试(复本不 import services)。

**提交约定:** 用户已确认不开新分支，所有 commit 直接在当前分支(`master`)进行。

---

## 文件结构

| 文件 | 责任 | 操作 |
|---|---|---|
| `backend/services/fraudhunter/model_service/model_executor.py` | 回测执行器：新增两个纯静态方法 + `_generate_backtest_sql` 接入 JOIN + `execute_backtest` 取数与降级 | Modify |
| `tests/backend/modules/model_executor/__init__.py` | 测试包标识(空) | Create |
| `tests/backend/modules/model_executor/test_backtest_cust_realtime.py` | 两个纯函数的本地复本单测(参数化) | Create |

---

## Task 1: 装pytest + 新增两个纯静态方法 + 本地复本单测

**Files:**
- Modify: `pyproject.toml`(dev 依赖)、`uv.lock`(自动)
- Create: `tests/backend/modules/model_executor/__init__.py`
- Create: `tests/backend/modules/model_executor/test_backtest_cust_realtime.py`
- Modify: `backend/services/fraudhunter/model_service/model_executor.py`(在 `ModelExecutor` 类内、`get_wide_table_name` 之后新增两个 `@staticmethod`)

- [ ] **Step 1: 安装 pytest 作为 dev 依赖**

Run:
```bash
uv add --dev pytest
```
Expected: `pyproject.toml` 出现 `[tool.uv] dev-dependencies` 段含 `pytest`，`uv.lock` 更新。

- [ ] **Step 2: 创建测试包标识**

Create `tests/backend/modules/model_executor/__init__.py`，内容为空文件(仅用于 Python 包识别)。

- [ ] **Step 3: 写本地复本单测(定义期望行为契约)**

Create `tests/backend/modules/model_executor/test_backtest_cust_realtime.py`:

```python
"""
tests/backend/modules/model_executor/test_backtest_cust_realtime.py
==================================================================
单元测试：回测支持客户(cust_no)实时指标 —— 两个纯函数的行为契约

被测逻辑位置：
    backend/services/fraudhunter/model_service/model_executor.py
    ModelExecutor._build_cust_realtime_join_clause
    ModelExecutor._uses_cust_realtime_indicator

测试策略：
    ✅ 纯函数，无外部依赖，参数→返回值，不涉及 IO/DB/API
    ✅ 本地复本镜像(与生产代码逐行对齐)

为何用本地复本而非标准 import：
    一旦 import services.* (含 model_executor)，便会触发
    backend/services/__init__.py 的热切导入链 → 加载
    query_engine.duckdb_service → utils.config 读 config.yaml
    (本环境 gitignore 不存在) + utils.logger 模块级初始化 +
    DuckDBService(QueryEngineService, LoggerMixin) metaclass 冲突，
    导致无法 import。此问题会在后端部署完整环境(config.yaml 就绪)后
    自然消解，届时可将下方两个函数替换为：
        from services.fraudhunter.model_service.model_executor import ModelExecutor
    并改用 ModelExecutor._build_cust_realtime_join_clause / _uses_cust_realtime_indicator。
    维护者每次改动生产代码这两处纯函数时，须同步更新本复本，保持逐行一致。
"""
from typing import Dict, List, Optional

import pytest


# ── 本地复本(须与生产代码 ModelExecutor 的两个 @staticmethod 逐行一致) ──
def _build_cust_realtime_join_clause(cust_realtime_table_name: Optional[str]) -> List[str]:
    """构建客户实时宽表 LEFT JOIN 的 SQL 行(与回测现有 cust_offline JOIN 同风格、同关联键)。
    关联键：存款实时宽表的客户号外键列 i_dep_acct_no_offline_00001 = 客户实时宽表 target_id。
    无表名时返回空列表(不 JOIN)。"""
    if not cust_realtime_table_name:
        return []
    return [
        "LEFT JOIN",
        f"    {cust_realtime_table_name} as cust_realtime_indicator",
        "ON",
        "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
    ]


def _uses_cust_realtime_indicator(alias_mapping: Optional[Dict[str, str]]) -> bool:
    """判断规则是否引用了客户实时指标(别名映射 values 含 'cust_realtime_indicator')。"""
    return bool(alias_mapping) and "cust_realtime_indicator" in alias_mapping.values()


class TestBuildCustRealtimeJoinClause:
    @pytest.mark.parametrize("table_name", [None, "", "   "])
    def test_no_table_returns_empty(self, table_name):
        assert _build_cust_realtime_join_clause(table_name) == []

    def test_with_table_emits_aligned_join(self):
        lines = _build_cust_realtime_join_clause("cust_wide_table_abc12345_20260618")
        assert lines == [
            "LEFT JOIN",
            "    cust_wide_table_abc12345_20260618 as cust_realtime_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
        ]

    def test_clause_uses_same_join_key_as_cust_offline(self):
        """关联键须与回测现有 cust_offline JOIN 一致(都以 dep_acct_realtime 的客户号外键关联)。"""
        lines = _build_cust_realtime_join_clause("t")
        joined = "\n".join(lines)
        assert "dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id" in joined


class TestUsesCustRealtimeIndicator:
    def test_true_when_mapping_contains_cust_realtime(self):
        assert _uses_cust_realtime_indicator({"i_cust_no_realtime_00001": "cust_realtime_indicator"}) is True

    def test_false_when_only_other_aliases(self):
        mapping = {
            "i_dep_acct_no_realtime_00001": "dep_acct_realtime_indicator",
            "i_cust_no_offline_00001": "cust_offline_indicator",
        }
        assert _uses_cust_realtime_indicator(mapping) is False

    def test_false_when_none(self):
        assert _uses_cust_realtime_indicator(None) is False

    def test_false_when_empty(self):
        assert _uses_cust_realtime_indicator({}) is False
```

- [ ] **Step 4: 跑测试，确认复本用例通过(验证期望行为契约正确)**

Run:
```bash
uv run pytest tests/backend/modules/model_executor/test_backtest_cust_realtime.py -v
```
Expected: 全部用例 PASS(约 9 条)。若 FAIL，修正复本使其符合期望行为(此时复本即契约，先确保契约自洽)。

- [ ] **Step 5: 在 model_executor.py 实现两个纯静态方法(与复本逐行一致)**

Modify `backend/services/fraudhunter/model_service/model_executor.py`，在 `get_wide_table_name` 方法之后(约第 110 行 `return OBJECT_TYPE_TO_WIDE_TABLE.get(...)` 之后)、`_get_latest_version_snapshot` 之前，插入：

```python
    @staticmethod
    def _build_cust_realtime_join_clause(cust_realtime_table_name: Optional[str]) -> List[str]:
        """构建客户实时宽表 LEFT JOIN 的 SQL 行（与回测现有 cust_offline JOIN 同风格、同关联键）。

        关联键：存款实时宽表的客户号外键列 i_dep_acct_no_offline_00001
        = 客户实时宽表 target_id（与 cust_offline JOIN 完全平行）。

        Args:
            cust_realtime_table_name: 当天客户宽表 PG 表名；为空则不生成 JOIN。

        Returns:
            JOIN 子句的 SQL 行列表；无表名时返回空列表（不 JOIN）。
        """
        if not cust_realtime_table_name:
            return []
        return [
            "LEFT JOIN",
            f"    {cust_realtime_table_name} as cust_realtime_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
        ]

    @staticmethod
    def _uses_cust_realtime_indicator(alias_mapping: Optional[Dict[str, str]]) -> bool:
        """判断规则是否引用了客户实时指标（别名映射 values 含 cust_realtime_indicator）。"""
        return bool(alias_mapping) and 'cust_realtime_indicator' in alias_mapping.values()
```

> 注：`Optional`/`Dict`/`List` 已在文件顶部 `from typing import Dict, Any, List, Optional` 导入(第 15 行)，无需新增 import。

- [ ] **Step 6: 人工对照，确认实现与复本逐行一致**

因 import services 链在本环境不可行，无法直接跑生产代码测试。打开 `model_executor.py` 的两个新方法与 `test_backtest_cust_realtime.py` 顶部两个复本函数，**逐行核对完全一致**(含关联键字符串、空值分支)。这一步是本地复本模式下的强制验证。

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/backend/modules/model_executor/ backend/services/fraudhunter/model_service/model_executor.py
git commit -m "feat(model_executor): 新增回测客户实时指标的纯函数与本地复本单测"
```

---

## Task 2: `_generate_backtest_sql` 接入客户实时 JOIN

**Files:**
- Modify: `backend/services/fraudhunter/model_service/model_executor.py:188-266`(`_generate_backtest_sql` 签名 + SQL 拼接) 与 `:419-426`(调用处)

- [ ] **Step 1: 给 `_generate_backtest_sql` 增加可选参数**

Modify `_generate_backtest_sql` 签名(第 188-196 行)，在 `cust_offline_table_name: str,` 之后、`etl_date: date` 之前插入 `cust_realtime_table_name: Optional[str] = None,`，并在 docstring 的 SQL 结构说明里补一行客户实时表说明。

签名改后（把 `cust_realtime_table_name` 放在 `etl_date` **之后**并带默认值，`etl_date` 保持原必填无默认——符合 Python「非默认参数不能跟在默认参数后」的规则）：

```python
    def _generate_backtest_sql(
        self,
        db: Session,
        model: FraudHunterModelDefinition,
        dep_acct_realtime_table_name: str,
        dep_acct_offline_table_name: str,
        cust_offline_table_name: str,
        etl_date: date,
        cust_realtime_table_name: Optional[str] = None,
    ) -> str:
```

> 注：`cust_realtime_table_name` 置于 `etl_date` 之后（带默认值 `None`），`etl_date` 语义不变；调用处(Task 3 Step 4)按位置 `..., current_date, cust_realtime_table if uses_cust_realtime else None` 传入。docstring 的「SQL结构」段追加：`- 客户实时指标使用当天的客户宽表（cust_realtime_indicator，可选）`。

- [ ] **Step 2: 重构 SQL 的 FROM/JOIN 拼接，条件插入客户实时 JOIN**

将第 245-265 行的整段 SQL 模板替换为下方版本(把 FROM/JOIN 抽成 `from_join_lines`，并 extend 客户实时 JOIN 行)：

```python
        # 构建 FROM/JOIN 子句（含可选的客户实时 JOIN）
        from_join_lines = [
            "FROM",
            f"    {dep_acct_realtime_table_name} as dep_acct_realtime_indicator",
            "LEFT JOIN",
            f"    {dep_acct_offline_table_name} as dep_acct_offline_indicator",
            "ON",
            "    dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id",
            "LEFT JOIN",
            f"    {cust_offline_table_name} as cust_offline_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id",
        ]
        from_join_lines.extend(self._build_cust_realtime_join_clause(cust_realtime_table_name))
        from_join_clause = "\n".join(from_join_lines)

        # 生成完整SQL - 使用PG表
        sql = f"""-- 模型历史回测SQL
-- 模型: {model.model_code} ({model.model_name})
-- 执行日期: {etl_date.strftime('%Y-%m-%d')}

SELECT
    {select_clause}
{from_join_clause}
WHERE
    {where_clause}
LIMIT 10000
"""
        return sql
```

> 关键：`from_join_clause` 替换了原模板里写死的 `FROM ... LEFT JOIN ... LEFT JOIN ...` 三段；当 `cust_realtime_table_name` 为空时 `_build_cust_realtime_join_clause` 返回 `[]`，SQL 与改动前完全等价(纯存款模型零回归)。SELECT/WHERE 逻辑不变(第 228-243 行)。

- [ ] **Step 3: 人工检查 SQL 结构(本地无法执行，靠静态审查)**

在脑中/编辑器里对照：不传 `cust_realtime_table_name` 时，`from_join_lines` 与原模板的 FROM/JOIN 文本逐行一致；传入时末尾多出 cust_realtime 的 LEFT JOIN 块，缩进与 cust_offline 块对齐。

- [ ] **Step 4: Commit**

```bash
git add backend/services/fraudhunter/model_service/model_executor.py
git commit -m "feat(model_executor): _generate_backtest_sql 支持可选的客户实时宽表 JOIN"
```

---

## Task 3: `execute_backtest` 取当天客户宽表 + 条件降级 + 传参

**Files:**
- Modify: `backend/services/fraudhunter/model_service/model_executor.py`(取数 ~377-379、表名提取 ~392-394、降级判断接在 skip 检查 ~416 之后、调用处 ~419-426)

- [ ] **Step 1: 新增取当天客户宽表快照**

在第 377-379 行(`cust_offline_result = ... previous_date`)之后插入：

```python
                # 获取当天的最新版本客户宽表快照（用于客户实时指标，与 dep_acct_realtime 同口径）
                cust_realtime_result = self._get_latest_version_snapshot(
                    db, cust_wide_table_name, current_date
                )
```

- [ ] **Step 2: 提取客户实时表名**

在第 394 行(`cust_offline_table = cust_offline_result.pg_table_name`)之后插入：

```python
                cust_realtime_table = cust_realtime_result.pg_table_name
```

- [ ] **Step 3: 在现有 skip 检查之后、生成 SQL 之前，加入客户实时降级判断**

现有 skip 检查止于第 416 行(`continue`)。在其后、第 418 行(`# 生成SQL`)之前插入：

```python
                # 判断模型是否引用客户实时指标；引用且当天客户宽表缺失则跳过当天
                rule_config_for_check = RuleConfig(**model.rule_config)
                check_engine = RuleEngine(db=db)
                alias_mapping_for_check = check_engine.build_indicator_alias_mapping(
                    rule_config_for_check, use_alias=True
                )
                uses_cust_realtime = self._uses_cust_realtime_indicator(alias_mapping_for_check)
                if uses_cust_realtime and not cust_realtime_table:
                    warning_msg = f"日期 {current_date} 的当天客户宽表不存在，无法回测客户实时指标，跳过"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '当天客户宽表不存在（客户实时指标）'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue
```

> 语义：仅当模型**实际引用**客户实时指标、且当天客户宽表快照缺失时才 skip 当天；模型未引用客户实时指标时不依赖当天客户宽表(纯存款模型零回归)。`RuleConfig`/`RuleEngine` 已在文件顶部导入(第 28-29 行)。

- [ ] **Step 4: 修改 `_generate_backtest_sql` 调用，条件传入客户实时表名**

将第 419-426 行的调用替换为：

```python
                # 生成SQL（仅当模型引用客户实时指标时才传入当天客户宽表，避免无谓 JOIN）
                sql = self._generate_backtest_sql(
                    db,
                    model,
                    dep_acct_realtime_table,
                    dep_acct_offline_table,
                    cust_offline_table,
                    current_date,
                    cust_realtime_table if uses_cust_realtime else None,
                )
```

> 关键：`cust_realtime_table if uses_cust_realtime else None` —— 模型未引用客户实时指标时传 `None`，不 JOIN 客户实时表；引用且表存在时传入并 JOIN。`current_date` 仍作为位置参数对应 `etl_date`。

- [ ] **Step 5: 全量复跑复本单测，确认未破坏既有契约**

Run:
```bash
uv run pytest tests/backend/modules/model_executor/test_backtest_cust_realtime.py -v
```
Expected: 全部 PASS(本任务未改纯函数，应仍全绿；作为回归保险)。

- [ ] **Step 6: Commit**

```bash
git add backend/services/fraudhunter/model_service/model_executor.py
git commit -m "feat(model_executor): execute_backtest 取当天客户宽表并对客户实时指标条件降级"
```

---

## Task 4: 端到端手动验证清单(写入计划附录并提示执行)

> 因本环境无 `config.yaml`、无法 import services 链，端到端验证须在具备完整后端配置的环境(用户本机/CI)执行。以下为执行该实现后须人工核验的场景。

**Files:** 无代码改动(仅验证)。

- [ ] **Step 1: 准备环境**

确保 `backend/config/config.yaml` 就绪、后端可正常启动；准备一个 `status='online'`、`indicator_type='realtime'`、`object_type='cust_no'` 的客户实时指标，并将其纳入 `cust_wide_table` 当前版本；准备一个引用该客户实时指标的 `online` 模型。

- [ ] **Step 2: 场景A —— 客户实时指标回测取值正确**

对该模型发起历史回测(覆盖当天)。检查生成的 SQL(`dry_run` 执行记录的 `generated_sqls` 或日志)：
- [ ] SQL 含 `LEFT JOIN {当天客户宽表} as cust_realtime_indicator`
- [ ] 关联键为 `dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id`
- [ ] SELECT 含 `[实时]{客户实时指标名}` 列
- [ ] 回测执行不报 `missing FROM-clause entry for table cust_realtime_indicator`

- [ ] **Step 3: 场景B —— 当天客户宽表缺失则 skip**

构造当天 `cust_wide_table` 无 ready 快照的情况(或回测到客户宽表尚未就绪的日期)，对引用客户实时指标的模型回测：
- [ ] 该日 `status='skipped'`，`message` 含「当天客户宽表不存在」
- [ ] `results.warnings` 含对应告警
- [ ] SQL 不被执行(不报错)

- [ ] **Step 4: 场景C —— 纯存款模型零回归**

对一个**不引用**任何客户实时指标的模型回测：
- [ ] 生成的 SQL **不含** `cust_realtime_indicator` 相关 JOIN
- [ ] 与改动前行为一致(不因当天客户宽表状态而额外 skip)

- [ ] **Step 5: Commit 验证记录(可选)**

如需留存，可将上述场景的 SQL 片段/截图整理到 `docs/superpowers/specs/2026-06-18-backtest-cust-realtime-design.md` 末尾的「验证记录」小节并 commit；否则跳过。

---

## Self-Review(计划自检)

**1. Spec 覆盖:**
- 改动1(execute_backtest 取当天客户宽表) → Task 3 Step 1-2 ✓
- 改动2(_generate_backtest_sql 新增 JOIN) → Task 2 Step 1-2 ✓
- 改动3(条件降级) → Task 3 Step 3-4 ✓
- 取数决策(当天客户宽表) → Task 3 Step 1(`current_date`) ✓
- 测试计划(纯函数本地复本 + 端到端清单) → Task 1 + Task 4 ✓
- 不改 rule_engine / 实时链路 / SELECT / cust_offline 逻辑 → 计划全程未触及 ✓
- 范围仅 cust_no → 无 loan_acct_no 改动 ✓

**2. 占位扫描:** 无 TBD/TODO；每步含完整代码或精确命令。✓

**3. 类型/命名一致性:**
- `_build_cust_realtime_join_clause` / `_uses_cust_realtime_indicator` 在 Task 1(实现+复本)、Task 2、Task 3 引用名一致 ✓
- `cust_realtime_table_name`(SQL 参数) 与 `cust_realtime_table`(execute_backtest 变量) 区分明确、各自一致 ✓
- `uses_cust_realtime` 在 Task 3 Step 3 定义、Step 4 引用一致 ✓

**4. 已知限制(已写入 spec，本计划不改):** 客户实时指标列在当天客户宽表的值由离线同步填充；若该实时指标未配离线 `logic_content`，列可能为 NULL(Task 4 场景A 的人工核验可暴露此情形)。
