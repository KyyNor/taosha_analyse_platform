# 反诈指标与模型管理系统设计文档

## 文档版本
- **版本**: v1.0.0
- **创建日期**: 2025-12-02
- **作者**: Claude Code
- **状态**: 设计阶段

---

## 目录
1. [项目概述](#1-项目概述)
2. [核心问题与解决方案](#2-核心问题与解决方案)
3. [系统架构设计](#3-系统架构设计)
4. [数据库模型设计](#4-数据库模型设计)
5. [后端API设计](#5-后端api设计)
6. [服务层架构](#6-服务层架构)
7. [前端界面设计](#7-前端界面设计)
8. [可视化规则引擎](#8-可视化规则引擎)
9. [指标组与动态SQL](#9-指标组与动态sql)
10. [PySpark Streaming任务生成](#10-pyspark-streaming任务生成)
11. [回测功能设计](#11-回测功能设计)
12. [任务调度集成](#12-任务调度集成)
13. [部署架构](#13-部署架构)
14. [开发路线图](#14-开发路线图)

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
- 实现指标组概念，减少重复计算
- 提供可视化模型定义能力，让业务人员也能定义简单模型
- 支持模型回测和历史数据验证
- 自动生成调度任务和PySpark Streaming代码

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
- ✅ 指标组概念（批量计算多个指标）
- ✅ 指标试运行和结果预览
- ✅ 简化版可视化模型定义（规则引擎方式）
- ✅ 模型回测功能（批量历史数据验证）
- ✅ DolphinScheduler任务集成

**第二阶段（扩展）**：
- ⏳ PySpark代码支持（复杂指标计算）
- ⏳ 实时指标监控和告警
- ⏳ 模型A/B测试
- ⏳ 指标血缘分析

---

## 2. 核心问题与解决方案

### 2.1 问题1：指标定义方式

**问题**：是否需要同时支持SQL和PySpark两种定义方式？

**解决方案**：MVP阶段仅支持SQL

**理由**：
```
┌─────────────────────────────────────────────────────────────┐
│  90%+ 的指标场景    →  SQL完全可以覆盖                        │
│  复杂指标(如ML特征) →  初期可以先手动开发，后续再系统化         │
│  开发成本           →  只支持SQL可节省约40%开发工作量           │
└─────────────────────────────────────────────────────────────┘
```

**技术实现**：
- 预留 `logic_type` 字段（sql/pyspark），但第一版只实现SQL解析和执行
- 使用Spark SQL的ThriftServer JDBC接口执行SQL
- 通过正则表达式和SQL解析库验证SQL语法

### 2.2 问题2：冗余计算优化

**问题**：多个指标从同一张表计算会导致重复扫描和计算

**解决方案**：采用"指标组"概念

**方案对比**：
```
┌────────────────┬─────────────┬─────────────┬──────────────┐
│     方案       │  开发复杂度  │  运行效率   │    推荐度    │
├────────────────┼─────────────┼─────────────┼──────────────┤
│ 1.智能SQL合并  │    高        │    高       │    ❌        │
│ 2.指标组批量   │    中        │    中高     │    ✅        │
│ 3.物化中间表   │    低        │    中       │    ✅        │
│ 4.不处理冗余   │    最低      │    低       │    初期可接受 │
└────────────────┴─────────────┴─────────────┴──────────────┘
```

**技术实现**：
- 定义指标时可选择归属指标组
- 同一指标组的多个指标共享一个SQL查询
- SQL格式要求：`SELECT account_id, indicator_code, indicator_value, dt FROM ...`
- 系统自动识别指标组并批量执行

### 2.3 问题3：模型可视化定义

**问题**：能否让业务人员自己定义模型？

**解决方案**：实现简化版规则引擎（非复杂拖拽式）

**设计理念**：
```
简化版可视化 = 规则引擎（非复杂拖拽式）
业务人员能做的：选指标 → 定阈值 → 选关系 → 生成模型
开发人员只需：维护指标库 + 处理复杂模型
```

**技术实现**：
- JSON配置格式存储规则定义
- 支持AND/OR逻辑组合
- 支持常见比较操作符（>、>=、<、<=、=、!=）
- 前端提供表单式配置界面（而非拖拽式）
- 后端根据JSON配置生成PySpark Streaming代码

---

## 3. 系统架构设计

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    反诈指标模型管理系统                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  指标管理    │  │  模型管理   │  │      任务管理           │  │
│  │             │  │             │  │                         │  │
│  │ ·离线指标   │  │ ·规则定义   │  │ ·DS任务生成             │  │
│  │ ·实时指标   │  │ ·可视化配置 │  │ ·任务状态监控           │  │
│  │ ·指标组     │  │ ·回测功能   │  │ ·Streaming任务管理      │  │
│  │ ·试运行     │  │             │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
├─────────┴────────────────┴─────────────────────┴────────────────┤
│                         核心服务层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SQL解析引擎 │  │ 代码生成器  │  │    调度集成服务          │  │
│  │             │  │             │  │                         │  │
│  │ ·语法校验   │  │ ·指标SQL    │  │ ·DS REST API            │  │
│  │ ·字段提取   │  │ ·PySpark    │  │ ·任务DAG生成            │  │
│  │ ·依赖分析   │  │   Streaming │  │                         │  │
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

### 3.2 技术栈选型

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

### 3.3 模块划分

**后端模块**：
```
backend/
├── api/                              # API路由层
│   ├── indicator_routes.py          # 指标管理API
│   ├── model_routes.py               # 模型管理API
│   ├── task_routes.py                # 任务管理API
│   └── backtest_routes.py            # 回测API
├── services/                         # 服务层
│   ├── indicator_service/            # 指标服务
│   │   ├── indicator_manager.py     # 指标CRUD
│   │   ├── indicator_executor.py    # 指标执行
│   │   ├── indicator_group_manager.py # 指标组管理
│   │   └── sql_validator.py         # SQL验证
│   ├── model_service/                # 模型服务
│   │   ├── model_manager.py         # 模型CRUD
│   │   ├── rule_engine.py           # 规则引擎
│   │   ├── code_generator.py        # 代码生成
│   │   └── backtest_service.py      # 回测服务
│   ├── scheduler_service/            # 调度服务
│   │   ├── dolphin_client.py        # DS客户端
│   │   └── task_manager.py          # 任务管理
│   └── spark_service/                # Spark服务
│       ├── spark_jdbc_client.py     # JDBC客户端
│       └── streaming_deployer.py    # Streaming部署
├── models/                           # 数据模型
│   ├── indicator.py                  # 指标模型
│   ├── model.py                      # 模型模型
│   ├── task.py                       # 任务模型
│   └── execution.py                  # 执行记录
└── utils/                            # 工具类
    ├── sql_parser.py                 # SQL解析
    ├── template_engine.py            # 模板引擎
    └── validator.py                  # 验证器
```

**前端模块**：
```
frontend/
├── app/(main)/
│   ├── indicators/                   # 指标管理页面
│   │   ├── page.tsx                 # 指标列表
│   │   ├── [id]/page.tsx            # 指标详情/编辑
│   │   └── create/page.tsx          # 创建指标
│   ├── models/                       # 模型管理页面
│   │   ├── page.tsx                 # 模型列表
│   │   ├── [id]/page.tsx            # 模型详情/编辑
│   │   └── create/page.tsx          # 创建模型
│   ├── tasks/                        # 任务管理页面
│   │   ├── page.tsx                 # 任务列表
│   │   └── [id]/page.tsx            # 任务详情
│   └── backtest/                     # 回测页面
│       └── [modelId]/page.tsx       # 模型回测
├── components/
│   ├── indicator/                    # 指标相关组件
│   │   ├── IndicatorForm.tsx        # 指标表单
│   │   ├── SQLEditor.tsx            # SQL编辑器
│   │   ├── IndicatorPreview.tsx     # 指标预览
│   │   └── IndicatorGroupSelector.tsx # 指标组选择
│   ├── model/                        # 模型相关组件
│   │   ├── RuleBuilder.tsx          # 规则构建器
│   │   ├── RulePreview.tsx          # 规则预览
│   │   └── ModelDashboard.tsx       # 模型仪表板
│   └── task/                         # 任务相关组件
│       ├── TaskList.tsx             # 任务列表
│       └── TaskMonitor.tsx          # 任务监控
└── lib/
    ├── services/
    │   ├── indicatorService.ts      # 指标服务
    │   ├── modelService.ts          # 模型服务
    │   └── taskService.ts           # 任务服务
    └── types/
        ├── indicator.ts             # 指标类型
        ├── model.ts                 # 模型类型
        └── task.ts                  # 任务类型
```

---

## 4. 数据库模型设计

### 4.1 元数据存储（MySQL）

#### 4.1.1 指标定义表

```sql
-- 指标定义表
CREATE TABLE af_indicator_definition (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    indicator_code VARCHAR(64) NOT NULL UNIQUE COMMENT '指标编码，如 i_login_cnt_7d',
    indicator_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    indicator_type VARCHAR(16) NOT NULL COMMENT '指标类型：offline/realtime',
    description TEXT COMMENT '指标描述',

    -- 加工逻辑
    logic_type VARCHAR(16) DEFAULT 'sql' COMMENT '逻辑类型：sql/pyspark（预留）',
    logic_content TEXT NOT NULL COMMENT 'SQL内容或代码',

    -- 指标组（解决冗余计算）
    indicator_group VARCHAR(64) COMMENT '指标组编码，同组指标可合并计算',
    source_tables VARCHAR(512) COMMENT '依赖的源表列表，逗号分隔',

    -- 输出约束
    key_column VARCHAR(64) DEFAULT 'account_id' COMMENT '主键列名',
    value_column VARCHAR(64) DEFAULT 'indicator_value' COMMENT '指标值列名',

    -- 调度配置
    schedule_type VARCHAR(16) DEFAULT 'daily' COMMENT '调度类型：daily/hourly/realtime',
    schedule_cron VARCHAR(64) COMMENT '调度周期cron表达式',
    ds_task_id BIGINT COMMENT 'DolphinScheduler任务ID',

    -- 输出配置
    output_table VARCHAR(128) COMMENT '输出表名',
    output_partition_field VARCHAR(64) DEFAULT 'dt' COMMENT '分区字段',

    -- 状态管理
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态：draft/testing/online/offline/archived',
    version INT DEFAULT 1 COMMENT '版本号',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_indicator_code (indicator_code),
    INDEX idx_indicator_group (indicator_group),
    INDEX idx_status (status),
    INDEX idx_indicator_type (indicator_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标定义表';
```

#### 4.1.2 模型定义表

```sql
-- 模型定义表
CREATE TABLE af_model_definition (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    model_code VARCHAR(64) NOT NULL UNIQUE COMMENT '模型编码',
    model_name VARCHAR(128) NOT NULL COMMENT '模型名称',
    model_type VARCHAR(16) DEFAULT 'rule_based' COMMENT '模型类型：rule_based/ml_based（预留）',
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

    -- 实时流配置
    stream_source VARCHAR(256) COMMENT 'Kafka topic',
    stream_consumer_group VARCHAR(128) COMMENT 'Kafka消费者组',
    window_type VARCHAR(16) COMMENT '窗口类型：tumbling/sliding/session',
    window_seconds INT DEFAULT 0 COMMENT '窗口大小（秒），0表示无窗口',

    -- 输出配置
    output_table VARCHAR(128) COMMENT '输出表名',
    output_partition_field VARCHAR(64) DEFAULT 'dt' COMMENT '分区字段',

    -- 生成的代码（系统自动生成）
    generated_code TEXT COMMENT '生成的PySpark代码',
    code_version INT DEFAULT 1 COMMENT '代码版本',

    -- 调度配置
    ds_task_id BIGINT COMMENT 'DolphinScheduler任务ID（实时模型用于监控任务）',

    -- 状态管理
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态：draft/testing/online/offline/archived',

    -- 性能指标（回测后填充）
    backtest_precision DECIMAL(5,4) COMMENT '回测精确率',
    backtest_recall DECIMAL(5,4) COMMENT '回测召回率',
    backtest_f1_score DECIMAL(5,4) COMMENT '回测F1分数',
    last_backtest_time TIMESTAMP COMMENT '最后回测时间',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_model_code (model_code),
    INDEX idx_status (status),
    INDEX idx_model_type (model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型定义表';
```

#### 4.1.3 指标组定义表

```sql
-- 指标组定义表
CREATE TABLE af_indicator_group (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    group_code VARCHAR(64) NOT NULL UNIQUE COMMENT '指标组编码',
    group_name VARCHAR(128) NOT NULL COMMENT '指标组名称',
    description TEXT COMMENT '描述',

    -- 数据源配置
    source_tables VARCHAR(512) COMMENT '共享的源表列表',
    base_sql TEXT COMMENT '基础查询SQL（可选，用于预处理）',

    -- 输出配置
    output_table VARCHAR(128) COMMENT '输出表名',
    output_mode VARCHAR(16) DEFAULT 'row' COMMENT '输出模式：row/wide',

    -- 调度配置
    schedule_type VARCHAR(16) DEFAULT 'daily' COMMENT '调度类型',
    schedule_cron VARCHAR(64) COMMENT '调度周期',
    ds_task_id BIGINT COMMENT 'DolphinScheduler任务ID',

    -- 状态
    status VARCHAR(16) DEFAULT 'draft' COMMENT '状态',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_group_code (group_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指标组定义表';
```

#### 4.1.4 任务执行记录表

```sql
-- 任务执行记录表
CREATE TABLE af_task_execution (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_type VARCHAR(32) NOT NULL COMMENT '任务类型：indicator/model/backtest',
    task_id VARCHAR(128) NOT NULL COMMENT '任务标识（指标/模型的ID或代码）',
    execution_id VARCHAR(64) NOT NULL UNIQUE COMMENT '执行ID（UUID）',

    -- 执行信息
    execution_type VARCHAR(16) COMMENT '执行类型：scheduled/manual/backtest',
    start_time TIMESTAMP COMMENT '开始时间',
    end_time TIMESTAMP COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长（秒）',

    -- 状态
    status VARCHAR(16) DEFAULT 'running' COMMENT '状态：running/success/failed/cancelled',
    error_message TEXT COMMENT '错误信息',

    -- 执行参数
    parameters JSON COMMENT '执行参数（分区、配置等）',

    -- 执行结果
    result_summary JSON COMMENT '结果摘要（处理记录数、命中数等）',

    -- 资源使用
    spark_app_id VARCHAR(128) COMMENT 'Spark Application ID',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '触发人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_task_type_id (task_type, task_id),
    INDEX idx_execution_id (execution_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行记录表';
```

#### 4.1.5 回测记录表

```sql
-- 回测记录表
CREATE TABLE af_backtest_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    backtest_id VARCHAR(64) NOT NULL UNIQUE COMMENT '回测ID（UUID）',
    model_id BIGINT NOT NULL COMMENT '模型ID',
    model_code VARCHAR(64) NOT NULL COMMENT '模型编码',

    -- 回测配置
    start_date DATE NOT NULL COMMENT '回测开始日期',
    end_date DATE NOT NULL COMMENT '回测结束日期',
    sample_size INT COMMENT '样本数量',

    -- 回测结果
    total_records INT COMMENT '总记录数',
    hit_records INT COMMENT '命中记录数',
    true_positive INT COMMENT '真阳性',
    false_positive INT COMMENT '假阳性',
    true_negative INT COMMENT '真阴性',
    false_negative INT COMMENT '假阴性',

    -- 性能指标
    precision_score DECIMAL(5,4) COMMENT '精确率',
    recall_score DECIMAL(5,4) COMMENT '召回率',
    f1_score DECIMAL(5,4) COMMENT 'F1分数',
    accuracy_score DECIMAL(5,4) COMMENT '准确率',

    -- 执行信息
    execution_id VARCHAR(64) COMMENT '关联的执行ID',
    start_time TIMESTAMP COMMENT '开始时间',
    end_time TIMESTAMP COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长',

    -- 状态
    status VARCHAR(16) DEFAULT 'running' COMMENT '状态',
    error_message TEXT COMMENT '错误信息',

    -- 结果详情
    result_detail JSON COMMENT '详细结果（样本数据、混淆矩阵等）',

    -- 审计字段
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_model_id (model_id),
    INDEX idx_backtest_id (backtest_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测记录表';
```

### 4.2 数据层存储（Hive）

#### 4.2.1 指标结果表（行存格式）

```sql
-- Hive表：指标结果表（行存储）
CREATE TABLE IF NOT EXISTS anti_fraud.indicator_result_row (
    account_id STRING COMMENT '账户ID',
    indicator_code STRING COMMENT '指标编码',
    indicator_value STRING COMMENT '指标值',
    indicator_type STRING COMMENT '指标类型（数值/字符串/布尔）',
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

#### 4.2.2 指标宽表（动态生成）

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

#### 4.2.3 模型命中结果表

```sql
-- Hive表：模型命中结果表
CREATE TABLE IF NOT EXISTS anti_fraud.model_hit_result (
    hit_id STRING COMMENT '命中ID（UUID）',
    account_id STRING COMMENT '账户ID',
    model_code STRING COMMENT '模型编码',
    hit_time TIMESTAMP COMMENT '命中时间',

    -- 风险评估
    risk_level STRING COMMENT '风险等级：low/medium/high/critical',
    risk_score INT COMMENT '风险分数 0-100',

    -- 命中详情
    hit_reason STRING COMMENT '命中原因（JSON格式）',
    /*
    示例：
    {
      "matched_rules": [
        {
          "indicator": "i_login_cnt_7d",
          "expected": "> 10",
          "actual": 15
        },
        {
          "indicator": "i_trans_amt_1d",
          "expected": "> 50000",
          "actual": 65000.00
        }
      ]
    }
    */

    -- 指标快照
    indicator_snapshot STRING COMMENT '命中时的指标快照（JSON格式）',

    -- 处理建议
    suggested_action STRING COMMENT '建议操作：alert/review/block',

    -- 数据日期
    data_date DATE COMMENT '数据日期',

    -- 元数据
    model_version INT COMMENT '模型版本',
    stream_timestamp TIMESTAMP COMMENT '流处理时间戳'
)
PARTITIONED BY (dt STRING COMMENT '分区日期 YYYYMMDD')
STORED AS PARQUET
LOCATION '/user/hive/warehouse/anti_fraud.db/model_hit_result'
TBLPROPERTIES (
    'parquet.compression'='snappy',
    'description'='反诈模型命中结果表'
);
```

---

## 5. 后端API设计

### 5.1 API路由规范

**基础路径**: `/api/taosha/v1/anti-fraud`

**路由组织**:
```
/api/taosha/v1/anti-fraud
├── /indicators              # 指标管理
├── /indicator-groups        # 指标组管理
├── /models                  # 模型管理
├── /tasks                   # 任务管理
└── /backtest                # 回测功能
```

### 5.2 指标管理API

#### 5.2.1 创建指标

```http
POST /api/taosha/v1/anti-fraud/indicators
Content-Type: application/json

{
  "indicator_code": "i_login_cnt_7d",
  "indicator_name": "7天登录次数",
  "indicator_type": "offline",
  "description": "统计账户最近7天的登录次数",
  "logic_type": "sql",
  "logic_content": "SELECT account_id, 'i_login_cnt_7d' as indicator_code, COUNT(DISTINCT login_date) as indicator_value, CURRENT_DATE as dt FROM user_login WHERE login_date >= DATE_SUB(CURRENT_DATE, 7) GROUP BY account_id",
  "indicator_group": "login_behavior",
  "source_tables": "user_login",
  "schedule_type": "daily",
  "schedule_cron": "0 2 * * *",
  "output_table": "anti_fraud.indicator_result_row"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "indicator_code": "i_login_cnt_7d",
    "status": "draft",
    "version": 1,
    "created_at": "2025-12-02T10:00:00Z"
  }
}
```

#### 5.2.2 试运行指标

```http
POST /api/taosha/v1/anti-fraud/indicators/{id}/dry-run
Content-Type: application/json

{
  "sample_size": 100,
  "partition": "20251201"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "success",
    "duration_seconds": 5.2,
    "sample_result": [
      {
        "account_id": "ACC001",
        "indicator_code": "i_login_cnt_7d",
        "indicator_value": "5",
        "dt": "20251201"
      },
      {
        "account_id": "ACC002",
        "indicator_code": "i_login_cnt_7d",
        "indicator_value": "12",
        "dt": "20251201"
      }
    ],
    "total_records": 10000,
    "validation": {
      "has_required_fields": true,
      "field_types_correct": true,
      "warnings": []
    }
  }
}
```

#### 5.2.3 发布指标到DolphinScheduler

```http
POST /api/taosha/v1/anti-fraud/indicators/{id}/publish
Content-Type: application/json

{
  "project_name": "anti_fraud",
  "workflow_name": "indicator_calculation"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "indicator_id": 1,
    "ds_task_id": 12345,
    "ds_task_code": "indicator_i_login_cnt_7d",
    "workflow_instance_id": 67890,
    "status": "online",
    "schedule_url": "http://dolphinscheduler:12345/dolphinscheduler/projects/1/workflow/definition/67890"
  }
}
```

#### 5.2.4 查询指标列表

```http
GET /api/taosha/v1/anti-fraud/indicators?page=1&page_size=20&status=online&indicator_type=offline&indicator_group=login_behavior
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
        "indicator_group": "login_behavior",
        "status": "online",
        "ds_task_id": 12345,
        "last_execution_time": "2025-12-02T02:00:00Z",
        "last_execution_status": "success",
        "created_at": "2025-11-01T10:00:00Z"
      }
    ]
  }
}
```

#### 5.2.5 获取指标详情

```http
GET /api/taosha/v1/anti-fraud/indicators/{id}
```

#### 5.2.6 更新指标

```http
PUT /api/taosha/v1/anti-fraud/indicators/{id}
Content-Type: application/json

{
  "description": "更新后的描述",
  "logic_content": "更新后的SQL"
}
```

#### 5.2.7 删除指标

```http
DELETE /api/taosha/v1/anti-fraud/indicators/{id}
```

### 5.3 指标组管理API

#### 5.3.1 创建指标组

```http
POST /api/taosha/v1/anti-fraud/indicator-groups
Content-Type: application/json

{
  "group_code": "login_behavior",
  "group_name": "登录行为指标组",
  "description": "统计用户登录相关的多个指标",
  "source_tables": "user_login,user_session",
  "output_table": "anti_fraud.indicator_result_row",
  "output_mode": "row",
  "schedule_type": "daily",
  "schedule_cron": "0 2 * * *"
}
```

#### 5.3.2 为指标组添加指标

```http
POST /api/taosha/v1/anti-fraud/indicator-groups/{group_id}/indicators
Content-Type: application/json

{
  "indicator_ids": [1, 2, 3]
}
```

#### 5.3.3 批量执行指标组

```http
POST /api/taosha/v1/anti-fraud/indicator-groups/{group_id}/execute
Content-Type: application/json

{
  "partition": "20251201",
  "dry_run": false
}
```

### 5.4 模型管理API

#### 5.4.1 创建模型

```http
POST /api/taosha/v1/anti-fraud/models
Content-Type: application/json

{
  "model_code": "m_high_risk_login",
  "model_name": "高风险登录模型",
  "model_type": "rule_based",
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
  "stream_source": "kafka_topic_user_events",
  "stream_consumer_group": "anti_fraud_model_consumer",
  "output_table": "anti_fraud.model_hit_result"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "model_code": "m_high_risk_login",
    "status": "draft",
    "generated_code": "# PySpark Streaming代码（自动生成）\nfrom pyspark.sql import SparkSession\n...",
    "code_version": 1,
    "created_at": "2025-12-02T10:00:00Z"
  }
}
```

#### 5.4.2 生成模型代码

```http
POST /api/taosha/v1/anti-fraud/models/{id}/generate-code
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
    "code_path": "/opt/spark/jobs/anti_fraud_m_high_risk_login_v2.py"
  }
}
```

#### 5.4.3 发布模型（部署Streaming任务）

```http
POST /api/taosha/v1/anti-fraud/models/{id}/publish
Content-Type: application/json

{
  "deployment_mode": "cluster",
  "executor_memory": "4g",
  "executor_cores": 2,
  "num_executors": 3
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "model_id": 1,
    "spark_app_id": "app-20251202100000-0001",
    "ds_task_id": 23456,
    "status": "online",
    "monitoring_url": "http://spark-master:8080/app/app-20251202100000-0001"
  }
}
```

### 5.5 回测功能API

#### 5.5.1 创建回测任务

```http
POST /api/taosha/v1/anti-fraud/backtest
Content-Type: application/json

{
  "model_id": 1,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "sample_size": 10000,
  "ground_truth_table": "anti_fraud.labeled_fraud_cases",
  "ground_truth_key": "account_id",
  "ground_truth_label": "is_fraud"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "backtest_id": "bt_550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "execution_id": "exec_660f9511-f3ac-52e5-b827-557766551111"
  }
}
```

#### 5.5.2 查询回测进度

```http
GET /api/taosha/v1/anti-fraud/backtest/{backtest_id}/progress
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "backtest_id": "bt_550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "progress": 65.5,
    "current_date": "2025-11-20",
    "total_days": 30,
    "processed_days": 19,
    "estimated_remaining_seconds": 120
  }
}
```

#### 5.5.3 获取回测结果

```http
GET /api/taosha/v1/anti-fraud/backtest/{backtest_id}/result
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "backtest_id": "bt_550e8400-e29b-41d4-a716-446655440000",
    "model_id": 1,
    "model_code": "m_high_risk_login",
    "status": "success",
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "duration_seconds": 450,
    "metrics": {
      "total_records": 10000,
      "hit_records": 856,
      "true_positive": 732,
      "false_positive": 124,
      "true_negative": 8956,
      "false_negative": 188,
      "precision": 0.8552,
      "recall": 0.7957,
      "f1_score": 0.8244,
      "accuracy": 0.9688
    },
    "confusion_matrix": {
      "tp": 732,
      "fp": 124,
      "tn": 8956,
      "fn": 188
    },
    "daily_metrics": [
      {
        "date": "2025-11-01",
        "hit_count": 28,
        "precision": 0.8571,
        "recall": 0.8000
      }
    ]
  }
}
```

### 5.6 任务管理API

#### 5.6.1 查询任务执行历史

```http
GET /api/taosha/v1/anti-fraud/tasks/executions?task_type=indicator&task_id=1&page=1&page_size=20
```

#### 5.6.2 查询任务执行详情

```http
GET /api/taosha/v1/anti-fraud/tasks/executions/{execution_id}
```

#### 5.6.3 手动触发任务执行

```http
POST /api/taosha/v1/anti-fraud/tasks/trigger
Content-Type: application/json

{
  "task_type": "indicator",
  "task_id": "1",
  "parameters": {
    "partition": "20251201"
  }
}
```

---

## 6. 服务层架构

### 6.1 指标服务

#### 6.1.1 指标管理服务

**文件**: `backend/services/indicator_service/indicator_manager.py`

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.indicator import AFIndicatorDefinition
from backend.schemas.indicator import IndicatorCreate, IndicatorUpdate
from backend.utils.logger import logger

class IndicatorManager:
    """指标管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_indicator(
        self,
        indicator_data: IndicatorCreate,
        created_by: str
    ) -> AFIndicatorDefinition:
        """创建指标"""
        # 验证指标编码唯一性
        existing = self.db.query(AFIndicatorDefinition).filter(
            AFIndicatorDefinition.indicator_code == indicator_data.indicator_code
        ).first()

        if existing:
            raise ValueError(f"指标编码已存在: {indicator_data.indicator_code}")

        # 创建指标记录
        db_indicator = AFIndicatorDefinition(
            **indicator_data.model_dump(),
            created_by=created_by,
            status='draft'
        )

        self.db.add(db_indicator)
        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"创建指标成功: {db_indicator.indicator_code}")
        return db_indicator

    def get_indicator(self, indicator_id: int) -> Optional[AFIndicatorDefinition]:
        """获取指标详情"""
        return self.db.query(AFIndicatorDefinition).filter(
            AFIndicatorDefinition.id == indicator_id
        ).first()

    def list_indicators(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        indicator_type: Optional[str] = None,
        indicator_group: Optional[str] = None
    ) -> tuple[List[AFIndicatorDefinition], int]:
        """查询指标列表"""
        query = self.db.query(AFIndicatorDefinition)

        if status:
            query = query.filter(AFIndicatorDefinition.status == status)
        if indicator_type:
            query = query.filter(AFIndicatorDefinition.indicator_type == indicator_type)
        if indicator_group:
            query = query.filter(AFIndicatorDefinition.indicator_group == indicator_group)

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total

    def update_indicator(
        self,
        indicator_id: int,
        indicator_data: IndicatorUpdate,
        updated_by: str
    ) -> AFIndicatorDefinition:
        """更新指标"""
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        # 只有draft状态才允许更新逻辑内容
        if db_indicator.status != 'draft' and indicator_data.logic_content:
            raise ValueError("只有草稿状态的指标才允许修改逻辑内容")

        # 更新字段
        update_data = indicator_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_indicator, key, value)

        db_indicator.updated_by = updated_by
        db_indicator.version += 1

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"更新指标成功: {db_indicator.indicator_code}")
        return db_indicator

    def delete_indicator(self, indicator_id: int) -> bool:
        """删除指标"""
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            return False

        # 只有draft和offline状态才允许删除
        if db_indicator.status not in ['draft', 'offline']:
            raise ValueError("只有草稿或下线状态的指标才允许删除")

        self.db.delete(db_indicator)
        self.db.commit()

        logger.info(f"删除指标成功: {db_indicator.indicator_code}")
        return True

    def change_status(
        self,
        indicator_id: int,
        new_status: str,
        updated_by: str
    ) -> AFIndicatorDefinition:
        """更改指标状态"""
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        # 状态转换验证
        valid_transitions = {
            'draft': ['testing', 'archived'],
            'testing': ['draft', 'online', 'archived'],
            'online': ['offline'],
            'offline': ['online', 'archived'],
            'archived': []
        }

        if new_status not in valid_transitions.get(db_indicator.status, []):
            raise ValueError(
                f"不允许的状态转换: {db_indicator.status} -> {new_status}"
            )

        db_indicator.status = new_status
        db_indicator.updated_by = updated_by

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(
            f"指标状态变更: {db_indicator.indicator_code} "
            f"{db_indicator.status} -> {new_status}"
        )
        return db_indicator
```

#### 6.1.2 SQL验证服务

**文件**: `backend/services/indicator_service/sql_validator.py`

```python
import re
from typing import Dict, List, Optional
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where
from sqlparse.tokens import Keyword, DML

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

            if not re.search(r'\bGROUP BY\b', sql_upper):
                result['warnings'].append("指标SQL通常需要GROUP BY子句")

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
                    field_name = str(identifier).split()[-1]  # 获取别名或字段名
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

#### 6.1.3 指标执行服务

**文件**: `backend/services/indicator_service/indicator_executor.py`

```python
from typing import Dict, List, Optional
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.services.spark_service.spark_jdbc_client import SparkJDBCClient
from backend.models.execution import AFTaskExecution
from backend.utils.logger import logger

class IndicatorExecutor:
    """指标执行服务"""

    def __init__(self, db: Session, spark_client: SparkJDBCClient):
        self.db = db
        self.spark_client = spark_client

    async def dry_run(
        self,
        indicator_id: int,
        indicator_code: str,
        logic_content: str,
        sample_size: int = 100,
        partition: Optional[str] = None
    ) -> Dict:
        """试运行指标"""
        execution_id = str(uuid.uuid4())

        # 记录执行开始
        execution = AFTaskExecution(
            task_type='indicator',
            task_id=str(indicator_id),
            execution_id=execution_id,
            execution_type='manual',
            status='running',
            parameters={'sample_size': sample_size, 'partition': partition}
        )
        self.db.add(execution)
        self.db.commit()

        try:
            start_time = datetime.now()

            # 构建LIMIT SQL
            limited_sql = f"{logic_content} LIMIT {sample_size}"

            # 执行SQL
            result_df = await self.spark_client.execute_sql(limited_sql)

            # 验证结果格式
            validation = self._validate_result_format(result_df)

            # 提取样本数据
            sample_result = result_df.head(sample_size).to_dict('records')

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 更新执行记录
            execution.status = 'success'
            execution.end_time = end_time
            execution.duration_seconds = int(duration)
            execution.result_summary = {
                'total_records': len(result_df),
                'sample_size': len(sample_result)
            }
            self.db.commit()

            logger.info(
                f"指标试运行成功: {indicator_code}, "
                f"执行ID: {execution_id}, 耗时: {duration}s"
            )

            return {
                'execution_id': execution_id,
                'status': 'success',
                'duration_seconds': duration,
                'sample_result': sample_result,
                'total_records': len(result_df),
                'validation': validation
            }

        except Exception as e:
            # 记录失败
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            self.db.commit()

            logger.error(
                f"指标试运行失败: {indicator_code}, "
                f"执行ID: {execution_id}, 错误: {str(e)}"
            )

            raise

    def _validate_result_format(self, df) -> Dict:
        """验证结果格式"""
        validation = {
            'has_required_fields': True,
            'field_types_correct': True,
            'warnings': []
        }

        required_fields = ['account_id', 'indicator_code', 'indicator_value', 'dt']

        # 检查必需字段
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            validation['has_required_fields'] = False
            validation['warnings'].append(f"缺少字段: {', '.join(missing_fields)}")

        # 检查字段类型
        # 这里可以添加更详细的类型检查逻辑

        return validation
```

### 6.2 模型服务

#### 6.2.1 规则引擎服务

**文件**: `backend/services/model_service/rule_engine.py`

```python
from typing import Dict, List, Any
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

#### 6.2.2 代码生成服务

**文件**: `backend/services/model_service/code_generator.py`

```python
from typing import Dict, List
from jinja2 import Template

class PySp arkCodeGenerator:
    """PySpark Streaming代码生成器"""

    def generate_streaming_code(
        self,
        model_code: str,
        rule_config: Dict,
        indicator_codes: List[str],
        stream_config: Dict
    ) -> str:
        """生成PySpark Streaming代码"""

        template_str = """
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
反诈模型实时任务: {{ model_code }}
自动生成时间: {{ generation_time }}
警告: 此文件由系统自动生成,请勿手动修改
\"\"\"

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_json, struct, lit, current_timestamp
from pyspark.sql.types import *
import json
from datetime import datetime

# 模型配置
MODEL_CODE = "{{ model_code }}"
KAFKA_BOOTSTRAP_SERVERS = "{{ kafka_servers }}"
KAFKA_TOPIC = "{{ kafka_topic }}"
KAFKA_CONSUMER_GROUP = "{{ consumer_group }}"
OUTPUT_TABLE = "{{ output_table }}"
CHECKPOINT_LOCATION = "{{ checkpoint_location }}"

# 指标宽表配置
INDICATOR_TABLE = "{{ indicator_table }}"
REQUIRED_INDICATORS = {{ required_indicators }}

# 规则配置
RULE_CONFIG = {{ rule_config }}

def create_spark_session():
    \"\"\"创建Spark会话\"\"\"
    return SparkSession.builder \\
        .appName(f"AntiF raud_Model_{MODEL_CODE}") \\
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_LOCATION) \\
        .config("spark.sql.adaptive.enabled", "true") \\
        .enableHiveSupport() \\
        .getOrCreate()

def evaluate_condition(indicator_value, operator, threshold):
    \"\"\"评估单个条件\"\"\"
    if operator == ">":
        return indicator_value > threshold
    elif operator == ">=":
        return indicator_value >= threshold
    elif operator == "<":
        return indicator_value < threshold
    elif operator == "<=":
        return indicator_value <= threshold
    elif operator == "=":
        return indicator_value == threshold
    elif operator == "!=":
        return indicator_value != threshold
    else:
        return False

def evaluate_rules(indicators, rule_config):
    \"\"\"递归评估规则\"\"\"
    logic = rule_config.get("logic", "AND")
    rules = rule_config.get("rules", [])

    results = []
    matched_conditions = []

    for rule in rules:
        if rule.get("type") == "condition":
            indicator_code = rule["indicator"]
            operator = rule["operator"]
            threshold = rule["value"]

            indicator_value = indicators.get(indicator_code)
            if indicator_value is None:
                continue

            # 评估条件
            result = evaluate_condition(indicator_value, operator, threshold)
            results.append(result)

            if result:
                matched_conditions.append({
                    "indicator": indicator_code,
                    "expected": f"{operator} {threshold}",
                    "actual": indicator_value
                })

        elif rule.get("type") == "group":
            # 递归评估子规则组
            sub_result, sub_conditions = evaluate_rules(indicators, rule)
            results.append(sub_result)
            matched_conditions.extend(sub_conditions)

    # 根据逻辑操作符组合结果
    if logic == "AND":
        final_result = all(results) if results else False
    elif logic == "OR":
        final_result = any(results) if results else False
    else:
        final_result = False

    return final_result, matched_conditions

def process_batch(batch_df, batch_id):
    \"\"\"处理每个批次的数据\"\"\"
    try:
        # 1. 从Kafka读取事件
        events_df = batch_df.select(
            col("key").cast("string").alias("event_key"),
            from_json(col("value").cast("string"), event_schema).alias("event")
        ).select(
            "event_key",
            col("event.account_id").alias("account_id"),
            col("event.event_type").alias("event_type"),
            col("event.event_time").alias("event_time"),
            col("event.event_data").alias("event_data")
        )

        # 2. 关联指标宽表
        indicator_df = spark.sql(f\"\"\"
            SELECT account_id,
                   {", ".join(REQUIRED_INDICATORS)}
            FROM {INDICATOR_TABLE}
            WHERE dt = date_format(current_date(), 'yyyyMMdd')
        \"\"\")

        # 3. 关联事件和指标
        joined_df = events_df.join(indicator_df, on="account_id", how="left")

        # 4. 应用规则评估（使用Pandas UDF提高性能）
        from pyspark.sql.functions import pandas_udf, PandasUDFType
        from pandas import DataFrame as PandasDataFrame

        @pandas_udf("struct<hit:boolean, risk_level:string, risk_score:int, hit_reason:string, indicator_snapshot:string>", PandasUDFType.SCALAR)
        def apply_model_rules(*indicator_cols):
            \"\"\"应用模型规则的Pandas UDF\"\"\"
            import pandas as pd

            results = []
            for idx in range(len(indicator_cols[0])):
                # 构建指标字典
                indicators = {}
                for i, indicator_code in enumerate(REQUIRED_INDICATORS):
                    indicators[indicator_code] = indicator_cols[i][idx]

                # 评估规则
                is_hit, matched_conditions = evaluate_rules(indicators, RULE_CONFIG)

                if is_hit:
                    output_config = RULE_CONFIG.get("output", {})
                    result = {
                        "hit": True,
                        "risk_level": output_config.get("risk_level", "medium"),
                        "risk_score": output_config.get("risk_score", 50),
                        "hit_reason": json.dumps({"matched_rules": matched_conditions}, ensure_ascii=False),
                        "indicator_snapshot": json.dumps(indicators, ensure_ascii=False)
                    }
                else:
                    result = {
                        "hit": False,
                        "risk_level": None,
                        "risk_score": 0,
                        "hit_reason": None,
                        "indicator_snapshot": None
                    }

                results.append(result)

            return pd.Series(results)

        # 应用UDF
        indicator_cols = [col(ind) for ind in REQUIRED_INDICATORS]
        result_df = joined_df.withColumn("model_result", apply_model_rules(*indicator_cols))

        # 5. 过滤命中记录
        hit_df = result_df.filter(col("model_result.hit") == True).select(
            lit(MODEL_CODE).alias("model_code"),
            col("account_id"),
            current_timestamp().alias("hit_time"),
            col("model_result.risk_level").alias("risk_level"),
            col("model_result.risk_score").alias("risk_score"),
            col("model_result.hit_reason").alias("hit_reason"),
            col("model_result.indicator_snapshot").alias("indicator_snapshot"),
            date_format(current_timestamp(), "yyyyMMdd").alias("dt")
        )

        # 6. 写入结果表
        if hit_df.count() > 0:
            hit_df.write.mode("append") \\
                .partitionBy("dt") \\
                .format("parquet") \\
                .saveAsTable(OUTPUT_TABLE)

            print(f"Batch {batch_id}: 命中 {hit_df.count()} 条记录")
        else:
            print(f"Batch {batch_id}: 无命中记录")

    except Exception as e:
        print(f"Batch {batch_id} 处理失败: {str(e)}")
        raise

def main():
    \"\"\"主函数\"\"\"
    # 创建Spark会话
    global spark
    spark = create_spark_session()

    # 定义Kafka事件Schema
    global event_schema
    event_schema = StructType([
        StructField("account_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("event_time", TimestampType(), False),
        StructField("event_data", StringType(), True)
    ])

    # 从Kafka读取流
    kafka_stream = spark.readStream \\
        .format("kafka") \\
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \\
        .option("subscribe", KAFKA_TOPIC) \\
        .option("group.id", KAFKA_CONSUMER_GROUP) \\
        .option("startingOffsets", "latest") \\
        .option("failOnDataLoss", "false") \\
        .load()

    # 处理流数据
    query = kafka_stream.writeStream \\
        .foreachBatch(process_batch) \\
        .outputMode("append") \\
        .option("checkpointLocation", CHECKPOINT_LOCATION) \\
        .start()

    print(f"模型 {MODEL_CODE} 已启动,监听主题: {KAFKA_TOPIC}")

    # 等待终止
    query.awaitTermination()

if __name__ == "__main__":
    main()
"""

        # 渲染模板
        template = Template(template_str)
        code = template.render(
            model_code=model_code,
            generation_time=datetime.now().isoformat(),
            kafka_servers=stream_config.get('kafka_servers', 'localhost:9092'),
            kafka_topic=stream_config['stream_source'],
            consumer_group=stream_config.get('stream_consumer_group', f'{model_code}_consumer'),
            output_table=stream_config.get('output_table', 'anti_fraud.model_hit_result'),
            checkpoint_location=stream_config.get('checkpoint_location', f'/tmp/spark-checkpoint/{model_code}'),
            indicator_table=stream_config.get('indicator_table', 'anti_fraud.indicator_result_wide'),
            required_indicators=indicator_codes,
            rule_config=rule_config
        )

        return code
```

### 6.3 调度服务

#### 6.3.1 DolphinScheduler客户端

**文件**: `backend/services/scheduler_service/dolphin_client.py`

```python
from typing import Dict, Optional
import requests
from requests.auth import HTTPBasicAuth
from backend.utils.logger import logger

class DolphinSchedulerClient:
    """DolphinScheduler REST API客户端"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """登录获取token"""
        try:
            response = self.session.post(
                f"{self.base_url}/dolphinscheduler/login",
                data={
                    "userName": self.username,
                    "userPassword": self.password
                }
            )
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                self.token = result['data']
                self.session.headers.update({'token': self.token})
                logger.info("DolphinScheduler登录成功")
                return True
            else:
                logger.error(f"DolphinScheduler登录失败: {result.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"DolphinScheduler登录异常: {str(e)}")
            return False

    def create_task_definition(
        self,
        project_code: int,
        workflow_definition_code: int,
        task_name: str,
        task_type: str,
        task_params: Dict
    ) -> Optional[int]:
        """创建任务定义"""
        try:
            if not self.token:
                self.login()

            response = self.session.post(
                f"{self.base_url}/dolphinscheduler/projects/{project_code}/"
                f"task-definition",
                json={
                    "workflowDefinitionCode": workflow_definition_code,
                    "taskName": task_name,
                    "taskType": task_type,
                    "taskParams": task_params,
                    "flag": "YES",
                    "taskPriority": "MEDIUM",
                    "workerGroup": "default",
                    "failRetryTimes": 0,
                    "failRetryInterval": 1,
                    "timeoutFlag": "CLOSE",
                    "timeoutNotifyStrategy": "WARN",
                    "timeout": 0
                }
            )
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                task_code = result['data']
                logger.info(f"创建任务定义成功: {task_name}, code: {task_code}")
                return task_code
            else:
                logger.error(f"创建任务定义失败: {result.get('msg')}")
                return None

        except Exception as e:
            logger.error(f"创建任务定义异常: {str(e)}")
            return None

    def update_schedule(
        self,
        project_code: int,
        schedule_id: int,
        cron_expression: str,
        start_time: str,
        end_time: str
    ) -> bool:
        """更新调度配置"""
        try:
            if not self.token:
                self.login()

            response = self.session.put(
                f"{self.base_url}/dolphinscheduler/projects/{project_code}/"
                f"schedules/{schedule_id}",
                json={
                    "crontab": cron_expression,
                    "startTime": start_time,
                    "endTime": end_time,
                    "timezoneId": "Asia/Shanghai"
                }
            )
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                logger.info(f"更新调度配置成功: schedule_id={schedule_id}")
                return True
            else:
                logger.error(f"更新调度配置失败: {result.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"更新调度配置异常: {str(e)}")
            return False

    def trigger_task(
        self,
        project_code: int,
        workflow_definition_code: int,
        schedule_time: Optional[str] = None
    ) -> Optional[int]:
        """手动触发任务执行"""
        try:
            if not self.token:
                self.login()

            params = {
                "workflowDefinitionCode": workflow_definition_code,
                "failureStrategy": "CONTINUE",
                "warningType": "NONE",
                "execType": "START_PROCESS"
            }

            if schedule_time:
                params["scheduleTime"] = schedule_time

            response = self.session.post(
                f"{self.base_url}/dolphinscheduler/projects/{project_code}/"
                f"executors/start-process-instance",
                json=params
            )
            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                instance_id = result['data']
                logger.info(f"触发任务执行成功: instance_id={instance_id}")
                return instance_id
            else:
                logger.error(f"触发任务执行失败: {result.get('msg')}")
                return None

        except Exception as e:
            logger.error(f"触发任务执行异常: {str(e)}")
            return None
```

---

由于文档内容非常长,我将继续完成剩余部分。让我更新任务状态并继续编写。

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "\u5206\u6790\u9700\u6c42\u6587\u6863,\u7406\u89e3\u4e1a\u52a1\u573a\u666f\u548c\u6280\u672f\u7ea6\u675f", "status": "completed", "activeForm": "\u5206\u6790\u9700\u6c42\u6587\u6863"}, {"content": "\u8bbe\u8ba1\u6570\u636e\u5e93\u6a21\u578b(\u6307\u6807\u5b9a\u4e49\u3001\u6a21\u578b\u5b9a\u4e49\u3001\u6267\u884c\u8bb0\u5f55\u7b49)", "status": "completed", "activeForm": "\u8bbe\u8ba1\u6570\u636e\u5e93\u6a21\u578b"}, {"content": "\u8bbe\u8ba1\u540e\u7aefAPI\u63a5\u53e3(\u6307\u6807\u7ba1\u7406\u3001\u6a21\u578b\u7ba1\u7406\u3001\u4efb\u52a1\u8c03\u5ea6)", "status": "completed", "activeForm": "\u8bbe\u8ba1\u540e\u7aefAPI\u63a5\u53e3"}, {"content": "\u8bbe\u8ba1\u524d\u7aef\u9875\u9762\u548c\u7ec4\u4ef6\u67b6\u6784", "status": "in_progress", "activeForm": "\u8bbe\u8ba1\u524d\u7aef\u9875\u9762\u548c\u7ec4\u4ef6\u67b6\u6784"}, {"content": "\u8bbe\u8ba1\u53ef\u89c6\u5316\u89c4\u5219\u5f15\u64ce(\u6a21\u578b\u5b9a\u4e49)", "status": "pending", "activeForm": "\u8bbe\u8ba1\u53ef\u89c6\u5316\u89c4\u5219\u5f15\u64ce"}, {"content": "\u8bbe\u8ba1\u6307\u6807\u7ec4\u548c\u52a8\u6001SQL\u751f\u6210\u65b9\u6848", "status": "pending", "activeForm": "\u8bbe\u8ba1\u6307\u6807\u7ec4\u548c\u52a8\u6001SQL\u751f\u6210\u65b9\u6848"}, {"content": "\u8bbe\u8ba1PySpark Streaming\u4efb\u52a1\u751f\u6210\u548c\u7ba1\u7406", "status": "pending", "activeForm": "\u8bbe\u8ba1PySpark Streaming\u4efb\u52a1\u751f\u6210\u548c\u7ba1\u7406"}, {"content": "\u8bbe\u8ba1\u56de\u6d4b\u529f\u80fd\u67b6\u6784", "status": "pending", "activeForm": "\u8bbe\u8ba1\u56de\u6d4b\u529f\u80fd\u67b6\u6784"}, {"content": "\u7f16\u5199\u5b8c\u6574\u7684\u8bbe\u8ba1\u6587\u6863", "status": "pending", "activeForm": "\u7f16\u5199\u5b8c\u6574\u7684\u8bbe\u8ba1\u6587\u6863"}]
---

## 7. 前端界面设计

### 7.1 设计原则

遵循项目现有的设计体系:
- **设计语言**: 现代扁平化设计，明暗双主题
- **组件库**: Radix UI + Tailwind CSS
- **响应式**: 移动端优先，断点768px
- **状态管理**: React Context + hooks

### 7.2 页面结构

#### 7.2.1 指标管理页面 (`/indicators`)

**指标列表页**:
```tsx
// app/(main)/indicators/page.tsx
import { IndicatorList } from '@/components/indicator/IndicatorList'
import { IndicatorFilters } from '@/components/indicator/IndicatorFilters'

export default function IndicatorsPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">指标管理</h1>
        <Link href="/indicators/create">
          <Button>创建指标</Button>
        </Link>
      </div>

      <IndicatorFilters />
      <IndicatorList />
    </div>
  )
}
```

**指标创建/编辑页**:
```tsx
// app/(main)/indicators/[id]/page.tsx
import { IndicatorForm } from '@/components/indicator/IndicatorForm'
import { SQLEditor } from '@/components/indicator/SQLEditor'
import { IndicatorPreview } from '@/components/indicator/IndicatorPreview'

export default function IndicatorDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="container mx-auto p-6">
      <Tabs defaultValue="basic">
        <TabsList>
          <TabsTrigger value="basic">基本信息</TabsTrigger>
          <TabsTrigger value="logic">加工逻辑</TabsTrigger>
          <TabsTrigger value="preview">预览测试</TabsTrigger>
        </TabsList>

        <TabsContent value="basic">
          <IndicatorForm indicatorId={params.id} />
        </TabsContent>

        <TabsContent value="logic">
          <SQLEditor indicatorId={params.id} />
        </TabsContent>

        <TabsContent value="preview">
          <IndicatorPreview indicatorId={params.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

#### 7.2.2 模型管理页面 (`/models`)

**模型列表页**:
```tsx
// app/(main)/models/page.tsx
import { ModelList } from '@/components/model/ModelList'
import { ModelCard } from '@/components/model/ModelCard'

export default function ModelsPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">模型管理</h1>
        <Link href="/models/create">
          <Button>创建模型</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ModelList />
      </div>
    </div>
  )
}
```

**模型创建/编辑页**:
```tsx
// app/(main)/models/[id]/page.tsx
import { ModelForm } from '@/components/model/ModelForm'
import { RuleBuilder } from '@/components/model/RuleBuilder'
import { CodePreview } from '@/components/model/CodePreview'
import { BacktestPanel } from '@/components/model/BacktestPanel'

export default function ModelDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="container mx-auto p-6">
      <Tabs defaultValue="basic">
        <TabsList>
          <TabsTrigger value="basic">基本信息</TabsTrigger>
          <TabsTrigger value="rules">规则定义</TabsTrigger>
          <TabsTrigger value="code">生成代码</TabsTrigger>
          <TabsTrigger value="backtest">回测</TabsTrigger>
        </TabsList>

        <TabsContent value="basic">
          <ModelForm modelId={params.id} />
        </TabsContent>

        <TabsContent value="rules">
          <RuleBuilder modelId={params.id} />
        </TabsContent>

        <TabsContent value="code">
          <CodePreview modelId={params.id} />
        </TabsContent>

        <TabsContent value="backtest">
          <BacktestPanel modelId={params.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### 7.3 核心组件设计

#### 7.3.1 SQL编辑器组件

```typescript
// components/indicator/SQLEditor.tsx
'use client'

import { useState, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { indicatorService } from '@/lib/services/indicatorService'

interface SQLEditorProps {
  indicatorId: string
  initialValue?: string
  onChange?: (value: string) => void
}

export function SQLEditor({ indicatorId, initialValue, onChange }: SQLEditorProps) {
  const [sql, setSQL] = useState(initialValue || '')
  const [validation, setValidation] = useState<any>(null)
  const [isValidating, setIsValidating] = useState(false)

  const handleValidate = async () => {
    setIsValidating(true)
    try {
      const result = await indicatorService.validateSQL(sql)
      setValidation(result)
    } catch (error) {
      console.error('SQL validation failed:', error)
    } finally {
      setIsValidating(false)
    }
  }

  const handleFormat = () => {
    // SQL格式化逻辑
    const formatted = formatSQL(sql)
    setSQL(formatted)
    onChange?.(formatted)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">SQL编辑器</h3>
        <div className="space-x-2">
          <Button variant="outline" onClick={handleFormat}>
            格式化
          </Button>
          <Button onClick={handleValidate} disabled={isValidating}>
            {isValidating ? '验证中...' : '验证SQL'}
          </Button>
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <Editor
          height="400px"
          language="sql"
          theme="vs-dark"
          value={sql}
          onChange={(value) => {
            setSQL(value || '')
            onChange?.(value || '')
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            automaticLayout: true,
          }}
        />
      </div>

      {validation && (
        <div className="space-y-2">
          {validation.errors.length > 0 && (
            <Alert variant="destructive">
              <AlertDescription>
                <ul className="list-disc list-inside">
                  {validation.errors.map((error: string, index: number) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {validation.warnings.length > 0 && (
            <Alert>
              <AlertDescription>
                <ul className="list-disc list-inside">
                  {validation.warnings.map((warning: string, index: number) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {validation.valid && (
            <Alert variant="success">
              <AlertDescription>SQL验证通过</AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </div>
  )
}
```

#### 7.3.2 规则构建器组件

```typescript
// components/model/RuleBuilder.tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

interface Rule {
  type: 'condition' | 'group'
  logic?: 'AND' | 'OR'
  indicator?: string
  operator?: string
  value?: any
  rules?: Rule[]
}

interface RuleBuilderProps {
  modelId: string
  initialRules?: Rule
  onChange?: (rules: Rule) => void
}

export function RuleBuilder({ modelId, initialRules, onChange }: RuleBuilderProps) {
  const [rules, setRules] = useState<Rule>(
    initialRules || { type: 'group', logic: 'AND', rules: [] }
  )

  const addCondition = (parentRules: Rule[]) => {
    const newCondition: Rule = {
      type: 'condition',
      indicator: '',
      operator: '>',
      value: 0,
    }
    parentRules.push(newCondition)
    setRules({ ...rules })
    onChange?.(rules)
  }

  const addGroup = (parentRules: Rule[]) => {
    const newGroup: Rule = {
      type: 'group',
      logic: 'AND',
      rules: [],
    }
    parentRules.push(newGroup)
    setRules({ ...rules })
    onChange?.(rules)
  }

  const removeRule = (parentRules: Rule[], index: number) => {
    parentRules.splice(index, 1)
    setRules({ ...rules })
    onChange?.(rules)
  }

  const renderRule = (rule: Rule, parentRules: Rule[], index: number, depth: number = 0) => {
    if (rule.type === 'condition') {
      return (
        <Card key={index} className="p-4" style={{ marginLeft: `${depth * 20}px` }}>
          <div className="flex items-center gap-4">
            <Select
              value={rule.indicator}
              onValueChange={(value) => {
                rule.indicator = value
                setRules({ ...rules })
                onChange?.(rules)
              }}
            >
              {/* 指标选项 */}
            </Select>

            <Select
              value={rule.operator}
              onValueChange={(value) => {
                rule.operator = value
                setRules({ ...rules })
                onChange?.(rules)
              }}
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
              onChange={(e) => {
                rule.value = parseFloat(e.target.value)
                setRules({ ...rules })
                onChange?.(rules)
              }}
            />

            <Button
              variant="destructive"
              size="sm"
              onClick={() => removeRule(parentRules, index)}
            >
              删除
            </Button>
          </div>
        </Card>
      )
    } else if (rule.type === 'group') {
      return (
        <Card key={index} className="p-4 space-y-4" style={{ marginLeft: `${depth * 20}px` }}>
          <div className="flex items-center justify-between">
            <Select
              value={rule.logic}
              onValueChange={(value: 'AND' | 'OR') => {
                rule.logic = value
                setRules({ ...rules })
                onChange?.(rules)
              }}
            >
              <option value="AND">并且 (AND)</option>
              <option value="OR">或者 (OR)</option>
            </Select>

            <div className="space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => addCondition(rule.rules!)}
              >
                添加条件
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => addGroup(rule.rules!)}
              >
                添加组
              </Button>
              {depth > 0 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => removeRule(parentRules, index)}
                >
                  删除组
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {rule.rules?.map((subRule, subIndex) =>
              renderRule(subRule, rule.rules!, subIndex, depth + 1)
            )}
          </div>
        </Card>
      )
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">规则定义</h3>
        <Button onClick={() => addCondition(rules.rules!)}>添加第一个条件</Button>
      </div>

      {renderRule(rules, [], 0)}
    </div>
  )
}
```

---

## 8. 可视化规则引擎

### 8.1 规则配置格式

```typescript
// lib/types/model.ts
export interface RuleCondition {
  type: 'condition'
  indicator: string           // 指标编码
  operator: '>' | '>=' | '<' | '<=' | '=' | '!='
  value: number | string
}

export interface RuleGroup {
  type: 'group'
  logic: 'AND' | 'OR'
  rules: (RuleCondition | RuleGroup)[]
}

export interface ModelRuleConfig {
  logic: 'AND' | 'OR'
  rules: (RuleCondition | RuleGroup)[]
  output: {
    risk_level: 'low' | 'medium' | 'high' | 'critical'
    risk_score: number
    action?: 'alert' | 'review' | 'block'
  }
}
```

### 8.2 规则示例

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
    "action": "review"
  }
}
```

### 8.3 规则解释

上述规则的逻辑表达式:
```
(i_login_cnt_7d > 10) 
AND (i_trans_amt_1d > 50000)
AND ((i_device_change_cnt >= 3) OR (i_ip_city_cnt > 5))
```

满足条件的账户将被标记为:
- 风险等级: high
- 风险分数: 85
- 建议操作: review (人工审核)

---

## 9. 指标组与动态SQL

### 9.1 指标组概念

**目标**: 解决多个指标从同一数据源计算导致的重复扫描问题

**实现方式**:
1. 定义指标组,指定共享的数据源
2. 同组指标使用统一的SQL模板
3. 每个指标输出符合行存储格式

### 9.2 指标组SQL模板

```sql
-- 指标组: login_behavior
-- 数据源: user_login, user_session
-- 输出指标: i_login_cnt_7d, i_login_cnt_30d, i_avg_session_duration

SELECT 
    account_id,
    indicator_code,
    indicator_value,
    CURRENT_DATE as dt
FROM (
    SELECT 
        ul.account_id,
        -- 指标1: 7天登录次数
        STACK(3,
            'i_login_cnt_7d', 
            CAST(COUNT(DISTINCT CASE WHEN ul.login_date >= DATE_SUB(CURRENT_DATE, 7) 
                                      THEN ul.login_date END) AS STRING),
            
            -- 指标2: 30天登录次数
            'i_login_cnt_30d',
            CAST(COUNT(DISTINCT CASE WHEN ul.login_date >= DATE_SUB(CURRENT_DATE, 30) 
                                      THEN ul.login_date END) AS STRING),
            
            -- 指标3: 平均会话时长
            'i_avg_session_duration',
            CAST(AVG(us.session_duration) AS STRING)
        ) AS (indicator_code, indicator_value)
    FROM user_login ul
    LEFT JOIN user_session us ON ul.account_id = us.account_id 
        AND us.session_date >= DATE_SUB(CURRENT_DATE, 30)
    GROUP BY ul.account_id
) t
```

### 9.3 动态SQL生成器

```python
# backend/services/indicator_service/dynamic_sql_generator.py

class DynamicSQLGenerator:
    """动态SQL生成器 - 用于指标组批量计算"""

    def generate_group_sql(
        self,
        group_code: str,
        indicators: List[AFIndicatorDefinition]
    ) -> str:
        """生成指标组的批量SQL"""

        # 1. 提取所有指标的SQL逻辑
        indicator_sqls = []
        for indicator in indicators:
            # 从单个指标SQL中提取计算逻辑
            calc_logic = self._extract_calculation(indicator.logic_content)
            indicator_sqls.append({
                'code': indicator.indicator_code,
                'logic': calc_logic
            })

        # 2. 识别共同的数据源
        common_tables = self._find_common_tables(indicators)

        # 3. 构建STACK表达式
        stack_expressions = []
        for ind_sql in indicator_sqls:
            stack_expressions.append(
                f"'{ind_sql['code']}', CAST({ind_sql['logic']} AS STRING)"
            )

        stack_count = len(stack_expressions)
        stack_expr = f"STACK({stack_count}, {', '.join(stack_expressions)})"

        # 4. 生成最终SQL
        sql_template = f"""
        SELECT 
            account_id,
            indicator_code,
            indicator_value,
            CURRENT_DATE as dt
        FROM (
            SELECT 
                account_id,
                {stack_expr} AS (indicator_code, indicator_value)
            FROM {common_tables['main']}
            {self._generate_joins(common_tables['joins'])}
            GROUP BY account_id
        ) t
        """

        return sql_template

    def _extract_calculation(self, sql: str) -> str:
        """从完整SQL中提取计算逻辑"""
        # 使用SQL解析器提取SELECT子句中的计算表达式
        # 这里简化处理，实际需要更复杂的解析逻辑
        pass

    def _find_common_tables(self, indicators: List[AFIndicatorDefinition]) -> Dict:
        """识别共同使用的表"""
        pass

    def _generate_joins(self, join_tables: List[str]) -> str:
        """生成JOIN子句"""
        pass
```

### 9.4 宽表生成策略

#### 9.4.1 方案1: 使用PIVOT动态生成

```sql
-- 从行存储表动态生成宽表
CREATE TABLE anti_fraud.indicator_result_wide AS
SELECT 
    account_id,
    data_date,
    {% for indicator in indicators %}
    MAX(CASE WHEN indicator_code = '{{ indicator.code }}' 
        THEN CAST(indicator_value AS {{ indicator.data_type }}) END) 
        AS {{ indicator.code }},
    {% endfor %}
    MAX(calculate_time) as calculate_time
FROM anti_fraud.indicator_result_row
WHERE dt = '${partition_date}'
GROUP BY account_id, data_date;
```

#### 9.4.2 方案2: 使用Hudi增量更新

```python
# 使用Apache Hudi实现宽表的Schema Evolution

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.hudi.catalog.HoodieCatalog") \
    .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension") \
    .getOrCreate()

# 读取行存储表
row_df = spark.sql("""
    SELECT account_id, indicator_code, indicator_value, dt
    FROM anti_fraud.indicator_result_row
    WHERE dt = '20251201'
""")

# Pivot转换为宽表格式
wide_df = row_df.groupBy("account_id", "dt").pivot("indicator_code").agg(
    max("indicator_value")
)

# 使用Hudi写入(支持Schema Evolution)
hudi_options = {
    'hoodie.table.name': 'indicator_result_wide',
    'hoodie.datasource.write.recordkey.field': 'account_id',
    'hoodie.datasource.write.partitionpath.field': 'dt',
    'hoodie.datasource.write.table.name': 'indicator_result_wide',
    'hoodie.datasource.write.operation': 'upsert',
    'hoodie.datasource.write.precombine.field': 'calculate_time',
    'hoodie.upsert.shuffle.parallelism': 100,
    'hoodie.insert.shuffle.parallelism': 100
}

wide_df.write.format("hudi") \
    .options(**hudi_options) \
    .mode("append") \
    .save("hdfs://namenode:8020/user/hive/warehouse/anti_fraud.db/indicator_result_wide")
```

---

## 10. PySpark Streaming任务生成

### 10.1 任务生成流程

```
规则配置(JSON) 
    ↓
规则引擎验证
    ↓
提取依赖指标列表
    ↓
生成PySpark代码(Jinja2模板)
    ↓
代码验证和测试
    ↓
打包部署到Spark集群
    ↓
注册到DolphinScheduler监控
```

### 10.2 代码模板结构

```python
# 代码模板的核心部分已在第6.2.2节展示
# 这里补充部署相关的配置

class StreamingJobDeployer:
    """PySpark Streaming任务部署器"""

    def deploy_job(
        self,
        model_code: str,
        generated_code: str,
        deploy_config: Dict
    ) -> Dict:
        """部署Streaming任务"""

        # 1. 保存代码到文件系统
        job_file = self._save_code_file(model_code, generated_code)

        # 2. 提交Spark任务
        spark_submit_cmd = self._build_spark_submit_command(
            job_file,
            deploy_config
        )

        # 3. 执行提交命令
        result = subprocess.run(
            spark_submit_cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # 解析Application ID
            app_id = self._extract_app_id(result.stdout)

            return {
                'success': True,
                'app_id': app_id,
                'tracking_url': self._get_tracking_url(app_id)
            }
        else:
            return {
                'success': False,
                'error': result.stderr
            }

    def _build_spark_submit_command(
        self,
        job_file: str,
        config: Dict
    ) -> str:
        """构建spark-submit命令"""

        cmd = f"""
        spark-submit \\
            --master {config.get('master', 'yarn')} \\
            --deploy-mode {config.get('deploy_mode', 'cluster')} \\
            --name {config.get('job_name')} \\
            --driver-memory {config.get('driver_memory', '2g')} \\
            --executor-memory {config.get('executor_memory', '4g')} \\
            --executor-cores {config.get('executor_cores', 2)} \\
            --num-executors {config.get('num_executors', 3)} \\
            --conf spark.sql.streaming.checkpointLocation={config.get('checkpoint')} \\
            --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \\
            {job_file}
        """

        return cmd
```

---

## 11. 回测功能设计

### 11.1 回测流程

```
选择模型 → 配置回测参数 → 加载历史数据 → 应用规则 → 对比真实标签 → 计算性能指标
```

### 11.2 回测服务实现

```python
# backend/services/model_service/backtest_service.py

from typing import Dict, List
from datetime import date, datetime
import uuid
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

class BacktestService:
    """模型回测服务"""

    def __init__(self, spark: SparkSession, db: Session):
        self.spark = spark
        self.db = db

    def run_backtest(
        self,
        model_id: int,
        start_date: date,
        end_date: date,
        ground_truth_config: Dict
    ) -> str:
        """执行模型回测"""

        # 1. 创建回测记录
        backtest_id = str(uuid.uuid4())
        model = self.db.query(AFModelDefinition).get(model_id)

        backtest_record = AFBacktestRecord(
            backtest_id=backtest_id,
            model_id=model_id,
            model_code=model.model_code,
            start_date=start_date,
            end_date=end_date,
            status='running',
            start_time=datetime.now()
        )
        self.db.add(backtest_record)
        self.db.commit()

        try:
            # 2. 加载历史指标数据
            indicator_df = self._load_historical_indicators(
                model.indicator_codes,
                start_date,
                end_date
            )

            # 3. 应用模型规则
            prediction_df = self._apply_model_rules(
                indicator_df,
                model.rule_config
            )

            # 4. 加载真实标签
            ground_truth_df = self._load_ground_truth(
                ground_truth_config,
                start_date,
                end_date
            )

            # 5. 关联预测和真实标签
            result_df = prediction_df.join(
                ground_truth_df,
                on=["account_id", "data_date"],
                how="inner"
            )

            # 6. 计算性能指标
            metrics = self._calculate_metrics(result_df)

            # 7. 更新回测记录
            backtest_record.status = 'success'
            backtest_record.end_time = datetime.now()
            backtest_record.total_records = metrics['total']
            backtest_record.hit_records = metrics['predicted_positive']
            backtest_record.true_positive = metrics['tp']
            backtest_record.false_positive = metrics['fp']
            backtest_record.true_negative = metrics['tn']
            backtest_record.false_negative = metrics['fn']
            backtest_record.precision_score = metrics['precision']
            backtest_record.recall_score = metrics['recall']
            backtest_record.f1_score = metrics['f1']
            backtest_record.accuracy_score = metrics['accuracy']
            self.db.commit()

            logger.info(f"回测完成: {backtest_id}, F1={metrics['f1']:.4f}")

            return backtest_id

        except Exception as e:
            backtest_record.status = 'failed'
            backtest_record.error_message = str(e)
            backtest_record.end_time = datetime.now()
            self.db.commit()

            logger.error(f"回测失败: {backtest_id}, 错误: {str(e)}")
            raise

    def _load_historical_indicators(
        self,
        indicator_codes: List[str],
        start_date: date,
        end_date: date
    ):
        """加载历史指标数据"""

        sql = f"""
        SELECT 
            account_id,
            data_date,
            {", ".join(indicator_codes)}
        FROM anti_fraud.indicator_result_wide
        WHERE dt >= '{start_date.strftime('%Y%m%d')}'
          AND dt <= '{end_date.strftime('%Y%m%d')}'
        """

        return self.spark.sql(sql)

    def _apply_model_rules(self, df, rule_config: Dict):
        """应用模型规则"""

        # 这里需要将规则配置转换为Spark SQL表达式
        # 简化示例：
        condition_expr = self._build_spark_condition(rule_config)

        result_df = df.withColumn(
            "prediction",
            when(condition_expr, 1).otherwise(0)
        )

        return result_df

    def _build_spark_condition(self, rule_config: Dict):
        """构建Spark SQL条件表达式"""
        # 递归构建条件表达式
        # 例如: (col("i_login_cnt_7d") > 10) & (col("i_trans_amt_1d") > 50000)
        pass

    def _load_ground_truth(self, config: Dict, start_date: date, end_date: date):
        """加载真实标签数据"""

        sql = f"""
        SELECT 
            {config['key_field']} as account_id,
            {config['date_field']} as data_date,
            {config['label_field']} as actual_label
        FROM {config['table_name']}
        WHERE {config['date_field']} >= '{start_date}'
          AND {config['date_field']} <= '{end_date}'
        """

        return self.spark.sql(sql)

    def _calculate_metrics(self, result_df) -> Dict:
        """计算性能指标"""

        # 转换为Pandas进行计算
        pandas_df = result_df.select("prediction", "actual_label").toPandas()

        y_true = pandas_df["actual_label"].values
        y_pred = pandas_df["prediction"].values

        # 计算混淆矩阵
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        # 计算指标
        metrics = {
            'total': len(y_true),
            'predicted_positive': int(y_pred.sum()),
            'actual_positive': int(y_true.sum()),
            'tp': int(tp),
            'fp': int(fp),
            'tn': int(tn),
            'fn': int(fn),
            'precision': float(precision_score(y_true, y_pred, zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, zero_division=0)),
            'f1': float(f1_score(y_true, y_pred, zero_division=0)),
            'accuracy': float((tp + tn) / len(y_true)) if len(y_true) > 0 else 0.0
        }

        return metrics
```

### 11.3 回测结果可视化

```typescript
// components/model/BacktestResults.tsx

import { Bar, Line } from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface BacktestResultsProps {
  backtestId: string
}

export function BacktestResults({ backtestId }: BacktestResultsProps) {
  const { data: backtest } = useBacktestResult(backtestId)

  if (!backtest) return <div>加载中...</div>

  const { metrics, daily_metrics } = backtest

  return (
    <div className="space-y-6">
      {/* 总体指标 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>精确率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {(metrics.precision * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>召回率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {(metrics.recall * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>F1分数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {(metrics.f1 * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>准确率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {(metrics.accuracy * 100).toFixed(2)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 混淆矩阵 */}
      <Card>
        <CardHeader>
          <CardTitle>混淆矩阵</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 max-w-md">
            <div className="p-4 border rounded bg-green-50">
              <div className="text-sm text-gray-600">真阳性 (TP)</div>
              <div className="text-2xl font-bold">{metrics.tp}</div>
            </div>
            <div className="p-4 border rounded bg-red-50">
              <div className="text-sm text-gray-600">假阳性 (FP)</div>
              <div className="text-2xl font-bold">{metrics.fp}</div>
            </div>
            <div className="p-4 border rounded bg-red-50">
              <div className="text-sm text-gray-600">假阴性 (FN)</div>
              <div className="text-2xl font-bold">{metrics.fn}</div>
            </div>
            <div className="p-4 border rounded bg-green-50">
              <div className="text-sm text-gray-600">真阴性 (TN)</div>
              <div className="text-2xl font-bold">{metrics.tn}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 每日趋势 */}
      <Card>
        <CardHeader>
          <CardTitle>每日性能趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <LineChart width={800} height={300} data={daily_metrics}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="precision" stroke="#8884d8" name="精确率" />
            <Line type="monotone" dataKey="recall" stroke="#82ca9d" name="召回率" />
            <Line type="monotone" dataKey="f1" stroke="#ffc658" name="F1分数" />
          </LineChart>
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## 12. 任务调度集成

### 12.1 DolphinScheduler集成架构

```
反诈系统
    ↓ (通过REST API)
DolphinScheduler
    ↓ (提交任务)
Spark集群
    ↓ (读写数据)
Hadoop/Hive
```

### 12.2 任务类型

#### 12.2.1 离线指标计算任务

```python
# 任务类型: SPARK
# 任务配置示例

{
    "taskType": "SPARK",
    "taskParams": {
        "mainClass": "",
        "mainJar": {
            "id": 1
        },
        "deployMode": "cluster",
        "driverCores": 1,
        "driverMemory": "2G",
        "numExecutors": 3,
        "executorMemory": "4G",
        "executorCores": 2,
        "appName": "indicator_calculation_i_login_cnt_7d",
        "mainArgs": "--indicator-code i_login_cnt_7d --partition ${partition_date}",
        "others": "",
        "programType": "PYTHON",
        "sparkVersion": "SPARK3",
        "runMode": "SPARK_SQL"
    }
}
```

#### 12.2.2 指标组批量任务

```python
# 批量计算指标组的DAG定义

{
    "tasks": [
        {
            "code": "load_raw_data",
            "name": "加载原始数据",
            "type": "SQL",
            "sql": "-- 数据预处理SQL"
        },
        {
            "code": "calculate_indicator_group_login",
            "name": "计算登录行为指标组",
            "type": "SPARK",
            "dependsOn": ["load_raw_data"]
        },
        {
            "code": "generate_wide_table",
            "name": "生成指标宽表",
            "type": "SPARK",
            "dependsOn": ["calculate_indicator_group_login"]
        }
    ]
}
```

#### 12.2.3 实时模型监控任务

```python
# 任务类型: SHELL (用于监控Streaming任务状态)

{
    "taskType": "SHELL",
    "taskParams": {
        "rawScript": """
#!/bin/bash

MODEL_CODE="m_high_risk_login"
APP_ID=$(yarn application -list | grep $MODEL_CODE | awk '{print $1}')

if [ -z "$APP_ID" ]; then
    echo "ERROR: Streaming job not found for model: $MODEL_CODE"
    exit 1
fi

# 检查任务状态
STATE=$(yarn application -status $APP_ID | grep State | awk '{print $3}')

if [ "$STATE" != "RUNNING" ]; then
    echo "ERROR: Streaming job is not running. State: $STATE"
    # 发送告警
    curl -X POST http://alert-service/api/alert \\
        -H "Content-Type: application/json" \\
        -d "{\"model\": \"$MODEL_CODE\", \"status\": \"$STATE\"}"
    exit 1
fi

echo "SUCCESS: Streaming job is running normally"
exit 0
        """
    }
}
```

### 12.3 调度策略

#### 12.3.1 离线指标调度

```python
# 每日凌晨2点执行
schedule_cron = "0 2 * * *"

# 依赖配置
dependencies = {
    "upstream": ["etl_user_login", "etl_user_transaction"],  # 上游ETL任务
    "downstream": ["generate_wide_table"]  # 下游宽表生成
}

# 失败重试策略
retry_config = {
    "retry_times": 2,
    "retry_interval": 5  # 分钟
}
```

#### 12.3.2 实时模型调度

```python
# 持续运行的Streaming任务不需要周期调度
# 但需要配置监控任务

monitor_schedule = {
    "cron": "*/15 * * * *",  # 每15分钟检查一次
    "alert_channels": ["email", "dingtalk", "sms"]
}
```

---

## 13. 部署架构

### 13.1 系统部署拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│                          用户层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ 开发人员 │  │ 业务人员 │  │ 运维人员 │                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
│       │             │             │                              │
└───────┼─────────────┼─────────────┼──────────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │       Nginx (负载均衡)          │
        └─────────────┬─────────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │  Next.js Frontend (3000)      │
        │  (静态资源 + SSR)               │
        └─────────────┬─────────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │  FastAPI Backend (50020)      │
        │  (Uvicorn + 多worker)          │
        └──┬────────┬────────┬──────────┘
           │        │        │
    ┌──────▼──┐ ┌──▼────┐ ┌─▼──────────┐
    │  MySQL  │ │ Spark │ │ Dolphin    │
    │ (元数据) │ │ JDBC  │ │ Scheduler  │
    └─────────┘ └───┬───┘ └────────────┘
                    │
        ┌───────────▼───────────────┐
        │   Spark 集群               │
        │  ┌──────────────────────┐ │
        │  │ Streaming Jobs (实时) │ │
        │  ├──────────────────────┤ │
        │  │ Batch Jobs (离线)     │ │
        │  └──────────────────────┘ │
        └───────────┬───────────────┘
                    │
        ┌───────────▼───────────────┐
        │   Hadoop 生态              │
        │  ┌─────┐  ┌──────┐        │
        │  │ HDFS│  │ Hive │        │
        │  └─────┘  └──────┘        │
        └───────────────────────────┘
                    │
        ┌───────────▼───────────────┐
        │   Kafka 集群 (实时流)      │
        └───────────────────────────┘
```

### 13.2 服务器资源规划

#### 13.2.1 Web服务器

```yaml
Frontend Server:
  数量: 2台 (主备)
  配置:
    CPU: 4核
    内存: 8GB
    磁盘: 100GB SSD
  软件:
    - Node.js 20.x
    - Next.js 14.x
    - PM2 (进程管理)

Backend Server:
  数量: 2台 (负载均衡)
  配置:
    CPU: 8核
    内存: 16GB
    磁盘: 200GB SSD
  软件:
    - Python 3.11+
    - FastAPI 0.116+
    - Uvicorn (4 workers)
```

#### 13.2.2 数据库服务器

```yaml
MySQL Server:
  数量: 1主2从
  配置:
    CPU: 16核
    内存: 64GB
    磁盘: 1TB SSD (RAID10)
  版本: MySQL 8.0
  配置优化:
    - innodb_buffer_pool_size: 48GB
    - max_connections: 1000
```

#### 13.2.3 Spark集群

```yaml
Spark Master:
  数量: 2台 (HA)
  配置:
    CPU: 8核
    内存: 16GB

Spark Workers:
  数量: 5-10台 (按需扩展)
  配置:
    CPU: 32核
    内存: 128GB
    磁盘: 2TB HDD

Streaming Jobs:
  资源分配 (每个模型):
    executor-memory: 4G
    executor-cores: 2
    num-executors: 3
```

### 13.3 Docker部署配置

#### 13.3.1 Docker Compose示例

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MySQL数据库
  mysql:
    image: mysql:8.0
    container_name: anti_fraud_mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: anti_fraud
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    networks:
      - anti_fraud_network

  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: anti_fraud_backend
    environment:
      - DATABASE_URL=mysql+pymysql://root:${MYSQL_ROOT_PASSWORD}@mysql:3306/anti_fraud
      - SPARK_JDBC_URL=${SPARK_JDBC_URL}
      - DOLPHINSCHEDULER_URL=${DOLPHINSCHEDULER_URL}
    volumes:
      - ./backend:/app
      - spark_jobs:/opt/spark/jobs
    ports:
      - "50020:50020"
    depends_on:
      - mysql
    networks:
      - anti_fraud_network
    command: uvicorn backend.main:app --host 0.0.0.0 --port 50020 --workers 4

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: anti_fraud_frontend
    environment:
      - NEXT_PUBLIC_API_BASE=http://backend:50020
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - anti_fraud_network

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: anti_fraud_nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend
    networks:
      - anti_fraud_network

volumes:
  mysql_data:
  spark_jobs:

networks:
  anti_fraud_network:
    driver: bridge
```

#### 13.3.2 后端Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 50020

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "50020", "--workers", "4"]
```

#### 13.3.3 前端Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci

# 构建应用
COPY . .
RUN npm run build

# 生产镜像
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "start"]
```

---

## 14. 开发路线图

### 14.1 Phase 1: MVP核心功能 (4-6周)

#### Week 1-2: 基础架构
- [ ] 数据库模型设计和建表
- [ ] FastAPI项目脚手架搭建
- [ ] Next.js前端项目初始化
- [ ] Spark JDBC连接配置
- [ ] DolphinScheduler API集成测试

#### Week 3-4: 指标管理
- [ ] 指标CRUD API开发
- [ ] SQL验证器实现
- [ ] 指标执行器(试运行)
- [ ] 指标列表页面
- [ ] 指标编辑页面(含SQL编辑器)
- [ ] 指标预览功能

#### Week 5-6: 模型管理
- [ ] 模型CRUD API开发
- [ ] 规则引擎实现
- [ ] 规则配置JSON Schema定义
- [ ] 模型列表页面
- [ ] 可视化规则构建器
- [ ] PySpark代码生成器(基础版)

### 14.2 Phase 2: 增强功能 (4-6周)

#### Week 7-8: 指标组与动态SQL
- [ ] 指标组管理API
- [ ] 动态SQL生成器
- [ ] 行存到宽表转换逻辑
- [ ] 指标组批量执行
- [ ] 指标组管理页面

#### Week 9-10: 任务调度与监控
- [ ] DolphinScheduler任务创建
- [ ] 任务状态监控
- [ ] 执行历史记录
- [ ] 任务列表页面
- [ ] 任务详情和日志查看

#### Week 11-12: 回测功能
- [ ] 回测服务实现
- [ ] 性能指标计算
- [ ] 回测结果存储
- [ ] 回测配置页面
- [ ] 回测结果可视化

### 14.3 Phase 3: 优化与扩展 (3-4周)

#### Week 13-14: 系统优化
- [ ] SQL解析性能优化
- [ ] 指标缓存机制
- [ ] 前端加载性能优化
- [ ] 错误处理完善
- [ ] 日志系统优化

#### Week 15-16: 扩展功能
- [ ] PySpark代码支持(可选)
- [ ] 实时指标监控
- [ ] 告警规则配置
- [ ] 模型版本管理
- [ ] 指标血缘分析

### 14.4 Phase 4: 生产就绪 (2-3周)

#### Week 17-18: 测试与文档
- [ ] 单元测试覆盖
- [ ] 集成测试
- [ ] 压力测试
- [ ] 用户手册编写
- [ ] API文档完善

#### Week 19: 部署与上线
- [ ] Docker镜像构建
- [ ] 生产环境部署
- [ ] 数据迁移
- [ ] 用户培训
- [ ] 上线验收

### 14.5 里程碑检查点

```
Milestone 1 (Week 2):  ✓ 基础架构完成，能运行Hello World
Milestone 2 (Week 4):  ✓ 指标管理功能完成，能创建和试运行指标
Milestone 3 (Week 6):  ✓ 模型管理功能完成，能可视化定义规则
Milestone 4 (Week 8):  ✓ 指标组功能完成，能批量计算指标
Milestone 5 (Week 12): ✓ 回测功能完成，能评估模型性能
Milestone 6 (Week 16): ✓ 所有核心功能完成，进入测试阶段
Milestone 7 (Week 19): ✓ 生产环境上线
```

---

## 附录

### A. 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 指标 | Indicator | 从原始数据计算得到的统计特征，如"7天登录次数" |
| 指标组 | Indicator Group | 共享数据源的一组指标，可以批量计算 |
| 模型 | Model | 基于多个指标的组合规则，用于识别风险账户 |
| 规则引擎 | Rule Engine | 解析和执行规则配置的组件 |
| 回测 | Backtest | 使用历史数据验证模型效果的过程 |
| 宽表 | Wide Table | 每个账户一行，多个指标作为列的表结构 |
| 行存 | Row Format | 每个指标值一行的存储格式 |
| 命中 | Hit | 账户满足模型规则，被识别为风险 |

### B. 参考资料

1. **技术文档**
   - FastAPI官方文档: https://fastapi.tiangolo.com/
   - PySpark官方文档: https://spark.apache.org/docs/latest/api/python/
   - DolphinScheduler文档: https://dolphinscheduler.apache.org/

2. **设计参考**
   - 特征工程平台设计: Feast, Tecton
   - 规则引擎: Drools, Easy Rules
   - 实时风控: 阿里云实时风控方案

3. **开源项目**
   - Feast: Feature Store for ML
   - Great Expectations: 数据质量框架
   - Airflow: 工作流调度(DolphinScheduler类似)

### C. 联系与支持

- **项目负责人**: [待定]
- **技术支持**: [待定]
- **问题反馈**: [待定]

---

**文档结束**

