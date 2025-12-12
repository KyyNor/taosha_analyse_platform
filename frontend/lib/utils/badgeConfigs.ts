/**
 * 通用标签配置
 * 可以在多个页面中复用的标签样式配置
 */

// 告警状态标签配置
export const alertStatusBadgeConfig = {
  not_configured: { variant: "secondary" as const, label: "未配置" },
  sent: { variant: "default" as const, label: "已发送" },
  duplicate: { variant: "outline" as const, label: "重复告警" }
};

// 管控状态标签配置
export const controlStatusBadgeConfig = {
  not_configured: { variant: "secondary" as const, label: "未配置" },
  executed: { variant: "default" as const, label: "已执行" },
  duplicate: { variant: "outline" as const, label: "重复管控" }
};

// 通用状态标签配置
export const statusBadgeConfig = {
  active: { variant: "default" as const, label: "启用" },
  inactive: { variant: "secondary" as const, label: "禁用" },
  pending: { variant: "outline" as const, label: "待处理" },
  success: { variant: "default" as const, label: "成功" },
  failed: { variant: "destructive" as const, label: "失败" },
  running: { variant: "default" as const, label: "运行中" },
  stopped: { variant: "secondary" as const, label: "已停止" }
};

// 优先级标签配置
export const priorityBadgeConfig = {
  high: { variant: "destructive" as const, label: "高" },
  medium: { variant: "default" as const, label: "中" },
  low: { variant: "secondary" as const, label: "低" }
};

// 类型标签配置
export const typeBadgeConfig = {
  system: { variant: "default" as const, label: "系统" },
  user: { variant: "outline" as const, label: "用户" },
  admin: { variant: "secondary" as const, label: "管理员" }
};