import { RISK_TAG_LABELS } from './constants';

/** 身份证号脱敏：前3位****后4位 */
export function maskIdCard(id: string | undefined | null): string {
  if (!id || id.length < 8) return id || '-';
  return id.slice(0, 3) + '****' + id.slice(-4);
}

/** risk_type 可能是逗号分隔的复合值，逐项翻译为中文 */
export function translateRiskType(
  value: string | undefined | null,
  _labels?: Record<string, string>,
): string {
  if (!value) return '-';
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => RISK_TAG_LABELS[s] || s)  // 英文 key → 中文；已是中文则原样返回
    .join(' / ');
}
