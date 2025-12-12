# 告警管控记录API文档

## 概述

告警管控记录API提供了完整的告警管控记录管理功能，包括查询、详情查看、数据导出和统计分析。

## API端点

### 1. 获取告警管控记录列表

**GET** `/api/fraudhunter/alert-control-records`

#### 查询参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| page | int | 否 | 1 | 页码，从1开始 |
| page_size | int | 否 | 20 | 每页大小，最大1000 |
| start_date | string | 否 | - | 开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | - | 结束日期 (YYYY-MM-DD) |
| account_id | string | 否 | - | 账号ID（精确匹配） |
| model_id | int | 否 | - | 模型ID（精确匹配） |
| model_name | string | 否 | - | 模型名称（模糊匹配） |
| alert_status | string | 否 | - | 告警状态：not_configured/sent/duplicate |
| control_status | string | 否 | - | 管控状态：not_configured/executed/duplicate |
| search | string | 否 | - | 搜索关键词（账号、模型名称、告警消息） |

#### 响应格式

```json
{
  "records": [
    {
      "id": 1,
      "hit_record_id": 123,
      "account_id": "test_account_001",
      "record_date": "2024-12-12",
      "model_id": 1,
      "model_name": "高风险交易模型",
      "alert_status": "sent",
      "alert_message": "账户 test_account_001 在 2024-12-12 10:30:15，因命中高风险交易模型，触发告警",
      "alert_person": "system",
      "alert_time": "2024-12-12T10:30:20",
      "control_status": "not_configured",
      "control_time": null,
      "control_serial_number": null,
      "created_at": "2024-12-12T10:30:15",
      "updated_at": "2024-12-12T10:30:20"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 2. 获取告警管控记录详情

**GET** `/api/fraudhunter/alert-control-records/{record_id}`

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| record_id | int | 是 | 告警管控记录ID |

#### 响应格式

```json
{
  "record": {
    "id": 1,
    "hit_record_id": 123,
    "account_id": "test_account_001",
    "record_date": "2024-12-12",
    "model_id": 1,
    "model_name": "高风险交易模型",
    "alert_status": "sent",
    "alert_message": "账户 test_account_001 在 2024-12-12 10:30:15，因命中高风险交易模型，触发告警",
    "alert_person": "system",
    "alert_time": "2024-12-12T10:30:20",
    "control_status": "not_configured",
    "control_time": null,
    "control_serial_number": null,
    "created_at": "2024-12-12T10:30:15",
    "updated_at": "2024-12-12T10:30:20"
  },
  "hit_record": {
    "id": 123,
    "account_id": "test_account_001",
    "hit_time": "2024-12-12T10:30:15",
    "hit_model_ids": [1, 2],
    "hit_model_names": ["高风险交易模型", "异常行为模型"],
    "indicator_data": {
      "transaction_amount": 50000,
      "risk_score": 85,
      "device_fingerprint": "abc123"
    },
    "created_at": "2024-12-12T10:30:15",
    "updated_at": "2024-12-12T10:30:15"
  }
}
```

### 3. 导出告警管控记录

**POST** `/api/fraudhunter/alert-control-records/export`

#### 查询参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| format | string | 否 | csv | 导出格式：csv 或 excel |
| start_date | string | 否 | - | 开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | - | 结束日期 (YYYY-MM-DD) |
| account_id | string | 否 | - | 账号ID |
| model_id | int | 否 | - | 模型ID |
| model_name | string | 否 | - | 模型名称 |
| alert_status | string | 否 | - | 告警状态 |
| control_status | string | 否 | - | 管控状态 |
| search | string | 否 | - | 搜索关键词 |

#### 响应

返回文件下载流，文件名格式：`alert_control_records_YYYYMMDD_HHMMSS.csv/xlsx`

### 4. 获取告警管控统计

**GET** `/api/fraudhunter/alert-control-records/statistics/summary`

#### 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| start_date | string | 否 | 统计开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | 统计结束日期 (YYYY-MM-DD) |

#### 响应格式

```json
{
  "total_records": 100,
  "alert_statistics": {
    "total_alerts": 80,
    "sent_alerts": 75,
    "duplicate_alerts": 5
  },
  "control_statistics": {
    "total_controls": 20,
    "executed_controls": 18,
    "duplicate_controls": 2
  },
  "date_range": {
    "start_date": "2024-12-01",
    "end_date": "2024-12-12"
  }
}
```

## 状态说明

### 告警状态 (alert_status)

- `not_configured`: 未配置 - 模型未启用告警功能
- `sent`: 已发送 - 告警消息已发送
- `duplicate`: 重复 - 当天已对该账号发送过告警

### 管控状态 (control_status)

- `not_configured`: 未配置 - 模型未启用管控功能
- `executed`: 已执行 - 管控操作已执行
- `duplicate`: 重复 - 当天已对该账号执行过管控

## 错误处理

### 常见错误码

- `400 Bad Request`: 请求参数无效
  - 无效的日期格式
  - 无效的状态值
  - 无效的导出格式
- `404 Not Found`: 记录不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

## 使用示例

### 查询特定账号的告警记录

```bash
curl -X GET "http://localhost:50020/api/fraudhunter/alert-control-records?account_id=test_account_001&alert_status=sent"
```

### 导出Excel格式的记录

```bash
curl -X POST "http://localhost:50020/api/fraudhunter/alert-control-records/export?format=excel&start_date=2024-12-01&end_date=2024-12-12" \
  -H "Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  --output alert_records.xlsx
```

### 获取记录详情

```bash
curl -X GET "http://localhost:50020/api/fraudhunter/alert-control-records/123"
```

## 注意事项

1. **分页限制**: 每页最大1000条记录，建议使用合理的分页大小以提高性能
2. **导出限制**: 导出功能会包含所有符合筛选条件的记录，大量数据导出时请注意性能
3. **日期格式**: 所有日期参数必须使用 `YYYY-MM-DD` 格式
4. **编码格式**: CSV导出使用UTF-8编码（带BOM），确保Excel正确显示中文
5. **缓存**: 统计接口可能需要缓存优化，大数据量时建议添加缓存机制