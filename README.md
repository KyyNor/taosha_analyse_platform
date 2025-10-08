# 淘沙分析平台

一个基于自然语言的企业级数据分析平台，让用户通过自然语言查询数据，自动生成SQL并执行。

## 🌟 主要特性

### 💡 智能查询
- **自然语言转SQL**：支持中文自然语言查询，自动生成对应的SQL语句
- **智能理解**：基于LLM的语义理解，准确识别用户查询意图
- **实时交互**：WebSocket支持查询进度实时推送
- **多数据库支持**：支持DuckDB(快速分析)和MySQL(生产数据)

### 🗂️ 元数据管理
- **表管理**：完整的数据表配置和管理
- **字段管理**：详细的字段定义和类型管理
- **术语管理**：业务术语和数据字典
- **主题管理**：数据主题分类和权限控制

### 👥 权限控制
- **RBAC模型**：基于角色的访问控制
- **细粒度权限**：支持功能级和数据级权限控制
- **多角色支持**：超级管理员、管理员、分析师、查看者等
- **安全认证**：JWT令牌认证和权限验证

### 📊 数据可视化
- **结果展示**：表格、图表等多种展示方式
- **数据导出**：支持CSV、Excel、JSON等格式导出
- **历史管理**：查询历史记录和收藏功能
- **统计分析**：查询成功率、执行时间等统计

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI**：高性能异步Web框架
- **SQLAlchemy**：ORM数据库操作
- **LangGraph + Vanna**：AI驱动的NL2SQL引擎
- **ChromaDB**：向量数据库，用于语义检索
- **WebSocket**：实时通信
- **JWT**：认证和授权

### 前端技术栈
- **Vue3 + TypeScript**：现代化前端框架
- **DaisyUI + Tailwind CSS**：美观的UI组件库
- **Pinia**：状态管理
- **Axios**：HTTP客户端
- **WebSocket**：实时通信

### 数据库支持
- **SQLite**：开发环境
- **MySQL**：生产环境
- **DuckDB**：快速分析引擎
- **ChromaDB**：向量存储

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- MySQL 8.0+ (生产环境)

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python start.py
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 或使用启动脚本
chmod +x start.sh
./start.sh
```

### 默认账户
- 用户名：`admin`
- 密码：`admin123456`
- 角色：超级管理员

## 📁 项目结构

```
taosha_analyse_platform/
├── backend/                    # 后端服务
│   ├── api/                   # API路由
│   │   └── v1/               # API版本1
│   ├── models/               # 数据模型
│   ├── services/             # 业务服务
│   │   ├── nl2sql/          # NL2SQL引擎
│   │   ├── query_engine/    # 查询引擎
│   │   ├── query_history/   # 查询历史
│   │   ├── user/            # 用户管理
│   │   └── websocket/       # WebSocket
│   ├── schemas/              # Pydantic模型
│   ├── utils/                # 工具函数
│   ├── config/               # 配置文件
│   ├── db/                   # 数据库配置
│   └── scripts/              # 脚本文件
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/              # API接口
│   │   ├── components/       # 组件
│   │   ├── views/            # 页面
│   │   ├── stores/           # 状态管理
│   │   ├── services/         # 服务类
│   │   ├── types/            # 类型定义
│   │   └── router/           # 路由配置
│   └── public/               # 静态资源
└── docs/                      # 文档
```

## 🔧 配置说明

### 环境变量

创建 `backend/.env` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite:///./taosha.db
MYSQL_URL=mysql+asyncmy://user:password@localhost/taosha

# JWT配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# 向量数据库配置
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

## 📈 功能模块

### 1. 智能查询
- 自然语言输入
- SQL自动生成
- 查询结果展示
- 进度实时跟踪

### 2. 元数据管理
- 数据表配置
- 字段定义
- 业务术语
- 数据主题

### 3. 用户权限
- 用户管理
- 角色管理
- 权限分配
- 访问控制

### 4. 查询历史
- 历史记录
- 收藏查询
- 重新执行
- 统计分析

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - AI工作流编排
- [Vanna](https://github.com/vanna-ai/vanna) - NL2SQL框架
- [DaisyUI](https://daisyui.com/) - Tailwind CSS组件库

## 📞 联系方式

如有问题或建议，请创建 Issue 或联系开发团队。

---

⭐ 如果这个项目对你有帮助，请给个星标支持！