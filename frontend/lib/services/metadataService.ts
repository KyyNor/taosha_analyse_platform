import api from "../api";

// 数据表管理
export async function getTables(params?: { fields?: boolean; table_name?: string; isAvailable?: boolean }) {
  const res = await api.get("/metadata/tables", { params });
  return res.data;
}

export async function getTableById(tableId: number) {
  const res = await api.get(`/metadata/tables/${tableId}`);
  return res.data.data;
}

export async function getColumnsByTable(tableId: number) {
  const res = await api.get("/metadata/columns", { params: { table_id: tableId } });
  return res.data;
}

export async function createTable(data: any) {
  const res = await api.post("/metadata/tables", data);
  return res.data;
}

export async function updateTable(tableId: number, data: any) {
  const res = await api.put(`/metadata/tables/${tableId}`, data);
  return res.data;
}

export async function deleteTable(tableId: number) {
  const res = await api.delete(`/metadata/tables/${tableId}`);
  return res.data;
}

// 关系配置管理
export async function getRelations() {
  const res = await api.get("/metadata/relation-configs");
  return res.data;
}

export async function getRelationById(configId: number) {
  const res = await api.get(`/metadata/relation-configs/${configId}`);
  return res.data;
}

export async function createRelation(data: any) {
  const res = await api.post("/metadata/relation-configs", data);
  return res.data;
}

export async function updateRelation(configId: number, data: any) {
  const res = await api.put(`/metadata/relation-configs/${configId}`, data);
  return res.data;
}

export async function deleteRelation(configId: number) {
  const res = await api.delete(`/metadata/relation-configs/${configId}`);
  return res.data;
}

// 术语表管理
export async function getGlossary() {
  const res = await api.get("/metadata/glossary/terms");
  return res.data;
}

export async function getGlossaryTermById(termId: number) {
  const res = await api.get(`/metadata/glossary/terms/${termId}`);
  return res.data;
}

export async function createGlossaryTerm(data: any) {
  const res = await api.post("/metadata/glossary/terms", data);
  return res.data;
}

export async function updateGlossaryTerm(termId: number, data: any) {
  const res = await api.put(`/metadata/glossary/terms/${termId}`, data);
  return res.data;
}

export async function deleteGlossaryTerm(termId: number) {
  const res = await api.delete(`/metadata/glossary/terms/${termId}`);
  return res.data;
}

// 数据主题管理
export async function getThemes(params?: { theme_type?: string }) {
  const res = await api.get("/metadata/themes", { params });
  return res.data;
}

export async function getThemeById(themeId: number) {
  const res = await api.get(`/metadata/themes/${themeId}`);
  return res.data;
}

export async function createTheme(data: any) {
  const res = await api.post("/metadata/themes", data);
  return res.data;
}

export async function updateTheme(themeId: number, data: any) {
  const res = await api.put(`/metadata/themes/${themeId}`, data);
  return res.data;
}

export async function deleteTheme(themeId: number) {
  const res = await api.delete(`/metadata/themes/${themeId}`);
  return res.data;
}

export async function getThemeTables(themeId: number) {
  const res = await api.get(`/metadata/themes/${themeId}/tables`);
  return res.data;
}

export async function addTableToTheme(themeId: number, tableId: number) {
  const res = await api.post(`/metadata/themes/${themeId}/tables`, { table_id: tableId });
  return res.data;
}

export async function removeTableFromTheme(themeId: number, tableId: number) {
  const res = await api.delete(`/metadata/themes/${themeId}/tables/${tableId}`);
  return res.data;
}

// 提示词模板管理
export async function getPromptTemplates() {
  const res = await api.get("/metadata/prompt-templates");
  return res.data;
}

export async function getPromptTemplateById(templateId: number) {
  const res = await api.get(`/metadata/prompt-templates/${templateId}`);
  return res.data;
}

export async function createPromptTemplate(data: any) {
  const res = await api.post("/metadata/prompt-templates", data);
  return res.data;
}

export async function updatePromptTemplate(templateId: number, data: any) {
  const res = await api.put(`/metadata/prompt-templates/${templateId}`, data);
  return res.data;
}

export async function deletePromptTemplate(templateId: number) {
  const res = await api.delete(`/metadata/prompt-templates/${templateId}`);
  return res.data;
}