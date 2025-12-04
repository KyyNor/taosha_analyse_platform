# FraudHunter 反诈指标与模型管理系统设计文档

## 文档版本
- **版本**: v2.0.0
- **创建日期**: 2025-12-02
- **更新日期**: 2025-12-03
- **作者**: Claude Code
- **状态**: 设计阶段

---

## 目录
1. [项目概述](#1-项目概述)
2. [系统架构设计](#2-系统架构设计)
3. [数据库模型设计](#3-数据库模型设计)
4. [后端API设计](#4-后端api设计)
5. [服务层架构](#5-服务层架构)
6. [前端界面设计](#6-前端界面设计)
7. [可视化规则引擎](#7-可视化规则引擎)
8. [指标组与动态SQL](#8-指标组与动态sql)
9. [异步任务执行机制](#9-异步任务执行机制)
10. [部署架构](#10-部署架构)
11. [开发路线图](#11-开发路线图)

---

## 1. 项目概述

### 1.1 背景与目标

**业务背景**：
- 数据存储在Hadoop上，离线数据通过Spark SQL(ThriftServer JDBC)加工
- 实时数据通过Kafka接入，使用PySpark Streaming处理
- 业务部门需要快速定义反诈指标和模型，现有宽表维护方式不灵活
- 任务调度使用DolphinScheduler

**系统目标**：
- 提供开发人员友好的指标定义界面（支持SQL逻辑）
- 实现指标组概念，一个SQL可加工多个指标，减少重复计算
- 提供可视化模型定义能力，让业务人员也能定义简单模型
- 支持指标和模型的版本管理和历史追溯
- 支持模型试运行和历史数据验证
- 异步任务执行，支持任务进度追踪

### 1.2 技术约束

- **开发资源有限**：优先实现MVP功能，避免过度设计
- **技术栈约束**：
  - 数据层：Hadoop + Spark SQL(JDBC) + Kafka + PySpark Streaming
  - 调度系统：DolphinScheduler
  - 后端：FastAPI + SQLAlchemy 2.0 + Python 3.11+
  - 前端：Next.js 14 + React 18 + TypeScript

### 1.3 MVP阶段功能范围

**第一阶段（MVP）**：
- ✅ 指标定义（仅支持SQL，不支持PySpark代码）
- ✅ 指标组概念（一个SQL批量计算多个指标）
- ✅ 指标版本管理和历史追溯
- ✅ 指标试运行和结果预览
- ✅ 简化版可视化模型定义（规则引擎方式）
- ✅ 模型版本管理和历史追溯
- ✅ 模型试运行功能（指定时间范围验证）
- ✅ DolphinScheduler任务集成
- ✅ 异步任务执行和进度追踪

**第二阶段（扩展）**：
- ⏳ PySpark代码支持（复杂指标计算）
- ⏳ 实时指标监控和告警
- ⏳ 模型A/B测试
- ⏳ 指标血缘分析

---

## 2. 系统架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                  FraudHunter 反诈指标模型管理系统                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  指标管理    │  │  模型管理   │  │      任务管理           │  │
│  │             │  │             │  │                         │  │
│  │ ·离线指标   │  │ ·规则定义   │  │ ·异步任务执行           │  │
│  │ ·指标组     │  │ ·可视化配置 │  │ ·任务状态追踪           │  │
│  │ ·版本管理   │  │ ·版本管理   │  │ ·DS任务集成             │  │
│  │ ·试运行     │  │ ·试运行     │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
├─────────┴────────────────┴─────────────────────┴────────────────┤
│                         核心服务层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SQL解析引擎 │  │ 代码生成器  │  │    调度集成服务          │  │
│  │             │  │             │  │                         │  │
│  │ ·语法校验   │  │ ·指标SQL    │  │ ·DS REST API            │  │
│  │ ·字段提取   │  │ ·PySpark    │  │ ·任务DAG生成            │  │
│  │ ·依赖分析   │  │   Streaming │  │ ·任务状态同步           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                         数据层                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MySQL: 元数据存储（指标定义、模型定义、任务状态）          │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Hadoop/Hive: 指标结果表(行存) → 宽表(动态生成)            │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Kafka: 实时流水数据接入                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

                              ↓ 集成

┌─────────────────────────────────────────────────────────────────┐
│                       外部系统集成                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ DolphinScheduler │  │ Spark ThriftServer │  │ PySpark Streaming │  │
│  │  任务调度     │  │   JDBC执行   │  │   实时计算         │     │
│  └──────────────┘  └──────────────┘  └────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

**后端技术栈**：
- **Web框架**：FastAPI 0.116+（异步支持、自动文档）
- **ORM**：SQLAlchemy 2.0（现代化API、类型提示）
- **数据库**：MySQL 8.0+（元数据存储）
- **数据处理**：PySpark 3.5+、PyHive（Spark SQL JDBC）
- **调度集成**：DolphinScheduler REST API客户端
- **配置管理**：Pydantic Settings（类型安全配置）
- **日志系统**：Loguru（结构化日志）

**前端技术栈**：
- **框架**：Next.js 14、React 18、TypeScript 5.0+
- **UI组件**：Radix UI、Tailwind CSS 3.4+
- **状态管理**：React Context + 自定义hooks
- **HTTP客户端**：Axios 1.7+
- **代码编辑器**：Monaco Editor（SQL编辑）
- **图表库**：Recharts/ECharts（结果可视化）

**数据层技术栈**：
- **离线存储**：Hadoop HDFS + Hive
- **实时流**：Kafka + PySpark Streaming
- **查询引擎**：Spark SQL (ThriftServer)
- **任务调度**：DolphinScheduler

### 2.3 模块划分

**后端模块**：
```
backend/
├── api/
│   └── fraudhunter/                    # FraudHunter API路由层
│       ├── indicator_routes.py         # 指标管理API
│       ├── model_routes.py             # 模型管理API
│       └── task_routes.py              # 任务管理API
├── services/
│   └── fraudhunter/                    # FraudHunter服务层
│       ├── indicator_service/          # 指标服务
│       │   ├── indicator_manager.py    # 指标CRUD
│       │   ├── indicator_executor.py   # 指标执行
│       │   ├── indicator_group_manager.py # 指标组管理
│       │   └── sql_validator.py        # SQL验证
│       ├── model_service/              # 模型服务
│       │   ├── model_manager.py        # 模型CRUD
│       │   ├── rule_engine.py          # 规则引擎
│       │   ├── code_generator.py       # 代码生成
│       │   └── model_executor.py       # 模型执行
│       ├── scheduler_service/          # 调度服务
│       │   ├── dolphin_client.py       # DS客户端
│       │   └── task_manager.py         # 任务管理
│       └── spark_service/              # Spark服务
│           ├── spark_jdbc_client.py    # JDBC客户端
│           └── streaming_deployer.py   # Streaming部署
├── models/
│   └── fraudhunter/                    # FraudHunter数据模型
│       ├── indicator.py                # 指标模型
│       ├── model.py                    # 模型模型
│       ├── task.py                     # 任务模型
│       └── execution.py                # 执行记录
└── utils/                              # 工具类
    ├── sql_parser.py                   # SQL解析
    ├── template_engine.py              # 模板引擎
    └── validator.py                    # 验证器
```

**前端模块**：
```
frontend/
├── app/(main)/
│   └── fraudhunter/                    # FraudHunter前端页面
│       ├── indicators/                 # 指标管理页面
│       │   ├── page.tsx               # 指标列表
│       │   ├── [id]/page.tsx          # 指标详情/编辑
│       │   └── create/page.tsx        # 创建指标
│       ├── models/                     # 模型管理页面
│       │   ├── page.tsx               # 模型列表
│       │   ├── [id]/page.tsx          # 模型详情/编辑
│       │   └── create/page.tsx        # 创建模型
│       └── tasks/                      # 任务管理页面
│           ├── page.tsx               # 任务列表
│           └── [id]/page.tsx          # 任务详情
├── components/
│   └── fraudhunter/                    # FraudHunter组件
│       ├── indicator/                  # 指标相关组件
│       │   ├── IndicatorForm.tsx      # 指标表单
│       │   ├── SQLEditor.tsx          # SQL编辑器
│       │   ├── IndicatorPreview.tsx   # 指标预览
│       │   └── IndicatorGroupSelector.tsx # 指标组选择
│       ├── model/                      # 模型相关组件
│       │   ├── RuleBuilder.tsx        # 规则构建器
│       │   ├── RulePreview.tsx        # 规则预览
│       │   └── ModelDashboard.tsx     # 模型仪表板
│       └── task/                       # 任务相关组件
│           ├── TaskList.tsx           # 任务列表
│           └── TaskMonitor.tsx        # 任务监控
└── lib/
    └── services/
        └── fraudhunter/                # FraudHunter服务
            ├── indicatorService.ts     # 指标服务
            ├── modelService.ts         # 模型服务
            └── taskService.ts          # 任务服务
```

---

## 3. 数据库模型设计

### 3.1 核心设计理念

**指标组概念**：
- 指标定义表(`fraudhunter_indicator_definition`)只存储指标元信息和指标组ID
- 指标组表(`fraudhunter_indicator_group`)存储SQL加工逻辑
- 同一个指标组的多个指标共享同一个SQL，SQL一次执行产出多个指标

**版本管理**：
- 指标和模型都有版本历史表
- 主表存储当前发布版本和最新版本号
- 历史表记录所有版本变更

### 3.2 元数据存储（MySQL）

#### 3.2.1 指标组表

```sql
-- 指标组表（存储SQL加工逻辑）
CREATE TABLE fraudhunter_indicator_group (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    group_code VARCHAR(64) NOT NULL UNIQUE COMMENT '指标组编码',
    group_name VARCHAR(128) NOT NULL COMMENT '指标组名称',
    description TEXT COMMENT '描述',

    -- 加工逻辑
    logic_type VARCHAR(16) DEFAULT 'sql' COMMENT '逻辑类型：sql/pyspark（预留）',
    logic_content TEXT NOT NULL COMMENT 'SQL内容或代码',

    -- 数据源配置
    source_tables VARCHAR(512) COMMENT '依赖的源表列表，逗号分隔',

    -- 输出配置
    output_table VARCHAR(128) COMMENT '输出表名',
    output_mode VARCHAR(16) DEFAULT 'row' COMMENT '输出模式：row（行存）',

    -- 版本管理
    current_version INT DEFAULT 1 COMMENT '当前发布版本',
    latest_version INT DEFAULT 1 COMMENT '最新版本号',

    -- 状态管理
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态：draft/testing/online/offline/archived',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_group_code (group_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标组表';
```

#### 3.2.2 指标组版本历史表

```sql
-- 指标组版本历史表
CREATE TABLE fraudhunter_indicator_group_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    group_id BIGINT NOT NULL COMMENT '指标组ID',
    version INT NOT NULL COMMENT '版本号',

    -- 历史快照（JSON格式存储完整配置）
    group_code VARCHAR(64) NOT NULL COMMENT '指标组编码',
    group_name VARCHAR(128) NOT NULL COMMENT '指标组名称',
    description TEXT COMMENT '描述',
    logic_type VARCHAR(16) COMMENT '逻辑类型',
    logic_content TEXT COMMENT 'SQL内容',
    source_tables VARCHAR(512) COMMENT '源表列表',

    -- 变更信息
    change_type VARCHAR(16) NOT NULL COMMENT '变更类型：create/update/publish/archive',
    change_description TEXT COMMENT '变更说明',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_group_version (group_id, version),
    INDEX idx_group_id (group_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标组版本历史表';
```

#### 3.2.3 指标定义表

```sql
-- 指标定义表
CREATE TABLE fraudhunter_indicator_definition (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    indicator_code VARCHAR(64) NOT NULL UNIQUE COMMENT '指标编码，如 i_login_cnt_7d',
    indicator_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    indicator_type VARCHAR(16) NOT NULL COMMENT '指标类型：offline/realtime',
    description TEXT COMMENT '指标描述',

    -- 数据类型
    data_type VARCHAR(16) NOT NULL COMMENT '数据类型：numeric/enum/text/boolean',
    enum_values TEXT COMMENT '枚举值（当data_type=enum时，JSON数组格式）',

    -- 指标组关联
    indicator_group_id BIGINT NOT NULL COMMENT '指标组ID',

    -- 版本管理
    current_version INT DEFAULT 1 COMMENT '当前发布版本',
    latest_version INT DEFAULT 1 COMMENT '最新版本号',

    -- 状态管理
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态：draft/testing/online/offline/archived',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_indicator_code (indicator_code),
    INDEX idx_indicator_group_id (indicator_group_id),
    INDEX idx_status (status),
    INDEX idx_indicator_type (indicator_type),
    FOREIGN KEY (indicator_group_id) REFERENCES fraudhunter_indicator_group(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标定义表';
```

#### 3.2.4 指标定义版本历史表

```sql
-- 指标定义版本历史表
CREATE TABLE fraudhunter_indicator_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    indicator_id BIGINT NOT NULL COMMENT '指标ID',
    version INT NOT NULL COMMENT '版本号',

    -- 历史快照
    indicator_code VARCHAR(64) NOT NULL COMMENT '指标编码',
    indicator_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    indicator_type VARCHAR(16) NOT NULL COMMENT '指标类型',
    description TEXT COMMENT '描述',
    data_type VARCHAR(16) COMMENT '数据类型',
    enum_values TEXT COMMENT '枚举值',
    indicator_group_id BIGINT COMMENT '指标组ID',

    -- 变更信息
    change_type VARCHAR(16) NOT NULL COMMENT '变更类型：create/update/publish/archive',
    change_description TEXT COMMENT '变更说明',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_indicator_version (indicator_id, version),
    INDEX idx_indicator_id (indicator_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标定义版本历史表';
```

#### 3.2.5 模型定义表

```sql
-- 模型定义表
CREATE TABLE fraudhunter_model_definition (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    model_code VARCHAR(64) NOT NULL UNIQUE COMMENT '模型编码',
    model_name VARCHAR(128) NOT NULL COMMENT '模型名称',
    description TEXT COMMENT '模型描述',

    -- 模型规则（JSON格式存储可视化定义）
    rule_config JSON NOT NULL COMMENT '规则配置JSON',
    /*
    示例：
    {
      "logic": "AND",
      "rules": [
        {
          "type": "condition",
          "indicator": "i_login_cnt_7d",
          "operator": ">",
          "value": 10
        },
        {
          "type": "condition",
          "indicator": "i_trans_amt_1d",
          "operator": ">",
          "value": 50000
        },
        {
          "type": "group",
          "logic": "OR",
          "rules": [
            {
              "type": "condition",
              "indicator": "i_device_change_cnt",
              "operator": ">=",
              "value": 3
            },
            {
              "type": "condition",
              "indicator": "i_ip_city_cnt",
              "operator": ">",
              "value": 5
            }
          ]
        }
      ],
      "output": {
        "risk_level": "high",
        "risk_score": 85,
        "action": "block"
      }
    }
    */

    -- 关联指标
    indicator_codes TEXT COMMENT '使用的指标编码列表，JSON数组',

    -- 输出配置
    output_table VARCHAR(128) COMMENT '输出表名',
    output_partition_field VARCHAR(64) DEFAULT 'dt' COMMENT '分区字段',

    -- 生成的代码（系统自动生成）
    generated_code TEXT COMMENT '生成的PySpark代码',
    code_version INT DEFAULT 1 COMMENT '代码版本',

    -- 版本管理
    current_version INT DEFAULT 1 COMMENT '当前发布版本',
    latest_version INT DEFAULT 1 COMMENT '最新版本号',

    -- 状态管理
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态：draft/testing/online/offline/archived',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_model_code (model_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型定义表';
```

#### 3.2.6 模型定义版本历史表

```sql
-- 模型定义版本历史表
CREATE TABLE fraudhunter_model_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    model_id BIGINT NOT NULL COMMENT '模型ID',
    version INT NOT NULL COMMENT '版本号',

    -- 历史快照
    model_code VARCHAR(64) NOT NULL COMMENT '模型编码',
    model_name VARCHAR(128) NOT NULL COMMENT '模型名称',
    description TEXT COMMENT '描述',
    rule_config JSON COMMENT '规则配置',
    indicator_codes TEXT COMMENT '指标编码列表',
    output_table VARCHAR(128) COMMENT '输出表名',
    output_partition_field VARCHAR(64) COMMENT '分区字段',
    generated_code TEXT COMMENT '生成的代码',

    -- 变更信息
    change_type VARCHAR(16) NOT NULL COMMENT '变更类型：create/update/publish/archive',
    change_description TEXT COMMENT '变更说明',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_model_version (model_id, version),
    INDEX idx_model_id (model_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型定义版本历史表';
```

#### 3.2.7 任务执行表

```sql
-- 任务执行表
CREATE TABLE fraudhunter_task_execution (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_type VARCHAR(32) NOT NULL COMMENT '任务类型：indicator/model',
    task_id BIGINT NOT NULL COMMENT '任务关联ID（指标组ID或模型ID）',
    execution_id VARCHAR(64) NOT NULL UNIQUE COMMENT '执行ID（UUID）',

    -- 执行信息
    start_time TIMESTAMP COMMENT '开始时间',
    end_time TIMESTAMP COMMENT '结束时间',

    -- 状态
    status VARCHAR(16) DEFAULT 'pending' COMMENT '状态：pending/running/success/failed/cancelled',

    -- 执行结果
    result_summary JSON COMMENT '结果摘要（处理记录数、命中数等）',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '触发人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_task_type_id (task_type, task_id),
    INDEX idx_execution_id (execution_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行表';
```

#### 3.2.8 任务执行详细记录表

```sql
-- 任务执行详细记录表
CREATE TABLE fraudhunter_task_execution_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    execution_id VARCHAR(64) NOT NULL COMMENT '执行ID',

    -- 执行详情
    etl_date DATE COMMENT 'ETL日期',
    version INT COMMENT '执行版本号',

    -- 执行参数
    parameters JSON COMMENT '执行参数（配置、环境变量等）',

    -- 执行日志
    log_content TEXT COMMENT '执行日志',
    error_message TEXT COMMENT '错误信息',

    -- 执行统计
    rows_processed BIGINT COMMENT '处理行数',
    rows_output BIGINT COMMENT '输出行数',
    duration_seconds INT COMMENT '执行时长（秒）',

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_execution_id (execution_id),
    INDEX idx_etl_date (etl_date),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (execution_id) REFERENCES fraudhunter_task_execution(execution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行详细记录表';
```

### 3.3 数据层存储（Hive）

#### 3.3.1 指标结果表（行存格式）

```sql
-- Hive表：指标结果表（行存储）
CREATE TABLE IF NOT EXISTS anti_fraud.indicator_result_row (
    account_id STRING COMMENT '账户ID',
    indicator_code STRING COMMENT '指标编码',
    indicator_value STRING COMMENT '指标值',
    indicator_type STRING COMMENT '指标类型（数值/枚举/文本/布尔）',
    data_date DATE COMMENT '数据日期',
    calculate_time TIMESTAMP COMMENT '计算时间'
)
PARTITIONED BY (dt STRING COMMENT '分区日期 YYYYMMDD')
STORED AS PARQUET
LOCATION '/user/hive/warehouse/anti_fraud.db/indicator_result_row'
TBLPROPERTIES (
    'parquet.compression'='snappy',
    'description'='反诈指标结果表-行存储格式'
);
```

#### 3.3.2 指标宽表（动态生成）

```sql
-- Hive表：指标宽表（通过动态SQL从行表生成）
CREATE TABLE IF NOT EXISTS anti_fraud.indicator_result_wide (
    account_id STRING COMMENT '账户ID',
    data_date DATE COMMENT '数据日期',
    -- 动态字段（通过PIVOT或动态SQL生成）
    -- i_login_cnt_7d INT COMMENT '7天登录次数',
    -- i_trans_amt_1d DECIMAL(18,2) COMMENT '1天交易金额',
    -- ... 其他指标字段
    calculate_time TIMESTAMP COMMENT '计算时间'
)
PARTITIONED BY (dt STRING COMMENT '分区日期 YYYYMMDD')
STORED AS PARQUET
LOCATION '/user/hive/warehouse/anti_fraud.db/indicator_result_wide'
TBLPROPERTIES (
    'parquet.compression'='snappy',
    'description'='反诈指标结果表-宽表格式'
);
```

---

## 4. 后端API设计

### 4.1 API路由规范

**基础路径**: `/api/taosha/v1/fraudhunter`

**路由组织**:
```
/api/taosha/v1/fraudhunter
├── /indicator-groups        # 指标组管理
├── /indicators              # 指标管理
├── /models                  # 模型管理
└── /tasks                   # 任务管理
```

### 4.2 指标组管理API

#### 4.2.1 创建指标组

```http
POST /api/taosha/v1/fraudhunter/indicator-groups
Content-Type: application/json

{
  "group_code": "login_behavior",
  "group_name": "登录行为指标组",
  "description": "统计用户登录相关的多个指标",
  "logic_type": "sql",
  "logic_content": "SELECT account_id, indicator_code, indicator_value, CURRENT_DATE as dt FROM user_login WHERE login_date >= DATE_SUB(CURRENT_DATE, 7) GROUP BY account_id",
  "source_tables": "user_login,user_session",
  "output_table": "anti_fraud.indicator_result_row",
  "output_mode": "row"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "group_code": "login_behavior",
    "current_version": 1,
    "latest_version": 1,
    "status": "draft",
    "created_at": "2025-12-02T10:00:00Z"
  }
}
```

#### 4.2.2 指标组试运行

```http
POST /api/taosha/v1/fraudhunter/indicator-groups/{id}/dry-run
Content-Type: application/json

{
  "etl_date": "2025-10-20",
  "group_version": 1,
  "sample_size": 100
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "task_550e8400-e29b-41d4-a716-446655440000",
    "status": "pending",
    "message": "任务已提交，请通过task_id查询进度"
  }
}
```

#### 4.2.3 发布指标组

```http
POST /api/taosha/v1/fraudhunter/indicator-groups/{id}/publish
Content-Type: application/json

{
  "version": 1,
  "change_description": "首次发布"
}
```

### 4.3 指标管理API

#### 4.3.1 创建指标

```http
POST /api/taosha/v1/fraudhunter/indicators
Content-Type: application/json

{
  "indicator_code": "i_login_cnt_7d",
  "indicator_name": "7天登录次数",
  "indicator_type": "offline",
  "description": "统计账户最近7天的登录次数",
  "data_type": "numeric",
  "indicator_group_id": 1
}
```

#### 4.3.2 查询指标列表

```http
GET /api/taosha/v1/fraudhunter/indicators?page=1&page_size=20&status=online&indicator_type=offline&indicator_group_id=1
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 45,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": 1,
        "indicator_code": "i_login_cnt_7d",
        "indicator_name": "7天登录次数",
        "indicator_type": "offline",
        "data_type": "numeric",
        "indicator_group_id": 1,
        "current_version": 2,
        "latest_version": 3,
        "status": "online",
        "created_at": "2025-11-01T10:00:00Z"
      }
    ]
  }
}
```

### 4.4 模型管理API

#### 4.4.1 创建模型

```http
POST /api/taosha/v1/fraudhunter/models
Content-Type: application/json

{
  "model_code": "m_high_risk_login",
  "model_name": "高风险登录模型",
  "description": "检测异常登录行为",
  "rule_config": {
    "logic": "AND",
    "rules": [
      {
        "type": "condition",
        "indicator": "i_login_cnt_7d",
        "operator": ">",
        "value": 10
      },
      {
        "type": "group",
        "logic": "OR",
        "rules": [
          {
            "type": "condition",
            "indicator": "i_device_change_cnt",
            "operator": ">=",
            "value": 3
          },
          {
            "type": "condition",
            "indicator": "i_ip_city_cnt",
            "operator": ">",
            "value": 5
          }
        ]
      }
    ],
    "output": {
      "risk_level": "high",
      "risk_score": 85,
      "action": "review"
    }
  },
  "indicator_codes": ["i_login_cnt_7d", "i_device_change_cnt", "i_ip_city_cnt"],
  "output_table": "anti_fraud.model_result"
}
```

#### 4.4.2 模型试运行

```http
POST /api/taosha/v1/fraudhunter/models/{id}/dry-run
Content-Type: application/json

{
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "model_version": 1,
  "sample_size": 10000
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "task_660f9511-f3ac-52e5-b827-557766551111",
    "status": "pending",
    "message": "任务已提交，请通过task_id查询进度"
  }
}
```

#### 4.4.3 生成模型代码

```http
POST /api/taosha/v1/fraudhunter/models/{id}/generate-code
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "model_id": 1,
    "code_version": 2,
    "generated_code": "# PySpark Streaming代码\n...",
    "code_path": "/opt/spark/jobs/fraudhunter_m_high_risk_login_v2.py"
  }
}
```

### 4.5 任务管理API

#### 4.5.1 查询任务进度

```http
GET /api/taosha/v1/fraudhunter/tasks/{task_id}/progress
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "task_550e8400-e29b-41d4-a716-446655440000",
    "task_type": "indicator",
    "status": "running",
    "progress": 65.5,
    "current_step": "执行SQL查询",
    "start_time": "2025-12-03T10:00:00Z",
    "estimated_remaining_seconds": 120
  }
}
```

#### 4.5.2 获取任务结果

```http
GET /api/taosha/v1/fraudhunter/tasks/{task_id}/result
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "task_550e8400-e29b-41d4-a716-446655440000",
    "status": "success",
    "duration_seconds": 180,
    "result": {
      "total_records": 10000,
      "sample_result": [
        {
          "account_id": "ACC001",
          "indicator_code": "i_login_cnt_7d",
          "indicator_value": "5",
          "dt": "20251020"
        }
      ]
    }
  }
}
```

#### 4.5.3 查询任务执行历史

```http
GET /api/taosha/v1/fraudhunter/tasks/executions?task_type=indicator&task_id=1&page=1&page_size=20
```

#### 4.5.4 取消任务

```http
POST /api/taosha/v1/fraudhunter/tasks/{task_id}/cancel
```

---

## 5. 服务层架构

### 5.1 指标服务

#### 5.1.1 指标组管理服务

**文件**: `backend/services/fraudhunter/indicator_service/indicator_group_manager.py`

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from models.fraudhunter.indicator import FraudHunterIndicatorGroup
from schemas.fraudhunter.indicator import IndicatorGroupCreate, IndicatorGroupUpdate
from utils.logger import logger

class IndicatorGroupManager:
    """指标组管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_indicator_group(
        self,
        group_data: IndicatorGroupCreate,
        created_by: str
    ) -> FraudHunterIndicatorGroup:
        """创建指标组"""
        # 验证编码唯一性
        existing = self.db.query(FraudHunterIndicatorGroup).filter(
            FraudHunterIndicatorGroup.group_code == group_data.group_code
        ).first()

        if existing:
            raise ValueError(f"指标组编码已存在: {group_data.group_code}")

        # 创建指标组记录
        db_group = FraudHunterIndicatorGroup(
            **group_data.model_dump(),
            created_by=created_by,
            status='draft',
            current_version=1,
            latest_version=1
        )

        self.db.add(db_group)
        self.db.commit()
        self.db.refresh(db_group)

        # 创建版本历史
        self._create_version_history(db_group, 'create', '初始创建', created_by)

        logger.info(f"创建指标组成功: {db_group.group_code}")
        return db_group

    def update_indicator_group(
        self,
        group_id: int,
        group_data: IndicatorGroupUpdate,
        updated_by: str
    ) -> FraudHunterIndicatorGroup:
        """更新指标组"""
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        # 只有draft状态才允许更新逻辑内容
        if db_group.status != 'draft' and group_data.logic_content:
            raise ValueError("只有草稿状态的指标组才允许修改逻辑内容")

        # 更新字段
        update_data = group_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_group, key, value)

        db_group.updated_by = updated_by
        db_group.latest_version += 1

        self.db.commit()
        self.db.refresh(db_group)

        # 创建版本历史
        self._create_version_history(db_group, 'update', '更新配置', updated_by)

        logger.info(f"更新指标组成功: {db_group.group_code}")
        return db_group

    def publish_indicator_group(
        self,
        group_id: int,
        version: int,
        updated_by: str,
        change_description: Optional[str] = None
    ) -> FraudHunterIndicatorGroup:
        """发布指标组"""
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        # 验证版本号
        if version > db_group.latest_version:
            raise ValueError(f"版本号不存在: {version}")

        # 更新发布版本
        db_group.current_version = version
        db_group.status = 'online'
        db_group.updated_by = updated_by

        self.db.commit()
        self.db.refresh(db_group)

        # 创建版本历史
        self._create_version_history(
            db_group,
            'publish',
            change_description or f'发布版本{version}',
            updated_by
        )

        logger.info(f"发布指标组成功: {db_group.group_code}, 版本: {version}")
        return db_group

    def _create_version_history(
        self,
        group: FraudHunterIndicatorGroup,
        change_type: str,
        change_description: str,
        created_by: str
    ):
        """创建版本历史记录"""
        from models.fraudhunter.indicator import FraudHunterIndicatorGroupHistory

        history = FraudHunterIndicatorGroupHistory(
            group_id=group.id,
            version=group.latest_version,
            group_code=group.group_code,
            group_name=group.group_name,
            description=group.description,
            logic_type=group.logic_type,
            logic_content=group.logic_content,
            source_tables=group.source_tables,
            output_table=group.output_table,
            output_mode=group.output_mode,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by
        )

        self.db.add(history)
        self.db.commit()
```

#### 5.1.2 SQL验证服务

**文件**: `backend/services/fraudhunter/indicator_service/sql_validator.py`

```python
import re
from typing import Dict, List
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword

class SQLValidator:
    """SQL验证服务"""

    REQUIRED_FIELDS = {
        'account_id': 'STRING',
        'indicator_code': 'STRING',
        'indicator_value': 'STRING',
        'dt': 'STRING'
    }

    FORBIDDEN_KEYWORDS = [
        'DROP', 'TRUNCATE', 'DELETE', 'INSERT', 'UPDATE',
        'CREATE', 'ALTER', 'GRANT', 'REVOKE'
    ]

    def validate_sql(self, sql: str) -> Dict:
        """验证SQL语法和规范"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'extracted_fields': [],
            'extracted_tables': []
        }

        try:
            # 1. 基本格式验证
            if not sql or not sql.strip():
                result['valid'] = False
                result['errors'].append("SQL不能为空")
                return result

            # 2. 禁止危险操作
            sql_upper = sql.upper()
            for keyword in self.FORBIDDEN_KEYWORDS:
                if re.search(rf'\b{keyword}\b', sql_upper):
                    result['valid'] = False
                    result['errors'].append(f"禁止使用 {keyword} 操作")

            # 3. 解析SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                result['valid'] = False
                result['errors'].append("SQL解析失败")
                return result

            statement = parsed[0]

            # 4. 必须是SELECT语句
            if statement.get_type() != 'SELECT':
                result['valid'] = False
                result['errors'].append("只支持SELECT查询")
                return result

            # 5. 提取字段和表名
            result['extracted_fields'] = self._extract_fields(statement)
            result['extracted_tables'] = self._extract_tables(statement)

            # 6. 验证必需字段
            missing_fields = []
            for field in self.REQUIRED_FIELDS.keys():
                if field not in result['extracted_fields']:
                    missing_fields.append(field)

            if missing_fields:
                result['valid'] = False
                result['errors'].append(
                    f"缺少必需字段: {', '.join(missing_fields)}"
                )

            # 7. 警告检查
            if 'SELECT *' in sql_upper:
                result['warnings'].append("建议明确指定字段而不是使用 SELECT *")

        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"SQL验证异常: {str(e)}")

        return result

    def _extract_fields(self, statement) -> List[str]:
        """提取SELECT字段"""
        fields = []
        for token in statement.tokens:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    field_name = str(identifier).split()[-1]
                    fields.append(field_name.lower())
            elif isinstance(token, Identifier):
                field_name = str(token).split()[-1]
                fields.append(field_name.lower())
        return fields

    def _extract_tables(self, statement) -> List[str]:
        """提取表名"""
        tables = []
        from_seen = False
        for token in statement.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.append(str(identifier).split()[0])
                elif isinstance(token, Identifier):
                    tables.append(str(token).split()[0])
                elif token.ttype is Keyword:
                    break
            elif token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
        return tables
```

### 5.2 模型服务

#### 5.2.1 规则引擎服务

**文件**: `backend/services/fraudhunter/model_service/rule_engine.py`

```python
from typing import Dict, List
from enum import Enum

class LogicOperator(str, Enum):
    """逻辑操作符"""
    AND = "AND"
    OR = "OR"

class ComparisonOperator(str, Enum):
    """比较操作符"""
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "="
    NEQ = "!="

class RuleEngine:
    """规则引擎 - 解析和验证模型规则配置"""

    def validate_rule_config(self, rule_config: Dict) -> Dict:
        """验证规则配置"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'extracted_indicators': []
        }

        try:
            # 提取使用的指标
            indicators = self._extract_indicators(rule_config)
            result['extracted_indicators'] = list(set(indicators))

            # 验证规则结构
            self._validate_rule_structure(rule_config, result)

        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"规则验证异常: {str(e)}")

        return result

    def _extract_indicators(self, rule_config: Dict) -> List[str]:
        """递归提取规则中使用的指标"""
        indicators = []

        if 'rules' in rule_config:
            for rule in rule_config['rules']:
                if rule.get('type') == 'condition':
                    indicators.append(rule['indicator'])
                elif rule.get('type') == 'group':
                    indicators.extend(self._extract_indicators(rule))

        return indicators

    def _validate_rule_structure(self, rule_config: Dict, result: Dict):
        """验证规则结构"""
        # 验证logic字段
        if 'logic' in rule_config:
            if rule_config['logic'] not in [op.value for op in LogicOperator]:
                result['errors'].append(
                    f"无效的逻辑操作符: {rule_config['logic']}"
                )

        # 验证rules字段
        if 'rules' not in rule_config or not rule_config['rules']:
            result['errors'].append("规则配置中必须包含rules字段且不能为空")
            return

        # 递归验证子规则
        for i, rule in enumerate(rule_config['rules']):
            if rule.get('type') == 'condition':
                self._validate_condition(rule, i, result)
            elif rule.get('type') == 'group':
                self._validate_rule_structure(rule, result)
            else:
                result['errors'].append(
                    f"规则#{i}: 无效的规则类型 {rule.get('type')}"
                )

        # 验证output配置
        if 'output' in rule_config:
            self._validate_output(rule_config['output'], result)

    def _validate_condition(self, condition: Dict, index: int, result: Dict):
        """验证条件规则"""
        required_fields = ['indicator', 'operator', 'value']

        for field in required_fields:
            if field not in condition:
                result['errors'].append(
                    f"条件规则#{index}: 缺少必需字段 {field}"
                )

        # 验证操作符
        if 'operator' in condition:
            if condition['operator'] not in [op.value for op in ComparisonOperator]:
                result['errors'].append(
                    f"条件规则#{index}: 无效的比较操作符 {condition['operator']}"
                )

    def _validate_output(self, output: Dict, result: Dict):
        """验证输出配置"""
        required_fields = ['risk_level', 'risk_score']

        for field in required_fields:
            if field not in output:
                result['warnings'].append(f"输出配置中缺少建议字段: {field}")

        # 验证risk_level
        if 'risk_level' in output:
            valid_levels = ['low', 'medium', 'high', 'critical']
            if output['risk_level'] not in valid_levels:
                result['errors'].append(
                    f"无效的风险等级: {output['risk_level']}, "
                    f"有效值: {', '.join(valid_levels)}"
                )

        # 验证risk_score
        if 'risk_score' in output:
            score = output['risk_score']
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                result['errors'].append(
                    f"风险分数必须在0-100之间: {score}"
                )
```

### 5.3 异步任务服务

#### 5.3.1 任务管理器

**文件**: `backend/services/fraudhunter/task_service/task_manager.py`

```python
import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.fraudhunter.task import FraudHunterTaskExecution
from utils.logger import logger

class TaskManager:
    """异步任务管理器"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def submit_task(
        self,
        db: Session,
        task_type: str,
        task_id: int,
        task_func,
        created_by: str,
        **kwargs
    ) -> str:
        """提交异步任务"""
        # 生成任务ID
        execution_id = f"task_{uuid.uuid4()}"

        # 创建任务记录
        task_execution = FraudHunterTaskExecution(
            task_type=task_type,
            task_id=task_id,
            execution_id=execution_id,
            status='pending',
            created_by=created_by
        )

        db.add(task_execution)
        db.commit()

        # 创建异步任务
        task = asyncio.create_task(
            self._run_task(execution_id, task_func, **kwargs)
        )
        self.running_tasks[execution_id] = task

        logger.info(f"任务已提交: {execution_id}")
        return execution_id

    async def _run_task(self, execution_id: str, task_func, **kwargs):
        """执行任务"""
        from models.db_base import get_db_session

        with get_db_session() as db:
            try:
                # 更新任务状态为运行中
                task_execution = db.query(FraudHunterTaskExecution).filter(
                    FraudHunterTaskExecution.execution_id == execution_id
                ).first()

                task_execution.status = 'running'
                task_execution.start_time = datetime.now()
                db.commit()

                # 执行任务
                result = await task_func(db, execution_id, **kwargs)

                # 更新任务状态为成功
                task_execution.status = 'success'
                task_execution.end_time = datetime.now()
                task_execution.result_summary = result
                db.commit()

                logger.info(f"任务执行成功: {execution_id}")

            except Exception as e:
                # 更新任务状态为失败
                task_execution = db.query(FraudHunterTaskExecution).filter(
                    FraudHunterTaskExecution.execution_id == execution_id
                ).first()

                task_execution.status = 'failed'
                task_execution.end_time = datetime.now()
                task_execution.result_summary = {'error': str(e)}
                db.commit()

                logger.error(f"任务执行失败: {execution_id}, 错误: {str(e)}")

            finally:
                # 清理任务记录
                if execution_id in self.running_tasks:
                    del self.running_tasks[execution_id]

    def get_task_progress(self, db: Session, execution_id: str) -> Dict:
        """获取任务进度"""
        task_execution = db.query(FraudHunterTaskExecution).filter(
            FraudHunterTaskExecution.execution_id == execution_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {execution_id}")

        return {
            'task_id': execution_id,
            'task_type': task_execution.task_type,
            'status': task_execution.status,
            'start_time': task_execution.start_time,
            'end_time': task_execution.end_time
        }

    def get_task_result(self, db: Session, execution_id: str) -> Dict:
        """获取任务结果"""
        task_execution = db.query(FraudHunterTaskExecution).filter(
            FraudHunterTaskExecution.execution_id == execution_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {execution_id}")

        if task_execution.status not in ['success', 'failed']:
            raise ValueError(f"任务尚未完成: {execution_id}")

        return {
            'task_id': execution_id,
            'status': task_execution.status,
            'result': task_execution.result_summary
        }

    async def cancel_task(self, db: Session, execution_id: str) -> bool:
        """取消任务"""
        if execution_id in self.running_tasks:
            task = self.running_tasks[execution_id]
            task.cancel()

            # 更新任务状态
            task_execution = db.query(FraudHunterTaskExecution).filter(
                FraudHunterTaskExecution.execution_id == execution_id
            ).first()

            task_execution.status = 'cancelled'
            task_execution.end_time = datetime.now()
            db.commit()

            logger.info(f"任务已取消: {execution_id}")
            return True

        return False
```

---

## 6. 前端界面设计

### 6.1 页面路由规划

```
/fraudhunter
├── /indicator-groups              # 指标组管理
│   ├── /                         # 指标组列表
│   ├── /create                   # 创建指标组
│   └── /[id]                     # 指标组详情/编辑
├── /indicators                    # 指标管理
│   ├── /                         # 指标列表
│   ├── /create                   # 创建指标
│   └── /[id]                     # 指标详情/编辑
├── /models                        # 模型管理
│   ├── /                         # 模型列表
│   ├── /create                   # 创建模型
│   └── /[id]                     # 模型详情/编辑
└── /tasks                         # 任务管理
    ├── /                         # 任务列表
    └── /[id]                     # 任务详情
```

### 6.2 核心组件设计

#### 6.2.1 指标组表单组件

**文件**: `frontend/components/fraudhunter/indicator/IndicatorGroupForm.tsx`

```typescript
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { SQLEditor } from './SQLEditor'

interface IndicatorGroupFormProps {
  initialData?: IndicatorGroup
  onSubmit: (data: IndicatorGroupCreate) => Promise<void>
}

export function IndicatorGroupForm({ initialData, onSubmit }: IndicatorGroupFormProps) {
  const [formData, setFormData] = useState({
    group_code: initialData?.group_code || '',
    group_name: initialData?.group_name || '',
    description: initialData?.description || '',
    logic_content: initialData?.logic_content || '',
    source_tables: initialData?.source_tables || '',
    output_table: initialData?.output_table || 'anti_fraud.indicator_result_row'
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">指标组编码</label>
        <Input
          value={formData.group_code}
          onChange={(e) => setFormData({ ...formData, group_code: e.target.value })}
          placeholder="如: login_behavior"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">指标组名称</label>
        <Input
          value={formData.group_name}
          onChange={(e) => setFormData({ ...formData, group_name: e.target.value })}
          placeholder="如: 登录行为指标组"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">描述</label>
        <Textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={3}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">SQL加工逻辑</label>
        <SQLEditor
          value={formData.logic_content}
          onChange={(value) => setFormData({ ...formData, logic_content: value })}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">源表列表（逗号分隔）</label>
        <Input
          value={formData.source_tables}
          onChange={(e) => setFormData({ ...formData, source_tables: e.target.value })}
          placeholder="如: user_login,user_session"
        />
      </div>

      <div className="flex justify-end space-x-4">
        <Button type="button" variant="outline">取消</Button>
        <Button type="submit">保存</Button>
      </div>
    </form>
  )
}
```

#### 6.2.2 规则构建器组件

**文件**: `frontend/components/fraudhunter/model/RuleBuilder.tsx`

```typescript
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

interface Rule {
  type: 'condition' | 'group'
  indicator?: string
  operator?: string
  value?: number
  logic?: 'AND' | 'OR'
  rules?: Rule[]
}

interface RuleBuilderProps {
  value: Rule
  indicators: Indicator[]
  onChange: (rule: Rule) => void
}

export function RuleBuilder({ value, indicators, onChange }: RuleBuilderProps) {
  const addCondition = () => {
    const newRule: Rule = {
      type: 'condition',
      indicator: indicators[0]?.indicator_code || '',
      operator: '>',
      value: 0
    }

    onChange({
      ...value,
      rules: [...(value.rules || []), newRule]
    })
  }

  const addGroup = () => {
    const newGroup: Rule = {
      type: 'group',
      logic: 'AND',
      rules: []
    }

    onChange({
      ...value,
      rules: [...(value.rules || []), newGroup]
    })
  }

  const removeRule = (index: number) => {
    const newRules = [...(value.rules || [])]
    newRules.splice(index, 1)
    onChange({ ...value, rules: newRules })
  }

  const updateRule = (index: number, updatedRule: Rule) => {
    const newRules = [...(value.rules || [])]
    newRules[index] = updatedRule
    onChange({ ...value, rules: newRules })
  }

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">规则配置</h3>
          <Select
            value={value.logic}
            onChange={(e) => onChange({ ...value, logic: e.target.value as 'AND' | 'OR' })}
          >
            <option value="AND">AND（所有条件满足）</option>
            <option value="OR">OR（任一条件满足）</option>
          </Select>
        </div>

        <div className="space-y-2">
          {value.rules?.map((rule, index) => (
            <div key={index} className="flex items-start space-x-2">
              {rule.type === 'condition' ? (
                <ConditionRule
                  rule={rule}
                  indicators={indicators}
                  onChange={(updated) => updateRule(index, updated)}
                />
              ) : (
                <RuleBuilder
                  value={rule}
                  indicators={indicators}
                  onChange={(updated) => updateRule(index, updated)}
                />
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeRule(index)}
              >
                删除
              </Button>
            </div>
          ))}
        </div>

        <div className="flex space-x-2">
          <Button onClick={addCondition} variant="outline">添加条件</Button>
          <Button onClick={addGroup} variant="outline">添加规则组</Button>
        </div>
      </div>
    </Card>
  )
}

function ConditionRule({ rule, indicators, onChange }: any) {
  return (
    <div className="flex items-center space-x-2 flex-1">
      <Select
        value={rule.indicator}
        onChange={(e) => onChange({ ...rule, indicator: e.target.value })}
      >
        {indicators.map((ind: Indicator) => (
          <option key={ind.indicator_code} value={ind.indicator_code}>
            {ind.indicator_name}
          </option>
        ))}
      </Select>

      <Select
        value={rule.operator}
        onChange={(e) => onChange({ ...rule, operator: e.target.value })}
      >
        <option value=">">大于</option>
        <option value=">=">大于等于</option>
        <option value="<">小于</option>
        <option value="<=">小于等于</option>
        <option value="=">等于</option>
        <option value="!=">不等于</option>
      </Select>

      <Input
        type="number"
        value={rule.value}
        onChange={(e) => onChange({ ...rule, value: Number(e.target.value) })}
        className="w-32"
      />
    </div>
  )
}
```

#### 6.2.3 任务监控组件

**文件**: `frontend/components/fraudhunter/task/TaskMonitor.tsx`

```typescript
import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { taskService } from '@/lib/services/fraudhunter/taskService'

interface TaskMonitorProps {
  taskId: string
  onComplete?: (result: any) => void
}

export function TaskMonitor({ taskId, onComplete }: TaskMonitorProps) {
  const [progress, setProgress] = useState<any>(null)
  const [polling, setPolling] = useState(true)

  useEffect(() => {
    if (!polling) return

    const interval = setInterval(async () => {
      try {
        const data = await taskService.getTaskProgress(taskId)
        setProgress(data)

        if (data.status === 'success' || data.status === 'failed') {
          setPolling(false)
          if (data.status === 'success' && onComplete) {
            const result = await taskService.getTaskResult(taskId)
            onComplete(result)
          }
        }
      } catch (error) {
        console.error('获取任务进度失败:', error)
      }
    }, 2000) // 每2秒轮询一次

    return () => clearInterval(interval)
  }, [taskId, polling, onComplete])

  if (!progress) {
    return <div>加载中...</div>
  }

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">任务执行进度</h3>
          <span className={`px-2 py-1 rounded text-sm ${
            progress.status === 'success' ? 'bg-green-100 text-green-800' :
            progress.status === 'failed' ? 'bg-red-100 text-red-800' :
            progress.status === 'running' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {progress.status}
          </span>
        </div>

        {progress.status === 'running' && (
          <>
            <Progress value={progress.progress || 0} />
            <p className="text-sm text-gray-600">
              当前步骤: {progress.current_step}
            </p>
            {progress.estimated_remaining_seconds && (
              <p className="text-sm text-gray-600">
                预计剩余时间: {progress.estimated_remaining_seconds}秒
              </p>
            )}
          </>
        )}

        {progress.status === 'success' && (
          <div className="text-green-600">
            任务执行成功
          </div>
        )}

        {progress.status === 'failed' && (
          <div className="text-red-600">
            任务执行失败
          </div>
        )}
      </div>
    </Card>
  )
}
```

---

## 7. 可视化规则引擎

### 7.1 规则配置JSON格式

```json
{
  "logic": "AND",
  "rules": [
    {
      "type": "condition",
      "indicator": "i_login_cnt_7d",
      "operator": ">",
      "value": 10
    },
    {
      "type": "group",
      "logic": "OR",
      "rules": [
        {
          "type": "condition",
          "indicator": "i_device_change_cnt",
          "operator": ">=",
          "value": 3
        },
        {
          "type": "condition",
          "indicator": "i_ip_city_cnt",
          "operator": ">",
          "value": 5
        }
      ]
    }
  ],
  "output": {
    "risk_level": "high",
    "risk_score": 85,
    "action": "review"
  }
}
```

### 7.2 支持的操作符

**比较操作符**：
- `>` - 大于
- `>=` - 大于等于
- `<` - 小于
- `<=` - 小于等于
- `=` - 等于
- `!=` - 不等于

**逻辑操作符**：
- `AND` - 所有条件必须满足
- `OR` - 任一条件满足即可

### 7.3 指标数据类型约束

根据指标的`data_type`字段，不同类型的指标支持不同的操作符：

**numeric（数值型）**：
- 支持所有比较操作符

**enum（枚举型）**：
- 仅支持 `=` 和 `!=`
- 值必须在enum_values定义范围内

**boolean（布尔型）**：
- 仅支持 `=`
- 值为 true 或 false

**text（文本型）**：
- 支持 `=` 和 `!=`

---

## 8. 指标组与动态SQL

### 8.1 指标组设计理念

**核心思想**：一个SQL加工多个指标，减少重复计算

**实现方式**：
1. 多个指标关联到同一个指标组
2. 指标组中定义SQL加工逻辑
3. SQL执行一次，输出多个指标的结果

**SQL格式要求**：
```sql
SELECT
    account_id,              -- 必需字段：账户ID
    indicator_code,          -- 必需字段：指标编码
    indicator_value,         -- 必需字段：指标值
    dt                       -- 必需字段：数据日期
FROM
    (
        -- 子查询：实际的业务逻辑
        SELECT
            account_id,
            'i_login_cnt_7d' as indicator_code,
            COUNT(*) as indicator_value,
            CURRENT_DATE as dt
        FROM user_login
        WHERE login_date >= DATE_SUB(CURRENT_DATE, 7)
        GROUP BY account_id

        UNION ALL

        SELECT
            account_id,
            'i_login_device_cnt' as indicator_code,
            COUNT(DISTINCT device_id) as indicator_value,
            CURRENT_DATE as dt
        FROM user_login
        WHERE login_date >= DATE_SUB(CURRENT_DATE, 7)
        GROUP BY account_id
    ) t
```

### 8.2 宽表动态生成

**生成逻辑**：
1. 从行存表中读取最新分区的数据
2. 使用PIVOT操作将行转列
3. 写入宽表

**示例SQL**：
```sql
INSERT OVERWRITE TABLE anti_fraud.indicator_result_wide PARTITION(dt='${etl_date}')
SELECT
    account_id,
    MAX(CASE WHEN indicator_code = 'i_login_cnt_7d' THEN indicator_value END) as i_login_cnt_7d,
    MAX(CASE WHEN indicator_code = 'i_login_device_cnt' THEN indicator_value END) as i_login_device_cnt,
    MAX(CASE WHEN indicator_code = 'i_trans_amt_1d' THEN indicator_value END) as i_trans_amt_1d,
    CURRENT_TIMESTAMP as calculate_time
FROM anti_fraud.indicator_result_row
WHERE dt = '${etl_date}'
GROUP BY account_id
```

---

## 9. 异步任务执行机制

### 9.1 任务执行流程

```
1. 前端提交任务请求
   ↓
2. 后端创建任务记录（状态: pending）
   ↓
3. 后端返回task_id给前端
   ↓
4. 后端异步执行任务
   ├── 更新状态为 running
   ├── 执行业务逻辑
   └── 更新状态为 success/failed
   ↓
5. 前端轮询任务进度
   ↓
6. 任务完成后获取结果
```

### 9.2 前端轮询策略

**轮询间隔**：
- 初始间隔：2秒
- 如果任务运行超过1分钟，间隔调整为5秒
- 如果任务运行超过5分钟，间隔调整为10秒

**超时策略**：
- 默认超时时间：30分钟
- 超时后提示用户，但不自动取消任务

**示例代码**：
```typescript
async function pollTaskProgress(taskId: string) {
  let interval = 2000
  const startTime = Date.now()

  while (true) {
    const progress = await taskService.getTaskProgress(taskId)

    if (progress.status === 'success' || progress.status === 'failed') {
      return progress
    }

    // 动态调整轮询间隔
    const elapsed = Date.now() - startTime
    if (elapsed > 5 * 60 * 1000) {
      interval = 10000
    } else if (elapsed > 60 * 1000) {
      interval = 5000
    }

    await new Promise(resolve => setTimeout(resolve, interval))
  }
}
```

---

## 10. 部署架构

### 10.1 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 业务人员  │  │ 数据分析师│  │ 开发人员 │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
└───────┼────────────┼────────────┼─────────────────────────┘
        │            │            │
        └────────────┴────────────┘
                     │
        ┌────────────▼────────────┐
        │     Nginx (反向代理)     │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐     ┌─────────▼────────┐
│  Next.js前端   │     │  FastAPI后端     │
│  (端口: 3000)  │     │  (端口: 50020)   │
└────────────────┘     └─────────┬────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
        ┌───────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
        │    MySQL     │  │  Qdrant   │  │   Spark     │
        │  (元数据)    │  │  (向量)   │  │ ThriftServer│
        └──────────────┘  └───────────┘  └──────┬──────┘
                                                 │
                                         ┌───────▼───────┐
                                         │     Hive      │
                                         │   (数据仓库)  │
                                         └───────────────┘
```

### 10.2 Docker部署配置

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  # 前端服务
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_BASE=/api/taosha/v1
    depends_on:
      - backend

  # 后端服务
  backend:
    build: ./backend
    ports:
      - "50020:50020"
    environment:
      - DATABASE_URL=mysql+pymysql://user:password@mysql:3306/fraudhunter
      - QDRANT_URL=http://qdrant:6333
      - SPARK_JDBC_URL=jdbc:hive2://spark-thrift:10000
    depends_on:
      - mysql
      - qdrant
    volumes:
      - ./backend:/app
      - ./config:/app/config

  # MySQL数据库
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=fraudhunter
      - MYSQL_USER=user
      - MYSQL_PASSWORD=password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  # Qdrant向量数据库
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  mysql_data:
  qdrant_data:
```

---

## 11. 开发路线图

### MVP阶段开发计划

#### 第二周：指标组功能开发
- **Day 1-2**: 指标组管理
  - 实现指标组CRUD接口
  - 实现SQL验证服务
  - 开发指标组表单组件

- **Day 3-4**: 指标定义
  - 实现指标CRUD接口
  - 实现版本管理功能
  - 开发指标管理界面

- **Day 5**: 指标试运行
  - 实现异步任务框架
  - 实现指标试运行功能
  - 开发任务监控组件

#### 第三周：模型功能开发
- **Day 1-2**: 规则引擎
  - 实现规则验证服务
  - 开发规则构建器组件
  - 实现规则解析逻辑

- **Day 3-4**: 模型管理
  - 实现模型CRUD接口
  - 实现代码生成服务
  - 开发模型管理界面

- **Day 5**: 模型试运行
  - 实现模型试运行功能
  - 开发结果展示组件
  - 实现结果数据可视化

#### 第四周：任务调度与集成
- **Day 1-2**: DolphinScheduler集成
  - 实现DS客户端
  - 实现任务发布功能
  - 实现任务状态同步

- **Day 3-4**: 完善异步任务
  - 优化任务执行流程
  - 实现任务日志记录
  - 开发任务历史查询

- **Day 5**: 测试与优化
  - 功能测试
  - 性能优化
  - Bug修复

### 功能优先级

**P0（必须完成）**：
- ✅ 指标组CRUD
- ✅ 指标CRUD
- ✅ 版本管理
- ✅ SQL验证
- ✅ 指标试运行
- ✅ 模型CRUD
- ✅ 规则引擎
- ✅ 模型试运行
- ✅ 异步任务执行

**P1（重要功能）**：
- 🔲 DolphinScheduler集成
- 🔲 任务执行历史查询
- 🔲 代码生成优化
- 🔲 结果数据可视化

**P2（可延后）**：
- 🔲 PySpark代码支持
- 🔲 实时指标监控
- 🔲 指标血缘分析
- 🔲 模型A/B测试

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| 指标组 | 一组共享相同SQL加工逻辑的指标集合 |
| 指标 | 单个业务度量值，如"7天登录次数" |
| 模型 | 基于多个指标的规则组合，用于风险判断 |
| 规则引擎 | 解析和执行模型规则的系统组件 |
| 试运行 | 在正式发布前，使用样本数据验证逻辑正确性 |
| 版本管理 | 记录和追溯配置变更历史 |
| 异步任务 | 后台执行的长时任务，不阻塞前端响应 |

### B. 参考文档

- **FastAPI官方文档**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0文档**: https://docs.sqlalchemy.org/
- **Next.js官方文档**: https://nextjs.org/docs
- **DolphinScheduler API**: https://dolphinscheduler.apache.org/
- **PySpark官方文档**: https://spark.apache.org/docs/latest/api/python/

---

**文档结束**
