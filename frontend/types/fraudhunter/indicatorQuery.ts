/**
 * 指标数据查询相关类型定义
 */

// 宽表类型
export type WideTableType = 'dep_acct_offline' | 'loan_acct_offline' | 'cust_offline' | 'dep_acct_realtime';

// 宽表类型配置
export const WIDE_TABLE_TYPE_OPTIONS: Array<{value: WideTableType; label: string}> = [
  { value: 'dep_acct_offline', label: '离线存款宽表' },
  { value: 'loan_acct_offline', label: '离线贷款宽表' },
  { value: 'cust_offline', label: '离线客户宽表' },
  { value: 'dep_acct_realtime', label: '实时存款宽表' }
];

export interface WideTableFile {
  id: number;
  wide_table_name: string;
  etl_date: string;
  version_hash: string | null;
  version_status: string | null;  // 版本状态: current, target, archived
  file_path: string;
  file_name: string;  // 文件名
  display_label: string;  // 显示标签: 数据日期(版本号[状态])
  status: string;
  generation_time: string;
  row_count?: number;
  column_count?: number;
  file_size_bytes?: number;
  is_realtime: boolean;
}

export interface IndicatorInfo {
  id: number;
  indicator_code: string;
  indicator_name: string;
  indicator_type: string;
  data_type: string;
  object_type: string;
}

export interface IndicatorQueryCondition {
  id: string;
  field: string;
  operator: "=" | ">" | "<" | ">=" | "<=" | "like";
  value: any;
  field_name?: string;
}

export interface IndicatorQueryRequest {
  snapshot_id: number;
  target_id?: string;
  conditions: Omit<IndicatorQueryCondition, "id">[];
  page: number;
  page_size: number;
}

export interface IndicatorQueryResponse {
  items: Record<string, any>[];
  total: number;
  page: number;
  page_size: number;
}

export interface WideTableFilesResponse {
  items: WideTableFile[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}