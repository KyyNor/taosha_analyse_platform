# 已知问题与方案

- shadcn/ui 组件尚未完整添加，后续按页面需求补全（Dialog、Tabs、Dropdown、Tooltip 等）。
- 旧 Vue 指令与生命周期需在迁移时改为 React 事件与 hooks。
- ECharts、Prism 等重型依赖尚未接入，建议动态导入并仅在客户端渲染。