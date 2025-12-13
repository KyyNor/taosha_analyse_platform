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

// 对象类型标签配置
export const objectTypeBadgeConfig = {
  dep_acct_no: { variant: "default" as const, label: "存款账户" },
  cust_no: { variant: "secondary" as const, label: "客户号" },
  loan_acct_no: { variant: "outline" as const, label: "贷款账户" }
};

// 指标类型标签配置
export const indicatorTypeBadgeConfig = {
  offline: { variant: "secondary" as const, label: "离线" },
  realtime: { variant: "default" as const, label: "实时" }
};

// 数据类型标签配置
export const dataTypeBadgeConfig = {
  numeric: { variant: "default" as const, label: "数值" },
  enum: { variant: "secondary" as const, label: "枚举" },
  text: { variant: "outline" as const, label: "文本" },
  boolean: { variant: "default" as const, label: "布尔" }
};

// 布尔类型标签配置
export const booleanBadgeConfig = {
  true: { variant: "default" as const, label: "是" },
  false: { variant: "secondary" as const, label: "否" }
};

// 指标任务/模型状态标签配置
export const taskStatusBadgeConfig = {
  draft: { variant: "secondary" as const, label: "草稿" },
  testing: { variant: "default" as const, label: "测试中" },
  online: { variant: "default" as const, label: "在线" },
  offline: { variant: "outline" as const, label: "离线" },
  archived: { variant: "destructive" as const, label: "已归档" }
};

// 试运行任务状态标签配置
export const executionStatusBadgeConfig = {
  pending: { variant: "secondary" as const, label: "待执行" },
  running: { variant: "default" as const, label: "运行中" },
  success: { variant: "default" as const, label: "成功" },
  failed: { variant: "destructive" as const, label: "失败" },
  cancelled: { variant: "outline" as const, label: "已取消" }
};

// 试运行任务类型标签配置
export const taskTypeBadgeConfig = {
  indicator_task: { variant: "default" as const, label: "指标任务试运行" },
  indicator: { variant: "secondary" as const, label: "指标试运行" },
  model_backtest: { variant: "outline" as const, label: "模型历史回测" }
};

// 宽表名称标签配置
export const wideTableNameBadgeConfig = {
  dep_acct_wide_table: { variant: "default" as const, label: "存款账户宽表" },
  cust_wide_table: { variant: "secondary" as const, label: "客户宽表" },
  loan_acct_wide_table: { variant: "outline" as const, label: "贷款账户宽表" }
};

// 宽表版本状态标签配置
export const wideTableVersionStatusBadgeConfig = {
  current: { variant: "default" as const, label: "当前版本" },
  target: { variant: "secondary" as const, label: "目标版本" },
  history: { variant: "outline" as const, label: "历史版本" },
  skipped: { variant: "destructive" as const, label: "已跳过" }
};

// 报表类型标签配置
export const reportTypeBadgeConfig = {
  summary: { variant: "default" as const, label: "汇总表" },
  detail: { variant: "secondary" as const, label: "明细表" }
};