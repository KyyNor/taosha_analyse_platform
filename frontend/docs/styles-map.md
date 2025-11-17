# 样式转换对照表

- daisyUI 按钮 → `Button` 组件（`variant`、`size`）。
- daisyUI 表单 → `Input`/`Textarea` + 原子类。
- 卡片与边框 → `rounded-md border p-4`。
- 布局与间距 → 原子类（`p-6`、`flex`、`gap-4`）。
- 颜色与主题 → CSS 变量 + `theme.extend.colors`。
- 加载覆盖/动画 → `globals.css` 定义 keyframes，组件以类触发。