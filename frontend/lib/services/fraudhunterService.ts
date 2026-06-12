import api from "../api";
import type { IndicatorDataType } from "@/types/fraudhunter/rule";

const BASE_PATH = "/fraudhunter";

// ============ 指标任务相关类型定义 ============
export interface IndicatorTask {
  id: number;
  task_code: string;
  task_name: string;
  description?: string;
  logic_type: string;
  logic_content: string;
  realtime_logic_content?: string;
  source_tables?: string;
  object_type: string;
  current_version: number;
  latest_version: number;
  status: string;
  created_by?: string;
  created_at: string;
  updated_by?: string;
  updated_at: string;
}

export interface IndicatorTaskCreate {
  task_code?: string;
  task_name: string;
  description?: string;
  logic_type?: string;
  logic_content: string;
  realtime_logic_content?: string;
  source_tables?: string;
  object_type: string;
}

export interface IndicatorTaskUpdate {
  task_name?: string;
  description?: string;
  logic_content?: string;
  realtime_logic_content?: string;
  source_tables?: string;
  object_type?: string;
}

export interface IndicatorTaskUpdateResponse {
  success: boolean;
  message?: string;
  errors?: string[];
  data?: IndicatorTask;
}

export interface IndicatorTaskCreateResponse {
  success: boolean;
  message?: string;
  errors?: string[];
  data?: IndicatorTask;
}

export interface IndicatorTaskListResponse {
  total: number;
  page: number;
  page_size: number;
  items: IndicatorTask[];
}

// ============ 指标相关类型定义 ============
export interface Indicator {
  id: number;
  indicator_code: string;
  indicator_name: string;
  indicator_type: string;
  object_type: string;
  description?: string;
  data_type: IndicatorDataType;
  enum_values?: string;
  indicator_task_id: number;
  current_version: number;
  latest_version: number;
  status: string;
  created_by?: string;
  created_at: string;
  updated_by?: string;
  updated_at: string;
}

export interface IndicatorCreate {
  indicator_code?: string;
  indicator_name: string;
  indicator_type: string;
  object_type: string;
  description?: string;
  data_type: IndicatorDataType;
  enum_values?: string;
  indicator_task_id?: number;
}

export interface IndicatorUpdate {
  indicator_name?: string;
  description?: string;
  object_type?: string;
  data_type?: IndicatorDataType;
  enum_values?: string;
}

export interface IndicatorListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Indicator[];
}

// ============ 批量创建相关类型定义 ============
export interface IndicatorBatchCreateItem {
  indicator_name: string;
  description?: string;
  data_type: IndicatorDataType;
  enum_values?: string;
}

export interface IndicatorTaskBatchCreate {
  indicator_type: string;
  object_type: string;
  task_data: IndicatorTaskCreate;
  indicators: IndicatorBatchCreateItem[];
}

export interface IndicatorBatchCreateResult {
  index: number;
  success: boolean;
  indicator?: {
    id: number;
    indicator_code: string;
    indicator_name: string;
  };
  error?: string;
}

export interface IndicatorBatchCreateResponse {
  task_id: number;
  task_code: string;
  task_name: string;
  total: number;
  success_count: number;
  failed_count: number;
  results: IndicatorBatchCreateResult[];
}

// ============ 预执行验证相关类型定义 ============
export interface TaskPreExecuteRequest {
  task_data: IndicatorTaskCreate;
  indicator_ids: number[];
  etl_date?: string;
}

export interface TaskPreExecuteResponse {
  success: boolean;
  message: string;
  execution_id?: string;
  sample_results?: Record<string, any>;
  validation_details?: {
    valid: boolean;
    required_fields: string[];
    actual_fields: string[];
    missing_fields: string[];
    extra_fields: string[];
    indicator_codes: string[];
  };
}

// ============ 任务相关类型定义 ============
export interface TaskExecution {
  id: number;
  task_type: string;
  task_id: number;
  execution_id: string;
  parent_execution_id?: string;
  start_time?: string;
  end_time?: string;
  status: string;
  result_summary?: any;
  created_by?: string;
  created_at: string;
}

export interface TaskExecutionListResponse {
  total: number;
  page: number;
  page_size: number;
  items: TaskExecution[];
}

export interface TaskProgress {
  task_id: string;
  task_type: string;
  parent_execution_id?: string;
  status: string;
  progress?: number;
  current_step?: string;
  start_time?: string;
  end_time?: string;
  estimated_remaining_seconds?: number;
}

export interface TaskResult {
  task_id: string;
  status: string;
  duration_seconds?: number;
  result?: any;
}

export interface DryRunRequest {
  etl_date: string;
  task_version?: number;
  sample_size?: number;
}

export interface DryRunResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface PublishToDSRequest {
  schedule_cron?: string;
}

export interface PublishToDSResponse {
  success: boolean;
  message: string;
  workflow_name?: string;
  workflow_code?: string;
  ds_task_name?: string;
  ds_task_code?: string;
  online_success?: boolean;
}

export interface RerunRequest {
  start_date: string;
  end_date?: string;
}

export interface RerunResponse {
  success: boolean;
  message: string;
  workflow_code?: string;
  start_date: string;
  end_date?: string;
}

// ============ 指标任务API ============
export const indicatorTaskService = {
  // 获取指标任务列表
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;  // 修改：使用search参数名与后端API一致
    object_type?: string;
  }): Promise<IndicatorTaskListResponse> {
    const response = await api.get(`${BASE_PATH}/indicator-tasks`, { params });
    return response.data;
  },

  // 获取指标任务详情
  async get(id: number): Promise<IndicatorTask> {
    const response = await api.get(`${BASE_PATH}/indicator-tasks/${id}`);
    return response.data;
  },

  // 创建指标任务
  async create(data: IndicatorTaskCreate): Promise<IndicatorTaskCreateResponse> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks`, data);
    return response.data;
  },

  // 更新指标任务
  async update(id: number, data: IndicatorTaskUpdate): Promise<IndicatorTaskUpdateResponse> {
    const response = await api.put(`${BASE_PATH}/indicator-tasks/${id}`, data);
    return response.data;
  },

  // 删除指标任务
  async delete(id: number): Promise<void> {
    await api.delete(`${BASE_PATH}/indicator-tasks/${id}`);
  },

  // 指标任务试运行
  async dryRun(id: number, data: DryRunRequest): Promise<DryRunResponse> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/dry-run`, data);
    return response.data;
  },

  // 归档指标任务
  async archive(id: number): Promise<IndicatorTask> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/archive`);
    return response.data;
  },

  // 上线到 DolphinScheduler
  async publishToDS(id: number, data: PublishToDSRequest = {}): Promise<PublishToDSResponse> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/publish-to-ds`, data);
    return response.data;
  },

  // 补数
  async rerun(id: number, data: RerunRequest): Promise<RerunResponse> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/rerun`, data);
    return response.data;
  },
};

// ============ 指标API ============
export const indicatorService = {
  // 获取指标列表
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    indicator_type?: string;
    object_type?: string;
    indicator_task_id?: number;
    query_type?: string;
  }): Promise<IndicatorListResponse> {
    const response = await api.get(`${BASE_PATH}/indicators`, { params });
    return response.data;
  },

  // 获取指标详情
  async get(id: number): Promise<Indicator> {
    const response = await api.get(`${BASE_PATH}/indicators/${id}`);
    return response.data;
  },

  // 创建指标
  async create(data: IndicatorCreate): Promise<Indicator> {
    const response = await api.post(`${BASE_PATH}/indicators`, data);
    return response.data;
  },

  // 更新指标
  async update(id: number, data: IndicatorUpdate): Promise<Indicator> {
    const response = await api.put(`${BASE_PATH}/indicators/${id}`, data);
    return response.data;
  },

  // 删除指标
  async delete(id: number): Promise<void> {
    await api.delete(`${BASE_PATH}/indicators/${id}`);
  },

  // 归档指标
  async archive(id: number): Promise<Indicator> {
    const response = await api.post(`${BASE_PATH}/indicators/${id}/archive`);
    return response.data;
  },

  // 批量创建指标
  async batchCreate(data: IndicatorTaskBatchCreate): Promise<IndicatorBatchCreateResponse> {
    const response = await api.post(`${BASE_PATH}/indicators/batch`, data);
    return response.data;
  },

  // 创建任务并关联指标
  async createTaskWithIndicators(taskData: IndicatorTaskCreate, indicatorIds: number[]): Promise<any> {
    const response = await api.post(`${BASE_PATH}/indicators/batch/create-task`, {
      task_data: taskData,
      indicator_ids: indicatorIds
    });
    return response.data;
  },

  // 预执行验证任务
  async validateTaskBeforeCreate(taskData: IndicatorTaskCreate, indicatorIds: number[], etlDate?: string): Promise<any> {
    const response = await api.post(`${BASE_PATH}/indicators/batch/validate-task`, {
      task_data: taskData,
      indicator_ids: indicatorIds,
      etl_date: etlDate
    });
    return response.data;
  },
};

// ============ 宽表版本相关类型定义 ============
export interface WideTableVersion {
  id: number;
  wide_table_name: string;
  version_hash: string;
  indicator_metadata: Record<string, {
    version: number;
    indicator_code: string;
    indicator_name: string;
    indicator_type: string;
    object_type: string;
    indicator_task_id: number;
  }>;
  status: string;
  target_at?: string;
  current_at?: string;
  history_at?: string;
  skipped_at?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface IndicatorProgressInfo {
  indicator_id: number;
  indicator_code: string;
  indicator_name: string;
  indicator_type: string;
  indicator_version: number;
  indicator_task_id?: number;
}

export interface WideTableVersionDetail extends WideTableVersion {
  indicators: IndicatorProgressInfo[];
  snapshot_count: number;
  completed_dates: string[];
}

export interface IncompleteTaskInfo {
  task_id: number;
  task_code: string;
  task_name: string;
  object_type: string;
}

export interface DateProgressDetail {
  etl_date: string;
  completed_count: number;
  total_count: number;
  is_complete: boolean;
  last_finish_time?: string;
  incomplete_tasks: IncompleteTaskInfo[];
}

export interface WideTableVersionProgress {
  version_hash: string;
  wide_table_name: string;
  total_indicators: number;
  completed_dates: string[];
  recent_progress: DateProgressDetail[];
  lookback_days: number;
}

export interface WideTableVersionListResponse {
  total: number;
  page: number;
  page_size: number;
  items: WideTableVersion[];
}

export interface WideTableSnapshot {
  id: number;
  wide_table_name: string;
  etl_date: string;
  version_hash?: string;
  parquet_file_path: string;
  file_size_bytes?: number;
  row_count?: number;
  column_count?: number;
  status: string;
  generation_time?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// ============ 宽表版本API ============
export const wideTableVersionService = {
  // 获取版本列表
  async list(params?: {
    page?: number;
    page_size?: number;
    wide_table_name?: string;
    status?: string;
  }): Promise<WideTableVersionListResponse> {
    const response = await api.get(`${BASE_PATH}/wide-table/versions`, { params });
    return response.data;
  },

  // 获取版本详情（含指标清单和执行进度）
  async getDetail(versionHash: string): Promise<WideTableVersionDetail> {
    const response = await api.get(`${BASE_PATH}/wide-table/versions/${versionHash}`);
    return response.data;
  },

  // 获取版本执行进度（自动使用配置的查询周期）
  async getProgress(versionHash: string): Promise<WideTableVersionProgress> {
    const response = await api.get(`${BASE_PATH}/wide-table/versions/${versionHash}/progress`);
    return response.data;
  },

  // 获取快照列表
  async listSnapshots(params?: {
    wide_table_name?: string;
    etl_date?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<WideTableSnapshot[]> {
    const response = await api.get(`${BASE_PATH}/wide-table/snapshots`, { params });
    return response.data;
  },
};

// ============ 任务API ============
export const taskService = {
  // 获取任务执行列表
  async list(params?: {
    page?: number;
    page_size?: number;
    task_type?: string;
    task_id?: number;
    status?: string;
    parent_execution_id?: string;
    result_summary?: string;
  }): Promise<TaskExecutionListResponse> {
    const response = await api.get(`${BASE_PATH}/tasks/executions`, { params });
    return response.data;
  },

  // 获取任务进度
  async getProgress(taskId: number): Promise<TaskProgress> {
    const response = await api.get(`${BASE_PATH}/tasks/${taskId}/progress`);
    return response.data;
  },

  // 获取任务结果
  async getResult(taskId: number): Promise<TaskResult> {
    const response = await api.get(`${BASE_PATH}/tasks/${taskId}/result`);
    return response.data;
  },

  // 取消任务
  async cancel(taskId: number): Promise<void> {
    await api.post(`${BASE_PATH}/tasks/${taskId}/cancel`);
  },
};

// ============ 指标数据查询服务 ============
export const indicatorQueryService = {
  // 获取宽表文件列表
  async getWideTableFiles(params: {
    wide_table_type: string;
    date_filter?: string;
    page?: number;
    page_size?: number;
  }) {
    const response = await api.get(`${BASE_PATH}/indicator-query/wide-tables`, { params });
    return response.data;
  },

  // 根据快照ID获取指标列表
  async getIndicatorsBySnapshot(snapshotId: number) {
    const response = await api.get(`${BASE_PATH}/indicator-query/indicators/${snapshotId}`);
    return response.data;
  },

  // 执行数据查询
  async queryData(request: {
    snapshot_id: number;
    target_id?: string;
    conditions: Array<{
      field: string;
      operator: string;
      value: any;
    }>;
    page: number;
    page_size: number;
  }) {
    const response = await api.post(`${BASE_PATH}/indicator-query/query`, request);
    return response.data;
  }
};

// ============ 预警管控模型服务 ============
export { riskControlModelService } from './fraudhunter/riskControlModelService';

// ============ 告警管控记录服务 ============
export { alertControlRecordService } from './fraudhunter/alertControlRecordService';

export default {
  indicatorTask: indicatorTaskService,
  indicator: indicatorService,
  task: taskService,
  wideTableVersion: wideTableVersionService,
  indicatorQuery: indicatorQueryService,
};
