export const ROLES = {
  SCHOOL_ADMIN: 'school_admin',
  TEACHER: 'teacher',
  COUNSELOR: 'counselor',
  STUDENT: 'student',
  PLATFORM_ADMIN: 'platform_admin',
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
  // 通用维度
  emotion: '情绪状态', sleep: '睡眠状态', academic_pressure: '学习压力',
  interpersonal: '人际关系', family_support: '家庭支持', campus_safety: '校园安全',
  internet_use: '网络使用', self_safety: '自我安全', general: '综合',
  self_trait: '自我认知与心理特质', family: '家庭环境与亲子关系',
  school_life: '校园生活与学习状态', digital: '数字环境与网络行为',
  social_rule: '社会规则与行为规范', social_support: '社会支持与求助意识',
  antisocial: '反社会倾向', digital_risk: '网络风险行为',
  // DASS-21
  stress: '压力', anxiety: '焦虑', depression: '抑郁',
  // CIAS-R 网络成瘾
  compulsive_use: '强迫性使用', withdrawal: '戒断反应', tolerance: '耐受性',
  interpersonal_health: '人际与健康', time_management: '时间管理',
  // 欺凌扩展
  victimization: '受欺凌', aggression: '攻击行为', bystander: '旁观行为',
  cyberbullying: '网络欺凌', help_seeking: '求助行为', safety: '安全感',
  // 家庭教养 EMBU
  rejection: '拒绝', emotional_warmth: '情感温暖', overprotection: '过度保护',
  // 自伤风险
  positive_mindset: '积极心态', sleep_quality: '睡眠质量', masking: '掩饰', self_care: '自我关怀',
  // 金盾行为筛查
  care_need: '关注需求', bad_behavior: '不良行为', serious_bad_behavior: '严重不良行为',
  criminal_indicator: '犯罪倾向指标',
  // 金盾家庭环境
  family_guardianship: '家庭监护', family_environment: '家庭环境', emotional_support: '情感支持',
  // 金盾自我认知
  empathy: '共情能力', egocentrism: '自我中心', manipulation: '操纵倾向',
  // 金盾社会规则
  violent_behavior: '暴力行为', marginal_contact: '边缘接触', rule_disregard: '规则漠视',
  // 金盾家庭成长环境
  communication: '沟通质量', parenting_style: '教养方式', autonomy: '自主性',
  // 金盾生活习惯
  daily_habits: '日常习惯', digital_env: '数字环境', social_law: '社会法律意识',
  // 金盾社会价值观
  rule_cognition: '规则认知', destructive: '破坏性', projection: '投射倾向',
  // 金盾校园支持
  family_guardian: '家庭监护人', learning_future: '学习与未来',
  // SDQ 长处与困难
  emotional_symptoms: '情绪症状', conduct_problems: '品行问题',
  hyperactivity: '多动', peer_problems: '同伴问题', prosocial: '亲社会行为',
  // 生活事件 ASLEC
  academic: '学业', punishment: '惩罚', loss: '丧失', health: '健康',
  // 情绪调节 ERQ
  cognitive_reappraisal: '认知重评', expressive_suppression: '表达抑制',
  // 自尊 RSES
  self_worth: '自我价值', self_acceptance: '自我接纳',
  // 心理韧性 CD-RISC
  toughness: '坚韧', adaptability: '适应性',
  // 孤独感 UCLA
  social_connect: '社交联系', emotional_loneliness: '情感孤独',
  // 社会支持 PSSS
  friend_support: '朋友支持', other_support: '其他支持',
  // 抑郁 CDI
  anhedonia: '快感缺失', negative_mood: '消极情绪',
  low_self_esteem: '低自尊', inefficiency: '无效率感',
  // 生活满意度 SWLS
  life_satisfaction: '生活满意度',
  // 自我效能 GSES
  self_efficacy: '自我效能',
  // 学业倦怠 ASBI
  emotional_exhaustion: '情绪耗竭', learning_disengagement: '学习脱离',
  low_achievement: '低成就感',
  // 考试焦虑 TAS
  worry: '担忧', emotionality: '情绪性', bodily_symptoms: '躯体症状',
  cognitive_interference: '认知干扰',
  learning_pressure: '学习压力',
};

/** 风险标签中文映射（risk_type / risk_tag 英文值 → 中文） */
export const RISK_TAG_LABELS: Record<string, string> = {
  emotion: '情绪关注信号', sleep: '睡眠关注信号',
  academic_pressure: '学业压力关注信号', interpersonal: '人际关系关注信号',
  family_support: '家庭支持关注信号', campus_safety: '校园安全关注信号',
  internet_use: '网络使用关注信号', self_safety: '自我安全关注信号',
  general: '综合关注信号', bullying: '校园欺凌关注信号',
  safety_awareness: '安全意识关注信号', mental_pressure: '心理压力关注信号',
  internet_addiction: '网络使用关注信号', family_relationship: '家庭关系关注信号',
  antisocial: '反社会倾向信号', digital_risk: '网络风险行为信号',
  // 数据库中已存在的中文标签（直接映射，避免显示"未知"）
  '反社会倾向信号': '反社会倾向信号',
  '自我安全关注信号': '自我安全关注信号',
  '家庭支持关注信号': '家庭支持关注信号',
  '家庭支持缺失信号': '家庭支持缺失信号',
  '网络风险行为信号': '网络风险行为信号',
  '家庭环境与亲子关系': '家庭环境与亲子关系',
  '社会支持与求助意识': '社会支持与求助意识',
  '数字环境与网络行为': '数字环境与网络行为',
  '社会规则与行为规范': '社会规则与行为规范',
  '自我认知与心理特质': '自我认知与心理特质',
  '校园生活与学习状态': '校园生活与学习状态',
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
  verification: '验证码', task_publish: '任务发布', task_reminder: '任务提醒',
  unfinished_reminder: '未完成提醒', platform_urge: '平台催办',
  risk_reminder: '风险关注', intervention_followup: '干预跟进',
  password_reset: '密码重置', risk_alert: '风险预警',
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

export const RISK_STATUS_LABELS: Record<string, string> = {
  pending: '待处理', viewed: '已查看', assigned: '已分配', processing: '处理中',
  in_progress: '处理中', resolved: '已解决', completed: '已完成', closed: '已关闭',
};

export const TEACHER_TYPE_LABELS: Record<string, string> = {
  head_teacher: '班主任', counselor: '心理老师', grade_director: '年级主任',
  moral_edu: '德育老师', normal: '普通教师',
};
