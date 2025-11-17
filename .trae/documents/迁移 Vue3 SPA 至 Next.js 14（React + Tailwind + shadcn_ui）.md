# 迁移概览
- 将 `frontend_bak`（Vue3 + Vite + Tailwind + daisyUI）迁移到 `frontend`（Next.js 14 + React 18 + Tailwind CSS 3 + shadcn/ui）。
- 保持既有业务路径与交互一致，并按 App Router 规范组织文件。
- 以页面为单位逐步迁移与验收，优先实现公共组件与基础设施（样式、API、状态）。

## 路由映射（保持不变）
- `/` → 服务器端重定向至 `/nlquery`
- `/nlquery` → QueryPage
- `/agent` → AgentPage
- `/metadata`（聚合页）
  - `/metadata/tables`
  - `/metadata/relations`
  - `/metadata/glossary`
  - `/metadata/themes`
  - `/metadata/prompt-templates`
- `/logs` → LogsPage
- `/favorites` → FavoritesPage
- `/settings` → SettingsPage
- `404` → `app/not-found.tsx`

## 目标项目结构（App Router）
- `app/layout.tsx`（全局布局与样式注入）
- `app/page.tsx`（重定向到 `/nlquery`）
- `app/(main)/nlquery/page.tsx`
- `app/(main)/agent/page.tsx`
- `app/(main)/metadata/page.tsx` 与子段：
  - `app/(main)/metadata/tables/page.tsx`
  - `app/(main)/metadata/relations/page.tsx`
  - `app/(main)/metadata/glossary/page.tsx`
  - `app/(main)/metadata/themes/page.tsx`
  - `app/(main)/metadata/prompt-templates/page.tsx`
- `app/(main)/logs/page.tsx`
- `app/(main)/favorites/page.tsx`
- `app/(main)/settings/page.tsx`
- `app/not-found.tsx`
- `components/`（通用组件，优先用 shadcn/ui）
- `lib/`（API 客户端、socket 封装、状态、实用函数）
- `styles/globals.css`（Tailwind 入口及主题变量）
- `public/`（静态资源）

## 初始化与基础配置
1. 初始化 Next.js 14（App Router，TypeScript，ESLint）到 `frontend/`。
2. 配置 Tailwind（`tailwind.config.ts`、`postcss.config.js`、`styles/globals.css`）。
3. 集成 shadcn/ui：
   - `npx shadcn@latest init` 并设定 `components.json`
   - 先添加：`button`、`input`、`select`、`textarea`、`dialog`、`dropdown-menu`、`tabs`、`table`、`popover`、`tooltip`、`toast/sonner`、`badge`、`accordion`
4. Next 重写与环境：
   - `next.config.mjs` 设置 `rewrites`：`/api/:path*` → `http://localhost:50020/api/:path*`
   - WebSocket：客户端直连 `ws://localhost:50020/ws`（Next 重写对 WS 限制，避免耦合）。
   - 使用环境变量：`NEXT_PUBLIC_API_BASE=/api`、`NEXT_PUBLIC_WS_BASE=ws://localhost:50020/ws`

## 状态管理迁移
- 由 Pinia 转为 React Context + Hooks（避免额外依赖，后续可抽象为 Zustand）。
- `lib/state/` 内按原 store 划分：
  - `appStore`（应用级设置、UI 状态）
  - `themeStore`（主题切换，Tailwind 变量）
  - `queryStore`（查询文本、结果、执行状态）
  - `agentStore`（Agent 设定与执行）
- 提供选择器 hooks（`useAppState` 等）与 action 分发，保持与原语义一致。

## API 与 Socket 迁移
- `lib/api.ts`：Axios 实例（`baseURL=/api`，拦截器、错误处理、取消请求）。
- 将 `client.ts`、`queryService.ts`、`agentService.ts`、`metadataService.ts` 映射到 `lib/services/*`，方法签名保持一致。
- Socket.io 客户端：`lib/socket.ts`（单例连接 + `useSocket` hook），在需要的页面以 `useEffect` 订阅与清理。

## 公共组件重构（shadcn/ui）
- Button/Input/Select/Textarea/Badge/Accordion/Tabs/Table/Dialog/Toast 替换 daisyUI 组件。
- 复用 Tailwind 原子类，尽量减少自定义 CSS；必要样式写入 `globals.css` 并以变量控制主题。
- 将 `src/components/common/*` 映射到 `components/*`：
  - `Modal` → `Dialog`
  - `Tabs` → `Tabs`
  - `Table` → `DataTable`（基于 `table` + Tailwind）
  - `Toast` → `sonner`（shadcn 推荐栈）
  - 表单控件统一为 shadcn 表单生态

## 图表与富文本
- ECharts：创建 `components/charts/EChart.tsx`（`use client` + 动态导入 `echarts`，SSR 关闭）。
- Markdown/Prism：将 `markdown.ts`、`prism.ts` 迁移为 React 组件与 hooks，按需在客户端渲染。

## 样式转换策略
- 先梳理 `src/styles/index.css`、`fonts.css`、`assets/styles/main.css` 中的自定义样式：
  - 能用 Tailwind 原子类表达的全部改为类组合
  - 主题色与阴影、圆角、排版统一放入 Tailwind 扩展（`theme.extend`）
  - 复杂动画与 Keyframes 迁移到 `globals.css`，通过类名触发
- 输出《样式转换对照表》（类名/组件 → Tailwind/shadcn 替代方案）。

## 页面逐步迁移流程
1. 基础设施完成后，按以下顺序迁移并验收：
   - `/nlquery` → 输入与结果视图（与后台交互、历史与收藏）
   - `/agent` → 任务/流程可视化与控制
   - `/metadata/*` → 五个子页（表/关系/术语/主题/模板）
   - `/logs`、`/favorites`、`/settings` → 工具页与配置
2. 每页迁移步骤：
   - 将 `.vue` 转为 `.tsx`，模板 → JSX，指令/事件改为 React 事件系统
   - 组件替换为 shadcn/ui，同步样式为 Tailwind 原子类
   - 接入 `lib/services/*` 与 `useSocket`
   - 加入测试用例与可访问性校验（aria attributes）
3. 验收标准：DOM 结构与交互一致；API 调用与数据一致；响应式断点一致。

## 测试与质量保证
- 单元测试：Jest + React Testing Library（组件行为、hooks）
- 端到端测试：Playwright（核心用户流程与跨浏览器：Chromium/Firefox/WebKit）
- 视觉回归：Playwright Screenshot 对关键页面拍屏对比
- CI 集成（可选）：在 push/PR 触发 Lint + Test + Build

## 性能与可维护性
- 仅在必要页面使用 `use client`，其余尽量保持服务器组件结构（但图表/Socket 页多为客户端）。
- 动态导入重型依赖（ECharts、Prism），降低初始包体。
- 资源缓存与 Memo 化（`React.memo`、`useMemo`、`useCallback`）。
- Next 画像优化、路由级代码拆分、生产构建检查（`next build`）。

## 交付物
- 可运行的 Next.js 项目（`frontend/`）
- 迁移过程文档（步骤、决定与注意点）
- 样式转换对照表（类/组件替换与示例）
- 已知问题列表与解决方案（含暂不迁移项与替代方案）

## 里程碑
- M1：项目初始化与基础栈（1 天）
- M2：公共组件与基础设施（1–2 天）
- M3：核心页面 `/nlquery`、`/agent`（2–3 天）
- M4：`/metadata/*` 子页（2–3 天）
- M5：日志/收藏/设置与测试完善（1–2 天）
- M6：性能调优与最终回归（1 天）

## 约束与假设
- 后端接口与 WebSocket 保持原地址与契约不变。
- 现有 Tailwind 自定义样式可迁移；daisyUI 全部替换为 shadcn/ui。
- 以功能一致性优先，逐步提升 RSC 比例与可维护性。