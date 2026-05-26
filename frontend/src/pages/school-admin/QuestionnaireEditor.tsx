import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Form, Input, Select, Button, Space, message, Divider, Modal, Switch, InputNumber, Popconfirm, Alert, Descriptions, Tag, Collapse } from 'antd';
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined, SaveOutlined, CopyOutlined } from '@ant-design/icons';
import {
  getQuestionnaire, createQuestionnaire, updateQuestionnaire, copyQuestionnaire,
  addQuestion, updateQuestion, deleteQuestion,
  addContradiction, deleteContradiction,
  type QuestionData, type OptionData, type ContradictionGroupData, type QuestionnaireDetail,
} from '../../api/questionnaires';

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
const dimensionLabels: Record<string, string> = { emotion: '情绪状态', sleep: '睡眠状态', academic_pressure: '学习压力', interpersonal: '人际关系', family_support: '家庭支持', campus_safety: '校园安全', internet_use: '网络使用', self_safety: '自我安全风险' };
const riskTagOptions = [
  { value: '', label: '不设置' }, ...dimensionOptions.map(d => ({ value: d.value, label: d.label + '关注信号' })),
  { value: 'bullying', label: '校园欺凌关注信号' },
];
const relationTypeLabels: Record<string, string> = { opposite: '相反关系', positive_correlated: '正相关', mutually_exclusive: '互斥关系' };
const categories = [
  { value: 'mental_health', label: '心理健康筛查' }, { value: 'bullying', label: '校园欺凌排查' },
  { value: 'internet_addiction', label: '网络沉迷评估' }, { value: 'family_relationship', label: '家庭关系调查' },
  { value: 'safety_awareness', label: '安全意识测评' }, { value: 'interpersonal', label: '人际关系测评' },
  { value: 'academic_pressure', label: '学业压力测评' }, { value: 'custom', label: '综合' },
];
const gradeOptions = [
  { value: '初一', label: '初一' }, { value: '初二', label: '初二' }, { value: '初三', label: '初三' },
  { value: '高一', label: '高一' }, { value: '高二', label: '高二' }, { value: '高三', label: '高三' },
];

const emptyOption = (): OptionData => ({ content: '', score: 0, sort_order: 0, is_risk_option: false });
const emptyQuestion = (): QuestionData => ({
  title: '', type: 'single_choice', required: true, sort_order: 0,
  is_reverse: false, is_attention_check: false,
  options: [emptyOption(), emptyOption()],
});

function JsonEditor({ value, onChange, placeholder }: { value: Record<string, unknown>; onChange: (v: Record<string, unknown>) => void; placeholder?: string }) {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  const [error, setError] = useState('');
  useEffect(() => { setText(JSON.stringify(value, null, 2)); }, [value]);
  return (
    <div>
      <Input.TextArea value={text} rows={6} placeholder={placeholder} onChange={e => {
        setText(e.target.value);
        try { const parsed = JSON.parse(e.target.value); setError(''); onChange(parsed); }
        catch { setError('JSON 格式不正确'); }
      }} />
      {error && <div style={{ color: '#ff4d4f', fontSize: 12, marginTop: 4 }}>{error}</div>}
    </div>
  );
}

export default function QuestionnaireEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const isNew = id === 'new';
  const qid = isNew ? null : Number(id);

  const rolePrefix = location.pathname.startsWith('/teacher') ? '/teacher' : '/school-admin';

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState<QuestionnaireDetail | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('custom');
  const [applicableGrades, setApplicableGrades] = useState<string[]>([]);
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
  const [scoringRule, setScoringRule] = useState<Record<string, unknown>>({});
  const [riskRules, setRiskRules] = useState<Record<string, unknown>>({});

  const isBuiltin = Boolean(detail?.is_builtin);

  useEffect(() => {
    if (!isNew && qid) {
      setLoading(true);
      getQuestionnaire(qid).then(d => {
        setDetail(d);
        setTitle(d.title); setDescription(d.description); setCategory(d.category); setStatus(d.status);
        setQuestions(d.questions || []); setContradictions(d.contradiction_groups || []);
        setDimensions(d.dimensions || []);
        setScoringRule(d.scoring_rule || {});
        setRiskRules(d.risk_rules || {});
        setApplicableGrades(d.applicable_grades ? d.applicable_grades.split(',').filter(Boolean) : []);
      }).finally(() => setLoading(false));
    }
  }, [qid, isNew]);

  const handleCopyBuiltin = async () => {
    if (!qid) return;
    const res = await copyQuestionnaire(qid);
    message.success('已复制为可编辑副本');
    navigate(`${rolePrefix}/questionnaires/${res.data.id}/edit`);
  };

  const handleSaveBase = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        title: title || '未命名问卷', description, category,
        applicable_grades: applicableGrades.join(','),
        dimensions, scoring_rule: scoringRule, risk_rules: riskRules,
      };
      if (isNew) {
        const res = await createQuestionnaire(payload);
        message.success('问卷创建成功，请继续添加题目');
        navigate(`${rolePrefix}/questionnaires/${res.data.id}/edit`, { replace: true });
      } else {
        await updateQuestionnaire(qid!, { ...payload, status });
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

  const moveQuestion = (idx: number, dir: -1 | 1) => {
    const newQuestions = [...questions];
    const target = idx + dir;
    if (target < 0 || target >= newQuestions.length) return;
    [newQuestions[idx], newQuestions[target]] = [newQuestions[target], newQuestions[idx]];
    setQuestions(newQuestions);
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
  const sourceTypeLabel = detail?.source_type === 'standard_like' ? '参考标准结构' : detail?.source_type === 'reference_screening' ? '参考性筛查' : '本校自建';

  // 维度编辑辅助
  const addDimension = () => setDimensions([...dimensions, { code: '', title: '' }]);
  const removeDimension = (idx: number) => setDimensions(dimensions.filter((_, i) => i !== idx));
  const updateDimension = (idx: number, field: 'code' | 'title', value: string) => {
    const newDims = [...dimensions];
    newDims[idx] = { ...newDims[idx], [field]: value };
    setDimensions(newDims);
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <Card loading={loading} title={isNew ? '新建问卷' : isBuiltin ? '内置问卷预览' : '编辑问卷'}
        extra={<Space>
          {!isBuiltin && <Button icon={<SaveOutlined />} onClick={handleSaveBase} loading={saving}>保存基本信息</Button>}
          {!isNew && isBuiltin && <Button icon={<CopyOutlined />} type="primary" onClick={handleCopyBuiltin}>复制为副本</Button>}
          {!isNew && !isBuiltin && <Button onClick={() => setStatus(s => s === 'active' ? 'inactive' : 'active')}>{status === 'active' ? '切换为停用' : '切换为启用'}</Button>}
        </Space>}
      >
        {isBuiltin && detail ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert message={detail.disclaimer || '本问卷仅用于学校教育管理和学生关怀场景下的风险关注筛查，结果不作为医学诊断依据。'} type="info" showIcon />
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="问卷名称">{detail.title}</Descriptions.Item>
              <Descriptions.Item label="版本">V{detail.version}</Descriptions.Item>
              <Descriptions.Item label="分类">{categories.find(item => item.value === detail.category)?.label || detail.category}</Descriptions.Item>
              <Descriptions.Item label="来源类型">{sourceTypeLabel}</Descriptions.Item>
              <Descriptions.Item label="适用年级" span={2}>{detail.applicable_grades || '-'}</Descriptions.Item>
              <Descriptions.Item label="题目数量">{detail.question_count}</Descriptions.Item>
              <Descriptions.Item label="状态">{status === 'active' ? '启用' : status}</Descriptions.Item>
              <Descriptions.Item label="问卷说明" span={2}>{detail.description || '暂无说明'}</Descriptions.Item>
              <Descriptions.Item label="维度定义" span={2}>
                <Space wrap>
                  {detail.dimensions?.length ? detail.dimensions.map(item => <Tag key={item.code}>{item.title}</Tag>) : '暂无'}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="评分规则" span={2}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.scoring_rule || {}, null, 2)}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="风险规则" span={2}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.risk_rules || {}, null, 2)}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="质量规则" span={2}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.quality_rules || {}, null, 2)}</pre>
              </Descriptions.Item>
            </Descriptions>
          </Space>
        ) : (
          <Form layout="vertical">
            <Form.Item label="问卷标题" required><Input value={title} onChange={e => setTitle(e.target.value)} placeholder="请输入问卷标题" /></Form.Item>
            <Form.Item label="问卷说明"><Input.TextArea value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="学生填写前的指导语" /></Form.Item>
            <Form.Item label="问卷分类"><Select value={category} onChange={setCategory} options={categories} /></Form.Item>
            <Form.Item label="适用年级"><Select mode="multiple" value={applicableGrades} onChange={setApplicableGrades} options={gradeOptions} placeholder="选择适用年级（可选）" /></Form.Item>

            <Collapse ghost style={{ marginBottom: 16 }}>
              <Collapse.Panel header="维度定义" key="dimensions">
                {dimensions.map((dim, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                    <Input value={dim.code} onChange={e => updateDimension(idx, 'code', e.target.value)} placeholder="维度编码 (如 emotion)" style={{ width: 160 }} />
                    <Input value={dim.title} onChange={e => updateDimension(idx, 'title', e.target.value)} placeholder="维度名称 (如 情绪状态)" style={{ flex: 1 }} />
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeDimension(idx)} />
                  </div>
                ))}
                <Button type="dashed" onClick={addDimension} block icon={<PlusOutlined />}>添加维度</Button>
              </Collapse.Panel>
              <Collapse.Panel header="评分规则 (JSON)" key="scoring">
                <JsonEditor value={scoringRule} onChange={setScoringRule} placeholder='{"method":"sum","score_types":["single_choice","scale"],"exclude_attention_check":true}' />
              </Collapse.Panel>
              <Collapse.Panel header="风险规则 (JSON)" key="risk">
                <JsonEditor value={riskRules} onChange={setRiskRules} placeholder='{"total_pct_ranges":[{"min":0,"max":29.99,"level":"low"},{"min":30,"max":49.99,"level":"medium"},{"min":50,"max":69.99,"level":"high"},{"min":70,"max":100,"level":"urgent"}]}' />
              </Collapse.Panel>
            </Collapse>
          </Form>
        )}
      </Card>

      {!isNew && (
        <Card title={`题目列表 (${questions.length} 题)`} style={{ marginTop: 16 }}
          extra={!isBuiltin ? <Button type="primary" icon={<PlusOutlined />} onClick={openAddQuestion}>添加题目</Button> : null}
        >
          {questions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无题目，点击上方按钮添加</div>
          ) : (
            <div>
              {questions.map((q, idx) => (
                <Card key={q.id || idx} size="small" style={{ marginBottom: 8 }}
                  title={<span>{idx + 1}. {q.title?.substring(0, 60)}{q.is_attention_check ? <span style={{ color: '#FA8C16', marginLeft: 8 }}>[注意力检测]</span> : ''}{q.code ? <span style={{ color: '#999', marginLeft: 8 }}>({q.code})</span> : null}</span>}
                  extra={!isBuiltin ? (
                    <Space>
                      <Button size="small" icon={<ArrowUpOutlined />} disabled={idx === 0} onClick={() => moveQuestion(idx, -1)} />
                      <Button size="small" icon={<ArrowDownOutlined />} disabled={idx === questions.length - 1} onClick={() => moveQuestion(idx, 1)} />
                      <Button size="small" onClick={() => openEditQuestion(q, idx)}>编辑</Button>
                      <Popconfirm title="确定删除？" onConfirm={() => handleDeleteQuestion(q.id!, idx)}>
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </Space>
                  ) : null}
                >
                  <span style={{ color: '#888', fontSize: 13 }}>{questionTypes.find(t => t.value === q.type)?.label}</span>
                  {q.dimension && <span style={{ color: '#4A90D9', fontSize: 13, marginLeft: 12 }}>维度: {dimensionLabels[q.dimension] || q.dimension}</span>}
                  {q.risk_tag && <span style={{ color: '#FA8C16', fontSize: 13, marginLeft: 12 }}>风险标签: {q.risk_tag}</span>}
                  {q.is_reverse && <span style={{ color: '#722ED1', fontSize: 13, marginLeft: 12 }}>反向计分</span>}
                  {q.options.length > 0 && <span style={{ color: '#888', fontSize: 13, marginLeft: 12 }}>选项: {q.options.map(o => `${o.content}(${o.score}分)`).join(', ')}</span>}
                </Card>
              ))}
            </div>
          )}
        </Card>
      )}

      {!isNew && (
        <Card title={`矛盾题组 (${contradictions.length} 组)`} style={{ marginTop: 16 }}
          extra={!isBuiltin ? <Button icon={<PlusOutlined />} onClick={() => { cgForm.resetFields(); setCgModalOpen(true); }}>添加矛盾题组</Button> : null}
        >
          {contradictions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>暂未设置矛盾题组</div>
          ) : (
            contradictions.map((cg, idx) => {
              const qa = questions.find(q => q.id === cg.question_a_id);
              const qb = questions.find(q => q.id === cg.question_b_id);
              return (
                <div key={cg.id || idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <span>题目A: {qa?.title?.substring(0, 30) || cg.question_a_id} ↔ 题目B: {qb?.title?.substring(0, 30) || cg.question_b_id} ({relationTypeLabels[cg.relation_type] || cg.relation_type})</span>
                  {!isBuiltin ? (
                    <Popconfirm title="确定删除？" onConfirm={() => handleDeleteCg(cg.id!, idx)}>
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
      <Modal title={editingIndex !== null ? '编辑题目' : '添加题目'} open={questionModalOpen && !isBuiltin} onOk={saveQuestion} onCancel={() => setQuestionModalOpen(false)} width={720} destroyOnHidden>
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
            </Space>
            {editingQuestion.is_attention_check && (
              <Form.Item label="注意力检测正确答案" required><Input value={editingQuestion.attention_correct_answer} onChange={e => setEditingQuestion({ ...editingQuestion, attention_correct_answer: e.target.value })} placeholder="请输入正确答案内容" /></Form.Item>
            )}

            {needsOptionsType(editingQuestion.type) && (
              <div>
                <Divider>选项配置</Divider>
                {editingQuestion.options.map((opt, oi) => (
                  <div key={oi} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
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
      <Modal title="添加矛盾题组" open={cgModalOpen && !isBuiltin} onOk={saveContradiction} onCancel={() => setCgModalOpen(false)}>
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
    </div>
  );
}
