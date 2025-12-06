# DolphinScheduler 集成方案设计

## 需求概述
在淘沙分析平台中集成 DolphinScheduler，实现指标任务上线时自动创建/更新工作流，包含：
- N个shell节点 + 1个SQL节点（SQL节点依赖所有shell节点）
- 工作流不存在时创建，存在时更新
- 统一的定时调度配置

## 架构设计

### 1. 配置层扩展
**文件**: `backend/config/config.yaml`
```yaml
# 新增 DolphinScheduler 配置段
dolphinscheduler:
  # DS 服务连接配置
  gateway:
    url: "http://localhost:12345"
    api_port: 12346
    user: "admin"
    password: "dolphinscheduler123"
    tenant: "default"

  # 项目配置
  project_name: "taosha_metrics"

  # 工作流配置
  workflow:
    default_timezone: "Asia/Shanghai"
    timeout: 60

  # 定时调度配置
  schedule:
    cron_expression: "0 0 2 * * ?"  # 每天凌晨2点
    online_schedule: true

  # 任务配置
  task:
    table_check:
      timeout: 30
      fail_retry_times: 3
      fail_retry_interval: 1
    sql_task:
      timeout: 60
      fail_retry_times: 288
      fail_retry_interval: 5
```

### 2. 服务层设计

#### 2.1 DolphinScheduler 服务基类
**文件**: `backend/services/dolphinscheduler/ds_service.py`
- 负责与 DS 的连接管理
- 初始化 pydolphinscheduler 配置
- 提供基础的项目管理工作流操作

#### 2.2 工作流生成服务
**文件**: `backend/services/dolphinscheduler/workflow_generator.py`
- 根据指标任务数据生成工作流定义
- 支持动态 shell 节点创建
- SQL 节点与依赖关系生成
- 任务生成会有一些其他逻辑，由用户补充完成

### 4. API 端点设计

#### 4.1 指标任务上线接口
**路由**: `POST /api/taosha/v1/fraudhunter/indicator-tasks/{task_id}/publish`
**文件**: indicator_task_routes.py
- 触发工作流创建和上线
- 返回工作流信息和状态

#### 4.2 指标任务补数接口
**路由**: `POST /api/taosha/v1/fraudhunter/indicator-tasks/{task_id}/rerun`
**文件**: indicator_task_routes.py
- 触发工作流补数任务，需输入补数的开始日期，结束日期默认当日


### 5. 前端集成

#### 5.1 指标任务管理页面扩展
**文件**: `frontend/app/(main)/fraudhunter/indicator-tasks/page.tsx`
- 在指标任务列表中增加 上线、补数 按钮
- 显示工作流链接（跳转到DS UI）

## 核心流程设计

### 流程1：指标任务上线到DS
```
1. 前端调用上线接口
2. 后端验证指标任务状态
3. 调用 workflow_generator
4. 生成工作流定义（shell节点 + SQL节点）
  1. 生成Shell节点
  2. 生成SQL节点（基于指标结果存储逻辑）
  3. 设置SQL节点依赖所有shell节点
  4. 应用统一的定时配置
  5. 设置超时和重试参数
5. 检查DS中是否存在同名工作流（同ID）
6. 不存在则创建，存在则更新
7. 设置定时调度
8. 更新数据到 FraudHunterIndicatorTask 表的ds_task_name，ds_task_code字段（新增）
9. 返回结果给前端
```

### 流程2：补数逻辑
```
1. 输入框用户输入补数开始日期
2. 调用ds的补数功能开始补数

```

## 文件清单

### 后端新增文件
```
backend/
├── config/config.yaml (修改)
├── services/dolphinscheduler/
│   ├── __init__.py
│   ├── ds_service.py
│   ├── workflow_generator.py
├── api/indicator_task_routes.py(修改)
models/fraudhunter/indicator.py(修改)
```

### 前端新增文件
```
frontend/
├── app/(main)/fraudhunter/indicator-tasks/page.tsx (修改)
```

### 依赖添加
```bash
# 后端
uv add apache-dolphinscheduler
```