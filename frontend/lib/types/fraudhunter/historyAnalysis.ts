/** 历史模型分析 — TypeScript 类型，与后端 TrendRequest / TrendPoint / TrendResponse 一一对应 */

export type Granularity = "day" | "week" | "month";

export interface TrendRequest {
  start_date: string;
  end_date: string;
  granularity: Granularity;
  model_ids?: number[] | null;
}

export interface TrendPoint {
  /** 时间刻度，格式取决于 granularity：YYYY-MM-DD / YYYY-Wxx / YYYY-MM */
  date_point: string;
  model_id: number;
  model_name: string;
  distinct_account_count: number;
}

export interface TrendResponse {
  series: TrendPoint[];
  total_points: number;
  meta: Record<string, unknown>;
}

/** 前端内部使用：将 series 按模型分组后的结构 */
export interface SeriesByModel {
  model_id: number;
  model_name: string;
  color: string;
  points: TrendPoint[];
  /** 区间内所有时间粒度的 distinct_account_count 之和（非跨期去重） */
  totalDistinctAccountCount: number;
}