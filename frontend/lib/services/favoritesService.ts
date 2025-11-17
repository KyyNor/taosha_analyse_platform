import api from "../api";

export async function getFavorites(page = 1, pageSize = 50) {
  const params = { page: String(page), pageSize: String(pageSize) };
  const res = await api.get("/favorites", { params });
  return res.data;
}

export async function executeFavorite(id: number) {
  const res = await api.post(`/favorites/${id}/execute`);
  return res.data;
}

export async function updateFavorite(id: number, title: string) {
  const res = await api.put(`/favorites/${id}`, { title });
  return res.data;
}

export async function deleteFavorite(id: number) {
  const res = await api.delete(`/favorites/${id}`);
  return res.data;
}