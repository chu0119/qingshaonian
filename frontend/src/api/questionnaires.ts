import client from './client';

export interface QuestionnaireInfo {
  id: number;
  school_id: number | null;
  title: string;
  description: string;
  category: string;
  applicable_grades: string;
  is_builtin: boolean;
  status: string;
  created_by: number | null;
  question_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface QuestionData {
  id?: number;
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

export async function getQuestionnaire(id: number): Promise<QuestionnaireDetail> {
  const res = await client.get(`/questionnaires/${id}`);
  return res.data.data;
}

export async function createQuestionnaire(data: Record<string, unknown>) {
  const res = await client.post('/questionnaires', data);
  return res.data;
}

export async function updateQuestionnaire(id: number, data: Record<string, unknown>) {
  const res = await client.put(`/questionnaires/${id}`, data);
  return res.data;
}

export async function deleteQuestionnaire(id: number) {
  const res = await client.delete(`/questionnaires/${id}`);
  return res.data;
}

export async function copyQuestionnaire(id: number) {
  const res = await client.post(`/questionnaires/${id}/copy`);
  return res.data;
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
