import client from './client';

export interface AiConfig {
  api_url: string;
  api_key: string;
  model_name: string;
  configured: boolean;
}

export interface AiAnalysisResult {
  analysis: string;
  model: string;
  configured: boolean;
}

export async function getAiConfig(): Promise<AiConfig> {
  const res = await client.get('/ai/config');
  return res.data.data;
}

export async function updateAiConfig(data: {
  api_url?: string;
  api_key?: string;
  model_name?: string;
}) {
  const res = await client.put('/ai/config', data);
  return res.data;
}

export async function analyzeData(
  type: 'student_risk' | 'class_report' | 'overall_report' | 'quality_report',
  data: Record<string, any>,
): Promise<AiAnalysisResult> {
  const res = await client.post('/ai/analyze', { type, data });
  return res.data.data;
}
