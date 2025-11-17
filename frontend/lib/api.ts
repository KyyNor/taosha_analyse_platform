import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || "/api"
});

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

export default api;