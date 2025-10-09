# 淘沙分析平台前端

基于 Vue 3 + TypeScript + Tailwind CSS + DaisyUI 的现代化数据分析平台前端项目。

## 项目概述

淘沙分析平台是一个基于 AI 的自然语言转 SQL 分析平台，用户可以通过自然语言描述查询需求，系统自动生成并执行 SQL 查询，提供数据分析和可视化功能。

## 技术栈

- **框架**: Vue 3.3+ (Composition API)
- **语言**: TypeScript 5.0+
- **构建工具**: Vite 5.0+
- **UI 框架**: Tailwind CSS 3.0+ + DaisyUI 4.0+
- **状态管理**: Pinia 2.1+
- **路由管理**: Vue Router 4.2+
- **HTTP 客户端**: Axios 1.6+
- **图表库**: Plotly.js (计划集成)
- **代码规范**: ESLint + Prettier
- **CSS 预处理**: PostCSS + Autoprefixer

## 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API 接口层
│   │   └── index.ts       # API 客户端配置
│   ├── assets/            # 静态资源
│   │   └── styles/        # 样式文件
│   ├── components/        # 组件
│   │   ├── common/        # 通用组件
│   │   ├── layout/        # 布局组件
│   │   └── query/         # 查询相关组件
│   ├── composables/       # 组合式函数
│   ├── router/            # 路由配置
│   ├── services/          # 服务层
│   │   └── api/           # API 服务
│   ├── stores/            # Pinia 状态管理
│   ├── types/             # TypeScript 类型定义
│   ├── utils/             # 工具函数
│   ├── views/             # 页面组件
│   │   └── metadata/      # 元数据管理子页面
│   ├── App.vue            # 根组件
│   └── main.ts            # 应用入口
├── docs/                  # 项目文档
├── package.json           # 项目依赖
├── vite.config.ts         # Vite 配置
├── tailwind.config.js     # Tailwind CSS 配置
├── tsconfig.json          # TypeScript 配置
└── README.md              # 项目说明
```

## 主要功能

### 1. 自然语言查询
- 支持自然语言输入查询需求
- AI 自动生成 SQL 查询
- 实时查询进度跟踪
- 查询结果展示和导出

### 2. 查询管理
- 查询历史记录
- 收藏查询功能
- 查询重跑和反馈

### 3. 元数据管理
- 数据表配置管理
- 字段元数据配置
- 业务术语管理
- 数据主题分类
- 关联关系配置

### 4. 系统功能
- 用户认证和权限管理
- 主题切换 (浅色/深色)
- 响应式设计
- 多语言支持 (计划中)

## 开发指南

### 环境要求

- Node.js 18.0+
- npm 9.0+ 或 pnpm 8.0+

### 安装依赖

```bash
npm install
# 或
pnpm install
```

### 开发模式

```bash
npm run dev
# 或
pnpm dev
```

开发服务器将在 `http://localhost:5173` 启动。

### 构建生产版本

```bash
npm run build
# 或
pnpm build
```

构建文件将输出到 `dist/` 目录。

### 代码检查

```bash
# ESLint 检查
npm run lint

# TypeScript 类型检查
npm run type-check

# Prettier 格式化
npm run format
```

## 开发规范

### 1. 组件开发

- 使用 Vue 3 Composition API
- 遵循单一职责原则
- 组件命名使用 PascalCase
- Props 和 Emits 需要明确的类型定义

### 2. 状态管理

- 使用 Pinia 进行状态管理
- 按功能模块拆分 store
- 使用 TypeScript 严格类型检查

### 3. 样式规范

- 使用 Tailwind CSS 类名
- 遵循 DaisyUI 设计规范
- 响应式设计优先

### 4. API 调用

- 统一使用 services 层封装 API
- 错误处理统一化
- Loading 状态管理

## 部署说明

### 环境变量

创建 `.env.production` 文件：

```bash
VITE_API_BASE_URL=https://api.taosha.com/v1
VITE_APP_TITLE=淘沙分析平台
VITE_APP_VERSION=1.0.0
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend-server:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API 集成

前端项目依赖后端 API 提供数据支持，详细的 API 需求请参考：

📖 [API 需求文档](./API_REQUIREMENTS.md)

## 浏览器支持

- Chrome 88+
- Firefox 78+
- Safari 14+
- Edge 88+

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。详情请参考 [LICENSE](../LICENSE) 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: support@taosha.com

## 更新日志

### v1.0.0 (2024-01-09)
- ✨ 初始版本发布
- 🚀 完成基础架构搭建
- 🎨 实现响应式 UI 设计
- 🔧 集成开发工具链
- 📝 完善 TypeScript 类型定义
- 🌐 实现路由和状态管理
- 🎯 完成核心查询功能界面
- 📊 实现元数据管理界面
- 🌙 支持主题切换功能