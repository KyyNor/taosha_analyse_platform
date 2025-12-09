import { ModelBacktestTemplate } from './ModelBacktestTemplate';
import { IndicatorTaskTemplate } from './IndicatorTaskTemplate';

// 任务类型到模板的映射
export const TASK_TEMPLATES = {
  'model_backtest': ModelBacktestTemplate,
  'indicator_task': IndicatorTaskTemplate,
  'indicator': IndicatorTaskTemplate,  // 兼容旧的类型名
} as const;

export type TaskType = keyof typeof TASK_TEMPLATES;

export { ModelBacktestTemplate, IndicatorTaskTemplate };