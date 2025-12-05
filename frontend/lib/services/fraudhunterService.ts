import api from "../api";

const BASE_PATH = "/fraudhunter";

// ============ 指标任务相关类型定义 ============
export interface IndicatorTask {
  id: number;
  task_code: string;
  task_name: string;
  description?: string;
  logic_type: string;
  logic_content: string;
  source_tables?: string;
  current_version: number;
  latest_version: number;
  status: string;
  created_by?: string;
  created_at: string;
  updated_by?: string;
  updated_at: string;
}

export interface IndicatorTaskCreate {
  task_code: string;
  task_name: string;
  description?: string;
  logic_type?: string;
  logic_content: string;
  source_tables?: string;
}

export interface IndicatorTaskUpdate {
  task_name?: string;
  description?: string;
  logic_content?: string;
  source_tables?: string;
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
  data_type: string;
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
  indicator_code: string;
  indicator_name: string;
  indicator_type: string;
  object_type: string;
  description?: string;
  data_type: string;
  enum_values?: string;
  indicator_task_id: number;
}

export interface IndicatorUpdate {
  indicator_name?: string;
  description?: string;
  object_type?: string;
  data_type?: string;
  enum_values?: string;
}

export interface IndicatorListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Indicator[];
}

// ============ 任务相关类型定义 ============
export interface TaskExecution {
  id: number;
  task_type: string;
  task_id: number;
  execution_id: string;
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

export interface PublishRequest {
  version: number;
  change_description?: string;
}

// ============ 指标任务API ============
export const indicatorTaskService = {
  // 获取指标任务列表
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    task_code?: string;
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
  async create(data: IndicatorTaskCreate): Promise<IndicatorTask> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks`, data);
    return response.data;
  },

  // 更新指标任务
  async update(id: number, data: IndicatorTaskUpdate): Promise<IndicatorTask> {
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

  // 发布指标任务
  async publish(id: number, data: PublishRequest): Promise<IndicatorTask> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/publish`, data);
    return response.data;
  },

  // 归档指标任务
  async archive(id: number): Promise<IndicatorTask> {
    const response = await api.post(`${BASE_PATH}/indicator-tasks/${id}/archive`);
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

  // 发布指标
  async publish(id: number, data: PublishRequest): Promise<Indicator> {
    const response = await api.post(`${BASE_PATH}/indicators/${id}/publish`, data);
    return response.data;
  },

  // 归档指标
  async archive(id: number): Promise<Indicator> {
    const response = await api.post(`${BASE_PATH}/indicators/${id}/archive`);
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
  }): Promise<TaskExecutionListResponse> {
    const response = await api.get(`${BASE_PATH}/tasks/executions`, { params });
    return response.data;
  },

  // 获取任务进度
  async getProgress(taskId: string): Promise<TaskProgress> {
    const response = await api.get(`${BASE_PATH}/tasks/${taskId}/progress`);
    return response.data;
  },

  // 获取任务结果
  async getResult(taskId: string): Promise<TaskResult> {
    const response = await api.get(`${BASE_PATH}/tasks/${taskId}/result`);
    return response.data;
  },

  // 取消任务
  async cancel(taskId: string): Promise<void> {
    await api.post(`${BASE_PATH}/tasks/${taskId}/cancel`);
  },
};

export default {
  indicatorTask: indicatorTaskService,
  indicator: indicatorService,
  task: taskService,
};
