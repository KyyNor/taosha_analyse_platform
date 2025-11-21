import api, { buildApiUrl } from "../api";

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  conversation_history?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
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
 */
export async function chatStream(request: ChatRequest, signal?: AbortSignal): Promise<Response> {
  const url = buildApiUrl("/agents/chat/stream");

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