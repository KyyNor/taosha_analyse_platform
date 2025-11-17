import api from "../api";

export async function runQuery(payload: { text: string }) {
  const res = await api.post("/query/run", payload);
  return res.data;
}

export async function fetchHistory() {
  const res = await api.get("/query/history");
  return res.data;
}