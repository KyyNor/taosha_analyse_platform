# 受害人预警

## 流程

```
实时指标任务 generate_realtime_wide_table_job
  步骤3 记录命中（告警/管控）
  步骤4 受害人预警 process_victim_alerts
    ├─ 筛选本次执行的告警管控记录：命中模型名称含"受害人" + alert_status=sent + control_status≠executed
    ├─ 同一账号当天已有记录 → 跳过；否则写入 fraudhunter_victim_alert_record（状态 new）并提交
    └─ 逐条 POST 触发 DS 任务（参数：告警ID）；触发失败 → 状态 error，message 记录原因
DS 任务 victim_alert_send_job --alert-id <告警ID>
    ├─ 读取记录；已是 sent → 跳过
    └─ POST 全部字段到下游服务：成功 → sent；失败 → error，message 记录错误内容
```

淘沙机器与下游服务不直接联通，由 DS 中转。步骤4 的任何异常只记日志，不影响实时任务和执行记录状态。

## 表 `fraudhunter_victim_alert_record`

| 字段 | 说明 |
|---|---|
| alert_id | 告警ID，`md5(account_id + 命中模型ID逗号拼接 + 告警时间 'YYYY-MM-DD HH:MM:SS')`，唯一 |
| account_id | 账号（告警管控记录 account_id） |
| hit_model_ids / hit_model_names | 命中模型ID / 名称（JSON 数组，取告警管控记录的全部命中模型） |
| hit_time | 命中时间（告警管控记录 alert_time，精确到秒） |
| record_date | 记录日期；`(account_id, record_date)` 唯一 |
| status | `new` 新建 / `sent` 已发送 / `error` 异常 |
| message | 异常时的错误内容 |

淘沙后端启动时自动建表（`create_all`）。DS 任务不建表，需淘沙后端先升级启动。

例：账号 `6222001`、模型 `[3, 12]`、告警时间 `2026-10-11 09:30:15` → `md5("62220013,122026-10-11 09:30:15")`。

## 配置（淘沙后端与 DS 同一份结构）

```yaml
fraudhunter:
  victim_alert:
    enabled: false                 # 淘沙后端开启后步骤4才生效；DS 任务不看此开关
    model_name_keyword: "受害人"
    trigger_api_url: ""            # 淘沙后端用：DS 任务启动接口
    send_api_url: ""               # DS 用：下游服务接口
    timeout_seconds: 10
```

## 接口契约（占位，按实际修改 `victim_alert_service.py` 中 `_post_trigger` / `_post_send` / `_is_send_success`）

**触发 DS 任务**（淘沙后端 → DS）

```
POST {trigger_api_url}
Content-Type: application/json

{"alert_id": "9f3c...（32位）"}
```

HTTP 2xx 视为成功。DS 侧把 `alert_id` 作为参数传给任务命令：

```bash
python -m services.scheduler.jobs.victim_alert_send_job --alert-id ${alert_id}
```

**发送下游服务**（DS → 下游）

```
POST {send_api_url}
Content-Type: application/json

{
  "alert_id": "9f3c...",
  "account_id": "6222001",
  "hit_model_ids": [3, 12],
  "hit_model_names": ["受害人保护模型", "涉诈模型"],
  "hit_time": "2026-10-11 09:30:15",
  "record_date": "2026-10-11",
  "status": "new",
  "message": null
}
```

响应 HTTP 2xx 且 JSON `{"code": "00000", ...}` 视为成功，其余（非 2xx、非 JSON、code 不符、超时/异常）均置 `error`。

## DS 任务退出码

| 退出码 | 含义 |
|---|---|
| 0 | 发送成功，或记录已是 sent（重跑幂等） |
| 1 | 发送失败，记录已置 error（DS 重试会再次发送） |
| 2 | 告警ID不存在 |

## 排查

- 日志关键字 `[受害人预警]`；
- 状态长期为 `new`：DS 已被触发但任务未执行或未结束，查 DS 实例；
- `error` 且 message 以"触发DS任务失败"开头：淘沙后端到 DS 接口不通或返回非 2xx。
