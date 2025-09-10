# 后端模块

## 技术栈
- **框架**: LangGraph + Vanna
- **语言**: Python 3.11
- **模型**: VLLM (内网部署)

## 模块结构
```
backend/
├── agents/          # LangGraph Agent定义
├── nl2sql/          # Vanna NL2SQL核心
├── database/        # 数据库连接和管理
├── api/            # FastAPI接口
└── config/         # 配置管理
```

## 主要功能
- 多轮对话管理
- 自然语言转SQL
- 数据库查询执行
- 结果可视化生成
- 交互过程记录