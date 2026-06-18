# 回测支持客户(cust_no)实时指标 — 设计文档

- **日期**: 2026-06-18
- **范围**: FraudHunter 模型历史回测（`backend/services/fraudhunter/model_service/model_executor.py`）
- **状态**: 设计已批准，待实现

---

## 背景与问题

FraudHunter 的实时模型匹配**生产链路**（`realtime_indicator_job.py`）已完整支持客户号（cust_no）维度实时指标：建客户实时宽表 → 4 表 JOIN（含 `cust_realtime_indicator`）→ 别名映射取值 → 告警生成，全链路闭环。

但**模型历史回测链路**（`model_executor.py`）不支持客户实时指标：

- `_generate_backtest_sql`（`model_executor.py:188-266`）的 FROM/JOIN 只关联三张表：`dep_acct_realtime_indicator`、`dep_acct_offline_indicator`、`cust_offline_indicator`，**没有 `cust_realtime_indicator` 别名**。
- 规则引擎的 `build_indicator_alias_mapping`（`rule_engine.py:1241-1242`）在回测场景下同样会把客户实时指标映射到别名 `cust_realtime_indicator`。
- **后果**: 任何引用了客户实时指标的模型，走历史回测时，生成的 SQL 会引用不存在的表别名 `cust_realtime_indicator.{code}` → SQL 执行报错，当天回测失败。

值得注意的是，回测的 SELECT（`model_executor.py:232-238`）和别名映射其实已经"准备好"使用客户实时指标——**唯一缺失的是那个 LEFT JOIN**。

### 关键现状（影响设计）

回测里的"实时"是近似概念，**不触碰真·实时宽表**：

- 回测"实时指标" = **当天（current_date）的离线宽表快照**（`_get_latest_version_snapshot(db, dep_acct_wide_table_name, current_date)`）
- 回测"离线指标" = **前一天（previous_date）的离线宽表快照**
- 真·实时宽表快照登记在带 `_realtime` 后缀的 wide_table_name 下、version_hash=NULL（`realtime_indicator_job.py:323`），回测的查询键（不带后缀 + 要求 version_hash）对不上，所以回测从不查真·实时宽表。
- 存款（dep_acct）实时指标回测能跑通，正是靠"当天离线宽表冒充当天实时"。

---

## 目标

让回测支持引用客户（cust_no）实时指标的模型：能正常生成 SQL、取到客户实时指标值、产出命中记录，与存款实时指标在回测里的处理口径一致。

## 取数决策（已确认）

**客户实时指标在回测里取「当天客户宽表（`cust_wide_table`, current_date）」快照的值**，与存款实时指标的回测处理完全平行（回测本就用当天离线宽表近似实时）。

不引入真·实时宽表（`*_realtime`）：避免回测逐历史日时多数日期无快照导致数据稀疏，以及 dep/cust 两边实时口径分裂。

---

## 设计

### 改动范围

- **仅改** `backend/services/fraudhunter/model_service/model_executor.py`。
- **仅覆盖 cust_no**。loan_acct_no 不在范围（其生产实时链路本就不计算、无实时宽表可取）。
- **不改**：`rule_engine.py`（别名映射已就绪）、`realtime_indicator_job.py`（生产链路已支持）、回测 SELECT 逻辑（已就绪）、现有 cust_offline/dep_acct 的 JOIN 与 skip 逻辑（避免回归）。

### 改动 1：`execute_backtest` 新增取当天客户宽表快照

位置：`model_executor.py:377-379`（取 `cust_offline_result`）旁。

```python
cust_realtime_result = self._get_latest_version_snapshot(
    db, cust_wide_table_name, current_date   # 当天，与 dep_acct_realtime 同口径
)
cust_realtime_table = cust_realtime_result.pg_table_name
```

复用现有 `_get_latest_version_snapshot`，查 `cust_wide_table` 在 current_date 的 ready 快照。

### 改动 2：`_generate_backtest_sql` 新增 cust_realtime JOIN

给方法新增可选参数 `cust_realtime_table_name: Optional[str] = None`。当其非空时，在现有 JOIN 链（`model_executor.py:258-261`）后追加，关联键与回测现有 `cust_offline` JOIN 完全平行：

```sql
LEFT JOIN {cust_realtime_table_name} AS cust_realtime_indicator
  ON dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id
```

SELECT、WHERE 不动——别名映射已就绪，JOIN 一补即闭环。

调用处（`model_executor.py:419-426`）传入 `cust_realtime_table`。

### 改动 3：降级 —— 条件依赖，避免回归

仅当模型**实际引用**客户实时指标时，才依赖当天客户宽表：

- 在 `execute_backtest` 里复用 `build_indicator_alias_mapping`（基于 `model.rule_config`）判断 `'cust_realtime_indicator' in mapping.values()`。
- **引用了** + 当天客户宽表存在 → 传入、JOIN。
- **引用了** + 当天客户宽表缺失 → skip 当天，记录 warning「当天客户宽表不存在，无法回测客户实时指标」。
- **没引用** → 不需要当天客户宽表，正常跑（即使缺失也不影响、不额外 skip）。

**效果**：纯存款模型零回归；只有真正用到客户实时指标的模型才多一个"当天客户宽表"依赖。现有 cust_offline/dep_acct 的 skip（`model_executor.py:407-416`）不动。

---

## 前提与固有近似（选项 A）

客户实时指标列在当天客户宽表里的值，由**离线同步**填充（跑指标的离线 `logic_content`）。若客户实时指标只配了 `realtime_logic_content`、没配离线 SQL，客户宽表里该列可能为 NULL → 回测里该客户实时指标取不到值。

这是"当天离线宽表近似实时"这一既有口径的固有限制（存款实时指标回测同理），本次不改。

---

## 测试计划

- **单测 `_generate_backtest_sql`**：
  - 传 `cust_realtime_table_name` → SQL 含 `cust_realtime_indicator` JOIN，关联键 `dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id` 正确。
  - 不传 → SQL 不含该 JOIN。
- **单测 `execute_backtest` 降级**：
  - 模型引用客户实时指标 + 当天客户宽表存在 → 正常 JOIN 取值。
  - 模型引用客户实时指标 + 当天客户宽表缺失 → 当天 skip + warning。
  - 模型未引用客户实时指标 → 不依赖当天客户宽表、不额外 skip。
- 参考现有 `tests/backend/modules/` 结构放置。

---

## 不在范围（YAGNI）

- loan_acct_no 实时指标回测支持。
- 将现有 cust_offline / dep_acct 的硬 skip 改为条件依赖。
- 引入真·实时宽表（`*_realtime`）作为回测取数源。
