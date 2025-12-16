import api from "../../api";

const BASE_PATH = "/fraudhunter/system-config";

// ============ 系统配置相关类型定义 ============

export interface SystemConfig {
  id: number;
  config_category: string;
  config_key: string;
  config_desc: string;
  config_type: string;
  config_value: {
    value: any;
  };
  sql_in_convert: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface SystemConfigCreate {
  config_category: string;
  config_key: string;
  config_desc: string;
  config_type: string;
  config_value: {
    value: any;
  };
  sql_in_convert: boolean;
  sort_order: number;
}

export interface SystemConfigUpdate extends SystemConfigCreate {}

export interface SystemConfigListResponse {
  items: SystemConfig[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExcelParseResponse {
  columns: string[];
  data: Record<string, any>[];
  row_count: number;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
}

// ============ 系统配置API ============

export const systemConfigService = {
  /**
   * 获取系统配置列表
   */
  async list(params: ListParams): Promise<SystemConfigListResponse> {
    const response = await api.get(BASE_PATH, { params });
    return response.data;
  },

  /**
   * 获取系统配置详情
   */
  async getById(id: number): Promise<SystemConfig> {
    const response = await api.get(`${BASE_PATH}/${id}`);
    return response.data;
  },

  /**
   * 创建系统配置
   */
  async create(data: SystemConfigCreate): Promise<SystemConfig> {
    const response = await api.post(BASE_PATH, data);
    return response.data;
  },

  /**
   * 更新系统配置
   */
  async update(id: number, data: SystemConfigUpdate): Promise<SystemConfig> {
    const response = await api.put(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  /**
   * 解析Excel文件
   */
  async parseExcel(file: File): Promise<ExcelParseResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`${BASE_PATH}/parse-excel`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }
};

export default systemConfigService;
