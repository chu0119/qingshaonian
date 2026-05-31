import client from './client';

export interface QuestionnaireInfo {
  id: number;
  school_id: number | null;
  code?: string | null;
  title: string;
  description: string;
  category: string;
  applicable_grades: string;
  is_builtin: boolean;
  source_type: string;
  disclaimer: string;
  dimensions: Array<{ code: string; title: string }>;
  scoring_rule: Record<string, unknown>;
  risk_rules: Record<string, unknown>;
  quality_rules: Record<string, unknown>;
  status: string;
  created_by: number | null;
  question_count: number;
  version: number;
  rule_version?: string;
  locked_after_publish?: boolean;
  source_questionnaire_id?: number | null;
  editable?: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface QuestionData {
  id?: number;
  code?: string | null;
  title: string;
  description?: string;
  type: string;
  required: boolean;
  sort_order: number;
  dimension?: string;
  risk_tag?: string;
  is_reverse: boolean;
  is_attention_check: boolean;
  attention_correct_answer?: string;
  risk_threshold?: number | null;
  options: OptionData[];
}

export interface OptionData {
  id?: number;
  content: string;
  score: number;
  sort_order: number;
  is_risk_option: boolean;
}

export interface ContradictionGroupData {
  id?: number;
  question_a_id: number;
  question_b_id: number;
  relation_type: string;
  max_score_diff: number;
  description?: string;
}

export interface QuestionnaireDetail extends QuestionnaireInfo {
  questions: QuestionData[];
  contradiction_groups: ContradictionGroupData[];
}

export async function getQuestionnaires(params?: Record<string, unknown>) {
  const res = await client.get('/questionnaires', { params });
  return res.data.data;
}

export async function getQuestionnaire(id: number, prefix?: string): Promise<QuestionnaireDetail> {
  const base = prefix ? `${prefix}/questionnaires` : '/questionnaires';
  const res = await client.get(`${base}/${id}`);
  return res.data.data;
}

export async function createQuestionnaire(data: Record<string, unknown>) {
  const res = await client.post('/questionnaires', data);
  return res.data;
}

export async function updateQuestionnaire(id: number, data: Record<string, unknown>, prefix?: string) {
  const base = prefix ? `${prefix}/questionnaires` : '/questionnaires';
  const res = await client.put(`${base}/${id}`, data);
  return res.data;
}

export async function deleteQuestionnaire(id: number) {
  const res = await client.delete(`/questionnaires/${id}`);
  return res.data;
}

export async function copyQuestionnaire(id: number, prefix?: string) {
  const base = prefix ? `${prefix}/questionnaires` : '/questionnaires';
  const res = await client.post(`${base}/${id}/copy`);
  return res.data.data;
}

export async function addQuestion(qid: number, data: QuestionData) {
  const res = await client.post(`/questionnaires/${qid}/questions`, data);
  return res.data;
}

export async function updateQuestion(qid: number, questionId: number, data: QuestionData) {
  const res = await client.put(`/questionnaires/${qid}/questions/${questionId}`, data);
  return res.data;
}

export async function deleteQuestion(qid: number, questionId: number) {
  const res = await client.delete(`/questionnaires/${qid}/questions/${questionId}`);
  return res.data;
}

export async function addContradiction(qid: number, data: ContradictionGroupData) {
  const res = await client.post(`/questionnaires/${qid}/contradictions`, data);
  return res.data;
}

export async function deleteContradiction(qid: number, cgId: number) {
  const res = await client.delete(`/questionnaires/${qid}/contradictions/${cgId}`);
  return res.data;
}

export async function sortQuestions(qid: number, questionIds: number[]) {
  const res = await client.put(`/questionnaires/${qid}/questions/sort`, { question_ids: questionIds });
  return res.data;
}

// ---------------------------------------------------------------------------
// 问卷导入导出
// ---------------------------------------------------------------------------

export interface ImportError {
  row: number;
  field: string;
  message: string;
}

export interface ImportResult {
  success: boolean;
  questionnaire_id?: number;
  title?: string;
  question_count?: number;
  status?: string;
  message?: string;
  errors?: ImportError[];
  total_errors?: number;
}

/** 下载问卷导入模板 (学校端) */
export async function downloadQuestionnaireTemplate() {
  const res = await client.get('/questionnaires/import-template', { responseType: 'blob' });
  _triggerDownload(res.data, 'questionnaire_template.xlsx');
}

/** 导入问卷 (学校端) */
export async function importQuestionnaire(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await client.post('/questionnaires/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data.data;
  } catch (error: any) {
    const detail = error.response?.data;
    if (detail?.data) {
      return { success: false, ...detail.data, message: detail.message };
    }
    return { success: false, errors: [{ row: 0, field: '文件', message: detail?.detail || '导入失败' }], total_errors: 1 };
  }
}

/** 导出单个问卷 (学校端) */
export async function exportQuestionnaire(id: number, title?: string) {
  const res = await client.get(`/questionnaires/${id}/export`, { responseType: 'blob' });
  const safeName = (title || 'questionnaire').replace(/[\\/*?:"<>|]/g, '').replace(/ /g, '_').slice(0, 80);
  _triggerDownload(res.data, `${safeName}.xlsx`);
}

/** 下载问卷导入模板 (平台端) */
export async function downloadPlatformTemplate() {
  const res = await client.get('/platform/questionnaires/import-template', { responseType: 'blob' });
  _triggerDownload(res.data, 'questionnaire_template.xlsx');
}

/** 导入问卷 (平台端) */
export async function importPlatformQuestionnaire(file: File): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await client.post('/platform/questionnaires/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data.data;
  } catch (error: any) {
    const detail = error.response?.data;
    if (detail?.data) {
      return { success: false, ...detail.data, message: detail.message };
    }
    return { success: false, errors: [{ row: 0, field: '文件', message: detail?.detail || '导入失败' }], total_errors: 1 };
  }
}

/** 导出单个问卷 (平台端) */
export async function exportPlatformQuestionnaire(id: number, title?: string) {
  const res = await client.get(`/platform/questionnaires/${id}/export`, { responseType: 'blob' });
  const safeName = (title || 'questionnaire').replace(/[\\/*?:"<>|]/g, '').replace(/ /g, '_').slice(0, 80);
  _triggerDownload(res.data, `${safeName}.xlsx`);
}

/** 批量导出问卷 (平台端) */
export async function batchExportQuestionnaires(ids: number[]) {
  const res = await client.post('/platform/questionnaires/batch-export', { questionnaire_ids: ids }, { responseType: 'blob' });
  _triggerDownload(res.data, 'questionnaires_export.zip');
}

function _triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
