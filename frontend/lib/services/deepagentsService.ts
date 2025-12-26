/**
 * DeepAgents 服务
 * 提供数据分析任务的 API 调用封装
 */

import api from "../api";

const BASE_PATH = "/deepagents";

// ============ 类型定义 ============

export interface AnalysisSession {
  id: number;
  session_id: string;
  question: string;
  question_source: string | null;
  proposer_topic_id: number | null;
  status: "pending" | "running" | "completed" | "failed";
  start_time: string | null;
  end_time: string | null;
  duration_seconds: number | null;
  report_path: string | null;
  report_content: string | null;
  llm_output: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AnalysisScore {
  id: number;
  session_id: string;
  process_score: number | null;
  process_reasons: string[] | null;
  process_deductions: string[] | null;
  report_score: number | null;
  report_reasons: string[] | null;
  report_deductions: string[] | null;
  conclusion_score: number | null;
  conclusion_reasons: string[] | null;
  conclusion_deductions: string[] | null;
  overall_score: number | null;
  improvement_suggestions: Array<{
    category: string;
    priority: string;
    suggestion: string;
  }> | null;
  scored_at: string | null;
  scorer_model: string | null;
}

export interface SessionListItem {
  id: number;
  session_id: string;
  question: string;
  question_source: string | null;
  status: string;
  start_time: string | null;
  end_time: string | null;
  duration_seconds: number | null;
  overall_score: number | null;
  created_at: string;
}

export interface SessionListResponse {
  items: SessionListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionDetailResponse {
  session: AnalysisSession;
  scores: AnalysisScore | null;
}

export interface SubmitTaskRequest {
  question: string;
  question_source?: string;
}

export interface SubmitTaskResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface QueueStatus {
  is_running: boolean;
  queue_size: number;
  running_count: number;
  current_task: {
    session_id: string;
  } | null;
}

// ============ API 服务 ============

export const deepagentsService = {
  /**
   * 提交分析任务
   */
  async submitTask(request: SubmitTaskRequest): Promise<SubmitTaskResponse> {
    const response = await api.post(`${BASE_PATH}/submit`, request);
    return response.data;
  },

  /**
   * 获取会话列表
   */
  async listSessions(params: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  } = {}): Promise<SessionListResponse> {
    const response = await api.get(`${BASE_PATH}/sessions`, { params });
    return response.data;
  },

  /**
   * 获取会话详情
   */
  async getSession(sessionId: string): Promise<SessionDetailResponse> {
    const response = await api.get(`${BASE_PATH}/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * 下载分析结果
   */
  async downloadOutput(sessionId: string): Promise<void> {
    const response = await api.get(
      `${BASE_PATH}/sessions/${sessionId}/download`,
      {
        responseType: "blob",
      }
    );

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `analysis_${sessionId.slice(0, 8)}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * 获取队列状态
   */
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await api.get(`${BASE_PATH}/queue/status`);
    return response.data;
  },

  /**
   * 启动队列
   */
  async startQueue(): Promise<{ status: string; message: string }> {
    const response = await api.post(`${BASE_PATH}/queue/start`);
    return response.data;
  },

  /**
   * 停止队列
   */
  async stopQueue(): Promise<{ status: string; message: string }> {
    const response = await api.post(`${BASE_PATH}/queue/stop`);
    return response.data;
  },
};

export default deepagentsService;
