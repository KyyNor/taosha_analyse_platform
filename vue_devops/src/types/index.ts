// 系统状态类型
export interface SystemStatus {
  app_name: string;
  version: string;
  database: {
    database_type: string;
    total_tables: number;
  };
}

// 数据表类型
export interface DataTable {
  table_name: string;
  comment?: string;
  row_count: number;
}

// 查询结果类型
export interface QueryResult {
  success: boolean;
  error?: string;
  sql_query?: string;
  data?: Record<string, any>[];
  logs?: QueryLog[];
  clear_check_details?: ClearCheckDetails;
}

// 查询日志类型
export interface QueryLog {
  step: string;
  success: boolean;
  timestamp: string;
  input_data?: string;
  model_output?: string;
  error?: string;
  prompt?: string;
}

// 输入清晰度验证类型
export interface ClearCheckDetails {
  is_clear: boolean;
  reason?: string;
  suggestions?: string[];
}

// 元数据表类型
export interface MetadataTable {
  name: string;
  comment?: string;
  is_available: number;
  columns?: MetadataColumn[];
}

// 元数据列类型
export interface MetadataColumn {
  name: string;
  type: string;
  comment?: string;
  is_available: number;
  business_type?: string;
  relation_id?: string;
}

// 术语类型
export interface GlossaryTerm {
  id: number;
  term: string;
  definition: string;
  sql_expression?: string;
  category?: string;
  aliases?: string[];
}

// 关联配置类型
export interface RelationConfig {
  relation_id: string;
  relation_family: string;
  relation_subfamily: string;
  relation_desc?: string;
}

// 聊天历史类型
export interface ChatHistory {
  query: string;
  timestamp: number;
  success: boolean;
  sql?: string;
  data_count: number;
}

// 响应结果展示类型
export type ResultType = 'text' | 'table' | 'chart' | 'code' | 'markdown' | 'image' | 'error';

export interface DisplayResult {
  type: ResultType;
  content: any;
  title?: string;
}