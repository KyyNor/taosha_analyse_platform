# 淘沙分析平台 - Vue3前端

这是淘沙数据分析平台的Vue3前端应用，提供现代化的用户界面用于自然语言数据查询和元数据管理。

## 功能特性

### 🔍 数据查询
- **自然语言查询**: 使用日常语言描述查询需求
- **智能SQL生成**: 自动将自然语言转换为SQL查询
- **实时结果展示**: 数据表格和可视化图表
- **查询历史**: 保存和重用历史查询
- **清晰度检查**: 智能建议优化查询表达

### 🛠️ 元数据管理
- **表元数据管理**: 完整的数据表和列信息维护
- **业务术语表**: 统一的数据字典和术语定义
- **关联配置**: 灵活的字段关联关系管理
- **实时统计**: 元数据概览和使用统计

### 🎨 设计特点
- **现代化UI**: 基于Tailwind CSS + DaisyUI的设计系统
- **响应式布局**: 适配桌面端和移动端
- **无障碍设计**: 完整的键盘导航和屏幕阅读器支持
- **性能优化**: 组件懒加载和数据缓存

## 技术栈

- **核心框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **路由管理**: Vue Router 4
- **样式框架**: Tailwind CSS + DaisyUI
- **图标库**: Heroicons
- **图表库**: Plotly.js
- **HTTP客户端**: Axios
- **构建工具**: Vite

## 快速开始

### 环境要求
- Node.js >= 16
- npm >= 8

### 安装依赖
```bash
npm install
```

### 开发服务器
```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动

### 构建生产版本
```bash
npm run build
```

构建文件将输出到 `dist/` 目录

### 预览生产版本
```bash
npm run preview
```

## 项目结构

```
vue_devops/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API接口封装
│   ├── components/        # 通用组件
│   │   ├── metadata/      # 元数据管理组件
│   │   ├── DataTable.vue  # 数据表格组件
│   │   ├── DataChart.vue  # 图表组件
│   │   └── ...
│   ├── router/            # 路由配置
│   ├── styles/            # 样式文件
│   ├── types/             # TypeScript类型定义
│   ├── views/             # 页面组件
│   │   ├── DataQuery.vue  # 数据查询页面
│   │   └── MetadataManagement.vue # 元数据管理页面
│   ├── App.vue            # 根组件
│   └── main.ts            # 应用入口
├── index.html             # HTML模板
├── package.json           # 项目配置
├── vite.config.ts         # Vite配置
├── tailwind.config.js     # Tailwind配置
└── tsconfig.json          # TypeScript配置
```

## 组件说明

### 核心组件
- **DataQuery**: 主页数据查询界面，支持自然语言输入
- **MetadataManagement**: 元数据管理界面，包含三个标签页
- **DataTable**: 通用数据表格组件，支持排序、分页
- **DataChart**: 智能图表组件，根据数据类型自动选择图表类型

### 元数据组件
- **TableMetadata**: 表元数据管理，支持增删改查
- **GlossaryManagement**: 业务术语管理
- **RelationConfig**: 关联字段配置管理
- **ColumnEditor**: 列信息编辑器
- **TermForm**: 术语表单组件

## API接口

前端通过HTTP代理连接后端API：

- **查询接口**: `POST /api/v1/query`
- **元数据接口**: `/api/v1/dev/metadata/*`
- **术语接口**: `/api/v1/dev/glossary/*`
- **关联配置**: `/api/v1/dev/relation-configs/*`

详细API文档请访问: `http://localhost:8000/docs`

## 开发规范

### 代码风格
- 使用TypeScript进行类型约束
- 遵循Vue 3 Composition API最佳实践
- 组件使用`<script setup>`语法
- 样式使用Tailwind CSS类名

### 命名规范
- 组件名使用PascalCase
- 文件名使用PascalCase
- 变量和函数使用camelCase
- CSS类名使用kebab-case

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具的变动

## 部署说明

### 环境变量
开发环境会自动代理API请求到 `http://localhost:8000`

生产环境需要配置正确的API地址。

### 构建优化
- 自动代码分割
- 静态资源压缩
- Tree-shaking优化
- 缓存策略

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情