export const ROLES = {
  SCHOOL_ADMIN: 'school_admin',
  TEACHER: 'teacher',
  COUNSELOR: 'counselor',
  STUDENT: 'student',
  PLATFORM_ADMIN: 'platform_admin',
} as const;

export const RISK_LEVELS = {
  low: { label: '关注', color: '#1890FF' },
  medium: { label: '预警', color: '#FA8C16' },
  high: { label: '警告', color: '#FF4D4F' },
  urgent: { label: '危急', color: '#CF1322' },
} as const;

export const RISK_LABELS: Record<string, string> = {
  low: '关注', medium: '预警',
  high: '警告', urgent: '危急',
};
export const RISK_COLORS: Record<string, string> = {
  low: '#1890FF', medium: '#FA8C16', high: '#FF4D4F', urgent: '#CF1322',
};

export const INTERVENTION_STATUS_LABELS: Record<string, string> = {
  pending: '待处理', viewed: '已查看', in_progress: '处理中', processing: '处理中',
  follow_up: '持续跟进', ongoing: '持续跟进', completed: '已完成', closed: '已关闭',
};

export const INTERVENTION_STATUS_COLORS: Record<string, string> = {
  pending: '#FA8C16', viewed: '#1890FF', in_progress: '#1890FF', processing: '#1890FF',
  follow_up: '#722ED1', ongoing: '#722ED1', completed: '#52C41A', closed: '#8C8C8C',
};

export const METHOD_LABELS: Record<string, string> = {
  student_talk: '学生谈话', teacher_communication: '班主任沟通',
  counselor_guidance: '心理老师辅导', counselor_counsel: '心理老师辅导',
  family_school: '家校沟通', parent_communication: '家校沟通',
  home_visit: '家访', referral: '转介专业机构', observation: '持续观察', other: '其他',
};

export const ROLE_LABELS: Record<string, string> = {
  school_admin: '学校管理员', teacher: '教师', counselor: '心理老师',
  platform_admin: '平台管理员', student: '学生',
};

export const DIMENSION_LABELS: Record<string, string> = {
  emotion: '情绪状态', sleep: '睡眠状态', academic_pressure: '学习压力',
  interpersonal: '人际关系', family_support: '家庭支持', campus_safety: '校园安全',
  internet_use: '网络使用', self_safety: '自我安全', general: '综合',
  self_trait: '自我认知与心理特质', family: '家庭环境与亲子关系',
  school_life: '校园生活与学习状态', digital: '数字环境与网络行为',
  social_rule: '社会规则与行为规范', social_support: '社会支持与求助意识',
  antisocial: '反社会倾向', digital_risk: '网络风险行为',
};

export const TASK_STATUS_LABELS: Record<string, string> = {
  not_started: '未开始', draft: '草稿', in_progress: '进行中', active: '进行中',
  completed: '已完成', expired: '已结束', ended: '已结束', closed: '已关闭',
  archived: '已归档', published: '已发布',
};

export const RESULT_LABELS: Record<string, string> = {
  success: '成功', failure: '失败', partial_success: '部分成功', not_configured: '未配置',
};

export const QUESTIONNAIRE_CATEGORY_LABELS: Record<string, string> = {
  custom: '综合筛查', mental_health: '心理健康', bullying: '校园欺凌',
  internet_addiction: '网络使用', academic_pressure: '学业压力', interpersonal: '人际关系',
  family_relationship: '家庭关系', safety_awareness: '安全意识', sleep: '睡眠质量',
  family: '家庭教养', jindun_behavior: '行为筛查', jindun_family: '家庭评估',
  self_esteem: '自我认知', resilience: '心理韧性', loneliness: '社交感受',
  social_support: '社会支持', depression: '情绪状态', strengths_difficulties: '成长发展',
  life_events: '生活事件', emotion_regulation: '情绪调节', life_satisfaction: '生活满意度',
  self_efficacy: '自我效能', academic_burnout: '学习状态', test_anxiety: '考试焦虑',
};

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  reference_screening: '参考性筛查', standard_like: '参考标准结构',
  school_custom: '学校自建', builtin: '内置问卷',
};

export const SMS_TYPE_LABELS: Record<string, string> = {
  task_publish: '任务发布', platform_urge: '平台催办', risk_alert: '风险预警',
  password_reset: '密码重置', verification_login: '登录验证',
  verification_forgot: '忘记密码', reminder: '提醒',
};

export const SMS_STATUS_LABELS: Record<string, string> = {
  sent: '已发送', failed: '发送失败', not_configured: '未配置', pending: '发送中',
};

export const ANALYSIS_TYPE_LABELS: Record<string, string> = {
  overall_report: '区域综合报告', student_risk: '学生风险分析',
  class_report: '班级报告', quality_report: '质量分析报告',
  regional: '区域分析',
};

export const TRIGGER_METHOD_LABELS: Record<string, string> = {
  total_score: '总分规则', dimension: '维度规则', manual: '手动创建', system: '系统自动',
};

export const QUESTIONNAIRE_STATUS_LABELS: Record<string, string> = {
  draft: '草稿', active: '启用', published: '已发布', archived: '已归档',
  disabled: '已停用', inactive: '已停用',
};

export const QUALITY_LABELS: Record<string, string> = {
  normal: '正常', questionable: '存疑', mild_anomaly: '轻度异常',
  moderate_anomaly: '中度异常', severe_anomaly: '严重异常',
};

export const VALIDITY_LABELS: Record<string, string> = {
  valid: '有效', basically_valid: '基本有效', questionable: '存疑',
  not_recommended: '不建议纳入统计',
};

export const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: '单选', multiple_choice: '多选', multi_choice: '多选',
  scale: '量表', true_false: '判断', fill_blank: '填空', short_answer: '简答',
  open_ended: '开放题',
};

export const RISK_STATUS_LABELS: Record<string, string> = {
  pending: '待处理', viewed: '已查看', assigned: '已分配', processing: '处理中',
  in_progress: '处理中', resolved: '已解决', completed: '已完成', closed: '已关闭',
};

export const TEACHER_TYPE_LABELS: Record<string, string> = {
  head_teacher: '班主任', counselor: '心理老师', grade_director: '年级主任',
  moral_edu: '德育老师', normal: '普通教师',
};
