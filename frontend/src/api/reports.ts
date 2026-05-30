import client from './client';

// ===== 学校综合报表 =====

export interface ClassOverview {
  class_name: string;
  student_count: number;
  completed_count: number;
  completion_rate: number;
}

export interface GradeOverview {
  grade_name: string;
  student_count: number;
  completed_count: number;
  completion_rate: number;
  classes: ClassOverview[];
}

export interface SchoolOverviewData {
  grades: GradeOverview[];
  total_students: number;
  total_completed: number;
  overall_completion_rate: number;
  school_name?: string;
}

export async function getSchoolOverview() {
  const res = await client.get('/reports/school-overview');
  return res.data.data as SchoolOverviewData;
}

// ===== 风险预警报表 =====

export interface RiskLevelItem {
  level: string;
  label: string;
  count: number;
  percentage: number;
}

export interface RiskStatusItem {
  status: string;
  label: string;
  count: number;
  percentage: number;
}

export interface RiskSummaryData {
  total: number;
  by_level: RiskLevelItem[];
  by_status: RiskStatusItem[];
}

export async function getRiskSummary() {
  const res = await client.get('/reports/risk-summary');
  return res.data.data as RiskSummaryData;
}

// ===== 答题质量报表 =====

export interface QualityLevelItem {
  level: string;
  count: number;
}

export interface QualityStatsData {
  total: number;
  by_level: QualityLevelItem[];
  suggest_retest_count: number;
  effective_rate: number;
}

export async function getQualityStats() {
  const res = await client.get('/quality/statistics/school');
  return res.data.data as QualityStatsData;
}

// ===== 学生纵向追踪 =====

export interface LongitudinalRecord {
  answer_sheet_id: number;
  task_id: number;
  questionnaire_title: string;
  submitted_at: string | null;
  total_score: number | null;
  dimension_scores: Record<string, number>;
  risk_level: string | null;
}

export interface LongitudinalData {
  student_id: number;
  student_name: string;
  records: LongitudinalRecord[];
}

export async function getStudentLongitudinal(studentId: number) {
  const res = await client.get(`/reports/student-longitudinal/${studentId}`);
  return res.data.data as LongitudinalData;
}

// ===== 群体报告 =====

export interface GroupSummaryData {
  group_name: string;
  student_count: number;
  completed_count: number;
  avg_total_score: number;
  dimension_avg: Record<string, number>;
  risk_distribution: Record<string, number>;
  completion_rate: number;
}

export async function getGroupSummary(scope: string, scopeId?: number) {
  const params: Record<string, unknown> = { scope };
  if (scopeId) params.scope_id = scopeId;
  const res = await client.get('/reports/group-summary', { params });
  return res.data.data as GroupSummaryData;
}
