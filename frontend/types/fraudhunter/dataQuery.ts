/**
 * 指标数据查询相关类型定义
 */

export interface WideTableFile {
  id: number;
  wide_table_name: string;
  etl_date: string;
  version_hash: string | null;
  file_path: string;
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

export interface QueryCondition {
  id: string;
  field: string;
  operator: "=" | ">" | "<" | ">=" | "<=" | "like";
  value: any;
  field_name?: string;
}

export interface DataQueryRequest {
  snapshot_id: number;
  target_id?: string;
  conditions: Omit<QueryCondition, "id">[];
  page: number;
  page_size: number;
}

export interface DataQueryResponse {
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