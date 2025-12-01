import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || "/api/taosha/v1"
});

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

export function buildApiUrl(path: string): string {
  const baseURL = process.env.NEXT_PUBLIC_API_BASE || "/api/taosha/v1";
  return `${baseURL}${path}`;
}

export default api;

// --- History API ---

export interface Session {
  id: string;
  title: string | null;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  type: string;
  created_at: string;
  meta_info?: any;
}

export const chatApi = {
  getHistory: async (userId: string) => {
    const res = await api.get<Session[]>(`/agents/history`, { params: { user_id: userId } });
    return res.data;
  },

  getSessionMessages: async (sessionId: string) => {
    const res = await api.get<MessageResponse[]>(`/agents/history/${sessionId}`);
    return res.data;
  },

  deleteSession: async (sessionId: string, userId: string) => {
    await api.delete(`/agents/history/${sessionId}`, { params: { user_id: userId } });
  },

  updateSessionTitle: async (sessionId: string, title: string) => {
    await api.put(`/agents/history/${sessionId}/title`, null, { params: { title } });
  }
};
