# 反诈指标与模型管理系统 - 设计摘要

## 📄 完整设计文档
**文件**: `anti_fraud_indicator_model_design.md`
**行数**: 3837行
**章节**: 14个主要章节 + 附录

---

## 🎯 系统定位

一个面向开发人员的**反诈指标与模型管理平台**,支持:
- ✅ 可视化定义指标(SQL)和模型(规则引擎)
- ✅ 指标组批量计算,减少冗余
- ✅ 自动生成PySpark Streaming代码
- ✅ 模型回测和性能评估
- ✅ DolphinScheduler任务调度集成

---

## 📊 核心架构

```
┌────────────────────────────────────────────┐
│  Web UI (Next.js + React + TypeScript)    │
│  - 指标管理  - 模型管理  - 任务监控       │
└─────────────────┬──────────────────────────┘
                  │ REST API
┌─────────────────▼──────────────────────────┐
│  Backend API (FastAPI + Python 3.11+)     │
│  - 指标服务  - 模型服务  - 调度服务       │
└──┬──────────┬──────────┬───────────────────┘
   │          │          │
   ▼          ▼          ▼
┌─────┐  ┌────────┐  ┌──────────────┐
│MySQL│  │ Spark  │  │ Dolphin      │
│元数据│  │ JDBC   │  │ Scheduler    │
└─────┘  └───┬────┘  └──────────────┘
             │
    ┌────────▼────────┐
    │  Spark 集群     │
    │  Streaming Jobs │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Hadoop + Hive   │
    │  数据存储       │
    └─────────────────┘
```

---

## 🗄️ 数据模型核心表

### 元数据库(MySQL)
1. **af_indicator_definition** - 指标定义表
2. **af_model_definition** - 模型定义表
3. **af_indicator_group** - 指标组定义表
4. **af_task_execution** - 任务执行记录表
5. **af_backtest_record** - 回测记录表

### 数据湖(Hive)
1. **indicator_result_row** - 指标结果表(行存)
2. **indicator_result_wide** - 指标结果表(宽表)
3. **model_hit_result** - 模型命中结果表

---

## 🔑 关键设计决策

### 1. 指标定义方式
**决策**: MVP阶段仅支持SQL,预留PySpark扩展
**理由**: 90%+场景SQL可覆盖,节省40%开发成本

### 2. 冗余计算优化
**决策**: 采用"指标组"概念批量计算
**实现**:
- 同组指标共享数据源
- 使用SQL STACK函数输出多个指标
- 行存储格式便于增量添加指标

### 3. 模型可视化定义
**决策**: 简化版规则引擎(表单式,非拖拽式)
**格式**: JSON配置存储规则
**支持**: AND/OR逻辑组合 + 6种比较操作符

### 4. 宽表生成策略
**方案1**: 使用PIVOT动态生成(简单场景)
**方案2**: 使用Apache Hudi支持Schema Evolution(推荐)

---

## 🚀 API设计亮点

**基础路径**: `/api/taosha/v1/anti-fraud`

### 核心端点
```
POST   /indicators              # 创建指标
POST   /indicators/{id}/dry-run # 试运行指标
POST   /indicators/{id}/publish # 发布到DS

POST   /models                  # 创建模型
POST   /models/{id}/generate-code # 生成PySpark代码
POST   /models/{id}/publish     # 部署Streaming任务

POST   /backtest                # 创建回测任务
GET    /backtest/{id}/result    # 获取回测结果
```

---

## 🎨 前端设计规范

遵循项目现有设计体系:
- **设计语言**: 现代扁平化,明暗双主题
- **组件库**: Radix UI + Tailwind CSS
- **状态管理**: React Context + hooks
- **响应式**: 移动端优先(断点768px)

### 核心页面
1. `/indicators` - 指标管理
2. `/models` - 模型管理
3. `/tasks` - 任务监控
4. `/backtest` - 回测分析

---

## 📦 技术栈总览

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| **前端** | Next.js 14 + React 18 + TypeScript | 现代化Web框架 |
| **后端** | FastAPI 0.116 + Python 3.11+ | 异步API框架 |
| **ORM** | SQLAlchemy 2.0 | 现代化ORM |
| **数据处理** | PySpark 3.5 + PyHive | 大数据计算 |
| **调度** | DolphinScheduler | 工作流调度 |
| **数据库** | MySQL 8.0 + Hive | 元数据+数据湖 |
| **消息队列** | Kafka | 实时流接入 |

---

## 🛣️ 开发路线图

### Phase 1: MVP核心功能 (4-6周)
- Week 1-2: 基础架构搭建
- Week 3-4: 指标管理功能
- Week 5-6: 模型管理功能

### Phase 2: 增强功能 (4-6周)
- Week 7-8: 指标组与动态SQL
- Week 9-10: 任务调度与监控
- Week 11-12: 回测功能

### Phase 3: 优化与扩展 (3-4周)
- Week 13-14: 系统优化
- Week 15-16: 扩展功能

### Phase 4: 生产就绪 (2-3周)
- Week 17-18: 测试与文档
- Week 19: 部署上线

**总计**: 13-19周 (约3-5个月)

---

## 💡 核心创新点

1. **指标组概念** - 通过STACK函数一次SQL输出多个指标,减少70%+重复计算
2. **规则引擎** - JSON配置驱动,业务人员可自助定义简单模型
3. **自动代码生成** - 从JSON规则自动生成PySpark Streaming代码
4. **回测评估** - 支持混淆矩阵、精确率、召回率等完整性能指标
5. **Schema Evolution** - 使用Hudi支持宽表动态增减字段

---

## 📖 文档章节索引

1. **项目概述** - 背景、目标、技术约束
2. **核心问题与解决方案** - 3个关键设计决策
3. **系统架构设计** - 整体架构图和模块划分
4. **数据库模型设计** - 完整DDL和关系设计
5. **后端API设计** - RESTful端点设计
6. **服务层架构** - 指标/模型/调度服务实现
7. **前端界面设计** - 页面结构和组件设计
8. **可视化规则引擎** - JSON配置格式和示例
9. **指标组与动态SQL** - 批量计算和宽表生成
10. **PySpark Streaming任务生成** - 代码模板和部署
11. **回测功能设计** - 评估流程和可视化
12. **任务调度集成** - DolphinScheduler集成
13. **部署架构** - 服务器规划和Docker配置
14. **开发路线图** - 分阶段实施计划

**附录**: 术语表、参考资料、联系支持

---

## 🔗 相关文档

- **需求原文**: `docs/new_m.md`
- **完整设计**: `docs/anti_fraud_indicator_model_design.md`
- **项目规范**: `CLAUDE.md`

---

**文档创建**: 2025-12-02
**版本**: v1.0.0
**状态**: ✅ 设计完成,待评审
