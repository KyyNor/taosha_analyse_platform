import api from "../api";

export async function startAgent(payload: Record<string, unknown>) {
  const res = await api.post("/agent/start", payload);
  return res.data;
}

export async function stopAgent(id: string) {
  const res = await api.post(`/agent/${id}/stop`);
  return res.data;
}