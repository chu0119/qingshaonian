/** 身份证号脱敏：前3位****后4位 */
export function maskIdCard(id: string | undefined | null): string {
  if (!id || id.length < 8) return id || '-';
  return id.slice(0, 3) + '****' + id.slice(-4);
}

/** 英文风险标签 → 中文兜底映射 */
const RISK_TAG_FALLBACK: Record<string, string> = {
  antisocial: '反社会倾向信号',
  self_safety: '自我安全关注信号',
  family_support: '家庭支持缺失信号',
  digital_risk: '网络风险行为信号',
};

/** risk_type 可能是逗号分隔的复合值，逐项翻译 */
export function translateRiskType(
  value: string | undefined | null,
  labels: Record<string, string>,
): string {
  if (!value) return '-';
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => labels[s] || RISK_TAG_FALLBACK[s] || s)
    .join(' / ');
}
