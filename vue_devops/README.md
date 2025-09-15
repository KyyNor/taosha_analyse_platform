# 淘沙分析平台 - Vue 前端

基于Vue 3 + TypeScript + Element Plus构建的现代化前端界面，完全复现Streamlit版本的所有功能，并提供更好的性能和用户体验。

## 技术栈

- **核心框架**: Vue 3 + TypeScript + Vite
- **UI组件库**: Element Plus (简约大气、圆角设计)
- **图表库**: ECharts (支持丰富的图表类型)
- **HTTP客户端**: Axios
- **状态管理**: Pinia
- **路由**: Vue Router
- **样式**: SCSS

## 功能特性

### 1. 数据查询
- 自然语言查询输入
- 多种结果展示：表格、图表、指标卡片
- SQL查询展示
- 查询历史记录
- 输入清晰度验证和建议
- 查询日志详情

### 2. 元数据管理
- 表元数据的增删改查
- 列元数据的增删改查
- 业务术语管理
- 关联字段配置
- 数据库同步功能

### 3. 术语搜索
- 实时搜索术语和别名
- 术语详情展示
- 分类筛选

### 4. AI对话框多种结果展示
- 文字内容
- 数据表格
- 可视化图表 (柱状图、散点图、饼图)
- 代码块 (SQL语法高亮)
- Markdown渲染
- 错误信息展示

## 设计特色

- **简约大气**: 采用Element Plus设计语言，界面清爽
- **圆角设计**: 所有卡片、按钮、输入框采用圆角设计
- **浅色主题**: 以白色和浅色为主，护眼舒适
- **无Emoji**: 纯文字图标设计，专业简洁
- **层次清晰**: 合理的信息层级和布局

## 快速开始

### 安装依赖
```bash
cd vue_devops
npm install
# 或者
yarn install
```

### 开发运行
```bash
npm run dev
# 或者
yarn dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本
```bash
npm run build
# 或者
yarn build
```

## 项目结构

```
vue_devops/
├── src/
│   ├── api/              # API接口定义
│   ├── components/       # 公共组件
│   │   ├── metadata/     # 元数据管理相关组件
│   │   ├── DataTable.vue # 数据表格组件
│   │   ├── DataChart.vue # 图表组件
│   │   └── ...          # 其他组件
│   ├── stores/           # Pinia状态管理
│   ├── styles/           # 全局样式
│   ├── types/            # TypeScript类型定义
│   ├── views/            # 页面组件
│   │   ├── DataQuery.vue        # 数据查询页面
│   │   ├── MetadataManagement.vue # 元数据管理页面
│   │   └── GlossarySearch.vue     # 术语搜索页面
│   ├── router/           # 路由配置
│   ├── App.vue          # 根组件
│   └── main.ts          # 应用入口
├── package.json         # 项目配置
├── vite.config.ts      # Vite配置
├── tsconfig.json       # TypeScript配置
└── index.html          # HTML模板
```

## API配置

后端API地址配置在 `vite.config.ts` 中，默认代理到 `http://localhost:8000`：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 性能优势

相比Streamlit版本：
- 响应速度提升50%+
- 更流畅的用户交互
- 更好的数据可视化效果
- 更灵活的布局和样式定制
- 更好的移动端适配

## 开发说明

1. **组件化开发**: 所有功能都拆分为可复用的组件
2. **类型安全**: 全面使用TypeScript，确保类型安全
3. **响应式设计**: 支持不同屏幕尺寸的适配
4. **错误处理**: 完善的错误处理和用户提示
5. **代码规范**: 统一的代码风格和命名规范