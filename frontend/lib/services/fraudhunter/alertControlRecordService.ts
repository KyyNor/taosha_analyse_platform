import api from "../../api";
import { AxiosResponse } from 'axios';
import type { TrendRequest, TrendResponse } from "@/lib/types/fraudhunter/historyAnalysis";

const BASE_PATH = "/fraudhunter";

// ============ 告警管控记录相关类型定义 ============
export interface AlertControlRecord {
  id: number;
  hit_record_id: number;
  account_id: string;
  branch_no?: string | null;
  record_date: string;
  hit_model_ids: number[];
  hit_model_names: string[];

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
  branch_no?: string | null;
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
  branch_no?: string;
  model_ids?: number[];
  model_name?: string;
  alert_status?: string;
  control_status?: string;
  search?: string;
  hide_inactive?: boolean;
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

// ============ 命中记录指标展示配置 ============
export interface IndicatorTagItem {
  indicator_code: string;
  indicator_name: string;
  indicator_type: 'offline' | 'realtime';
}

export interface IndicatorTagConfig {
  indicators: IndicatorTagItem[];
}

// 后端 Dict[int, ...] 经 JSON 序列化后键为字符串（hit_record_id）
export type IndicatorValuesMap = Record<string, Record<string, string | number | boolean | null>>;

// ============ 告警管控记录API ============
export const alertControlRecordService = {
  // 获取告警管控记录列表
  async list(params: {
    page?: number;
    page_size?: number;
  } & AlertControlFilters): Promise<AlertControlListResponse> {
    const response = await api.post(`${BASE_PATH}/alert-control-records`, params);
    return response.data;
  },

  // 获取告警管控记录详情
  async get(id: number): Promise<AlertControlRecordDetail> {
    const response = await api.get(`${BASE_PATH}/alert-control-records/${id}`);
    return response.data;
  },

  // 导出告警管控记录
  async export(data: ExportRequest): Promise<AxiosResponse> {
    const response = await api.post(`${BASE_PATH}/alert-control-records/export`, {
      ...data.filters,
      format: data.format,
    }, {
      responseType: 'blob'
    });
    return response;
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
  },

  // 获取模型命中账户数历史趋势
  async getModelHistoryTrend(params: TrendRequest): Promise<TrendResponse> {
    const response = await api.post(`${BASE_PATH}/alert-control-records/history/trend`, {
      start_date: params.start_date,
      end_date: params.end_date,
      granularity: params.granularity ?? "day",
      model_ids: params.model_ids?.length ? params.model_ids : undefined,
    });
    return response.data;
  },

  // 获取命中记录指标展示配置（空列表表示未配置）
  async getIndicatorTagConfig(): Promise<IndicatorTagConfig> {
    const response = await api.get(`${BASE_PATH}/alert-control-records/indicator-tag-config`);
    return response.data;
  },

  // 更新命中记录指标展示配置（顺序即展示顺序，空数组表示清空）
  async updateIndicatorTagConfig(indicatorCodes: string[]): Promise<IndicatorTagConfig> {
    const response = await api.put(`${BASE_PATH}/alert-control-records/indicator-tag-config`, {
      indicator_codes: indicatorCodes,
    });
    return response.data;
  },

  // 批量获取命中记录指标值（供列表页异步加载，单次最多500条）
  async fetchIndicatorValues(hitRecordIds: number[], indicatorCodes: string[]): Promise<IndicatorValuesMap> {
    const response = await api.post(`${BASE_PATH}/alert-control-records/indicator-values`, {
      hit_record_ids: hitRecordIds,
      indicator_codes: indicatorCodes,
    });
    return response.data.values;
  },
};

export default alertControlRecordService;
