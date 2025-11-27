import api from "../api";

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
}

export async function startAgent(payload: Record<string, unknown>) {
  const res = await api.post("/agent/start", payload);
  return res.data;
}

export async function stopAgent(id: string) {
  const res = await api.post(`/agent/${id}/stop`);
  return res.data;
}

/**
 * 发送聊天消息（非流式）
 */
export async function chat(request: ChatRequest) {
  const res = await api.post("/agents/chat", request);
  return res.data;
}

/**
 * 发送聊天消息（流式）
 * 使用Server-Sent Events (SSE)进行实时响应
 * 绕过Next.js代理缓冲，直接访问后端流式API
 */
export async function chatStream(request: ChatRequest, signal?: AbortSignal): Promise<Response> {
  // 使用专用的流式API地址，避免Next.js代理缓冲
  const baseUrl = process.env.NEXT_PUBLIC_API_STREAM_BASE
    || process.env.NEXT_PUBLIC_API_BASE
    || "/api/taosha/v1";
  const url = `${baseUrl}/agents/chat/stream`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
      "Cache-Control": "no-cache",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  return response;
}

/**
 * 检查Agent服务健康状态
 */
export async function checkHealth() {
  const res = await api.get("/agents/health");
  return res.data;
}