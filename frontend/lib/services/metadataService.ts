import api from "../api";

export async function getTables() {
  const res = await api.get("/metadata/tables");
  return res.data;
}

export async function getRelations() {
  const res = await api.get("/metadata/relation-configs");
  return res.data;
}

export async function getGlossary() {
  const res = await api.get("/metadata/glossary/terms");
  return res.data;
}

export async function getThemes() {
  const res = await api.get("/metadata/themes");
  return res.data;
}

export async function getPromptTemplates() {
  const res = await api.get("/metadata/prompt-templates");
  return res.data;
}