import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Form, Input, Select, Button, Space, message, Divider, Modal, Switch, InputNumber, Popconfirm, Alert, Descriptions, Tag, Collapse, Radio, Checkbox } from 'antd';
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined, SaveOutlined, CopyOutlined, EyeOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import {
  getQuestionnaire, createQuestionnaire, updateQuestionnaire, copyQuestionnaire,
  addQuestion, updateQuestion, deleteQuestion,
  addContradiction, deleteContradiction, sortQuestions,
  type QuestionData, type OptionData, type ContradictionGroupData, type QuestionnaireDetail,
} from '../../api/questionnaires';
import { getDictGrades } from '../../api/users';
import { QUESTIONNAIRE_STATUS_LABELS, QUESTIONNAIRE_CATEGORY_LABELS, DIMENSION_LABELS, SOURCE_TYPE_LABELS, RISK_LABELS, RISK_COLORS } from '../../utils/constants';

const questionTypes = [
  { value: 'single_choice', label: '单选题' }, { value: 'multi_choice', label: '多选题' },
  { value: 'true_false', label: '判断题' }, { value: 'scale', label: '量表题' },
  { value: 'fill_blank', label: '填空题' }, { value: 'short_answer', label: '简答题' },
];
const dimensionOptions = [
  { value: 'emotion', label: '情绪状态' }, { value: 'sleep', label: '睡眠状态' },
  { value: 'academic_pressure', label: '学习压力' }, { value: 'interpersonal', label: '人际关系' },
  { value: 'family_support', label: '家庭支持' }, { value: 'campus_safety', label: '校园安全' },
  { value: 'internet_use', label: '网络使用' }, { value: 'self_safety', label: '自我安全风险' },
];
const dimensionLabels = DIMENSION_LABELS;
const riskTagOptions = [
  { value: '', label: '不设置' }, ...dimensionOptions.map(d => ({ value: d.value, label: d.label + '关注信号' })),
  { value: 'bullying', label: '校园欺凌关注信号' },
];
const relationTypeLabels: Record<string, string> = { opposite: '相反关系', positive_correlated: '正相关', mutually_exclusive: '互斥关系' };
const categories = Object.entries(QUESTIONNAIRE_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }));

const emptyOption = (): OptionData => ({ content: '', score: 0, sort_order: 0, is_risk_option: false });
const emptyQuestion = (): QuestionData => ({
  title: '', type: 'single_choice', required: true, sort_order: 0,
  is_reverse: false, is_attention_check: false,
  options: [emptyOption(), emptyOption()],
});

// --- 规则解析辅助 ---
interface ScoringForm { method: string; score_types: string[]; exclude_attention_check: boolean; }
interface RiskRange { min: number; max: number; level: string; }
interface QualityForm { all_negative_detection: boolean; too_fast_detection: boolean; fast_min_seconds: number; attention_check: boolean; contradiction_check: boolean; pattern_check: boolean; consecutive_same: boolean; consecutive_max: number; same_option_ratio: boolean; same_option_max: number; }

const parseScoringRule = (v: Record<string, unknown>): ScoringForm => {
  try { return { method: (v.method as string) || 'sum', score_types: (v.score_types as string[]) || ['single_choice', 'scale'], exclude_attention_check: v.exclude_attention_check !== false }; }
  catch { return { method: 'sum', score_types: ['single_choice', 'scale'], exclude_attention_check: true }; }
};
const buildScoringRule = (f: ScoringForm) => ({ method: f.method, score_types: f.score_types, exclude_attention_check: f.exclude_attention_check });

const parseRiskRules = (v: Record<string, unknown>): RiskRange[] => {
  try {
    if (v.total_pct_ranges) return (v.total_pct_ranges as RiskRange[]);
    if (v.dimension_pct_ranges) return (v.dimension_pct_ranges as RiskRange[]);
    return [];
  } catch { return []; }
};
const buildRiskRules = (ranges: RiskRange[]) => ({ total_pct_ranges: ranges });

const parseQualityRules = (v: Record<string, unknown>): QualityForm => ({
  all_negative_detection: (v.all_negative_detection as any)?.enabled !== false,
  too_fast_detection: (v.too_fast_detection as any)?.enabled !== false,
  fast_min_seconds: (v.too_fast_detection as any)?.min_seconds ?? 3,
  attention_check: (v.attention_check as any)?.enabled !== false,
  contradiction_check: (v.contradiction_check as any)?.enabled !== false,
  pattern_check: (v.pattern_detection as any)?.enabled !== false,
  consecutive_same: (v.consecutive_same_detection as any)?.enabled !== false,
  consecutive_max: (v.consecutive_same_detection as any)?.max_count ?? 8,
  same_option_ratio: (v.same_option_ratio_detection as any)?.enabled !== false,
  same_option_max: (v.same_option_ratio_detection as any)?.max_ratio ?? 80,
});
const buildQualityRules = (f: QualityForm) => ({
  all_negative_detection: { enabled: f.all_negative_detection },
  too_fast_detection: { enabled: f.too_fast_detection, min_seconds: f.fast_min_seconds },
  attention_check: { enabled: f.attention_check },
  contradiction_check: { enabled: f.contradiction_check },
  pattern_detection: { enabled: f.pattern_check },
  consecutive_same_detection: { enabled: f.consecutive_same, max_count: f.consecutive_max },
  same_option_ratio_detection: { enabled: f.same_option_ratio, max_ratio: f.same_option_max },
});

const methodLabels: Record<string, string> = { sum: '各题得分求和', average: '各题得分取平均', weighted: '加权计分' };
const scoreTypeLabels: Record<string, string> = { single_choice: '单选题', multi_choice: '多选题', true_false: '判断题', scale: '量表题', fill_blank: '填空题', short_answer: '简答题' };
const defaultRiskRanges: RiskRange[] = [
  { min: 0, max: 29.99, level: 'low' },
  { min: 30, max: 49.99, level: 'medium' },
  { min: 50, max: 69.99, level: 'high' },
  { min: 70, max: 100, level: 'urgent' },
];

export default function QuestionnaireEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const isNew = id === 'new';
  const qid = isNew ? null : Number(id);

  const rolePrefix = location.pathname.startsWith('/platform') ? '/platform' : location.pathname.startsWith('/teacher') ? '/teacher' : '/school-admin';

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<QuestionnaireDetail | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('custom');
  const [applicableGrades, setApplicableGrades] = useState<string[]>([]);
  const [gradeOptions, setGradeOptions] = useState<{ value: string; label: string }[]>([]);
  const [status, setStatus] = useState('draft');
  const [questions, setQuestions] = useState<QuestionData[]>([]);
  const [contradictions, setContradictions] = useState<ContradictionGroupData[]>([]);
  const [editingQuestion, setEditingQuestion] = useState<QuestionData | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [questionModalOpen, setQuestionModalOpen] = useState(false);
  const [cgModalOpen, setCgModalOpen] = useState(false);
  const [cgForm] = Form.useForm();

  // 维度 & 规则
  const [dimensions, setDimensions] = useState<Array<{ code: string; title: string }>>([]);
  const [scoringForm, setScoringForm] = useState<ScoringForm>({ method: 'sum', score_types: ['single_choice', 'scale'], exclude_attention_check: true });
  const [riskRanges, setRiskRanges] = useState<RiskRange[]>(defaultRiskRanges);
  const [qualityForm, setQualityForm] = useState<QualityForm>({ all_negative_detection: true, too_fast_detection: true, fast_min_seconds: 3, attention_check: true, contradiction_check: true, pattern_check: true, consecutive_same: true, consecutive_max: 8, same_option_ratio: true, same_option_max: 80 });
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewIdx, setPreviewIdx] = useState(0);

  const isBuiltin = Boolean(detail?.is_builtin);

  useEffect(() => {
    getDictGrades()
      .then(items => setGradeOptions(items.map(g => ({ value: g.label, label: g.label }))))
      .catch(() => setGradeOptions([]));
  }, []);

  useEffect(() => {
    if (!isNew && qid) {
      setLoading(true);
      const apiPrefix = rolePrefix === '/platform' ? rolePrefix : undefined;
      getQuestionnaire(qid, apiPrefix).then(d => {
        setDetail(d);
        setTitle(d.title); setDescription(d.description); setCategory(d.category); setStatus(d.status);
        setQuestions(d.questions || []); setContradictions(d.contradiction_groups || []);
        setDimensions(d.dimensions || []);
        setScoringForm(parseScoringRule(d.scoring_rule || {}));
        setRiskRanges(parseRiskRules(d.risk_rules || {}).length ? parseRiskRules(d.risk_rules || {}) : defaultRiskRanges);
        setQualityForm(parseQualityRules(d.quality_rules || {}));
        setApplicableGrades(d.applicable_grades ? d.applicable_grades.split(',').filter(Boolean) : []);
      }).catch(() => message.error('获取问卷详情失败')).finally(() => setLoading(false));
    }
  }, [qid, isNew]);

  const handleCopyBuiltin = async () => {
    if (!qid) return;
    const res = await copyQuestionnaire(qid, rolePrefix === '/platform' ? rolePrefix : undefined);
    message.success('已复制为可编辑副本');
    navigate(`${rolePrefix}/questionnaires/${res.id}/edit`);
  };

  const handleSaveBase = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        title: title || '未命名问卷', description, category,
        applicable_grades: applicableGrades.join(','),
        dimensions: dimensions.map((d, i) => ({ code: d.code || `dim_${i + 1}`, title: d.title })),
        scoring_rule: buildScoringRule(scoringForm),
        risk_rules: buildRiskRules(riskRanges),
        quality_rules: buildQualityRules(qualityForm),
      };
      if (isNew) {
        const res = await createQuestionnaire(payload);
        message.success('问卷创建成功，请继续添加题目');
        navigate(`${rolePrefix}/questionnaires/${res.data.id}/edit`, { replace: true });
      } else {
        await updateQuestionnaire(qid!, { ...payload, status }, rolePrefix === '/platform' ? rolePrefix : undefined);
        message.success('保存成功');
      }
    } finally { setSaving(false); }
  };

  const openAddQuestion = () => { setEditingQuestion(emptyQuestion()); setEditingIndex(null); setQuestionModalOpen(true); };
  const openEditQuestion = (q: QuestionData, idx: number) => { setEditingQuestion({ ...q, options: [...q.options] }); setEditingIndex(idx); setQuestionModalOpen(true); };

  const saveQuestion = async () => {
    if (!editingQuestion) return;
    if (!editingQuestion.title.trim()) { message.warning('请输入题目标题'); return; }
    if (['single_choice', 'multi_choice', 'scale'].includes(editingQuestion.type) && editingQuestion.options.length === 0) {
      message.warning('请至少添加一个选项'); return;
    }
    try {
      if (editingIndex !== null && editingQuestion.id) {
        await updateQuestion(qid!, editingQuestion.id, editingQuestion);
        const newQuestions = [...questions]; newQuestions[editingIndex] = editingQuestion; setQuestions(newQuestions);
      } else {
        const res = await addQuestion(qid!, editingQuestion);
        setQuestions([...questions, { ...editingQuestion, id: res.data.id }]);
      }
      setQuestionModalOpen(false);
    } catch { message.error('保存失败'); }
  };

  const handleDeleteQuestion = async (questionId: number, idx: number) => {
    await deleteQuestion(qid!, questionId);
    setQuestions(questions.filter((_, i) => i !== idx));
  };

  const moveQuestion = async (idx: number, dir: -1 | 1) => {
    const newQuestions = [...questions];
    const target = idx + dir;
    if (target < 0 || target >= newQuestions.length) return;
    [newQuestions[idx], newQuestions[target]] = [newQuestions[target], newQuestions[idx]];
    setQuestions(newQuestions);
    if (qid) {
      try {
        await sortQuestions(qid, newQuestions.filter(q => q.id).map(q => q.id!));
      } catch { message.error('排序保存失败'); }
    }
  };

  const addOption = () => {
    if (!editingQuestion) return;
    setEditingQuestion({ ...editingQuestion, options: [...editingQuestion.options, emptyOption()] });
  };
  const removeOption = (optIdx: number) => {
    if (!editingQuestion || editingQuestion.options.length <= 2) return;
    setEditingQuestion({ ...editingQuestion, options: editingQuestion.options.filter((_, i) => i !== optIdx) });
  };
  const updateOption = (optIdx: number, field: string, value: unknown) => {
    if (!editingQuestion) return;
    const newOpts = [...editingQuestion.options];
    newOpts[optIdx] = { ...newOpts[optIdx], [field]: value };
    setEditingQuestion({ ...editingQuestion, options: newOpts });
  };

  const saveContradiction = async () => {
    const values = await cgForm.validateFields();
    await addContradiction(qid!, values);
    const allQuestions = questions;
    const qa = allQuestions.find(q => q.id === values.question_a_id);
    const qb = allQuestions.find(q => q.id === values.question_b_id);
    setContradictions([...contradictions, { ...values, question_a_title: qa?.title?.substring(0, 30), question_b_title: qb?.title?.substring(0, 30) } as unknown as ContradictionGroupData]);
    setCgModalOpen(false);
    cgForm.resetFields();
  };

  const handleDeleteCg = async (cgId: number, idx: number) => {
    await deleteContradiction(qid!, cgId);
    setContradictions(contradictions.filter((_, i) => i !== idx));
  };

  const needsOptionsType = (type: string) => ['single_choice', 'multi_choice', 'scale'].includes(type);
  const sourceTypeLabel = SOURCE_TYPE_LABELS[detail?.source_type ?? ''] || '本校自建';

  // 维度编辑辅助
  const addDimension = () => setDimensions([...dimensions, { code: '', title: '' }]);
  const removeDimension = (idx: number) => setDimensions(dimensions.filter((_, i) => i !== idx));
  const updateDimension = (idx: number, field: 'code' | 'title', value: string) => {
    const newDims = [...dimensions];
    newDims[idx] = { ...newDims[idx], [field]: value };
    setDimensions(newDims);
  };

  // 风险标签翻译
  const translateRiskTag = (tag: string) => {
    if (!tag) return '';
    return riskTagOptions.find(o => o.value === tag)?.label || tag;
  };

  // --- 规则展示辅助（预览模式）---
  const renderScoringSummary = (rule: Record<string, unknown>) => {
    const f = parseScoringRule(rule);
    return (
      <div>
        <div style={{ marginBottom: 6 }}><strong>评分方式：</strong>{methodLabels[f.method] || f.method}</div>
        <div style={{ marginBottom: 6 }}><strong>计分题型：</strong>{f.score_types.map(t => scoreTypeLabels[t] || t).join('、')}</div>
        <div><strong>排除注意力检测题：</strong>{f.exclude_attention_check ? '是' : '否'}</div>
      </div>
    );
  };

  const renderRiskSummary = (rules: Record<string, unknown>) => {
    const ranges = parseRiskRules(rules);
    if (!ranges.length) return <span style={{ color: '#999' }}>暂未配置</span>;
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {ranges.map((r, i) => (
          <Tag key={i} color={RISK_COLORS[r.level] || '#666'} style={{ margin: 0 }}>
            {RISK_LABELS[r.level] || r.level}：得分占比 {r.min}% ~ {r.max}%
          </Tag>
        ))}
      </div>
    );
  };

  const renderQualitySummary = (rules: Record<string, unknown>) => {
    const f = parseQualityRules(rules);
    const items = [
      { label: '全选相同选项检测', on: f.all_negative_detection },
      { label: '快速作答检测', on: f.too_fast_detection, detail: f.too_fast_detection ? `（少于 ${f.fast_min_seconds} 秒/题）` : '' },
      { label: '注意力检测题', on: f.attention_check },
      { label: '矛盾回答检测', on: f.contradiction_check },
      { label: '规律作答检测', on: f.pattern_check },
    ];
    return (
      <div>
        {items.map((it, i) => (
          <div key={i} style={{ marginBottom: 4 }}>
            {it.on ? <CheckCircleOutlined style={{ color: '#52C41A', marginRight: 6 }} /> : <CloseCircleOutlined style={{ color: '#D9D9D9', marginRight: 6 }} />}
            {it.label}{it.detail && <span style={{ color: '#888' }}>{it.detail}</span>}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <Card loading={loading} title={isNew ? '新建问卷' : isBuiltin ? '内置问卷预览' : '编辑问卷'}
        extra={<Space>
          {!isBuiltin && <Button icon={<SaveOutlined />} onClick={handleSaveBase} loading={saving}>保存基本信息</Button>}
          {!isNew && isBuiltin && <Button icon={<CopyOutlined />} type="primary" onClick={handleCopyBuiltin}>复制为副本</Button>}
          {!isNew && !isBuiltin && <Button onClick={() => setStatus(s => s === 'active' ? 'inactive' : 'active')}>{status === 'active' ? '切换为停用' : '切换为启用'}</Button>}
          {!isNew && questions.length > 0 && <Button icon={<EyeOutlined />} onClick={() => { setPreviewIdx(0); setPreviewOpen(true); }}>预览问卷</Button>}
        </Space>}
      >
        {isBuiltin && detail ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert message={detail.disclaimer || '本问卷仅用于学校教育管理和学生关怀场景下的风险关注筛查，结果不作为医学诊断依据。'} type="info" showIcon />
            <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
              <Descriptions.Item label="问卷名称">{detail.title}</Descriptions.Item>
              <Descriptions.Item label="版本">V{detail.version}</Descriptions.Item>
              <Descriptions.Item label="分类">{categories.find(item => item.value === detail.category)?.label || detail.category}</Descriptions.Item>
              <Descriptions.Item label="来源">{sourceTypeLabel}</Descriptions.Item>
              <Descriptions.Item label="适用年级" span={2}>{detail.applicable_grades || '-'}</Descriptions.Item>
              <Descriptions.Item label="题目数量">{detail.question_count}</Descriptions.Item>
              <Descriptions.Item label="状态">{QUESTIONNAIRE_STATUS_LABELS[status] || status}</Descriptions.Item>
              <Descriptions.Item label="问卷说明" span={2}>{detail.description || '暂无说明'}</Descriptions.Item>
              <Descriptions.Item label="评估维度" span={2}>
                <Space wrap>
                  {detail.dimensions?.length ? detail.dimensions.map(item => <Tag key={item.code} color="blue">{item.title}</Tag>) : '暂无'}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="评分设置" span={2}>{renderScoringSummary(detail.scoring_rule || {})}</Descriptions.Item>
              <Descriptions.Item label="风险等级划分" span={2}>{renderRiskSummary(detail.risk_rules || {})}</Descriptions.Item>
              <Descriptions.Item label="答题质量检测" span={2}>{renderQualitySummary(detail.quality_rules || {})}</Descriptions.Item>
            </Descriptions>
          </Space>
        ) : (
          <Form layout="vertical">
            <Form.Item label="问卷标题" required><Input value={title} onChange={e => setTitle(e.target.value)} placeholder="请输入问卷标题" /></Form.Item>
            <Form.Item label="问卷说明"><Input.TextArea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="学生填写前的指导语" /></Form.Item>
            <Form.Item label="问卷分类"><Select value={category} onChange={setCategory} options={categories} /></Form.Item>
            <Form.Item label="适用年级"><Select mode="multiple" value={applicableGrades} onChange={setApplicableGrades} options={gradeOptions} placeholder={gradeOptions.length ? '选择适用年级（可选）' : '请先在系统设置中配置年级'} disabled={!gradeOptions.length} /></Form.Item>

            <Collapse ghost style={{ marginBottom: 16 }}>
              <Collapse.Panel header="评估维度" key="dimensions">
                {dimensions.map((dim, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                    <Input value={dim.title} onChange={e => updateDimension(idx, 'title', e.target.value)} placeholder="维度名称（如 情绪状态）" style={{ flex: 1 }} />
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeDimension(idx)} />
                  </div>
                ))}
                <Button type="dashed" onClick={addDimension} block icon={<PlusOutlined />}>添加维度</Button>
              </Collapse.Panel>
              <Collapse.Panel header="评分设置" key="scoring">
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>评分方式</div>
                  <Select value={scoringForm.method} onChange={v => setScoringForm({ ...scoringForm, method: v })} style={{ width: 200 }}
                    options={[{ value: 'sum', label: '各题得分求和' }, { value: 'average', label: '各题得分取平均' }]} />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, color: '#666', fontSize: 13 }}>参与计分的题型</div>
                  <Checkbox.Group value={scoringForm.score_types} onChange={v => setScoringForm({ ...scoringForm, score_types: v as string[] })}
                    options={[{ value: 'single_choice', label: '单选题' }, { value: 'multi_choice', label: '多选题' }, { value: 'scale', label: '量表题' }, { value: 'true_false', label: '判断题' }]} />
                </div>
                <div>
                  <Switch checked={scoringForm.exclude_attention_check} onChange={v => setScoringForm({ ...scoringForm, exclude_attention_check: v })} />
                  <span style={{ marginLeft: 8 }}>排除注意力检测题不计入总分</span>
                </div>
              </Collapse.Panel>
              <Collapse.Panel header="风险等级划分" key="risk">
                <div style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>设置不同风险等级对应的得分占比区间</div>
                {riskRanges.map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <Tag color={RISK_COLORS[r.level] || '#666'} style={{ width: 48, textAlign: 'center', margin: 0 }}>{RISK_LABELS[r.level] || r.level}</Tag>
                    <span style={{ color: '#666' }}>得分占比</span>
                    <InputNumber value={r.min} onChange={v => { const rr = [...riskRanges]; rr[i] = { ...rr[i], min: v ?? 0 }; setRiskRanges(rr); }} min={0} max={100} size="small" style={{ width: 70 }} />
                    <span style={{ color: '#666' }}>% ~</span>
                    <InputNumber value={r.max} onChange={v => { const rr = [...riskRanges]; rr[i] = { ...rr[i], max: v ?? 100 }; setRiskRanges(rr); }} min={0} max={100} size="small" style={{ width: 70 }} />
                    <span style={{ color: '#666' }}>%</span>
                    {riskRanges.length > 1 && <Button size="small" danger icon={<DeleteOutlined />} onClick={() => setRiskRanges(riskRanges.filter((_, j) => j !== i))} />}
                  </div>
                ))}
                <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => setRiskRanges([...riskRanges, { min: 0, max: 100, level: 'low' }])}>添加等级</Button>
              </Collapse.Panel>
              <Collapse.Panel header="答题质量检测" key="quality">
                <div style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>开启后，系统会自动检测学生的答题质量，过滤无效问卷</div>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div><Switch checked={qualityForm.all_negative_detection} onChange={v => setQualityForm({ ...qualityForm, all_negative_detection: v })} /><span style={{ marginLeft: 8 }}>全部选同一选项检测</span></div>
                  <div>
                    <Switch checked={qualityForm.too_fast_detection} onChange={v => setQualityForm({ ...qualityForm, too_fast_detection: v })} />
                    <span style={{ marginLeft: 8 }}>快速作答检测</span>
                    {qualityForm.too_fast_detection && <>
                      <span style={{ marginLeft: 8, color: '#888' }}>少于</span>
                      <InputNumber value={qualityForm.fast_min_seconds} onChange={v => setQualityForm({ ...qualityForm, fast_min_seconds: v ?? 3 })} min={1} max={30} size="small" style={{ width: 60, margin: '0 4px' }} />
                      <span style={{ color: '#888' }}>秒/题视为异常</span>
                    </>}
                  </div>
                  <div><Switch checked={qualityForm.attention_check} onChange={v => setQualityForm({ ...qualityForm, attention_check: v })} /><span style={{ marginLeft: 8 }}>注意力检测题验证</span></div>
                  <div><Switch checked={qualityForm.contradiction_check} onChange={v => setQualityForm({ ...qualityForm, contradiction_check: v })} /><span style={{ marginLeft: 8 }}>矛盾回答检测</span></div>
                  <div><Switch checked={qualityForm.pattern_check} onChange={v => setQualityForm({ ...qualityForm, pattern_check: v })} /><span style={{ marginLeft: 8 }}>规律作答检测（如 ABAB 循环）</span></div>
                  <div><Switch checked={qualityForm.consecutive_same} onChange={v => setQualityForm({ ...qualityForm, consecutive_same: v })} /><span style={{ marginLeft: 8 }}>连续同选项检测</span></div>
                  <div><Switch checked={qualityForm.same_option_ratio} onChange={v => setQualityForm({ ...qualityForm, same_option_ratio: v })} /><span style={{ marginLeft: 8 }}>单一选项占比过高检测</span></div>
                </Space>
              </Collapse.Panel>
            </Collapse>
          </Form>
        )}
      </Card>

      {!isNew && (
        <Card title={`问卷题目 (${questions.length} 题)`} style={{ marginTop: 16 }}
          extra={!isBuiltin ? <Button type="primary" icon={<PlusOutlined />} onClick={openAddQuestion}>添加题目</Button> : null}
        >
          {questions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无题目，点击上方按钮添加</div>
          ) : (
            <div>
              {questions.map((q, idx) => (
                <Card key={q.id || idx} size="small" style={{ marginBottom: 8 }}
                  title={<span>{idx + 1}. {q.title?.substring(0, 60)}{q.is_attention_check ? <Tag color="orange" style={{ marginLeft: 8 }}>注意力检测</Tag> : ''}</span>}
                  extra={!isBuiltin ? (
                    <Space>
                      <Button size="small" icon={<ArrowUpOutlined />} disabled={idx === 0} onClick={() => moveQuestion(idx, -1)} />
                      <Button size="small" icon={<ArrowDownOutlined />} disabled={idx === questions.length - 1} onClick={() => moveQuestion(idx, 1)} />
                      <Button size="small" onClick={() => openEditQuestion(q, idx)}>编辑</Button>
                      <Popconfirm title="确定删除？" onConfirm={() => handleDeleteQuestion(q.id!, idx)} okText="确定" cancelText="取消">
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </Space>
                  ) : null}
                >
                  <Space size={12} wrap>
                    <Tag>{questionTypes.find(t => t.value === q.type)?.label || q.type}</Tag>
                    {q.dimension && <Tag color="blue">{dimensionLabels[q.dimension] || q.dimension}</Tag>}
                    {q.risk_tag && <Tag color="orange">{translateRiskTag(q.risk_tag)}</Tag>}
                    {q.is_reverse && <Tag color="purple">反向计分</Tag>}
                  </Space>
                  {q.options.length > 0 && (
                    <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {q.options.map((o, oi) => (
                        <Tag key={oi} color={o.is_risk_option ? 'red' : undefined}>
                          {o.content}（{o.score}分）{o.is_risk_option ? ' ⚠' : ''}
                        </Tag>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </Card>
      )}

      {!isNew && (
        <Card title={`答题逻辑校验 (${contradictions.length} 组)`} style={{ marginTop: 16 }}
          extra={!isBuiltin ? <Button icon={<PlusOutlined />} onClick={() => { cgForm.resetFields(); setCgModalOpen(true); }}>添加校验规则</Button> : null}
        >
          {contradictions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>暂未设置答题逻辑校验</div>
          ) : (
            contradictions.map((cg, idx) => {
              const qa = questions.find(q => q.id === cg.question_a_id);
              const qb = questions.find(q => q.id === cg.question_b_id);
              return (
                <div key={cg.id || idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <span>题目「{qa?.title?.substring(0, 30) || cg.question_a_id}」与「{qb?.title?.substring(0, 30) || cg.question_b_id}」应为{relationTypeLabels[cg.relation_type] || cg.relation_type}</span>
                  {!isBuiltin ? (
                    <Popconfirm title="确定删除？" onConfirm={() => handleDeleteCg(cg.id!, idx)} okText="确定" cancelText="取消">
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  ) : null}
                </div>
              );
            })
          )}
        </Card>
      )}

      {/* 题目编辑Modal */}
      <Modal title={editingIndex !== null ? '编辑题目' : '添加题目'} open={questionModalOpen && !isBuiltin} onOk={saveQuestion} onCancel={() => setQuestionModalOpen(false)} okText="确定" cancelText="取消" width={720} style={{ maxWidth: '95vw' }} destroyOnHidden>
        {editingQuestion && (
          <Form layout="vertical">
            <Form.Item label="题目标题" required><Input.TextArea value={editingQuestion.title} onChange={e => setEditingQuestion({ ...editingQuestion, title: e.target.value })} rows={2} /></Form.Item>
            <Form.Item label="题目说明"><Input value={editingQuestion.description} onChange={e => setEditingQuestion({ ...editingQuestion, description: e.target.value })} /></Form.Item>
            <Space style={{ marginBottom: 16 }} wrap>
              <div><span style={{ fontSize: 12, color: '#666' }}>题型</span><br /><Select value={editingQuestion.type} onChange={v => setEditingQuestion({ ...editingQuestion, type: v })} options={questionTypes} style={{ width: 120 }} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>必填</span><br /><Switch checked={editingQuestion.required} onChange={v => setEditingQuestion({ ...editingQuestion, required: v })} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>维度</span><br /><Select value={editingQuestion.dimension || ''} onChange={v => setEditingQuestion({ ...editingQuestion, dimension: v })} options={[{ value: '', label: '不设置' }, ...dimensionOptions]} style={{ width: 130 }} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>风险标签</span><br /><Select value={editingQuestion.risk_tag || ''} onChange={v => setEditingQuestion({ ...editingQuestion, risk_tag: v })} options={riskTagOptions} style={{ width: 160 }} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>反向计分</span><br /><Switch checked={editingQuestion.is_reverse} onChange={v => setEditingQuestion({ ...editingQuestion, is_reverse: v })} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>注意力检测</span><br /><Switch checked={editingQuestion.is_attention_check} onChange={v => setEditingQuestion({ ...editingQuestion, is_attention_check: v })} /></div>
              <div><span style={{ fontSize: 12, color: '#666' }}>风险阈值</span><br /><InputNumber value={editingQuestion.risk_threshold ?? undefined} onChange={v => setEditingQuestion({ ...editingQuestion, risk_threshold: v ?? null })} placeholder="不设置" style={{ width: 100 }} min={0} /></div>
            </Space>
            {editingQuestion.is_attention_check && (
              <Form.Item label="注意力检测正确答案" required><Input value={editingQuestion.attention_correct_answer} onChange={e => setEditingQuestion({ ...editingQuestion, attention_correct_answer: e.target.value })} placeholder="请输入正确答案内容" /></Form.Item>
            )}

            {needsOptionsType(editingQuestion.type) && (
              <div>
                <Divider>选项配置</Divider>
                {editingQuestion.options.map((opt, oi) => (
                  <div key={oi} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ width: 20 }}>{oi + 1}.</span>
                    <Input value={opt.content} onChange={e => updateOption(oi, 'content', e.target.value)} placeholder="选项内容" style={{ flex: 3 }} />
                    <InputNumber value={opt.score} onChange={v => updateOption(oi, 'score', v || 0)} placeholder="分值" style={{ width: 70 }} min={0} />
                    <Switch checked={opt.is_risk_option} onChange={v => updateOption(oi, 'is_risk_option', v)} style={{ width: 80 }} checkedChildren="风险项" unCheckedChildren="普通" />
                    {editingQuestion.options.length > 2 && <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeOption(oi)} />}
                  </div>
                ))}
                <Button type="dashed" onClick={addOption} block>+ 添加选项</Button>
              </div>
            )}
          </Form>
        )}
      </Modal>

      {/* 矛盾题组Modal */}
      <Modal title="添加答题逻辑校验" open={cgModalOpen && !isBuiltin} onOk={saveContradiction} onCancel={() => setCgModalOpen(false)} okText="确定" cancelText="取消">
        <Form form={cgForm} layout="vertical">
          <Form.Item name="question_a_id" label="题目A" rules={[{ required: true }]}>
            <Select options={questions.map(q => ({ value: q.id, label: `${q.title?.substring(0, 40)}` }))} />
          </Form.Item>
          <Form.Item name="question_b_id" label="题目B" rules={[{ required: true }]}>
            <Select options={questions.map(q => ({ value: q.id, label: `${q.title?.substring(0, 40)}` }))} />
          </Form.Item>
          <Form.Item name="relation_type" label="关系类型" initialValue="opposite">
            <Select options={[{ value: 'opposite', label: '相反关系' }, { value: 'positive_correlated', label: '正相关' }, { value: 'mutually_exclusive', label: '互斥关系' }]} />
          </Form.Item>
          <Form.Item name="max_score_diff" label="允许最大分差" initialValue={3}><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name="description" label="说明"><Input /></Form.Item>
        </Form>
      </Modal>

      {/* 预览Modal */}
      <Modal title={`问卷预览 — ${title || '未命名问卷'}`} open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={640} style={{ maxWidth: '95vw' }}>
        {questions.length > 0 && (() => {
          const q = questions[previewIdx];
          return (
            <div>
              <div style={{ marginBottom: 16, color: '#888', fontSize: 13 }}>
                第 {previewIdx + 1} / {questions.length} 题
                {q.dimension && <Tag style={{ marginLeft: 8 }}>{dimensionLabels[q.dimension] || q.dimension}</Tag>}
              </div>
              <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 16 }}>{previewIdx + 1}. {q.title}</div>
              {q.description && <div style={{ color: '#666', marginBottom: 12, fontSize: 13 }}>{q.description}</div>}
              {q.type === 'single_choice' && q.options.map((opt, oi) => (
                <Radio key={oi} style={{ display: 'block', marginBottom: 8 }} disabled>{opt.content}（{opt.score}分）{opt.is_risk_option && <Tag color="red" style={{ marginLeft: 4 }}>风险</Tag>}</Radio>
              ))}
              {q.type === 'multi_choice' && q.options.map((opt, oi) => (
                <Checkbox key={oi} style={{ display: 'block', marginBottom: 8 }} disabled>{opt.content}（{opt.score}分）{opt.is_risk_option && <Tag color="red" style={{ marginLeft: 4 }}>风险</Tag>}</Checkbox>
              ))}
              {q.type === 'scale' && q.options.map((opt, oi) => (
                <Radio key={oi} style={{ display: 'block', marginBottom: 8 }} disabled>{opt.content}（{opt.score}分）</Radio>
              ))}
              {q.type === 'true_false' && (
                <div><Radio disabled>是</Radio><Radio disabled style={{ marginLeft: 16 }}>否</Radio></div>
              )}
              {(q.type === 'fill_blank' || q.type === 'short_answer') && (
                <Input.TextArea disabled placeholder={q.type === 'fill_blank' ? '填空' : '请输入回答'} rows={q.type === 'short_answer' ? 3 : 1} />
              )}
              <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
                <Button disabled={previewIdx === 0} onClick={() => setPreviewIdx(previewIdx - 1)}>上一题</Button>
                {previewIdx < questions.length - 1 ? (
                  <Button type="primary" onClick={() => setPreviewIdx(previewIdx + 1)}>下一题</Button>
                ) : (
                  <Button type="primary" onClick={() => setPreviewOpen(false)}>完成预览</Button>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
