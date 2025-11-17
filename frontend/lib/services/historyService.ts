import api from "../api";

export async function getQueryHistory(page = 1, pageSize = 50, filters: any = {}) {
  const params = { page: String(page), page_size: String(pageSize), ...filters };
  const res = await api.get("/nlquery/history", { params });
  return res.data;
}

export async function getQueryHistoryDetail(taskId: string) {
  const res = await api.get(`/nlquery/${taskId}/history-detail`);
  return res.data;
}