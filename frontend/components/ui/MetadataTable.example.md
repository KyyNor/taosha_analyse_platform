# MetadataTable 标签功能使用示例

MetadataTable 组件现在支持内置的标签渲染功能，让你可以轻松地在表格中显示状态标签。

## 基本用法

### 1. 使用内置标签类型

```tsx
import { MetadataTable } from "@/components/ui/MetadataTable";
import { statusBadgeConfig } from "@/lib/utils/badgeConfigs";

const columns = [
  { key: "id", label: "ID", type: "number" },
  { key: "name", label: "名称", type: "text" },
  {
    key: "status",
    label: "状态",
    type: "badge",
    badgeConfig: {
      active: { variant: "default", label: "启用" },
      inactive: { variant: "secondary", label: "禁用" },
      pending: { variant: "outline", label: "待处理" }
    }
  }
];

<MetadataTable data={data} columns={columns} />
```

### 2. 使用预定义的标签配置

```tsx
import { statusBadgeConfig, priorityBadgeConfig } from "@/lib/utils/badgeConfigs";

const columns = [
  { key: "id", label: "ID", type: "number" },
  { key: "title", label: "标题", type: "text" },
  {
    key: "status",
    label: "状态",
    type: "badge",
    badgeConfig: statusBadgeConfig
  },
  {
    key: "priority",
    label: "优先级",
    type: "badge",
    badgeConfig: priorityBadgeConfig
  }
];
```

### 3. 自定义标签渲染

如果需要更复杂的逻辑，仍然可以使用自定义渲染：

```tsx
const columns = [
  {
    key: "status",
    label: "状态",
    type: "custom",
    render: (value, row) => {
      // 根据行数据动态决定标签样式
      const variant = row.isUrgent ? "destructive" : "default";
      return <Badge variant={variant}>{value}</Badge>;
    }
  }
];
```

## 可用的标签配置

### 告警状态 (alertStatusBadgeConfig)
- `not_configured`: 未配置 (secondary)
- `sent`: 已发送 (default)
- `duplicate`: 重复告警 (outline)

### 管控状态 (controlStatusBadgeConfig)
- `not_configured`: 未配置 (secondary)
- `executed`: 已执行 (default)
- `duplicate`: 重复管控 (outline)

### 通用状态 (statusBadgeConfig)
- `active`: 启用 (default)
- `inactive`: 禁用 (secondary)
- `pending`: 待处理 (outline)
- `success`: 成功 (default)
- `failed`: 失败 (destructive)
- `running`: 运行中 (default)
- `stopped`: 已停止 (secondary)

### 优先级 (priorityBadgeConfig)
- `high`: 高 (destructive)
- `medium`: 中 (default)
- `low`: 低 (secondary)

### 类型 (typeBadgeConfig)
- `system`: 系统 (default)
- `user`: 用户 (outline)
- `admin`: 管理员 (secondary)

## 标签变体

可用的标签变体：
- `default`: 默认样式（蓝色）
- `secondary`: 次要样式（灰色）
- `destructive`: 危险样式（红色）
- `outline`: 轮廓样式（透明背景）

## 完整示例

```tsx
import { MetadataTable } from "@/components/ui/MetadataTable";
import { statusBadgeConfig, priorityBadgeConfig } from "@/lib/utils/badgeConfigs";

export default function TaskListPage() {
  const columns = [
    { key: "id", label: "ID", type: "number" },
    { key: "title", label: "任务标题", type: "text", maxLength: 50 },
    {
      key: "status",
      label: "状态",
      type: "badge",
      badgeConfig: statusBadgeConfig
    },
    {
      key: "priority",
      label: "优先级",
      type: "badge",
      badgeConfig: priorityBadgeConfig
    },
    { key: "created_at", label: "创建时间", type: "datetime" }
  ];

  return (
    <MetadataTable
      data={tasks}
      columns={columns}
      loading={loading}
      onRefresh={loadTasks}
      onView={handleView}
      searchPlaceholder="搜索任务..."
      emptyText="暂无任务"
    />
  );
}
```

这样，其他页面就可以轻松地复用标签功能，而不需要重复编写标签渲染逻辑。