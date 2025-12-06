# FraudHunter 反诈指标与模型管理系统

## 快速开始

### 1. 安装依赖

```bash
# 安装sqlparse（SQL解析库）
uv add sqlparse
```

### 2. 创建数据库表

```bash
# 删除旧数据库（如果存在）
rm -f database/metadata.db

# 创建新表
uv run python -c "
from models.db_base import create_tables
import models.fraudhunter
create_tables()
print('数据库表创建成功')
"
```

### 3. 启动后端服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 50020
```

### 4. 测试API

方式一：访问API文档
```
http://localhost:50020/docs
```

方式二：运行测试脚本
```bash
uv run python test_fraudhunter_api.py
```

## API端点

### 指标组管理 (`/api/taosha/v1/fraudhunter/indicator-groups`)

- `POST /` - 创建指标组
- `GET /` - 获取指标组列表
- `GET /{id}` - 获取指标组详情
- `PUT /{id}` - 更新指标组
- `POST /{id}/dry-run` - 指标组试运行
- `POST /{id}/publish` - 发布指标组
- `POST /{id}/archive` - 归档指标组
- `DELETE /{id}` - 删除指标组

### 指标定义管理 (`/api/taosha/v1/fraudhunter/indicators`)

- `POST /` - 创建指标
- `GET /` - 获取指标列表
- `GET /{id}` - 获取指标详情
- `PUT /{id}` - 更新指标
- `POST /{id}/publish` - 发布指标
- `POST /{id}/archive` - 归档指标
- `DELETE /{id}` - 删除指标

### 任务管理 (`/api/taosha/v1/fraudhunter/tasks`)

- `GET /{task_id}/progress` - 查询任务进度
- `GET /{task_id}/result` - 获取任务结果
- `POST /{task_id}/cancel` - 取消任务
- `GET /executions` - 查询任务执行历史

## 目录结构

```
backend/
├── models/fraudhunter/              # 数据库模型
│   ├── indicator.py                 # 指标相关模型
│   ├── model.py                     # 模型相关模型
│   └── task.py                      # 任务相关模型
├── schemas/fraudhunter/             # Pydantic schemas
│   ├── indicator.py                 # 指标相关schema
│   └── task.py                      # 任务相关schema
├── services/fraudhunter/            # 服务层
│   ├── indicator_service/           # 指标服务
│   │   ├── sql_validator.py         # SQL验证
│   │   ├── indicator_group_manager.py # 指标组管理
│   │   └── indicator_manager.py     # 指标定义管理
│   └── task_service/                # 任务服务
│       ├── task_manager.py          # 任务管理器
│       └── indicator_executor.py    # 指标执行器
└── api/fraudhunter/                 # API路由
    ├── indicator_group_routes.py    # 指标组API
    ├── indicator_routes.py          # 指标定义API
    └── task_routes.py               # 任务管理API
```

## 核心概念

### 指标组 (Indicator Group)

一个SQL可以生成多个指标，减少重复计算。

**示例SQL**:
```sql
SELECT
    account_id,
    indicator_code,
    indicator_value,
    CURRENT_DATE as dt
FROM (
    SELECT
        account_id,
        'i_login_cnt_7d' as indicator_code,
        COUNT(*) as indicator_value
    FROM user_login
    WHERE login_date >= DATE_SUB(CURRENT_DATE, 7)
    GROUP BY account_id

    UNION ALL

    SELECT
        account_id,
        'i_login_device_cnt' as indicator_code,
        COUNT(DISTINCT device_id) as indicator_value
    FROM user_login
    WHERE login_date >= DATE_SUB(CURRENT_DATE, 7)
    GROUP BY account_id
) t
```

### 版本管理

- `current_version`: 当前发布版本
- `latest_version`: 最新版本号
- 每次更新会增加`latest_version`
- 发布时会同步`current_version`到指定版本

### 异步任务

所有耗时操作（试运行、生产执行）都通过异步任务执行：

1. 提交任务 → 返回`task_id`
2. 轮询进度 → `/tasks/{task_id}/progress`
3. 获取结果 → `/tasks/{task_id}/result`

## 注意事项

1. **Spark SQL集成**: 当前使用模拟执行，生产环境需要连接Spark ThriftServer
2. **用户认证**: 当前API未实现认证，`created_by`使用"system"
3. **DolphinScheduler集成**: 调度功能尚未实现

## 下一步

继续按照设计文档完成第三周的模型功能开发。

详细文档请查看: `docs/fraudhunter_week2_progress.md`
