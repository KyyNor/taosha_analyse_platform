import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || "/api/taosha/v1"
});

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

export function buildApiUrl(path: string): string {
  const baseURL = process.env.NEXT_PUBLIC_API_BASE || "/api";
  return `${baseURL}${path}`;
}

export default api;