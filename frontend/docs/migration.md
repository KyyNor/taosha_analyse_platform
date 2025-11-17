# 迁移过程

## 已完成
- 初始化 Next.js 14 + React 18 项目结构（`frontend/`）。
- 配置 Tailwind CSS 3 与基础设计令牌（`styles/globals.css`，`tailwind.config.ts`）。
- 集成 shadcn/ui 基础（Radix 依赖、`components/ui/*`，示例 `Button`）。
- 建立 App Router 路由骨架（`app/(main)/*` 与 `app/not-found.tsx`）。
- 配置 API 代理 `/api` 与 WebSocket 直连（`next.config.mjs`，`.env.local.example`）。
- 建立基础状态管理 Context 与 hooks（`lib/state/*`）。
- NLQuery 页面初版（表单、执行、结果渲染）。

## 待迁移页面与组件
- `/agent`：任务/流程管理与进度视图。
- `/metadata/*`：表、关系、术语、主题、模板五页。
- `/logs`：日志表格与详情弹框。
- `/favorites`：收藏管理与执行。
- `/settings`：系统设置。
- 公共组件：`FloatingBall`、`SidebarPanel`、`LogDetailModal` 等。

## 路由映射
- 保持原路径：`/nlquery`、`/agent`、`/metadata/*`、`/logs`、`/favorites`、`/settings`。
- 根路径 `/` 重定向到 `/nlquery`（`app/page.tsx`）。
- 404 → `app/not-found.tsx`。

## API 与 Socket
- REST：通过 `lib/api.ts`（Axios，`baseURL=/api`）。
- 服务映射：`lib/services/queryService.ts`、`agentService.ts`、`metadataService.ts`。

## 迁移方法论
1. 页面拆分：将 `.vue` 模板与逻辑转为 `.tsx` 组件与 hooks。
2. UI 重构：daisyUI → shadcn/ui + Tailwind 原子类，减少自定义 CSS。
3. 状态改写：Pinia → React Context/Hook（后续可替换为 Zustand）。
4. 动效与样式：Keyframes 与主题变量迁移到 `globals.css`；用类触发。
5. 测试与验收：组件单测（RTL），E2E（Playwright），视觉回归（截图比对）。

## 启动与验证
- 安装依赖：在 `frontend/` 执行 `npm install`。
- 开发模式：`npm run dev`，访问 `http://localhost:3000/`。
- 生产构建：`npm run build && npm run start`。

## 注意事项
- WebSocket 路径不走 Next 重写，避免升级耦合；使用公开环境变量。
- 仅在必要处使用 `use client`，降低包体与提升渲染性能。
- 重型依赖（ECharts、Prism）使用动态导入与客户端渲染。