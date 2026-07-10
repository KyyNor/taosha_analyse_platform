import api from "../api";

// 数据表管理
export async function getTables(params?: { page?: number; page_size?: number; fields?: boolean; table_name?: string; isAvailable?: boolean }) {
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

export async function batchUpdateTableAndColumns(tableId: number, data: { table: any; columns: any[] }) {
  const res = await api.put(`/metadata/table/batch`, data);
  return res.data;
}

// 关系配置管理
export async function getRelations(params?: { page?: number; page_size?: number }) {
  const res = await api.get("/metadata/relation-configs", { params });
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
export async function getGlossary(params?: { page?: number; page_size?: number }) {
  const res = await api.get("/metadata/glossary/terms", { params });
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


// 提示词模板管理
export async function getPromptTemplates(params?: { page?: number; page_size?: number }) {
  const res = await api.get("/metadata/prompt-templates", { params });
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

// FineReport报表管理
export interface FineReport {
  id: number;
  report_name: string;
  report_cpt_path: string;
  report_type: 'summary' | 'detail';
  report_design_address: string;
  report_mount_path?: string;
  report_mount_type: 'normal' | 'removed';
  department_id?: number;
  description: string;
  usage_scenario: string;
  is_available: number;
  created_at: string;
  updated_at: string;
}

export interface FineReportFilters {
  page?: number;
  page_size?: number;
  is_available?: number;
  report_type?: string;
  department_id?: number;
  keyword?: string;
}

export interface FineReportCreateData {
  report_name: string;
  report_cpt_path: string;
  report_type: 'summary' | 'detail';
  report_design_address: string;
  report_mount_path?: string;
  report_mount_type?: 'normal' | 'removed';
  department_id?: number;
  description?: string;
  usage_scenario?: string;
  is_available?: number;
}

export interface FineReportUpdateData {
  report_name?: string;
  report_cpt_path?: string;
  report_type?: 'summary' | 'detail';
  report_design_address?: string;
  report_mount_path?: string;
  report_mount_type?: 'normal' | 'removed';
  department_id?: number;
  description?: string;
  usage_scenario?: string;
  is_available?: number;
}

export async function getFineReports(filters?: FineReportFilters) {
  const res = await api.get("/metadata/fine-reports", { params: filters });
  return res.data;
}

export async function getFineReportById(reportId: number) {
  const res = await api.get(`/metadata/fine-reports/${reportId}`);
  return res.data.data;
}

export async function createFineReport(data: FineReportCreateData) {
  const res = await api.post("/metadata/fine-reports", data);
  return res.data;
}

export async function updateFineReport(reportId: number, data: FineReportUpdateData) {
  const res = await api.put(`/metadata/fine-reports/${reportId}`, data);
  return res.data;
}

export async function deleteFineReport(reportId: number) {
  const res = await api.delete(`/metadata/fine-reports/${reportId}`);
  return res.data;
}

export interface DesignerUrl {
  name: string;
  url: string;
  description: string;
}

export async function getDesignerUrls(): Promise<{ success: boolean; data: DesignerUrl[] }> {
  const res = await api.get("/metadata/fine-reports/designer-urls");
  return res.data;
}

// -------------------------------------------------------------------------
// 省市卡BIN维表
// -------------------------------------------------------------------------

export interface ProvinceCardBinRecord {
  card_bin?: string;
  bank_name?: string;
  province?: string;
  city?: string;
}

export async function getProvinceCardBins(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const res = await api.get("/fraudhunter/system-config/province-card-bins", { params });
  return res.data; // { items[], total, page, page_size }
}

export async function updateProvinceCardBin(
  data: ProvinceCardBinRecord,
  method: "POST" | "PUT" | "DELETE",
  cardBin?: string, // 用于 PUT/DELETE 的路径参数
) {
  const encoded = cardBin ? encodeURIComponent(cardBin) : "";
  if (method === "DELETE") {
    const res = await api.delete(`/fraudhunter/system-config/province-card-bins/${encoded}`);
    return res.data;
  }
  const res =
    method === "POST"
      ? await api.post("/fraudhunter/system-config/province-card-bins", data)
      : await api.put(`/fraudhunter/system-config/province-card-bins/${encoded}`, data);
  return res.data;
}

// -------------------------------------------------------------------------
// 受害人录入维表
// -------------------------------------------------------------------------

export interface VictimEntryRecord {
  account_no?: string;
  account_name?: string;
}

export async function getVictimEntries(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const res = await api.get("/fraudhunter/system-config/victim-entries", { params });
  return res.data; // { items[], total, page, page_size }
}

export async function updateVictimEntry(
  data: VictimEntryRecord,
  method: "POST" | "PUT" | "DELETE",
  accountNo?: string, // 用于 PUT/DELETE 的路径参数
) {
  const encoded = accountNo ? encodeURIComponent(accountNo) : "";
  if (method === "DELETE") {
    const res = await api.delete(`/fraudhunter/system-config/victim-entries/${encoded}`);
    return res.data;
  }
  const res =
    method === "POST"
      ? await api.post("/fraudhunter/system-config/victim-entries", data)
      : await api.put(`/fraudhunter/system-config/victim-entries/${encoded}`, data);
  return res.data;
}

export interface ImportResult {
  success: boolean;
  message: string;
  total_rows: number;
  success_count: number;
  fail_count: number;
  errors?: string[];
  detail?: string; // 后端错误时可能返回此字段
}

export async function importVictimEntries(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post<ImportResult>(
    "/fraudhunter/system-config/victim-entries/import",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return res.data;
}