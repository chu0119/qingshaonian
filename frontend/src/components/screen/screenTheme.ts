export const theme = {
  bg: '#060d1a',
  cardBg: 'rgba(6,22,48,0.85)',
  border: 'rgba(0,180,240,0.15)',
  borderHover: 'rgba(0,180,240,0.25)',
  cyan: '#00b8f0',
  blue: '#4d9fff',
  gold: '#e8b339',
  green: '#3dd68c',
  red: '#e5484d',
  orange: '#f08c3c',
  purple: '#9b8cf7',
  text: '#d0dcf0',
  textDim: '#7084a0',
  numberFont: "'Inter','DIN Alternate','Segoe UI',sans-serif",
  radius: 8,
  /* font size tokens for data screens */
  kpiFontSize: 'clamp(22px, 1.8vw, 36px)',
  kpiLabelSize: 'clamp(11px, 0.8vw, 14px)',
  cardTitleSize: 'clamp(13px, 0.85vw, 16px)',
  stripNumSize: 24,
  gaugeDetailSize: 28,
};

export const COLORS = {
  low: '#4d9fff',
  medium: '#f08c3c',
  high: '#e5484d',
  urgent: '#b71c1c',
  normal: '#3dd68c',
  questionable: '#e8b339',
};

export const riskLabels: Record<string, string> = { low: '关注', medium: '预警', high: '警告', urgent: '危急' };
export const statusLabels: Record<string, string> = { pending: '待处理', in_progress: '处理中', follow_up: '持续跟进', completed: '已完成', closed: '已关闭' };
export const qualityLabels: Record<string, string> = { normal: '正常', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '高度异常' };

export function fmtNumber(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + '万';
  return n.toLocaleString();
}

export function truncate(s: string, max: number): string {
  if (!s || s.length <= max) return s || '';
  return s.slice(0, max) + '…';
}
