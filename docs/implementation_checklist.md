# 数据分析Agent - 实现清单与开发指南

## 快速导航

### 文档索引
1. **data_analysis_agent_design.md** - 完整系统设计文档
   - 系统架构、功能设计、后端服务、前端架构
   - API设计、工作流、优先级规划

2. **optional_features.md** - 可选增强功能
   - 10个建议的增强功能点
   - 优先级评估和实现建议

3. **implementation_checklist.md** (本文件) - 快速参考和开发清单

---

## Phase 1: 基础Agent框架 (P0)

### 时间估算：2-3周
### 交付成果：支持简单查询执行的对话Agent

#### 后端任务
- [ ] 扩展LangGraph Agent支持工具调用
- [ ] 实现基础工具集（SQL查询、报表工具）
- [ ] 创建会话管理服务和API
- [ ] 实现意图识别模块
- [ ] 数据库表设计（conversations, messages, query_results）

#### 前端任务
- [ ] 创建ConversationPage主页面
- [ ] 实现ChatInput输入组件
- [ ] 实现MessageList消息列表
- [ ] 集成Pinia状态管理
- [ ] 实现StreamingMessage流式消息显示

#### 测试
- [ ] 基础Agent工作流单元测试
- [ ] API端点集成测试
- [ ] 前端组件测试

---

## Phase 2: 信息检索与元数据 (P0)

### 时间估算：1-2周
### 交付成果：支持从元数据检索的Agent

#### 后端任务
- [ ] 实现多模态检索服务
  - [ ] 分词 + 同义词扩展
  - [ ] 全文检索（DuckDB FTS）
  - [ ] 向量检索（Qdrant）
  - [ ] 智能重排（BM25）
- [ ] 报表元数据管理
  - [ ] 报表CRUD API
  - [ ] 报表信息同步到向量库
  - [ ] 批量导入功能
- [ ] 集成检索到Agent工作流

#### 前端任务
- [ ] 创建MetadataReportPage报表管理页面
- [ ] ReportConfigForm报表配置表单
- [ ] ReportImportModal批量导入弹窗
- [ ] ReportTable报表列表组件
- [ ] HistoryPage会话历史页面
- [ ] ConversationSearch搜索组件

#### 数据库
- [ ] 新增reports表
- [ ] 新增glossary表（术语表，用于同义词扩展）

---

## Phase 3: Generative UI (P1)

### 时间估算：1-2周
### 交付成果：自动可视化查询结果

#### 后端任务
- [ ] 实现图表类型决策引擎
  - [ ] 基于数据维度和类型选择组件
  - [ ] 生成对应的图表配置
- [ ] 扩展Agent返回结构支持visualization
- [ ] 数据格式化和聚合

#### 前端任务
- [ ] 实现图表组件库
  - [ ] LineChart 折线图
  - [ ] BarChart 柱状图
  - [ ] PieChart 饼图
  - [ ] TreeChart 树图
  - [ ] ComparisonTable 对比表
- [ ] 创建GenerativeUI容器组件
- [ ] 集成到MessageList中动态渲染

#### 第三方库
- [ ] ECharts 或 AntV G2 集成
- [ ] 数据转换工具库

---

## Phase 4: 会话增强与导出 (P2)

### 时间估算：1-2周
### 交付成果：完整的会话管理和数据导出

#### 后端任务
- [ ] 性能监控告警
  - [ ] 记录查询性能指标
  - [ ] 慢查询识别
  - [ ] 告警触发机制
- [ ] 数据导出功能
  - [ ] CSV导出
  - [ ] Excel导出
  - [ ] PDF报告生成
- [ ] 分享链接功能
  - [ ] 临时分享链接生成
  - [ ] 链接过期管理
  - [ ] 权限控制

#### 前端任务
- [ ] 添加导出按钮和菜单
- [ ] 实现分享功能UI
- [ ] 性能仪表板（可选）

#### 数据库
- [ ] 新增performance_metrics表
- [ ] 新增shared_results表

---

## Phase 5: DeepAgent工作流 (P1)

### 时间估算：2-3周
### 交付成果：多步骤复杂分析能力

#### 后端任务
- [ ] 工作流编排引擎
  - [ ] 分析问题和生成计划
  - [ ] 步骤执行框架
  - [ ] 步骤结果持久化
- [ ] 代码沙箱实现
  - [ ] RestrictedPython集成
  - [ ] 安全命名空间配置
  - [ ] 超时和内存限制
- [ ] HTML报告生成
  - [ ] Jinja2模板
  - [ ] 样式和脚本嵌入
  - [ ] 交互式图表保存
- [ ] 后台任务执行
  - [ ] 异步任务调度
  - [ ] 进度实时推送（SSE）
  - [ ] 失败重试机制

#### 前端任务
- [ ] 创建DeepAnalysisPage页面
- [ ] TodoList组件（展示分析计划）
- [ ] StepProgress组件（步骤进度）
- [ ] CodeBlockViewer组件（代码查看）
- [ ] ReportViewer组件（报告查看）
- [ ] SSE连接管理和进度更新

#### 数据库
- [ ] 新增deep_agent_sessions表
- [ ] 新增workflow_steps表

#### 文件系统
- [ ] backend/data/deep_agent_sessions/ 目录结构

---

## Phase 6: 收藏与完善 (P2)

### 时间估算：1周
### 交付成果：完整的收藏功能和系统优化

#### 后端任务
- [ ] 收藏管理服务
  - [ ] 收藏CRUD操作
  - [ ] 收藏分类管理
  - [ ] 快速执行API
- [ ] 性能优化
  - [ ] 查询结果缓存（Redis）
  - [ ] 批量操作优化
  - [ ] 数据库索引优化

#### 前端任务
- [ ] FavoriteBar快捷栏
- [ ] FavoriteList列表管理
- [ ] FavoriteForm编辑表单
- [ ] FavoriteManagementPage管理页面
- [ ] 快速执行按钮集成

#### 数据库
- [ ] 新增favorites表
- [ ] 性能指标索引优化

---

## 核心模块开发清单

### 后端 - 新增文件结构
```
backend/
├── services/
│   ├── agent_service/
│   │   ├── agent_coordinator.py          # Agent编排主类
│   │   ├── tools/
│   │   │   ├── base_tool.py
│   │   │   ├── spark_tool.py
│   │   │   ├── mysql_tool.py
│   │   │   ├── report_tool.py
│   │   │   └── retrieval_tool.py
│   │   └── intent_classifier.py          # 意图识别
│   │
│   ├── retrieval_service/
│   │   ├── text_processor.py             # 分词
│   │   ├── full_text_search.py           # FTS
│   │   ├── vector_search.py              # 向量搜索
│   │   └── reranker.py                   # 智能重排
│   │
│   ├── conversation_service/
│   │   ├── conversation_manager.py
│   │   └── message_handler.py
│   │
│   ├── deep_agent_service/
│   │   ├── deep_agent.py
│   │   ├── workflow_executor.py
│   │   ├── code_sandbox.py
│   │   └── report_generator.py
│   │
│   ├── favorite_service/
│   │   └── favorite_manager.py
│   │
│   └── export_service/
│       ├── csv_exporter.py
│       ├── excel_exporter.py
│       └── pdf_exporter.py
│
├── models/
│   ├── conversation.py
│   ├── message.py
│   ├── report_metadata.py
│   ├── deep_agent_session.py
│   ├── workflow_step.py
│   ├── favorite.py
│   └── performance_metric.py
│
├── repositories/
│   ├── conversation_repository.py
│   ├── message_repository.py
│   ├── report_repository.py
│   ├── deep_agent_repository.py
│   ├── favorite_repository.py
│   └── performance_repository.py
│
├── api/
│   ├── agent_routes.py                   # /api/agent/*
│   ├── conversation_routes.py            # /api/conversations/*
│   ├── metadata_report_routes.py         # /api/metadata/reports/*
│   ├── deep_analysis_routes.py           # /api/deep-analysis/*
│   ├── favorite_routes.py                # /api/favorites/*
│   └── export_routes.py                  # /api/export/*
│
└── utils/
    ├── chart_analyzer.py                 # 图表类型决策
    ├── sql_parser.py                     # SQL解析
    └── cost_estimator.py                 # 查询成本估算
```

### 前端 - 新增文件结构
```
frontend/src/
├── components/
│   ├── chat/
│   │   ├── ChatInput.vue
│   │   ├── MessageList.vue
│   │   ├── StreamingMessage.vue
│   │   └── ClarificationDialog.vue
│   │
│   ├── charts/
│   │   ├── LineChart.vue
│   │   ├── BarChart.vue
│   │   ├── PieChart.vue
│   │   ├── TreeChart.vue
│   │   └── ComparisonTable.vue
│   │
│   ├── workflow/
│   │   ├── TodoList.vue
│   │   ├── StepProgress.vue
│   │   └── CodeBlockViewer.vue
│   │
│   ├── metadata/
│   │   ├── ReportConfigForm.vue
│   │   ├── ReportImportModal.vue
│   │   └── ReportTable.vue
│   │
│   └── favorites/
│       ├── FavoriteBar.vue
│       ├── FavoriteList.vue
│       └── FavoriteForm.vue
│
├── views/
│   ├── ConversationPage.vue              # 主对话页面
│   ├── HistoryPage.vue                   # 历史记录
│   ├── MetadataReportPage.vue            # 报表配置
│   ├── DeepAnalysisPage.vue              # 分析进度
│   └── FavoriteManagementPage.vue        # 收藏管理
│
├── stores/
│   ├── agentStore.ts
│   ├── conversationStore.ts
│   ├── metadataStore.ts
│   ├── deepAnalysisStore.ts
│   └── favoriteStore.ts
│
├── services/api/
│   ├── agentService.ts
│   ├── conversationService.ts
│   ├── metadataReportService.ts
│   ├── deepAnalysisService.ts
│   ├── favoriteService.ts
│   └── exportService.ts
│
└── utils/
    ├── chartHelper.ts                    # 图表类型选择
    ├── sseClient.ts                      # SSE连接管理
    └── formatters.ts                     # 数据格式化
```

---

## 关键依赖和版本要求

### 后端新增依赖
```bash
uv add langgraph langchain-core            # Agent编排
uv add qdrant-client                       # 向量数据库
uv add elasticsearch                       # 全文搜索（可选）
uv add playwright                          # 报表自动化
uv add python-pptx python-docx openpyxl   # Office文档生成
uv add restricted-python ipython           # 代码沙箱
uv add reportlab                           # PDF生成
uv add pydantic-settings python-dotenv     # 配置管理
```

### 前端新增依赖
```bash
npm install echarts                        # 图表库
npm install ant-design-vue @ant-design/icons  # UI组件
npm install axios-mock-adapter            # 测试工具
```

---

## 数据库迁移清单

| Phase | 新表 | 修改表 | 索引 |
|------|------|--------|------|
| Phase 1 | conversations, messages, query_results | - | - |
| Phase 2 | reports, glossary | - | reports.id, glossary.term |
| Phase 4 | performance_metrics, shared_results | - | performance_metrics.query_hash |
| Phase 5 | deep_agent_sessions, workflow_steps | - | workflow_steps.session_id |
| Phase 6 | favorites | - | favorites.user_id, favorites.type |

---

## API端点规划

### Agent相关
```
POST   /api/taosha/v1/agent/chat                    # 发送查询
GET    /api/taosha/v1/agent/chat/{conv_id}         # 获取对话
GET    /api/taosha/v1/agent/chat/{conv_id}/stream  # SSE流
```

### 会话相关
```
GET    /api/taosha/v1/conversations                 # 列表
GET    /api/taosha/v1/conversations/{id}            # 详情
DELETE /api/taosha/v1/conversations/{id}            # 删除
POST   /api/taosha/v1/conversations/{id}/archive    # 归档
```

### 报表元数据
```
GET    /api/taosha/v1/metadata/reports              # 列表
POST   /api/taosha/v1/metadata/reports              # 创建
PUT    /api/taosha/v1/metadata/reports/{id}        # 更新
DELETE /api/taosha/v1/metadata/reports/{id}        # 删除
POST   /api/taosha/v1/metadata/reports/import       # 批量导入
```

### 收藏相关
```
GET    /api/taosha/v1/favorites                     # 列表
POST   /api/taosha/v1/favorites                     # 创建
PUT    /api/taosha/v1/favorites/{id}               # 更新
DELETE /api/taosha/v1/favorites/{id}               # 删除
POST   /api/taosha/v1/favorites/{id}/execute        # 快速执行
```

### DeepAgent相关
```
POST   /api/taosha/v1/deep-analysis/analyze        # 启动分析
GET    /api/taosha/v1/deep-analysis/{session_id}   # 获取进度
GET    /api/taosha/v1/deep-analysis/{session_id}/report  # 获取报告
```

### 导出相关
```
POST   /api/taosha/v1/export/csv                    # CSV导出
POST   /api/taosha/v1/export/excel                  # Excel导出
POST   /api/taosha/v1/export/pdf                    # PDF导出
POST   /api/taosha/v1/export/share                  # 生成分享链接
```

---

## 测试策略

### 单元测试目标
- Agent工具集：100%覆盖
- 检索服务：90%覆盖
- 数据转换：100%覆盖

### 集成测试
- Agent → 工具链路
- 会话持久化
- 数据导出流程

### E2E测试
- 完整对话流程
- DeepAgent工作流
- 历史查询回溯

---

## 性能目标

| 指标 | 目标 | 说明 |
|-----|------|------|
| 单次查询响应时间 | < 5s | P95 |
| Agent意图识别 | < 1s | 包括LLM调用 |
| 检索延迟 | < 200ms | 向量检索 |
| 报表查询 | < 10s | 包括Playwright操作 |
| 并发支持 | ≥ 100 | 并发用户 |

---

## 代码审查检查清单

- [ ] 所有API端点有完整的错误处理
- [ ] 工具调用有超时机制
- [ ] 数据库操作有事务管理
- [ ] 敏感数据有脱敏处理
- [ ] 日志记录完整（不含密码）
- [ ] TypeScript类型完整
- [ ] 组件有JSDoc注释
- [ ] 测试覆盖率 > 80%

---

## 部署检查清单

- [ ] 配置文件完整（config.yaml）
- [ ] 数据库迁移脚本
- [ ] 向量库初始化脚本
- [ ] 环境变量文档
- [ ] Docker镜像构建
- [ ] 性能基准测试
- [ ] 安全审计（代码沙箱、权限、SQL注入防护）

---

## 常见问题与解决方案

### Q: 如何处理LLM API调用的成本问题？
**A:**
- 缓存热查询的结果
- 使用本地模型做意图识别初步判断
- 批量API调用，减少往返次数

### Q: 代码沙箱如何保证安全？
**A:**
- 使用RestrictedPython限制导入
- 配置白名单库（numpy、pandas、matplotlib）
- 设置执行超时和内存限制
- 运行在独立进程中

### Q: 如何支持多数据源查询？
**A:**
- 统一Tool接口
- 在工具选择时根据检索结果判断数据源
- 支持跨源联查（可选的高级功能）

### Q: 如何保证历史记录的性能？
**A:**
- 定时归档老数据（> 90天）
- 加索引：conversation_id, user_id, created_at
- 考虑分表存储大量消息

---

## 与现有系统的集成点

### 复用现有模块
- ✅ 配置管理系统（config.yaml, utils/config.py）
- ✅ 日志系统（loguru）
- ✅ LLM服务（llm_service）
- ✅ 向量存储（Qdrant）
- ✅ 查询引擎（query_engine）
- ✅ 元数据服务（metadata_service）

### 需要扩展的模块
- 🔄 metadata_service - 添加报表元数据管理
- 🔄 nlquery_service - 扩展为完整Agent
- 🔄 tracking_service - 添加性能指标追踪

---

## 参考资源

- LangGraph文档：https://langchain-ai.github.io/langgraph/
- Qdrant向量库：https://qdrant.tech/documentation/
- RestrictedPython：https://restrictedpython.readthedocs.io/
- ECharts图表：https://echarts.apache.org/
- FastAPI异步：https://fastapi.tiangolo.com/async-concurrency/

