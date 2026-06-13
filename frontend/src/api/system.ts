import client from './client';

export interface SchoolInfo {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
}

export interface RiskLevelItem {
  level: string;
  label: string;
  min: number;
  max: number;
  color: string;
}

export interface RiskConfigData {
  risk_levels: RiskLevelItem[];
  fast_answer_threshold: number;
  consecutive_same_threshold: number;
}

export interface GradeItem {
  id: number;
  name: string;
  sort_order: number;
}

export async function getSchoolInfo() {
  const res = await client.get('/system/school-info');
  return res.data.data as SchoolInfo | null;
}

export async function updateSchoolInfo(data: { name?: string; address?: string; phone?: string }) {
  const res = await client.put('/system/school-info', data);
  return res.data.data as SchoolInfo;
}

export async function getRiskConfig() {
  const res = await client.get('/system/risk-config');
  return res.data.data as RiskConfigData;
}

export async function updateRiskConfig(data: Record<string, unknown>) {
  const res = await client.put('/system/risk-config', data);
  return res.data;
}

export async function getAdminGrades() {
  const res = await client.get('/system/grades');
  return res.data.data as GradeItem[];
}

export async function addGrade(data: { name: string; sort_order?: number }) {
  const res = await client.post('/system/grades', data);
  return res.data;
}

export async function deleteGrade(id: number) {
  const res = await client.delete(`/system/grades/${id}`);
  return res.data;
}

export async function seedDemoData() {
  const res = await client.post('/system/seed-data');
  return res.data;
}

// ===== 短信配置 =====

export interface SmsConfig {
  sms_enabled: string;
  sms_provider: string;
  sms_api_url: string;
  sms_app_key: string;
  sms_app_key_masked?: string;
  sms_app_secret: string;
  sms_app_secret_masked?: string;
  sms_sign_name: string;
  sms_sdk_app_id: string;
  sms_templates: string;
}

export async function getSmsConfig() {
  const res = await client.get('/system/sms-config');
  return res.data.data as SmsConfig;
}

export async function updateSmsConfig(data: Partial<SmsConfig>) {
  const res = await client.put('/system/sms-config', data);
  return res.data;
}

// ===== 数据大屏设置 =====

export interface ScreenConfig {
  screen_title: string;
  screen_subtitle: string;
}

export async function getScreenConfig() {
  const res = await client.get('/system/screen-config');
  return res.data.data as ScreenConfig;
}

export async function updateScreenConfig(data: {
  screen_title?: string;
  screen_subtitle?: string;
}) {
  const res = await client.put('/system/screen-config', data);
  return res.data;
}
