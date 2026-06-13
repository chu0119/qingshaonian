/**
 * 大屏主题 - 现代深色风格
 */
export const screenTheme = {
  // 背景
  bg: '#0a0e27',
  bgCard: 'rgba(15, 23, 60, 0.7)',
  bgCardHover: 'rgba(20, 30, 80, 0.8)',
  bgGradient: 'linear-gradient(135deg, #0a0e27 0%, #1a1f4e 50%, #0d1235 100%)',

  // 边框
  border: 'rgba(64, 158, 255, 0.15)',
  borderLight: 'rgba(64, 158, 255, 0.3)',
  borderGlow: 'rgba(64, 158, 255, 0.5)',

  // 文字
  text: '#e8f4ff',
  textSecondary: '#8ba3c7',
  textMuted: '#5a7394',
  textHighlight: '#ffffff',

  // 主色
  primary: '#409eff',
  primaryLight: '#66b1ff',
  primaryDark: '#337ecc',

  // 功能色
  success: '#67c23a',
  warning: '#e6a23c',
  danger: '#f56c6c',
  info: '#909399',

  // 数据色板
  chartColors: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#1abc9c', '#e74c3c', '#3498db'],

  // 风险等级色
  riskColors: {
    low: '#67c23a',
    medium: '#e6a23c',
    high: '#f56c6c',
    urgent: '#ff4757',
  },

  // 质量等级色
  qualityColors: {
    normal: '#67c23a',
    questionable: '#e6a23c',
    mild_anomaly: '#e6a23c',
    moderate_anomaly: '#f56c6c',
    severe_anomaly: '#ff4757',
  },

  // 字体
  fontFamily: "'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif",
  fontMono: "'JetBrains Mono', 'Fira Code', monospace",
};

export const riskLabels: Record<string, string> = {
  low: '关注',
  medium: '预警',
  high: '警告',
  urgent: '危急',
};

export const qualityLabels: Record<string, string> = {
  normal: '正常',
  questionable: '存疑',
  mild_anomaly: '轻度异常',
  moderate_anomaly: '中度异常',
  severe_anomaly: '高度异常',
};
