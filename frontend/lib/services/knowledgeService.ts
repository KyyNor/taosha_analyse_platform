import api from "../api";

// ==================== 类型定义 ====================

export interface KnowledgeDocument {
  id: number;
  title: string;
  source_type: 'file' | 'text' | 'sql';
  source_path?: string;
  raw_content: string;
  processing_status: 'pending' | 'processed' | 'failed';
  fragment_count: number;
  file_size?: number;
  content_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  fragments: KnowledgeFragment[];
}

export interface KnowledgeDocumentFilters {
  page?: number;
  page_size?: number;
  source_type?: string;
  search?: string;
}

export interface KnowledgeDocumentCreateData {
  title: string;
  source_type: 'file' | 'text' | 'sql';
  source_path?: string;
  raw_content?: string;
}

export interface KnowledgeDocumentUpdateData {
  title?: string;
  processing_status?: 'pending' | 'processed' | 'failed';
}

export interface KnowledgeFragment {
  id?: number;
  document_id?: number;
  title: string;
  content: string;
  summary?: string;
  generation_method: 'auto' | 'user_extraction' | 'manual';
  extraction_theme?: string;
  extraction_prompt?: string;
  is_modified: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CandidateFragmentsResponse {
  document_id: number;
  fragments: KnowledgeFragment[];
  total_count: number;
}

export interface SaveFragmentsRequest {
  fragments: KnowledgeFragment[];
}

export interface SaveFragmentsResponse {
  saved_fragment_ids: number[];
  saved_count: number;
  document_id: number;
}

export interface KnowledgeFragmentFilters {
  page?: number;
  page_size?: number;
  document_id?: number;
  generation_method?: string;
  search?: string;
}

export interface KnowledgeFragmentUpdateData {
  title?: string;
  content?: string;
  summary?: string;
  is_modified?: boolean;
}

export interface FragmentGenerationRequest {
  document_id: number;
  fragment_count: number;
}

export interface TopicExtractionRequest {
  extraction_theme: string;
  extraction_prompt: string;
}

// ==================== 文档管理 API ====================

/**
 * 获取文档列表
 */
export async function getDocuments(filters?: KnowledgeDocumentFilters) {
  const res = await api.get("/knowledge/documents", { params: filters });
  return res.data;
}

/**
 * 获取文档详情
 */
export async function getDocumentById(docId: number): Promise<KnowledgeDocumentDetail> {
  const res = await api.get(`/knowledge/documents/${docId}`);
  return res.data;
}

/**
 * 创建文档
 */
export async function createDocument(data: KnowledgeDocumentCreateData) {
  const res = await api.post("/knowledge/documents/add", data);
  return res.data;
}

/**
 * 更新文档
 */
export async function updateDocument(docId: number, data: KnowledgeDocumentUpdateData) {
  const res = await api.put(`/knowledge/documents/${docId}`, data);
  return res.data;
}

/**
 * 删除文档
 */
export async function deleteDocument(docId: number) {
  const res = await api.delete(`/knowledge/documents/${docId}`);
  return res.data;
}

// ==================== 片段生成和主题提取 API ====================

/**
 * LLM自动生成片段
 */
export async function generateFragments(docId: number, fragmentCount: number): Promise<CandidateFragmentsResponse> {
  const res = await api.post(`/knowledge/documents/${docId}/generate-fragments`, {
    document_id: docId,
    fragment_count: fragmentCount
  });
  return res.data;
}

/**
 * 主题提取
 */
export async function extractByTopic(docId: number, theme: string, prompt: string): Promise<CandidateFragmentsResponse> {
  const res = await api.post(`/knowledge/documents/${docId}/extract`, {
    extraction_theme: theme,
    extraction_prompt: prompt
  });
  return res.data;
}

/**
 * 保存选中的片段
 */
export async function saveFragments(docId: number, fragments: KnowledgeFragment[]): Promise<SaveFragmentsResponse> {
  const res = await api.post(`/knowledge/documents/${docId}/save-fragments`, {
    fragments
  });
  return res.data;
}

// ==================== 片段管理 API ====================

/**
 * 获取片段列表
 */
export async function getFragments(filters?: KnowledgeFragmentFilters) {
  const res = await api.get("/knowledge/fragments", { params: filters });
  return res.data;
}

/**
 * 获取片段详情
 */
export async function getFragmentById(fragId: number) {
  const res = await api.get(`/knowledge/fragments/${fragId}`);
  return res.data;
}

/**
 * 更新片段
 */
export async function updateFragment(fragId: number, data: KnowledgeFragmentUpdateData) {
  const res = await api.put(`/knowledge/fragments/${fragId}`, data);
  return res.data;
}

/**
 * 删除片段
 */
export async function deleteFragment(fragId: number) {
  const res = await api.delete(`/knowledge/fragments/${fragId}`);
  return res.data;
}
