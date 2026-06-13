/**
 * 全新科幻主题 — 深空蓝 + 荧光青 + 紫色点缀
 *
 * 设计原则：
 * 60% 深空背景  #030816 ~ #0a1628
 * 25% 蓝/青辅助  #00d4ff ~ #0066ff ~ #7c3aed
 * 10% 功能色（绿/红/橙/金）
 * 5%  光效高亮
 */
export const theme = {
  bg: '#030816',
  bgDeep: '#060e24',
  cardBg: 'rgba(6, 14, 40, 0.92)',
  cardBgSolid: '#081832',
  border: 'rgba(0, 140, 255, 0.15)',
  borderHover: 'rgba(0, 180, 255, 0.35)',
  cyan: '#00d4ff',
  blue: '#0066ff',
  purple: '#7c3aed',
  gold: '#ffd93d',
  green: '#00ffa3',
  red: '#ff4757',
  orange: '#ff9f43',
  text: '#e0eaff',
  textDim: '#5a7aa0',
  numberFont: "'DIN Alternate', 'Inter', 'Orbitron', 'Segoe UI', monospace",
  radius: 8,
  kpiFontSize: 'clamp(24px, 2vw, 40px)',
  kpiLabelSize: 'clamp(11px, 0.75vw, 13px)',
  cardTitleSize: 'clamp(13px, 0.85vw, 16px)',
  stripNumSize: 26,
  gaugeDetailSize: 30,
};

export const COLORS = {
  low: '#00d4ff',
  medium: '#ff9f43',
  high: '#ff4757',
  urgent: '#cc0033',
  normal: '#00ffa3',
  questionable: '#ffd93d',
  mild_anomaly: '#ffd93d',
  moderate_anomaly: '#ff9f43',
  severe_anomaly: '#ff4757',
};

export const riskLabels: Record<string, string> = {
  low: '关注', medium: '预警', high: '警告', urgent: '危急',
};
export const statusLabels: Record<string, string> = {
  pending: '待处理', in_progress: '处理中', follow_up: '持续跟进', completed: '已完成', closed: '已关闭',
};
export const qualityLabels: Record<string, string> = {
  normal: '正常', questionable: '存疑', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '高度异常',
};

export function fmtNumber(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + '万';
  return n.toLocaleString();
}

export function truncate(s: string, max: number): string {
  if (!s || s.length <= max) return s || '';
  return s.slice(0, max) + '…';
}
