# 淘沙分析平台 产品需求文档(PRD)

**版本**: v1.0
**文档状态**: 草稿
**最后更新**: 2024年
**文档负责人**: [待填写]

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目目标与范围](#2-项目目标与范围)
3. [角色与权限定义](#3-角色与权限定义)
4. [用户故事](#4-用户故事)
5. [系统架构设计](#5-系统架构设计)
6. [数据模型设计](#6-数据模型设计)
7. [非功能需求](#7-非功能需求)
8. [技术选型](#8-技术选型)
9. [接口设计](#9-接口设计)
10. [UI/UX设计](#10-uiux设计)
11. [测试策略](#11-测试策略)

---

## 1. 项目概述

### 1.1 项目基本信息

| 项目属性 | 内容 |
|---------|------|
| **项目代号** | 淘沙 |
| **项目中文名** | 淘沙分析平台 |
| **项目英文名** | Taosha Analyze Platform |
| **项目类型** | 企业内部数据分析平台 |

### 1.2 项目简介

淘沙分析平台是一个服务于**非技术人员**的企业内部数据分析与赋能平台。平台围绕自然语言查询数据提供一系列配套服务，允许用户按照自身习惯输入自然语言，由系统关联表结构转换为合法的查询SQL，执行后将查询结果返回给用户。

**核心价值**：
- 降低数据查询门槛，让业务人员无需学习SQL即可获取数据
- 提升数据获取效率，从提需求→等待开发→获得结果，缩短为即时查询
- 构建企业数据知识库，沉淀业务术语和数据关系

### 1.3 目标用户

- **主要用户**：业务部门的非技术人员
- **次要用户**：数据管理员（负责元数据维护和权限管理）

---

## 2. 项目目标与范围

### 2.1 项目目标

#### 2.1.1 业务目标
- 降低数据查询门槛，使非技术人员能够自助完成80%的常规数据查询
- 减少数据团队重复性查询工作量，提升数据团队产能30%以上
- 缩短数据获取周期，从平均2-3天缩短至30分钟以内

#### 2.1.2 用户目标
- 用户可以使用自然语言描述查询需求
- 查询响应时间控制在2分钟以内（NL2SQL转换）
- SQL查询准确率达到85%以上
- 提供友好的错误提示和改进建议

#### 2.1.3 技术目标
- 构建可扩展的NL2SQL平台架构
- 支持多种数据源（MySQL、Spark SQL、DuckDB）
- 建立完善的元数据管理体系
- 实现知识库的自动更新机制

### 2.2 项目范围

#### 2.2.1 包含范围（In Scope）
✅ 自然语言转SQL查询
✅ 元数据管理（表、字段、关联、术语等）
✅ 查询历史记录和日志管理
✅ 查询收藏功能
✅ 用户反馈机制
✅ 数据主题和权限管理
✅ 基础的图表展示（表格、柱状图、折线图、饼图）
✅ 查询结果导出（Excel、CSV）

#### 2.2.2 不包含范围（Out of Scope）
❌ 复杂的BI可视化功能（拖拽式报表设计）
❌ 跨数据源的联合查询
❌ 数据写入、更新、删除操作
❌ 实时流数据查询
❌ 数据血缘分析
❌ 移动端APP（仅Web端）

#### 2.2.3 分期规划

**一期（MVP）**：
- 基础NL2SQL查询功能
- 元数据管理
- 查询历史和收藏
- 基础权限控制

**二期**：
- 查询结果的智能图表推荐
- 高级权限控制（行级、列级）
- 查询性能优化和缓存

### 2.3 成功指标

| 指标类型 | 指标名称 | 目标值 |
|---------|---------|--------|
| 用户采用率 | 活跃用户数 | 覆盖80%目标用户 |
| 查询准确率 | SQL生成准确率 | ≥85% |
| 性能指标 | NL2SQL转换时间 | ≤5秒 |
| 性能指标 | SQL执行时间 | ≤30秒（中等数据量） |
| 用户满意度 | 正面反馈比例 | ≥70% |
| 效率提升 | 查询需求完成周期 | 从2-3天降至30分钟 |

---

## 3. 角色与权限定义

### 3.1 系统角色

| 角色名称 | 角色代码 | 角色描述 |
|---------|---------|---------|
| **普通用户** | USER | 使用平台进行数据查询的业务人员 |
| **管理员** | ADMIN | 负责元数据管理、查看所有日志、权限管理 |

### 3.2 角色权限矩阵

| 功能模块 | 功能点 | 普通用户 | 管理员 |
|---------|-------|---------|--------|
| **查询功能** | 自然语言查询 | ✅ | ✅ |
| | 查看个人查询历史 | ✅ | ✅ |
| | 查看所有查询历史 | ❌ | ✅ |
| | 重新执行查询 | ✅ | ✅ |
| | 导出查询结果 | ❌ | ✅ |
| **收藏功能** | 收藏查询 | ✅ | ✅ |
| | 管理个人收藏 | ✅ | ✅ |
| **反馈功能** | 提交反馈 | ✅ | ✅ |
| | 查看所有反馈 | ❌ | ✅ |
| **元数据管理** | 表元数据管理 | ❌ | ✅ |
| | 字段元数据管理 | ❌ | ✅ |
| | 关联元数据管理 | ❌ | ✅ |
| | 管理员术语管理 | ❌ | ✅ |
| | 个人术语管理 | ✅ | ✅ |
| | 提示词模板管理 | ❌ | ✅ |
| | 数据主题管理 | ❌ | ✅ |
| | 权限控制管理 | ❌ | ✅ |
| **日志管理** | 查看个人日志 | ✅ | ✅ |
| | 查看所有日志 | ❌ | ✅ |
| **用户管理** | 用户管理 | ❌ | ✅ |
| | 角色管理 | ❌ | ✅ |

### 3.3 数据权限

#### 3.3.1 表级权限
- 通过**数据主题**和**权限控制**表实现
- 普通用户的角色会细分为更多的子角色，且每个用户可以拥有多个角色，多个角色的权限取交集
- 用户只能查询其有权限的数据主题下的表
- 公共主题对所有用户可见

#### 3.3.2 行级权限（二期）
- 预留行级权限控制机制
- 例如：销售人员只能查看自己区域的数据

#### 3.3.3 列级权限（二期）
- 预留列级权限控制机制
- 例如：敏感字段（工资、身份证）仅特定角色可见

---

## 4. 用户故事

### 4.1 查询相关

#### US-001: 选择查询范围
**作为** 普通用户
**我想** 快速选择我能查询的数据表
**以便** 系统能够理解我的查询上下文

**验收标准**：
- 提供数据主题单选功能和数据表多选功能，两者切换使用
- 数据主题和数据表是互斥的，只能选其中一项，可以做成切换的
- 无论是数据主题还是数据表都会包含公共主题的表（一般是配置表）
- 显示表的中文名和简要描述
- 默认不选择任何主题或表（首次使用需引导）

---

#### US-002: 自然语言查询
**作为** 普通用户
**我想** 输入自然语言就能得到查询结果
**以便** 不需要学习SQL就能获取数据

**验收标准**：
- 主页面有类似Google的搜索框
- 查询框支持3行输入，底部有输入提示
- 点击查询按钮触发查询
- 查询时页面不阻塞，可滚动查看进度
- 查询框悬浮显示，不会被滚动遮挡
- 显示查询结果表格
- 适合图形展示的结果自动生成图表（柱状图、折线图、饼图）

---

#### US-003: 查看查询进度
**作为** 普通用户
**我想** 实时查看查询进度
**以便** 了解查询的执行状态和预估完成时间

**验收标准**：
- 显示已完成节点的输入、输出、开始时间、结束时间、耗时
- 显示正在执行节点的名称和开始时间
- 进度条或百分比显示
- 可以取消正在执行的查询
- 错误时显示错误信息和建议

---

#### US-004: 查看查询详情（管理员）
**作为** 管理员
**我想** 查看每次查询的详细信息
**以便** 了解系统运行状况和优化查询质量

**验收标准**：
- 查看生成的查询SQL
- 查看每个步骤的详细日志
- 查看LLM的输入和输出
- 查看SQL执行计划（可选）
- 可以导出日志用于分析

---

### 4.2 历史与收藏

#### US-005: 查看历史查询
**作为** 普通用户
**我想** 再次进入页面后能看到历史查询记录
**以便** 快速重复之前的查询或参考历史结果

**验收标准**：
- 显示个人最近的查询记录
- 每条记录包含：查询时间、自然语言输入、查询状态、结果行数
- 管理员可以查看所有用户的查询记录
- 点击记录可查看详情（输入、SQL、结果）
- 最近10条记录可以点击"重算"，直接重新执行SQL
- 支持按时间、状态筛选
- 分页展示

---

#### US-006: 收藏查询
**作为** 普通用户
**我想** 收藏常用的查询
**以便** 快速复用常见的查询需求

**验收标准**：
- 查询成功后显示"收藏"按钮
- 点击收藏后，系统自动生成简短标题（基于查询内容）
- 用户可以编辑标题
- 保存后进入个人收藏夹

---

#### US-007: 使用收藏
**作为** 普通用户
**我想** 查看并使用收藏的查询
**以便** 快速执行常用查询

**验收标准**：
- 收藏夹显示所有个人收藏
- 每条收藏包含：标题、用户输入、生成的SQL
- 点击"执行"直接执行SQL，记录日志
- 点击"修改后执行"，带着历史信息进入查询页面
- 在查询页面中，历史信息只读，用户输入新的自然语言调整
- 支持删除收藏
- 支持编辑收藏标题

---

### 4.3 反馈相关

#### US-008: 提交查询反馈
**作为** 普通用户
**我想** 对查询结果进行反馈
**以便** 帮助系统改进查询质量

**验收标准**：
- 每次查询后（成功或失败）都有反馈入口
- 反馈包含评价类型：正面、负面、中性（使用图标或文字，不使用emoji）
- 可以填写文字评价内容
- 反馈提交后显示感谢提示
- 管理员可以查看所有用户反馈

---

### 4.4 元数据管理

#### US-009: 维护表元数据
**作为** 管理员
**我想** 维护表元数据
**以便** 系统能够理解数据库中的表结构

**验收标准**：
- 新增、编辑、删除表元数据
- 表元数据包含：表中文名、表英文名、数据源、数据更新方式（增量/全量/其他）、表描述
- 修改后自动更新知识库
- 记录变更历史

---

#### US-010: 维护字段元数据
**作为** 管理员
**我想** 维护字段元数据
**以便** 系统能够理解字段的含义和用法

**验收标准**：
- 新增、编辑、删除字段元数据
- 字段元数据包含：
  - 字段中文名、字段英文名
  - 字段描述
  - 字段类型（数据库类型）
  - 业务字段类型（如：日期、金额、百分比）
  - 字段是否可用（不可用的字段不参与知识库训练）
  - 字段关联ID（格式：关联族|关联子族，如 acct_no|16）
  - 字段脱敏类型（id_no-身份证，mobile-手机号）
- 支持批量导入
- 修改后自动更新知识库
- 如果字段存在脱敏类型，且配置中脱敏开关打开，那么用户查询结果就会脱敏

---

#### US-011: 维护关联元数据
**作为** 管理员
**我想** 维护表之间的关联关系
**以便** 系统能够进行多表JOIN查询

**验收标准**：
- 新增、编辑、删除关联元数据
- 关联元数据包含：
  - 关联族（如 acct_no）
  - 关联子族（如 16、17）
  - 关联方式描述（如：acct_no|16 = LEFT(acct_no|17, 16)）
- 支持可视化的关联关系图（可选）
- 修改后自动更新知识库

---

#### US-012: 维护术语表
**作为** 管理员或普通用户
**我想** 维护术语表
**以便** 系统能够理解业务术语

**验收标准**：
- 管理员可以维护全局术语（所有用户可见，不可编辑）
- 普通用户可以维护个人术语（仅自己可见和编辑）
- 术语包含：术语名称、术语描述
- 当用户术语与管理员术语重名时，优先使用用户术语
- 修改后自动更新知识库

---

#### US-013: 维护提示词模板
**作为** 管理员
**我想** 维护提示词模板
**以便** 优化LLM的输出质量

**验收标准**：
- 新增、编辑、删除提示词模板
- 模板包含：模板名称、模板内容、变量清单
- 支持变量占位符（如 {table_schema}、{user_question}）
- 当配置的模板里的变量与变量清单不匹配的时候校验不通过
- 可以指定不同节点使用不同模板
- 支持版本管理（可选）

---

#### US-014: 维护数据主题
**作为** 管理员
**我想** 维护数据主题
**以便** 对表进行分类和权限管理

**验收标准**：
- 新增、编辑、删除数据主题
- 数据主题包含：主题名称、主题描述、主题表清单
- 区分公共主题和一般主题
- 公共主题在任何查询中都生效
- 用户选择主题A时，实际可查询表 = 主题A的表 + 公共主题的表

---

#### US-015: 维护权限控制
**作为** 管理员
**我想** 维护用户权限
**以便** 控制用户对数据的访问

**验收标准**：
- 配置角色的权限
- 权限类型：数据主题权限、数据表权限、菜单权限
- 权限清单：具体的主题ID、表ID、菜单ID列表
- 支持批量授权
- 权限变更实时生效
- 普通用户的角色会细分为更多的子角色，且每个用户可以拥有多个角色，多个角色的权限取交集

---

### 4.5 系统功能

#### US-016: 知识库自动更新
**作为** 管理员
**我想** 元数据更新后自动更新知识库
**以便** 无需手动触发知识库训练

**验收标准**：
- 每项元数据记录变动时间
- 定时任务定期扫描（如每5分钟）
- 发现变动时间晚于上次扫描时间的记录
- 按ID删除知识库中的旧数据
- 使用最新数据重新训练
- 显示训练状态和进度
- 训练失败时告警

---

#### US-017: 查询流程选择
**作为** 普通用户
**我想** 选择不同的查询流程
**以便** 根据查询复杂度优化查询体验

**验收标准**：
- 查询按钮旁有流程选择开关
- 流程1：校验用户输入是否清晰 → 生成SQL → 执行SQL → 返回结果（失败则带失败信息重新生成SQL）
- 流程2：生成SQL → 校验SQL和用户输入是否匹配 → 执行SQL → 返回结果（失败则带失败信息重新生成SQL）
- 默认使用流程2

---

#### US-018: 查询输入校验反馈
**作为** 普通用户
**我想** 当输入不清晰时得到明确提示
**以便** 我能够改进查询语句

**验收标准**：
- 当系统判断输入不清晰时，停止查询
- 明确告知不清晰的原因（如：缺少时间范围、指标不明确）
- 给出改进建议（如：请指定查询的时间范围）
- 用户可以根据建议修改后重新查询

---

#### US-019: 导出查询结果
**作为** 管理员
**我想** 导出查询结果
**以便** 在Excel中进一步分析或分享给同事

**验收标准**：
- 查询成功后显示"导出"按钮（默认只对管理员开放）
- 支持导出为Excel格式（.xlsx）
- 支持导出为CSV格式（.csv）
- 最大支持导出10,000行
- 超过10,000行时提示并导出前10,000行
- 导出文件名包含查询时间

---

## 5. 系统架构设计

### 5.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│                    (Vue3 + Vite)                            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                      API网关层                               │
│                   (FastAPI / Flask)                         │
│              - 认证鉴权 - 请求路由 - 限流                      │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌─────▼──────┐  ┌─────▼──────────┐
│  NL2SQL服务   │  │ 元数据服务  │  │  查询引擎服务   │
│ (LangGraph)  │  │            │  │   (Vanna)      │
│              │  │            │  │                │
│ - 意图识别   │  │ - 元数据CRUD│  │ - SQL执行      │
│ - SQL生成    │  │ - 知识库训练│  │ - 结果处理     │
│ - 结果验证   │  │ - 权限校验  │  │ - 缓存管理     │
└──────┬───────┘  └─────┬──────┘  └─────┬──────────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────────┐
│  向量数据库   │ │ 元数据库    │ │  业务数据库     │
│  (Chroma)    │ │ (MySQL)    │ │ (MySQL/Spark)  │
│              │ │            │ │                │
│ - 表结构向量  │ │ - 表元数据  │ │ - 业务数据      │
│ - 字段向量    │ │ - 字段元数据│ │                │
│ - 术语向量    │ │ - 用户数据  │ │                │
└──────────────┘ └────────────┘ └────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      外部服务层                              │
│                                                             │
│  ┌──────────┐                                              │
│  │   LLM    │                                              │
│  │(GPT-4等) │                                              │
│  └──────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 核心流程设计

#### 5.2.1 查询流程1：输入校验优先

```
用户输入自然语言
    ↓
选择数据主题/表
    ↓
【节点1】意图识别与输入校验
    ├─ 输入: 用户自然语言 + 表结构
    ├─ 处理: LLM判断输入是否清晰
    └─ 输出: 清晰度评分 + 不清晰原因 + 改进建议
    ↓
是否清晰？
    ├─ 否 → 返回改进建议给用户 → 结束
    └─ 是 → 继续
        ↓
【节点2】SQL生成
    ├─ 输入: 用户自然语言 + 表结构 + 术语表
    ├─ 处理: LLM生成SQL（RAG检索相关表结构）
    └─ 输出: 生成的SQL
    ↓
【节点3】SQL执行
    ├─ 输入: SQL语句
    ├─ 处理: 查询引擎执行SQL
    └─ 输出: 查询结果 或 错误信息
    ↓
是否成功？
    ├─ 是 → 【节点4】结果处理 → 返回结果
    └─ 否 → 【节点2】带错误信息重新生成SQL（最多重试3次）
```

#### 5.2.2 查询流程2：SQL生成优先（默认）

```
用户输入自然语言
    ↓
选择数据主题/表
    ↓
【节点1】SQL生成
    ├─ 输入: 用户自然语言 + 表结构 + 术语表
    ├─ 处理: LLM生成SQL（RAG检索相关表结构）
    └─ 输出: 生成的SQL
    ↓
【节点2】SQL与输入匹配度校验
    ├─ 输入: 用户自然语言 + 生成的SQL
    ├─ 处理: LLM判断SQL是否匹配用户意图
    └─ 输出: 匹配度评分 + 不匹配原因 + 改进建议
    ↓
是否匹配？
    ├─ 否 → 返回改进建议给用户 → 结束
    └─ 是 → 继续
        ↓
【节点3】SQL执行
    ├─ 输入: SQL语句
    ├─ 处理: 查询引擎执行SQL
    └─ 输出: 查询结果 或 错误信息
    ↓
是否成功？
    ├─ 是 → 【节点4】结果处理 → 返回结果
    └─ 否 → 【节点1】带错误信息重新生成SQL（最多重试3次）
```

#### 5.2.3 元数据同步流程

```
管理员修改元数据
    ↓
更新元数据库
    ├─ 记录变动时间(updated_at)
    └─ 触发变更标记
    ↓
定时任务扫描（每5分钟）
    ├─ 查询updated_at > last_scan_time的记录
    └─ 发现变更记录
    ↓
知识库更新
    ├─ 按ID删除向量数据库中的旧记录
    ├─ 重新生成embedding
    ├─ 写入向量数据库
    └─ 更新last_scan_time
    ↓
更新完成
```

#### 5.2.4 知识库训练流程

```
元数据准备
    ├─ 表元数据: 表名、描述、字段列表
    ├─ 字段元数据: 字段名、类型、描述、示例值
    ├─ 关联元数据: 表关联关系
    └─ 术语表: 术语名、描述
    ↓
生成训练文档
    ├─ DDL语句生成
    ├─ 示例查询生成
    ├─ 字段说明文档生成
    └─ 术语文档生成
    ↓
Embedding生成
    ├─ 使用Embedding模型（可配置）
    └─ 生成向量
    ↓
存入向量数据库(Chroma)
    ├─ 每项数据带唯一ID（如 table_2）
    └─ 支持增量更新
```

### 5.3 技术组件说明

#### 5.3.1 LangGraph工作流引擎
- **作用**：编排NL2SQL的多步骤流程
- **核心能力**：
  - 支持条件分支（输入是否清晰？SQL是否成功？）
  - 支持循环重试（SQL生成失败重试）
  - 支持节点间数据传递
  - 支持流式输出进度

#### 5.3.2 Vanna框架
- **作用**：提供NL2SQL的基础能力
- **核心能力**：
  - RAG检索相关表结构
  - SQL生成和优化
  - 查询结果处理
- **权限控制**：
  - 训练时每项数据带唯一ID（如 table_2）
  - 查询时重写向量数据库查询，根据权限限定用户能够使用的元数据ID
  - 按语义搜索，但只能返回ID限定范围内的内容

#### 5.3.3 向量数据库(Chroma)
- **作用**：存储元数据的向量表示
- **存储内容**：
  - 表结构向量
  - 字段描述向量
  - 术语向量
  - 历史查询SQL向量（用于相似查询推荐）
- **支持在配置文件中配置其他embedding模型**

#### 5.3.4 缓存层（内存缓存）
- **作用**：缓存查询进度和结果
- **使用Python内存缓存（可使用三方库）**
- **缓存内容**：
  - 任务进度
  - 查询结果（TTL 1小时）
  - 用户会话

#### 5.3.5 认证方案
- **测试环境**：
  - 传入base64编码过的header
  - 解码后是JSON，包含认证信息（用户名、角色ID、部门、失效时间等）
- **生产环境**：由外部修改
- **预留接口**：支持企业SSO/LDAP集成

### 5.4 代码复用策略

为了减少流程1和流程2的代码冗余：

```python
# 节点设计为可复用的函数
def node_input_validation(state):
    """输入校验节点"""
    pass

def node_sql_generation(state):
    """SQL生成节点"""
    pass

def node_sql_validation(state):
    """SQL校验节点"""
    pass

def node_sql_execution(state):
    """SQL执行节点"""
    pass

# 流程1
workflow_1 = StateGraph()
workflow_1.add_node("input_validation", node_input_validation)
workflow_1.add_node("sql_generation", node_sql_generation)
workflow_1.add_node("sql_execution", node_sql_execution)
workflow_1.add_edge("input_validation", "sql_generation")
workflow_1.add_edge("sql_generation", "sql_execution")

# 流程2
workflow_2 = StateGraph()
workflow_2.add_node("sql_generation", node_sql_generation)
workflow_2.add_node("sql_validation", node_sql_validation)
workflow_2.add_node("sql_execution", node_sql_execution)
workflow_2.add_edge("sql_generation", "sql_validation")
workflow_2.add_edge("sql_validation", "sql_execution")
```

---

## 6. 数据模型设计

### 6.1 数据库设计原则

- 元数据库使用MySQL（生产）/ SQLite（测试）
- 所有表使用`id`作为主键（BIGINT AUTO_INCREMENT）
- 所有表包含`created_at`和`updated_at`字段
- 软删除使用`is_deleted`字段（0-未删除，1-已删除）
- 字段命名使用下划线命名法（snake_case）
- 元数据表都以metadata开头

### 6.2 核心表设计

#### 6.2.1 角色管理

##### sys_role (角色表)
```sql
CREATE TABLE sys_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id VARCHAR(50) NOT NULL UNIQUE COMMENT '角色ID',
    role_type VARCHAR(20) NOT NULL COMMENT '角色类型(admin-管理员,org-机构角色,user-用户角色)',
    role_name VARCHAR(100) NOT NULL COMMENT '角色名称',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role_id (role_id),
    INDEX idx_role_type (role_type)
) COMMENT='角色表';
```

#### 6.2.2 元数据管理

##### metadata_table (表元数据)
```sql
CREATE TABLE metadata_table (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    table_name_cn VARCHAR(100) NOT NULL COMMENT '表中文名',
    table_name_en VARCHAR(100) NOT NULL COMMENT '表英文名',
    data_source VARCHAR(50) NOT NULL COMMENT '数据源(mysql,sparksql,duckdb)',
    update_method VARCHAR(20) COMMENT '数据更新方式(incremental,full,other)',
    table_description TEXT COMMENT '表描述',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_table_name (table_name_en, data_source),
    INDEX idx_updated_at (updated_at)
) COMMENT='表元数据';
```

##### metadata_field (字段元数据)
```sql
CREATE TABLE metadata_field (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    table_id BIGINT NOT NULL COMMENT '所属表ID',
    field_name_cn VARCHAR(100) COMMENT '字段中文名',
    field_name_en VARCHAR(100) NOT NULL COMMENT '字段英文名',
    field_description TEXT COMMENT '字段描述',
    field_type VARCHAR(50) COMMENT '字段类型(数据库类型)',
    business_type VARCHAR(50) COMMENT '业务字段类型',
    is_active TINYINT DEFAULT 1 COMMENT '字段是否可用',
    association_id VARCHAR(100) COMMENT '字段关联ID(格式:关联族|关联子族)',
    desensitization_type VARCHAR(20) COMMENT '脱敏类型(id_no-身份证,mobile-手机号)',
    sample_values TEXT COMMENT '示例值(JSON数组)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_table_id (table_id),
    INDEX idx_updated_at (updated_at)
) COMMENT='字段元数据';
```

##### metadata_association (关联元数据)
```sql
CREATE TABLE metadata_association (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    association_family VARCHAR(100) NOT NULL COMMENT '关联族',
    association_subfamily VARCHAR(100) NOT NULL COMMENT '关联子族',
    association_method TEXT COMMENT '关联方式描述',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_association (association_family, association_subfamily),
    INDEX idx_updated_at (updated_at)
) COMMENT='关联元数据';
```

##### metadata_glossary (术语表)
```sql
CREATE TABLE metadata_glossary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    term_name VARCHAR(100) NOT NULL COMMENT '术语名称',
    term_description TEXT COMMENT '术语描述',
    term_type VARCHAR(20) DEFAULT 'admin' COMMENT '术语类型(admin-管理员,user-用户)',
    user_id BIGINT COMMENT '所属用户ID(term_type=user时)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_term_name (term_name),
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
) COMMENT='术语表';
```

##### metadata_prompt_template (提示词模板)
```sql
CREATE TABLE metadata_prompt_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
    template_content TEXT NOT NULL COMMENT '模板内容',
    template_type VARCHAR(50) COMMENT '模板类型(input_validation,sql_generation等)',
    variable_list TEXT COMMENT '变量清单(JSON数组)',
    version VARCHAR(20) DEFAULT 'v1.0' COMMENT '版本号',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_template_type (template_type)
) COMMENT='提示词模板';
```

##### metadata_data_theme (数据主题)
```sql
CREATE TABLE metadata_data_theme (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    theme_name VARCHAR(100) NOT NULL COMMENT '主题名称',
    theme_description TEXT COMMENT '主题描述',
    theme_type VARCHAR(20) DEFAULT 'normal' COMMENT '主题类型(public-公共,normal-一般)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='数据主题';
```

##### metadata_theme_table (主题表关联)
```sql
CREATE TABLE metadata_theme_table (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    theme_id BIGINT NOT NULL COMMENT '主题ID',
    table_id BIGINT NOT NULL COMMENT '表ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_theme_table (theme_id, table_id),
    INDEX idx_theme_id (theme_id),
    INDEX idx_table_id (table_id)
) COMMENT='主题表关联';
```

##### metadata_lineage (数据血缘)
```sql
CREATE TABLE metadata_lineage (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    input_tables VARCHAR(500) NOT NULL COMMENT '输入表名(多个用逗号分割)',
    output_table VARCHAR(200) NOT NULL COMMENT '输出表名',
    process_sql TEXT COMMENT '处理SQL',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_output_table (output_table)
) COMMENT='数据血缘(仅查询,由其他程序同步)';
```

#### 6.2.3 权限控制

##### sys_permission (权限控制)
```sql
CREATE TABLE sys_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL COMMENT '角色ID',
    permission_type VARCHAR(50) NOT NULL COMMENT '权限类型(theme,table,menu)',
    resource_id BIGINT COMMENT '资源ID(主题ID,表ID,菜单ID)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_role_id (role_id),
    INDEX idx_permission_type (permission_type)
) COMMENT='权限控制';
```

#### 6.2.4 查询相关

##### nlquery_task (查询任务记录)
```sql
CREATE TABLE nlquery_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(50) NOT NULL UNIQUE COMMENT '任务ID(UUID)',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    user_question TEXT NOT NULL COMMENT '用户自然语言输入',
    workflow_type TINYINT DEFAULT 2 COMMENT '工作流类型(1-流程1,2-流程2)',
    selected_theme_id BIGINT COMMENT '选择的数据主题ID',
    selected_table_ids TEXT COMMENT '选择的表ID列表(JSON数组)',
    task_status VARCHAR(20) DEFAULT 'running' COMMENT '任务状态(running,success,failed,cancelled)',
    progress_data TEXT COMMENT '进度数据(JSON)',
    generated_sql TEXT COMMENT '生成的SQL',
    sql_execution_result TEXT COMMENT 'SQL执行结果(JSON)',
    result_row_count INT COMMENT '结果行数',
    error_message TEXT COMMENT '错误信息',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_ms INT COMMENT '耗时(毫秒)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (task_status),
    INDEX idx_start_time (start_time)
) COMMENT='查询任务记录';
```

##### nlquery_node_log (查询节点日志)
```sql
CREATE TABLE nlquery_node_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    node_name VARCHAR(100) NOT NULL COMMENT '节点名称',
    node_input TEXT COMMENT '节点输入(JSON)',
    node_output TEXT COMMENT '节点输出(JSON)',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_ms INT COMMENT '耗时(毫秒)',
    status VARCHAR(20) COMMENT '状态(success,failed)',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_node_name (node_name)
) COMMENT='查询节点日志';
```

##### nlquery_favorite (查询收藏)
```sql
CREATE TABLE nlquery_favorite (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    favorite_title VARCHAR(200) NOT NULL COMMENT '收藏标题',
    user_question TEXT NOT NULL COMMENT '用户自然语言输入',
    generated_sql TEXT NOT NULL COMMENT '生成的SQL',
    selected_theme_id BIGINT COMMENT '选择的数据主题ID',
    selected_table_ids TEXT COMMENT '选择的表ID列表(JSON数组)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) COMMENT='查询收藏';
```

##### nlquery_feedback (查询反馈)
```sql
CREATE TABLE nlquery_feedback (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(50) NOT NULL COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    feedback_type VARCHAR(20) NOT NULL COMMENT '反馈类型(positive,negative,neutral)',
    feedback_content TEXT COMMENT '反馈内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_feedback_type (feedback_type)
) COMMENT='查询反馈';
```

#### 6.2.5 系统配置

##### sys_config (系统配置)
```sql
CREATE TABLE sys_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_description TEXT COMMENT '配置描述',
    config_type VARCHAR(50) COMMENT '配置类型(llm,database,system)',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_type (config_type)
) COMMENT='系统配置';
```

##### knowbase_sync_log (知识库同步日志)
```sql
CREATE TABLE knowbase_sync_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sync_type VARCHAR(50) COMMENT '同步类型(table,field,association,glossary)',
    resource_id BIGINT COMMENT '资源ID',
    sync_status VARCHAR(20) COMMENT '同步状态(success,failed)',
    error_message TEXT COMMENT '错误信息',
    last_scan_time DATETIME COMMENT '上次扫描时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sync_type (sync_type),
    INDEX idx_resource_id (resource_id)
) COMMENT='知识库同步日志';
```

### 6.3 实体关系图(ERD)

```
角色管理:
sys_role (独立)

元数据模块:
metadata_table ──1:N── metadata_field
    │
    └──N:N── metadata_data_theme (through metadata_theme_table)

metadata_association (独立)

metadata_lineage (独立,只读)

metadata_glossary
    ├── term_type='admin' (全局)
    └── term_type='user' (关联user_id)

查询模块:
nlquery_task ──1:N── nlquery_node_log
    │
    └──1:N── nlquery_feedback

nlquery_favorite (关联user_id)
```

### 6.4 索引设计说明

**高频查询索引**：
- `nlquery_task.user_id + start_time`：查询个人历史
- `nlquery_task.task_status`：查询正在运行的任务
- `metadata_table.updated_at`：元数据同步扫描
- `metadata_field.table_id`：查询表的字段

**唯一约束**：
- `sys_role.role_id`
- `metadata_table.(table_name_en, data_source)`
- `nlquery_task.task_id`

---

## 7. 非功能需求

### 7.1 性能需求

| 性能指标 | 目标值 | 说明 |
|---------|-------|------|
| **NL2SQL转换时间** | ≤5秒 | 从提交查询到生成SQL |
| **SQL执行时间** | ≤30秒 | 中等数据量（<100万行） |
| **查询超时设置** | 60秒 | 超时自动取消并提示 |
| **并发支持** | 50+ | 支持50个并发用户查询 |
| **页面加载时间** | ≤2秒 | 首屏加载时间 |
| **API响应时间** | ≤500ms | 一般CRUD操作 |
| **大结果集处理** | 分页返回 | >1000行分页，单页最多1000行 |
| **导出限制** | 10000行 | 最大导出10000行数据 |

**性能优化策略**：
1. 查询结果缓存（内存缓存，TTL 1小时）
2. 相似查询推荐（减少重复计算）
3. SQL执行超时控制
4. 分页加载历史记录
5. 前端虚拟滚动（大数据表格）

### 7.2 安全需求

#### 7.2.1 用户认证
- **测试环境**：
  - 传入base64编码的header
  - 解码后包含认证信息（用户名、角色ID、部门、失效时间等）
- **生产环境**：由外部系统提供

#### 7.2.2 SQL注入防护
- **参数化查询**：所有SQL使用参数绑定
- **SQL语法检查**：生成的SQL进行语法校验
- **禁止操作**：禁止DROP、TRUNCATE、DELETE、UPDATE、INSERT等写操作
- **关键字过滤**：检测并拦截危险SQL关键字

#### 7.2.3 数据脱敏
- **敏感字段识别**：
  - 身份证号：显示前3位和后4位，中间*
  - 手机号：显示前3位和后4位，中间*
- **配置化脱敏规则**：在字段元数据中标记脱敏类型，配置中设置脱敏开关

#### 7.2.4 权限控制
- **RBAC模型**：基于角色的访问控制
- **数据权限**：
  - 表级权限：通过数据主题控制
  - 多角色权限：用户可拥有多个角色，权限取交集
  - 行级权限：预留接口（二期）
  - 列级权限：预留接口（二期）
- **API权限**：每个API接口校验用户权限

#### 7.2.5 审计日志
- **记录内容**：
  - 用户登录/登出
  - 所有查询操作（nlquery_task表）
  - 元数据变更（updated_at字段）
  - 权限变更
- **日志保留**：至少保留6个月

### 7.3 可用性需求

| 可用性指标 | 目标值 | 说明 |
|-----------|-------|------|
| **系统可用性** | 99% | 每月允许停机时间≤7.2小时 |
| **数据备份** | 每日 | 元数据库每日全量备份 |
| **备份保留** | 30天 | 备份数据保留30天 |
| **容错机制** | 自动重试 | LLM调用失败自动重试3次 |
| **优雅降级** | 提示用户 | LLM不可用时，提示稍后重试 |

**容错策略**：
1. LLM调用失败：重试3次，间隔1秒、2秒、4秒
2. 数据库连接失败：重试5次，使用连接池
3. SQL执行超时：自动取消查询，提示优化查询条件

### 7.4 可维护性

#### 7.4.1 代码规范
- **Python代码**：遵循PEP 8规范
  - 使用Black格式化
  - 使用Pylint静态检查
  - 类型注解（Type Hints）
- **JavaScript代码**：遵循ESLint规范
  - Airbnb风格
  - 使用Prettier格式化
  - TypeScript类型检查

#### 7.4.2 文档要求
- **API文档**：使用Swagger/OpenAPI自动生成
- **代码注释**：
  - 函数必须有docstring
  - 复杂逻辑必须有行内注释
- **用户手册**：提供完整的用户操作手册
- **开发文档**：
  - 项目README
  - 环境配置文档
  - 数据库设计文档

#### 7.4.3 日志管理
- **日志框架**：使用loguru（Python）、winston（Node.js）
- **日志级别**：DEBUG、INFO、WARNING、ERROR、CRITICAL
- **日志格式**：JSON格式，包含时间、级别、模块、消息、上下文
- **日志输出**：
  - 开发环境：控制台 + 文件
  - 生产环境：文件轮转（每日一个文件，保留90天）
- **日志内容**：
  - 所有API请求和响应
  - LLM调用记录
  - SQL执行记录
  - 错误堆栈

### 7.5 兼容性

#### 7.5.1 浏览器兼容性
| 浏览器 | 最低版本 |
|-------|---------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |

不支持IE浏览器。

#### 7.5.2 分辨率支持
- **最小分辨率**：1366x768
- **推荐分辨率**：1920x1080
- **响应式设计**：适配1366、1440、1920宽度

#### 7.5.3 数据库兼容
- **元数据库**：SQLite 3.35+（测试）、MySQL 5.7+（生产）
- **查询引擎**：DuckDB 0.8+（测试）、MySQL 5.7+、Spark SQL 3.0+（生产）

---

## 8. 技术选型

### 8.1 后端技术栈

| 技术组件 | 选型 | 版本 | 说明 |
|---------|------|------|------|
| **编程语言** | Python | 3.11+ | 主要开发语言 |
| **包管理** | uv | 最新版 | 快速的Python包管理器 |
| **Web框架** | FastAPI | 0.100+ | 高性能异步框架 |
| **工作流引擎** | LangGraph | 0.0.30+ | LLM应用工作流编排 |
| **NL2SQL框架** | Vanna | 0.3+ | NL2SQL基础框架 |
| **LLM SDK** | OpenAI/Anthropic | 最新版 | LLM调用 |
| **向量数据库** | ChromaDB | 0.4+ | 轻量级向量数据库 |
| **ORM** | SQLAlchemy | 2.0+ | 数据库ORM |
| **数据库驱动** | PyMySQL/asyncpg | 最新版 | MySQL/PostgreSQL驱动 |
| **缓存** | Python内存缓存 | - | 查询缓存和任务进度 |
| **日志** | Loguru | 0.7+ | 日志管理 |
| **配置管理** | PyYAML | 6.0+ | YAML配置文件解析 |
| **测试框架** | Pytest | 7.0+ | 单元测试和集成测试 |
| **代码质量** | Black/Pylint | 最新版 | 代码格式化和检查 |

### 8.2 前端技术栈

| 技术组件 | 选型 | 版本 | 说明 |
|---------|------|------|------|
| **编程语言** | TypeScript | 5.0+ | 类型安全的JavaScript |
| **包管理** | pnpm | 8.0+ | 快速的包管理器 |
| **框架** | Vue | 3.3+ | 渐进式前端框架 |
| **构建工具** | Vite | 4.0+ | 下一代前端构建工具 |
| **UI组件库** | DaisyUI | 最新版 | Tailwind CSS组件库 |
| **状态管理** | Pinia | 2.1+ | Vue状态管理 |
| **路由** | Vue Router | 4.2+ | 官方路由 |
| **HTTP客户端** | Axios | 1.5+ | HTTP请求库 |
| **图表库** | ECharts | 5.4+ | 数据可视化 |
| **WebSocket** | socket.io-client | 4.6+ | 实时通信 |
| **代码质量** | ESLint/Prettier | 最新版 | 代码检查和格式化 |
| **测试框架** | Vitest | 0.34+ | Vue单元测试 |

### 8.3 数据库

#### 8.3.1 元数据库
- **测试环境**：SQLite 3.35+
  - 文件路径：`backend/database/metadata.db`
  - 优点：无需安装、快速启动
- **生产环境**：MySQL 5.7+ / 8.0+
  - 字符集：utf8mb4
  - 排序规则：utf8mb4_unicode_ci

#### 8.3.2 查询引擎（业务数据库）
- **测试环境**：DuckDB 0.8+
  - 文件路径：`backend/database/business.duckdb`
  - 优点：支持SQL、性能优秀
- **生产环境**：
  - MySQL 5.7+ / 8.0+
  - Spark SQL 3.0+
  - 不支持跨引擎查询

### 8.4 LLM模型

**LLM配置支持**：
- **内网环境**：使用vLLM提供的OpenAI兼容接口
- **外网环境**：使用OpenRouter或硅基流动提供的OpenAI兼容接口
- **内置模型**：支持配置GGUF模型路径，程序在需要时自动启动并调用模型

**LLM配置示例**：
```yaml
llm:
  # 模式: api / local
  mode: api

  # API模式配置
  api:
    provider: openai  # openai, vllm, openrouter, siliconflow
    base_url: ${LLM_BASE_URL}  # 内网vLLM或外网服务URL
    api_key: ${LLM_API_KEY}
    model: gpt-4-turbo
    max_tokens: 2000
    temperature: 0.1
    timeout: 30
    retry_times: 3

  # 本地模型配置
  local:
    model_path: /path/to/model.gguf
    n_ctx: 4096
    n_threads: 8
  
  # Embedding模型配置
  embedding:
    provider: openai  # 可配置其他embedding模型
    model: text-embedding-ada-002
    base_url: ${EMBEDDING_BASE_URL}
    api_key: ${EMBEDDING_API_KEY}
```

### 8.5 缓存方案

**内存缓存使用场景**：
1. **任务进度缓存**：
   - Key: `task_progress:{task_id}`
   - Value: JSON格式的进度数据
   - TTL: 1小时

2. **查询结果缓存**：
   - Key: `query_result:{hash(sql)}`
   - Value: JSON格式的查询结果
   - TTL: 1小时

3. **用户会话**：
   - Key: `session:{user_id}`
   - Value: 用户会话信息
   - TTL: 7天

**可使用的Python缓存库**：
- cachetools
- functools.lru_cache
- diskcache

### 8.6 认证方案

**测试环境**：
```python
def parse_auth_header(header: str) -> dict:
    """
    解析base64编码的认证header
  
    Returns:
        {
            "username": "zhangsan",
            "role_ids": ["role_1", "role_2"],
            "department": "销售部",
            "department_id": "dept_001",
            "expire_time": 1234567890
        }
    """
    import base64
    import json
    decoded = base64.b64decode(header).decode('utf-8')
    return json.loads(decoded)
```

**生产环境**：由外部系统修改

### 8.7 项目目录结构

#### 8.7.1 后端目录结构
```
backend/
├── api/                        # API接口层
│   ├── __init__.py
│   ├── auth.py                # 认证接口
│   ├── nlquery.py             # 查询接口
│   ├── nlquery_favorite.py    # 收藏接口
│   ├── nlquery_feedback.py    # 反馈接口
│   ├── metadata.py            # 元数据接口
│   └── manager.py             # 管理接口
├── config/                     # 配置文件
│   ├── config.yaml            # 主配置文件
│   ├── config.dev.yaml        # 开发环境配置
│   └── config.prod.yaml       # 生产环境配置
├── database/                   # 测试数据库
│   ├── metadata.db            # SQLite元数据库
│   └── business.duckdb        # DuckDB业务数据库
├── logs/                       # 日志目录
│   ├── app.log               # 应用日志
│   └── error.log             # 错误日志
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── role.py               # 角色模型
│   ├── metadata.py           # 元数据模型
│   └── nlquery.py            # 查询模型
├── schemas/                    # Pydantic Schema
│   ├── __init__.py
│   ├── role.py
│   ├── metadata.py
│   └── nlquery.py
├── services/                   # 服务层
│   ├── query_engine/         # 查询引擎服务
│   │   ├── __init__.py
│   │   ├── base_engine.py    # 抽象引擎基类
│   │   ├── duckdb_engine.py  # DuckDB引擎
│   │   ├── mysql_engine.py   # MySQL引擎
│   │   ├── sparksql_engine.py# SparkSQL引擎
│   │   └── result_handler.py # 结果处理
│   ├── metadata_service/     # 元数据服务
│   │   ├── __init__.py
│   │   ├── table_service.py
│   │   ├── field_service.py
│   │   ├── association_service.py
│   │   ├── glossary_service.py
│   │   └── knowbase_sync_service.py  # 知识库同步
│   └── nl2sql_service/       # NL2SQL服务
│       ├── __init__.py
│       ├── workflow_1.py     # 查询流程1
│       ├── workflow_2.py     # 查询流程2
│       ├── nodes/            # LangGraph节点
│       │   ├── __init__.py
│       │   ├── input_validation.py
│       │   ├── sql_generation.py
│       │   ├── sql_validation.py
│       │   └── sql_execution.py
│       └── vanna_wrapper.py  # Vanna封装(含权限控制)
├── sql/                        # SQL建表语句
│   ├── sqlite/               # SQLite版本
│   │   └── init.sql
│   └── mysql/                # MySQL版本
│       └── init.sql
├── testcase/                   # 测试用例
│   ├── __init__.py
│   ├── test_api/             # API测试
│   ├── test_services/        # 服务测试
│   └── test_utils/           # 工具类测试
├── utils/                      # 工具类
│   ├── __init__.py
│   ├── config.py             # 配置工具类
│   ├── logger.py             # 日志工具类(loguru)
│   ├── db_utils.py           # 元数据库类(支持sqlite/mysql)
│   ├── auth_utils.py         # 认证工具
│   ├── cache_utils.py        # 缓存工具
│   └── common.py             # 通用工具
├── main.py                     # 应用入口
├── requirements.txt            # 依赖列表
└── pyproject.toml             # uv配置
```

**Vanna权限控制实现**：
```python
# services/nl2sql_service/vanna_wrapper.py

from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore

class PermissionControlledVanna(ChromaDB_VectorStore):
    """
    带权限控制的Vanna封装
  
    - 训练时每项数据带唯一ID（如 table_2）
    - 查询时根据用户权限限定可用的元数据ID
    - 按语义搜索，但只返回权限范围内的内容
    """
  
    def __init__(self, allowed_ids: list[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.allowed_ids = allowed_ids or []
  
    def get_similar_documents(self, question: str, n_results: int = 10) -> list[str]:
        """
        重写向量搜索方法，添加ID过滤
      
        Args:
            question: 用户问题
            n_results: 返回结果数量
          
        Returns:
            权限范围内的相似文档列表
        """
        # 执行语义搜索
        results = self._collection.query(
            query_texts=[question],
            n_results=n_results * 2,  # 多查询一些，过滤后可能不够
            include=["documents", "metadatas"]
        )
      
        # 过滤：只保留allowed_ids中的文档
        filtered_docs = []
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            doc_id = metadata.get("id", "")
            if doc_id in self.allowed_ids:
                filtered_docs.append(doc)
                if len(filtered_docs) >= n_results:
                    break
      
        return filtered_docs
```

#### 8.7.2 前端目录结构
```
frontend/
├── public/                     # 静态资源
│   └── favicon.ico
├── src/
│   ├── assets/               # 资源文件
│   │   ├── images/
│   │   └── styles/
│   ├── components/           # 通用组件
│   │   ├── QueryBox.vue      # 查询框组件
│   │   ├── ProgressViewer.vue # 进度查看器
│   │   ├── ResultTable.vue   # 结果表格
│   │   └── ThemeToggle.vue   # 主题切换
│   ├── views/                # 页面视图
│   │   ├── NLQueryPage.vue   # 查询页面
│   │   ├── MetadataPage.vue  # 元数据管理
│   │   │   ├── TableConfig.vue
│   │   │   ├── FieldConfig.vue
│   │   │   └── ...
│   │   ├── LogPage.vue       # 日志页面
│   │   └── FavoritePage.vue  # 收藏页面
│   ├── stores/               # Pinia状态管理
│   │   ├── user.ts           # 用户状态
│   │   ├── nlquery.ts        # 查询状态
│   │   └── metadata.ts       # 元数据状态
│   ├── api/                  # API调用
│   │   ├── auth.ts
│   │   ├── nlquery.ts
│   │   ├── metadata.ts
│   │   └── index.ts
│   ├── router/               # 路由
│   │   └── index.ts
│   ├── utils/                # 工具函数
│   │   ├── request.ts        # Axios封装
│   │   ├── auth.ts           # 认证工具
│   │   └── common.ts
│   ├── types/                # TypeScript类型
│   │   ├── user.ts
│   │   ├── nlquery.ts
│   │   └── metadata.ts
│   ├── App.vue               # 根组件
│   └── main.ts               # 应用入口
├── .env.development            # 开发环境变量
├── .env.production             # 生产环境变量
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 9. 接口设计

### 9.1 接口规范

#### 9.1.1 RESTful API规范
- **URL设计**：
  - 统一前缀：`/api/taosha/v1/`
  - 使用名词复数形式：`/api/taosha/v1/users`、`/api/taosha/v1/tables`
  - 使用kebab-case：`/api/taosha/v1/data-themes`

- **HTTP方法**：
  - GET：查询资源
  - POST：创建资源或执行操作

- **HTTP状态码**：
  - 200：成功
  - 201：创建成功
  - 400：请求参数错误
  - 401：未认证
  - 403：无权限
  - 404：资源不存在
  - 500：服务器错误

#### 9.1.2 统一响应格式
```json
{
  "code": 0,           // 业务状态码，0表示成功
  "message": "success", // 提示信息
  "data": {},          // 响应数据
  "timestamp": 1234567890  // 时间戳
}
```

**错误响应格式**：
```json
{
  "code": 1001,
  "message": "用户名或密码错误",
  "data": null,
  "timestamp": 1234567890
}
```

#### 9.1.3 分页响应格式
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],       // 数据列表
    "total": 100,      // 总记录数
    "page": 1,         // 当前页
    "page_size": 20,   // 每页大小
    "total_pages": 5   // 总页数
  },
  "timestamp": 1234567890
}
```

#### 9.1.4 错误码定义
```python
class ErrorCode:
    SUCCESS = 0
  
    # 认证相关 1xxx
    AUTH_FAILED = 1001        # 认证失败
    TOKEN_EXPIRED = 1002      # Token过期
    TOKEN_INVALID = 1003      # Token无效
    NO_PERMISSION = 1004      # 无权限
  
    # 参数相关 2xxx
    PARAM_MISSING = 2001      # 缺少参数
    PARAM_INVALID = 2002      # 参数格式错误
  
    # 业务相关 3xxx
    USER_NOT_FOUND = 3001     # 用户不存在
    TABLE_NOT_FOUND = 3002    # 表不存在
    QUERY_FAILED = 3003       # 查询失败
    SQL_GENERATION_FAILED = 3004  # SQL生成失败
  
    # 系统相关 5xxx
    INTERNAL_ERROR = 5000     # 内部错误
    DATABASE_ERROR = 5001     # 数据库错误
    LLM_ERROR = 5002          # LLM调用错误
```

### 9.2 核心接口清单

#### 9.2.1 认证接口

##### POST /api/taosha/v1/auth/login
**描述**：用户登录

**请求**：
```json
{
  "username": "zhangsan",
  "password": "password123"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJ...",
    "user": {
      "id": 123,
      "username": "zhangsan",
      "real_name": "张三",
      "roles": ["USER", "ANALYST"]
    }
  }
}
```

---

##### POST /api/taosha/v1/auth/logout
**描述**：用户登出

**请求**：无请求体，Header中携带Token

**响应**：
```json
{
  "code": 0,
  "message": "success"
}
```

---

#### 9.2.2 查询接口

##### POST /api/taosha/v1/nlquery/submit
**描述**：提交查询任务

**请求**：
```json
{
  "user_question": "查询最近一个月的销售额",
  "workflow_type": 2,
  "selected_theme_id": 10,
  "selected_table_ids": [1, 2, 3]
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-xxxx-xxxx"
  }
}
```

是的，我没有生成完整。由于文档篇幅较长，让我继续完成剩余部分：

---

##### GET /api/taosha/v1/nlquery/progress/{task_id}
**描述**：查询任务进度

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-xxxx",
    "status": "running",
    "progress": {
      "current_node": "sql_generation",
      "completed_nodes": [
        {
          "node_name": "input_validation",
          "start_time": "2024-01-01 10:00:00",
          "end_time": "2024-01-01 10:00:02",
          "duration_ms": 2000,
          "status": "success"
        }
      ]
    }
  }
}
```

---

##### GET /api/taosha/v1/nlquery/result/{task_id}
**描述**：获取查询结果

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-xxxx",
    "status": "success",
    "generated_sql": "SELECT ...",
    "result": {
      "columns": ["month", "sales_amount"],
      "rows": [
        ["2024-01", 100000],
        ["2024-02", 120000]
      ],
      "row_count": 2
    },
    "chart_config": {
      "type": "line",
      "x_axis": "month",
      "y_axis": "sales_amount"
    }
  }
}
```

---

##### POST /api/taosha/v1/nlquery/cancel/{task_id}
**描述**：取消查询任务

**响应**：
```json
{
  "code": 0,
  "message": "success"
}
```

---

##### GET /api/taosha/v1/nlquery/history
**描述**：查询历史记录

**请求参数**：
- `page`: 页码（默认1）
- `page_size`: 每页大小（默认20）
- `status`: 过滤状态（可选）

**响应**：分页格式，items为查询任务列表

---

##### POST /api/taosha/v1/nlquery/rerun/{task_id}
**描述**：重新执行查询（直接执行SQL）

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "new-uuid-xxxx"
  }
}
```

---

##### POST /api/taosha/v1/nlquery/export/{task_id}
**描述**：导出查询结果（管理员）

**请求**：
```json
{
  "format": "xlsx"  // xlsx, csv
}
```

**响应**：文件流（Content-Type: application/octet-stream）

---

#### 9.2.3 收藏接口

##### POST /api/taosha/v1/nlquery/favorite
**描述**：添加收藏

**请求**：
```json
{
  "task_id": "uuid-xxxx",
  "favorite_title": "月度销售统计"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "favorite_id": 123
  }
}
```

---

##### GET /api/taosha/v1/nlquery/favorite
**描述**：获取收藏列表

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 123,
        "favorite_title": "月度销售统计",
        "user_question": "查询最近一个月的销售额",
        "generated_sql": "SELECT ...",
        "created_at": "2024-01-01 10:00:00"
      }
    ]
  }
}
```

---

##### POST /api/taosha/v1/nlquery/favorite/{favorite_id}/update
**描述**：更新收藏（修改标题）

**请求**：
```json
{
  "favorite_title": "新标题"
}
```

---

##### POST /api/taosha/v1/nlquery/favorite/{favorite_id}/delete
**描述**：删除收藏

---

##### POST /api/taosha/v1/nlquery/favorite/{favorite_id}/execute
**描述**：执行收藏的查询

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-xxxx"
  }
}
```

---

#### 9.2.4 反馈接口

##### POST /api/taosha/v1/nlquery/feedback
**描述**：提交查询反馈

**请求**：
```json
{
  "task_id": "uuid-xxxx",
  "feedback_type": "positive",  // positive, negative, neutral
  "feedback_content": "查询结果准确，很好用"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "感谢您的反馈"
}
```

---

##### GET /api/taosha/v1/nlquery/feedback
**描述**：获取反馈列表（管理员）

**请求参数**：
- `page`: 页码
- `page_size`: 每页大小
- `feedback_type`: 过滤类型（可选）

**响应**：分页格式

---

#### 9.2.5 元数据接口

##### GET /api/taosha/v1/metadata/tables
**描述**：获取表列表

**请求参数**：
- `data_source`: 数据源（可选）
- `is_active`: 是否启用（可选）

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "table_name_cn": "订单表",
        "table_name_en": "order",
        "data_source": "mysql",
        "table_description": "存储订单信息"
      }
    ]
  }
}
```

---

##### POST /api/taosha/v1/metadata/tables
**描述**：新增表元数据

**请求**：
```json
{
  "table_name_cn": "订单表",
  "table_name_en": "order",
  "data_source": "mysql",
  "update_method": "incremental",
  "table_description": "存储订单信息"
}
```

---

##### POST /api/taosha/v1/metadata/tables/{table_id}/update
**描述**：更新表元数据

---

##### POST /api/taosha/v1/metadata/tables/{table_id}/delete
**描述**：删除表元数据（软删除）

---

##### GET /api/taosha/v1/metadata/fields
**描述**：获取字段列表

**请求参数**：
- `table_id`: 表ID（必填）

---

##### POST /api/taosha/v1/metadata/fields
**描述**：新增字段元数据

**请求**：
```json
{
  "table_id": 1,
  "field_name_cn": "订单金额",
  "field_name_en": "order_amount",
  "field_type": "DECIMAL(10,2)",
  "business_type": "amount",
  "field_description": "订单总金额",
  "is_active": 1,
  "association_id": null,
  "desensitization_type": null
}
```

---

**其他元数据接口**：
- 关联元数据：`/api/taosha/v1/metadata/associations`
- 术语表：`/api/taosha/v1/metadata/glossary`
- 提示词模板：`/api/taosha/v1/metadata/prompts`
- 数据主题：`/api/taosha/v1/metadata/themes`
- 权限控制：`/api/taosha/v1/metadata/permissions`
- 数据血缘：`/api/taosha/v1/metadata/lineage`（只读）

接口设计类似，不再赘述。

---

##### POST /api/taosha/v1/metadata/import
**描述**：批量导入元数据（Excel）

**请求**：
- Content-Type: multipart/form-data
- 文件：Excel文件
- 参数：import_type（table, field, glossary）

---

##### GET /api/taosha/v1/metadata/knowbase-sync-status
**描述**：获取知识库同步状态

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "last_sync_time": "2024-01-01 10:00:00",
    "pending_sync_count": 5,
    "syncing": false
  }
}
```

---

##### POST /api/taosha/v1/metadata/knowbase-sync-trigger
**描述**：手动触发知识库同步

---

#### 9.2.6 日志接口

##### GET /api/taosha/v1/logs/nlquery
**描述**：查询日志列表

**请求参数**：
- `page`: 页码
- `page_size`: 每页大小
- `user_id`: 用户ID（管理员可筛选）
- `status`: 状态
- `start_time`: 开始时间
- `end_time`: 结束时间

**响应**：分页格式

---

##### GET /api/taosha/v1/logs/nlquery/{task_id}
**描述**：查询日志详情

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-xxxx",
    "user_question": "查询最近一个月的销售额",
    "generated_sql": "SELECT ...",
    "status": "success",
    "nodes": [
      {
        "node_name": "input_validation",
        "node_input": {...},
        "node_output": {...},
        "duration_ms": 2000
      }
    ]
  }
}
```

---

#### 9.2.7 管理接口

##### GET /api/taosha/v1/manager/users
**描述**：获取用户列表

---

##### POST /api/taosha/v1/manager/users
**描述**：创建用户

---

##### POST /api/taosha/v1/manager/users/{user_id}/update
**描述**：更新用户信息

---

##### POST /api/taosha/v1/manager/users/{user_id}/delete
**描述**：删除用户

---

##### GET /api/taosha/v1/manager/stats
**描述**：获取统计数据

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total_users": 100,
    "total_queries_today": 500,
    "success_rate": 0.85,
    "avg_response_time": 3.5
  }
}
```

---

### 9.3 WebSocket接口

#### WS /ws/nlquery/progress/{task_id}
**描述**：实时推送查询进度

**客户端订阅**：
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/nlquery/progress/uuid-xxxx');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  // 更新UI
};
```

**服务端推送数据格式**：
```json
{
  "type": "progress",
  "data": {
    "current_node": "sql_generation",
    "completed_nodes": [...]
  }
}
```

---

## 10. UI/UX设计

### 10.1 设计原则

1. **简洁性**：界面简洁，突出核心功能（查询框）
2. **一致性**：组件样式、交互行为保持一致
3. **反馈性**：操作有明确反馈（成功、失败、进行中）
4. **容错性**：友好的错误提示和引导
5. **专业性**：严肃风格，不使用emoji等元素

### 10.2 主题设计

#### 10.2.1 浅色主题（默认）
- **主色调**：浅蓝色 `#409EFF`
- **背景色**：白色 `#FFFFFF`
- **文字色**：深灰色 `#303133`
- **边框色**：浅灰色 `#DCDFE6`
- **悬停色**：`#66B1FF`

#### 10.2.2 深色主题
- **主色调**：紫色 `#7C3AED`
- **背景色**：深灰色 `#1E1E1E`
- **文字色**：浅灰色 `#E5E5E5`
- **边框色**：`#3F3F3F`
- **悬停色**：`#9F7AEA`

### 10.3 通用样式

- **圆角**：所有组件使用圆角 `border-radius: 8px`
- **阴影**：浅阴影 `box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1)`
- **间距**：统一使用8px的倍数（8, 16, 24, 32）
- **字体**：
  - 中文：苹方、微软雅黑
  - 英文：Helvetica Neue, Arial
  - 代码：Monaco, Consolas

### 10.4 页面设计

#### 10.4.1 淘沙查询页面（主页）

**布局结构**：
```
┌─────────────────────────────────────────────────────────┐
│  导航栏: Logo | 淘沙查询 | 元数据配置 | 日志管理      │
│                                    主题切换 | 用户头像│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  [数据主题] [数据表] 切换选择                    │   │
│  │  选择: [下拉框/多选框]                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ┌───────────────────────────────────────────┐  │   │
│  │  │                                           │  │   │
│  │  │  输入您的查询问题...                       │  │   │
│  │  │  (3行输入框)                               │  │   │
│  │  │                                           │  │   │
│  │  └───────────────────────────────────────────┘  │   │
│  │  提示: 请明确时间范围、查询指标等               │   │
│  │                                                │   │
│  │  流程选择: ○ 流程1  ● 流程2                    │   │
│  │  [查询按钮]                                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌───────────────┬─────────────────────────────────┐   │
│  │  收藏列表      │  查询结果                        │   │
│  │  - 月度销售统计 │  ┌────────────────────────────┐ │   │
│  │  - 用户增长分析 │  │  进度: ■■■□□ 60%           │ │   │
│  │                │  │  节点1: 输入校验 ✓          │ │   │
│  │  历史记录      │  │  节点2: SQL生成 (运行中)    │ │   │
│  │  - 10分钟前    │  └────────────────────────────┘ │   │
│  │  - 1小时前     │                                │   │
│  │  - 昨天        │  ┌────────────────────────────┐ │   │
│  │                │  │  查询结果表格                │ │   │
│  │                │  │  [表格数据]                 │ │   │
│  │                │  └────────────────────────────┘ │   │
│  │                │                                │   │
│  │                │  ┌────────────────────────────┐ │   │
│  │                │  │  图表展示                    │ │   │
│  │                │  │  [折线图/柱状图/饼图]         │ │   │
│  │                │  └────────────────────────────┘ │   │
│  └───────────────┴─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**交互细节**：
1. **查询框悬浮**：查询触发后，查询框固定在顶部，不会被滚动遮挡
2. **实时进度**：进度条动态更新，显示当前节点和已完成节点
3. **结果展示**：
   - 表格使用虚拟滚动（大数据量）
   - 图表根据数据类型智能推荐
4. **收藏和历史**：点击即可快速执行或修改

---

#### 10.4.2 元数据配置页面

**导航二级菜单**：
- 表配置
- 字段配置
- 关联配置
- 术语管理
- 提示词模板
- 数据主题
- 数据血缘（只读）
- 权限控制

**通用布局**（以表配置为例）：
```
┌─────────────────────────────────────────────────────┐
│  元数据配置 > 表配置                                  │
├─────────────────────────────────────────────────────┤
│  [新增] [批量导入] [导出模板]        搜索: [搜索框]   │
├─────────────────────────────────────────────────────┤
│  表名(中文)  │ 表名(英文) │ 数据源 │ 更新方式 │ 操作  │
│  ──────────┼──────────┼──────┼────────┼──────  │
│  订单表      │ order     │ MySQL │ 增量    │ 编辑 删除│
│  用户表      │ user      │ MySQL │ 全量    │ 编辑 删除│
│  ...                                               │
├─────────────────────────────────────────────────────┤
│  [分页控件]  第1页 共10页  每页20条                   │
└─────────────────────────────────────────────────────┘
```

**新增/编辑弹窗**：
- 使用Modal对话框
- 表单验证
- 保存后自动更新列表

---

#### 10.4.3 日志管理页面

**布局**：
```
┌─────────────────────────────────────────────────────┐
│  日志管理                                             │
├─────────────────────────────────────────────────────┤
│  用户: [下拉框]  状态: [下拉框]  时间: [日期选择器]    │
│  [查询] [重置]                                       │
├─────────────────────────────────────────────────────┤
│  时间          │ 用户    │ 查询内容        │ 状态│操作│
│  ────────────┼────────┼──────────────┼────┼──── │
│  2024-01-01... │ 张三    │ 查询月度销售...  │ 成功│详情│
│  2024-01-01... │ 李四    │ 查询用户增长...  │ 失败│详情│
│  ...                                               │
├─────────────────────────────────────────────────────┤
│  [分页控件]                                          │
└─────────────────────────────────────────────────────┘
```

**日志详情弹窗**：
- 显示用户输入
- 显示生成的SQL（代码高亮）
- 显示节点执行日志（时间线）
- 显示执行结果或错误信息

---

#### 10.4.4 收藏夹页面（可选独立页面）

**布局**：
```
┌─────────────────────────────────────────────────────┐
│  我的收藏                                             │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐│
│  │ 月度销售统计                   [执行] [修改] [删除] ││
│  │ 查询内容: 查询最近一个月的销售额                   ││
│  │ SQL: SELECT month, SUM(amount) FROM ...          ││
│  │ 创建时间: 2024-01-01 10:00                       ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │ 用户增长分析                   [执行] [修改] [删除] ││
│  │ ...                                             ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

### 10.5 组件设计

#### 10.5.1 查询框组件 (QueryBox.vue)
**功能**：
- 数据主题/表切换选择
- 自然语言输入（3行）
- 流程选择开关
- 查询按钮
- 输入提示

**状态**：
- 空闲状态
- 查询中（按钮禁用、loading）
- 查询完成（按钮恢复）

---

#### 10.5.2 进度查看器 (ProgressViewer.vue)
**功能**：
- 进度条
- 节点列表（时间线样式）
- 当前节点高亮
- 节点展开/收起（查看输入输出）

---

#### 10.5.3 结果表格 (ResultTable.vue)
**功能**：
- 虚拟滚动（大数据量）
- 列宽可调整
- 排序功能
- 导出按钮（管理员）
- 收藏按钮
- 反馈按钮

---

#### 10.5.4 图表组件 (ChartViewer.vue)
**功能**：
- 基于ECharts
- 支持折线图、柱状图、饼图
- 响应式调整大小
- 可导出图片

---

#### 10.5.5 主题切换 (ThemeToggle.vue)
**功能**：
- 切换按钮（太阳/月亮图标）
- 切换浅色/深色主题
- 记忆用户选择（LocalStorage）

---

### 10.6 交互细节

#### 10.6.1 加载状态
- **全局Loading**：页面初始化、大数据加载
- **局部Loading**：按钮点击后（按钮内显示loading图标）
- **骨架屏**：列表加载时显示骨架屏

#### 10.6.2 错误提示
- **Toast提示**：轻量级提示（成功、失败）
- **Modal对话框**：重要错误、需要用户确认的操作
- **表单验证**：实时验证，红色边框+错误文字

#### 10.6.3 空状态
- **无数据**：显示友好的空状态插图和文案
- **无搜索结果**：提示调整搜索条件

#### 10.6.4 确认操作
- **删除操作**：弹出确认对话框
- **重算操作**：弹出确认对话框（提示会消耗资源）

---

## 11. 测试策略

### 11.1 测试范围

| 测试类型 | 覆盖率要求 | 说明 |
|---------|-----------|------|
| **单元测试** | >80% | 后端核心方法和API接口 |
| **集成测试** | 核心流程 | NL2SQL工作流、元数据同步 |
| **端到端测试** | 主要用户路径 | 查询流程、元数据管理 |
| **性能测试** | 关键接口 | 查询接口、批量导入 |
| **安全测试** | 全部接口 | SQL注入、权限校验 |

### 11.2 单元测试

#### 11.2.1 测试目录结构
```
backend/testcase/
├── __init__.py
├── conftest.py               # Pytest配置和Fixture
├── test_api/                 # API接口测试
│   ├── test_auth.py         # 认证接口测试
│   ├── test_nlquery.py      # 查询接口测试
│   ├── test_metadata.py     # 元数据接口测试
│   └── test_favorite.py     # 收藏接口测试
├── test_services/            # 服务层测试
│   ├── test_query_engine.py
│   ├── test_nl2sql_service.py
│   └── test_metadata_service.py
└── test_utils/               # 工具类测试
    ├── test_db_utils.py
    ├── test_auth_utils.py
    └── test_common.py
```

#### 11.2.2 测试示例

**API接口测试 (test_nlquery.py)**：
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestNLQueryAPI:
    """查询API测试"""
  
    def test_submit_query_success(self, auth_token):
        """测试提交查询成功"""
        response = client.post(
            "/api/taosha/v1/nlquery/submit",
            json={
                "user_question": "查询最近一个月的销售额",
                "workflow_type": 2,
                "selected_theme_id": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]
  
    def test_submit_query_without_auth(self):
        """测试未认证提交查询"""
        response = client.post(
            "/api/taosha/v1/nlquery/submit",
            json={"user_question": "test"}
        )
        assert response.status_code == 401
  
    def test_get_query_progress(self, auth_token, test_task_id):
        """测试获取查询进度"""
        response = client.get(
            f"/api/taosha/v1/nlquery/progress/{test_task_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "status" in data["data"]
```

**服务层测试 (test_nl2sql_service.py)**：
```python
import pytest
from services.nl2sql_service.workflow_2 import Workflow2
from services.nl2sql_service.nodes.sql_generation import node_sql_generation

class TestNL2SQLService:
    """NL2SQL服务测试"""
  
    def test_sql_generation_node(self):
        """测试SQL生成节点"""
        state = {
            "user_question": "查询最近一个月的销售额",
            "table_schema": {...},
            "glossary": {...}
        }
        result = node_sql_generation(state)
        assert "generated_sql" in result
        assert result["generated_sql"].upper().startswith("SELECT")
  
    @pytest.mark.asyncio
    async def test_workflow_2_success(self):
        """测试流程2成功执行"""
        workflow = Workflow2()
        result = await workflow.run(
            user_question="查询最近一个月的销售额",
            selected_table_ids=[1, 2]
        )
        assert result["status"] == "success"
        assert "generated_sql" in result
```

**工具类测试 (test_db_utils.py)**：
```python
import pytest
from utils.db_utils import MetadataDB

class TestMetadataDB:
    """元数据库工具测试"""
  
    def test_connect_sqlite(self):
        """测试SQLite连接"""
        db = MetadataDB(db_type="sqlite", db_path="test.db")
        assert db.is_connected()
  
    def test_query_tables(self):
        """测试查询表列表"""
        db = MetadataDB(db_type="sqlite", db_path="test.db")
        tables = db.get_tables()
        assert isinstance(tables, list)
  
    def test_insert_table(self):
        """测试插入表元数据"""
        db = MetadataDB(db_type="sqlite", db_path="test.db")
        table_id = db.insert_table({
            "table_name_cn": "测试表",
            "table_name_en": "test_table",
            "data_source": "mysql"
        })
        assert table_id > 0
```

#### 11.2.3 Pytest配置 (conftest.py)

```python
import pytest
from fastapi.testclient import TestClient
from main import app
from utils.db_utils import MetadataDB

@pytest.fixture(scope="session")
def client():
    """测试客户端"""
    return TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    """测试数据库"""
    db = MetadataDB(db_type="sqlite", db_path=":memory:")
    db.init_schema()
    yield db
    db.close()

@pytest.fixture(scope="function")
def auth_token(client):
    """认证Token"""
    response = client.post(
        "/api/taosha/v1/auth/login",
        json={"username": "test_user", "password": "test_pass"}
    )
    return response.json()["data"]["access_token"]

@pytest.fixture(scope="function")
def test_task_id(client, auth_token):
    """测试任务ID"""
    response = client.post(
        "/api/taosha/v1/nlquery/submit",
        json={
            "user_question": "test query",
            "workflow_type": 2,
            "selected_theme_id": 1
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    return response.json()["data"]["task_id"]
```

### 11.3 集成测试

**测试场景**：
1. **完整查询流程测试**：
   - 用户登录 → 提交查询 → 获取进度 → 获取结果 → 收藏查询
2. **元数据同步流程测试**：
   - 修改表元数据 → 触发同步 → 验证知识库更新
3. **权限控制测试**：
   - 普通用户无法访问管理员接口
   - 用户只能查询有权限的表
   - 多角色权限取交集验证

### 11.4 端到端测试（可选）

使用Playwright或Cypress进行前端E2E测试：
- 登录流程
- 查询流程
- 元数据配置流程

### 11.5 性能测试

**测试工具**：Locust或JMeter

**测试场景**：
1. **并发查询测试**：50个用户同时查询
2. **大数据量查询**：查询100万行数据的响应时间
3. **批量导入测试**：导入1000条元数据

### 11.6 安全测试

**测试内容**：
1. **SQL注入测试**：
   - 在用户输入中注入SQL语句
   - 验证系统能够拦截
2. **权限绕过测试**：
   - 尝试访问无权限的接口
   - 验证返回403
3. **Token伪造测试**：
   - 使用伪造的Token访问接口
   - 验证返回401

### 11.7 测试命令

```bash
# 运行所有单元测试
pytest backend/testcase/

# 运行特定测试文件
pytest backend/testcase/test_api/test_nlquery.py

# 运行特定测试类
pytest backend/testcase/test_api/test_nlquery.py::TestNLQueryAPI

# 运行特定测试方法
pytest backend/testcase/test_api/test_nlquery.py::TestNLQueryAPI::test_submit_query_success

# 生成覆盖率报告
pytest --cov=backend --cov-report=html

# 并行测试（需要pytest-xdist）
pytest -n auto
```

---