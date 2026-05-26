export const ROLES = {
  SCHOOL_ADMIN: 'school_admin',
  TEACHER: 'teacher',
  COUNSELOR: 'counselor',
  STUDENT: 'student',
  PLATFORM_ADMIN: 'platform_admin',
} as const;

export const RISK_LEVELS = {
  low: { label: '低风险', color: '#1890FF' },
  medium: { label: '中风险', color: '#FA8C16' },
  high: { label: '高风险', color: '#FF4D4F' },
  urgent: { label: '紧急风险', color: '#CF1322' },
} as const;
