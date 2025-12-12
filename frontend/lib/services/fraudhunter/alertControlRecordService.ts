import api from "../../api";

const BASE_PATH = "/fraudhunter";

// ============ 告警管控记录相关类型定义 ============
export interface AlertControlRecord {
  id: number;
  hit_record_id: number;
  account_id: string;
  record_date: string;
  model_id: number;
  model_name: string;
  
  // 告警信息
  alert_status: string;
  alert_message?: string;
  alert_person?: string;
  alert_time?: string;
  
  // 管控信息
  control_status: string;
  control_time?: string;
  control_serial_number?: string;
  
  // 审计信息
  created_at: string;
  updated_at: string;
}

export interface HitRecord {
  id: number;
  account_id: string;
  hit_time: string;
  hit_model_ids: number[];
  hit_model_names: string[];
  indicator_data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AlertControlRecordDetail {
  record: AlertControlRecord;
  hit_record: HitRecord;
}

export interface AlertControlFilters {
  start_date?: string;
  end_date?: string;
  account_id?: string;
  model_id?: number;
  model_name?: string;
  alert_status?: string;
  control_status?: string;
  search?: string;
}

export interface AlertControlListResponse {
  records: AlertControlRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExportRequest {
  filters: AlertControlFilters;
  format: 'csv' | 'excel';
}

// ============ 告警管控记录API ============
export const alertControlRecordService = {
  // 获取告警管控记录列表
  async list(params: {
    page?: number;
    page_size?: number;
  } & AlertControlFilters): Promise<AlertControlListResponse> {
    const response = await api.get(`${BASE_PATH}/alert-control-records`, { params });
    return response.data;
  },

  // 获取告警管控记录详情
  async get(id: number): Promise<AlertControlRecordDetail> {
    const response = await api.get(`${BASE_PATH}/alert-control-records/${id}`);
    return response.data;
  },

  // 导出告警管控记录
  async export(data: ExportRequest): Promise<Blob> {
    const response = await api.post(`${BASE_PATH}/alert-control-records/export`, data, {
      responseType: 'blob'
    });
    return response.data;
  },

  // 获取统计数据
  async getStats(filters?: AlertControlFilters): Promise<{
    total_records: number;
    alert_sent: number;
    alert_duplicate: number;
    control_executed: number;
    control_duplicate: number;
  }> {
    const response = await api.get(`${BASE_PATH}/alert-control-records/stats`, { 
      params: filters 
    });
    return response.data;
  }
};

export default alertControlRecordService;