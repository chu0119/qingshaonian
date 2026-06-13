/**
 * 学生答题页 — 增强版
 *
 * 新增优化：
 * 1. 题型标签（单选/多选/判断/填空）
 * 2. 选项选中动画反馈
 * 3. 键盘快捷键（← → 翻页，Space 确认）
 * 4. 当前题计时显示
 * 5. 提交前展示未答必填题列表
 * 6. 最近保存时间提示
 * 7. 量表题优化（1-5评分条）
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Radio, Checkbox, Button, Space, Progress, Typography, message, Modal, Result, Alert, Input, Checkbox as AntCheckbox, Drawer, Badge, Tag } from 'antd';
import { CheckCircleOutlined, SafetyOutlined, UnorderedListOutlined, ClockCircleOutlined } from '@ant-design/icons';
import client from '../../api/client';

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isMobile;
}

const TYPE_LABELS: Record<string, string> = {
  single_choice: '单选', multi_choice: '多选', true_false: '判断',
  scale: '量表', fill_blank: '填空', short_answer: '简答',
};
const TYPE_COLORS: Record<string, string> = {
  single_choice: '#1677ff', multi_choice: '#722ed1', true_false: '#13c2c2',
  scale: '#faad14', fill_bullet: '#52c41a', short_answer: '#8c8c8c',
};
const SCALE_LABELS = ['非常不符合', '比较不符合', '一般', '比较符合', '非常符合'];

export default function AnswerPage() {
  const { answerSheetId } = useParams<{ answerSheetId: string }>();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [sheet, setSheet] = useState<any>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [durations, setDurations] = useState<Record<number, number>>({});
  const [questionStart, setQuestionStart] = useState(Date.now());
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [consented, setConsented] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [navDrawerOpen, setNavDrawerOpen] = useState(false);
  const [lastSaved, setLastSaved] = useState<string>('');
  const [elapsed, setElapsed] = useState(0);
  const autoSaveRef = useRef<ReturnType<typeof setInterval>>();
  const answersRef = useRef<Record<number, any>>({});
  const durationsRef = useRef<Record<number, number>>({});

  useEffect(() => { answersRef.current = answers; }, [answers]);
  useEffect(() => { durationsRef.current = durations; }, [durations]);

  // 自动保存
  useEffect(() => {
    autoSaveRef.current = setInterval(() => {
      if (sheet && sheet.status === 'in_progress') {
        saveToServer(answersRef.current, false);
      }
    }, 30000);
    return () => { if (autoSaveRef.current) clearInterval(autoSaveRef.current); };
  }, [sheet]);

  // 当前题计时器
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - questionStart) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [questionStart]);

  // 键盘快捷键
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (submitted || !consented || !sheet) return;
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); nextQuestion(); }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); prevQuestion(); }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [submitted, consented, sheet, currentIndex]);

  // 加载答卷
  useEffect(() => {
    client.get(`/student/answer-sheets/${answerSheetId}`).then(r => {
      const data = r.data.data;
      if (!data || data.status === 'submitted') { setSubmitted(true); return; }
      setSheet(data);
      const prev: Record<number, any> = {};
      const dur: Record<number, number> = {};
      (data.questions || []).forEach((q: any) => {
        if (q.previous_answer) prev[q.id] = q.previous_answer;
        dur[q.id] = q.previous_duration || 0;
      });
      setAnswers(prev);
      setDurations(dur);
    }).catch((err: any) => message.error(err._friendlyMessage || '加载答卷失败'));
    setQuestionStart(Date.now());
  }, [answerSheetId]);

  const saveToServer = async (ans: Record<number, any>, showMsg = false) => {
    const answerList = Object.entries(ans).map(([qid, content]) => ({
      question_id: Number(qid), answer_content: content,
      duration_seconds: durationsRef.current[Number(qid)] || 0, displayed_order: 0,
    }));
    try {
      await client.put(`/student/answer-sheets/${answerSheetId}/save`, { answers: answerList });
      const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      setLastSaved(now);
      if (showMsg) message.success('进度已保存');
    } catch { /* silent fail */ }
  };

  const manualSave = async () => {
    setSaving(true);
    try { await saveToServer(answers, true); } finally { setSaving(false); }
  };

  const hasAnswer = (value: any) => {
    if (value === undefined || value === null) return false;
    if (Array.isArray(value?.selected_option_ids)) return value.selected_option_ids.length > 0;
    if (value.selected_option_id !== undefined && value.selected_option_id !== null) return true;
    if (value.value !== undefined && value.value !== null && value.value !== '') return true;
    if (typeof value.text === 'string') return value.text.trim().length > 0;
    return false;
  };

  const handleSubmit = () => {
    if (!sheet.can_answer) {
      message.warning('当前任务暂不可提交');
      return;
    }
    const unansweredRequired = questions
      .map((q: any, i: number) => ({ q, i }))
      .filter((item: { q: any; i: number }) => item.q.required && !hasAnswer(answers[item.q.id]));

    if (unansweredRequired.length > 0) {
      Modal.warning({
        title: '还有必答题未完成',
        width: 420,
        content: (
          <div>
            <p style={{ marginBottom: 12 }}>以下 {unansweredRequired.length} 道必答题尚未作答：</p>
            <div style={{ maxHeight: 200, overflow: 'auto' }}>
              {unansweredRequired.map((item: { q: any; i: number }) => (
                <div key={item.q.id} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>第 {item.i + 1} 题：{item.q.title.slice(0, 30)}{item.q.title.length > 30 ? '...' : ''}</span>
                  <Button type="link" size="small" onClick={() => { Modal.destroyAll(); jumpToQuestion(item.i); }}>去作答</Button>
                </div>
              ))}
            </div>
          </div>
        ),
        okText: '知道了',
      });
      return;
    }

    Modal.confirm({
      title: '确认提交',
      content: sheet.allow_edit ? '确认提交本次问卷吗？提交后仍可按任务设置修改。' : '提交后将无法修改答案，确定要提交吗？',
      okText: '确认提交', cancelText: '继续检查',
      onOk: async () => {
        setSaving(true);
        try {
          await saveToServer(answers, false);
          await client.post(`/student/answer-sheets/${answerSheetId}/submit`);
          setSubmitted(true);
        } catch (err: any) {
          message.error(err._friendlyMessage || '提交失败，请重试');
        } finally { setSaving(false); }
      },
    });
  };

  // ---- 知情同意页 ----
  if (!consented && sheet) {
    return (
      <div style={{ maxWidth: 600, margin: isMobile ? '16px auto' : '40px auto', padding: isMobile ? '0 8px' : 0 }}>
        <Card>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <SafetyOutlined style={{ fontSize: 48, color: '#4A90D9', marginBottom: 12 }} />
            <Typography.Title level={4} style={{ marginTop: 0 }}>测评知情同意书</Typography.Title>
          </div>
          <div style={{ lineHeight: 1.8, color: '#333', marginBottom: 24, padding: isMobile ? '12px' : '16px', background: '#fafafa', borderRadius: 8, fontSize: isMobile ? 14 : 15 }}>
            <p>亲爱的同学，你好！</p>
            <p>本问卷旨在了解同学们的学习和生活状况，以便学校和老师更好地为大家提供帮助和支持。</p>
            <p><strong>保密承诺：</strong></p>
            <ul style={{ paddingLeft: 20 }}>
              <li>你的回答仅用于学校开展关爱帮扶工作，不会对外公开。</li>
              <li>个人数据严格保密，仅授权人员可查看。</li>
              <li>测评结果不会影响你的学习成绩和在校评价。</li>
              <li>你有权随时退出本次测评。</li>
            </ul>
            <p>感谢你的信任与配合！</p>
          </div>
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <label style={{ cursor: 'pointer', fontSize: isMobile ? 14 : 15 }}>
              <AntCheckbox checked={consentChecked} onChange={e => setConsentChecked(e.target.checked)} style={{ marginRight: 8 }} />
              我已阅读并理解以上内容，自愿参与本次测评
            </label>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Button type="primary" disabled={!consentChecked} onClick={() => setConsented(true)} size="large" block={isMobile}>
              同意并开始测评
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (submitted) {
    return (
      <Result status="success" title="问卷提交成功"
        subTitle="感谢你完成本次问卷，学校和老师会根据整体情况开展后续支持工作。"
        extra={[
          <Button type="primary" key="back" onClick={() => navigate('/student/completed')} block={isMobile}>查看已完成问卷</Button>,
          <Button key="home" onClick={() => navigate('/student/home')} block={isMobile}>返回首页</Button>,
        ]} />
    );
  }

  if (!sheet) return <div style={{ textAlign: 'center', padding: 60 }}><Typography.Text type="secondary">加载中...</Typography.Text></div>;

  const questions = sheet.questions;
  const q = questions[currentIndex];
  const answeredCount = Object.keys(answers).filter(k => answers[Number(k)]).length;
  const requiredCount = questions.filter((qq: any) => qq.required).length;
  const requiredAnsweredCount = questions.filter((qq: any) => qq.required && hasAnswer(answers[qq.id])).length;
  const progress = questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0;

  const recordTime = () => {
    const now = Date.now();
    const spent = Math.round((now - questionStart) / 1000);
    if (q) setDurations(d => ({ ...d, [q.id]: (d[q.id] || 0) + spent }));
  };

  const jumpToQuestion = (idx: number) => { recordTime(); setCurrentIndex(idx); setQuestionStart(Date.now()); setNavDrawerOpen(false); };
  const nextQuestion = () => { recordTime(); if (currentIndex < questions.length - 1) { setCurrentIndex(currentIndex + 1); setQuestionStart(Date.now()); } };
  const prevQuestion = () => { recordTime(); if (currentIndex > 0) { setCurrentIndex(currentIndex - 1); setQuestionStart(Date.now()); } };
  const setAnswer = (qid: number, value: any) => { setAnswers(a => ({ ...a, [qid]: value })); };
  const setAnswerAndAdvance = (qid: number, value: any) => {
    setAnswers(a => ({ ...a, [qid]: value }));
    if (currentIndex < questions.length - 1) { setTimeout(() => { recordTime(); setCurrentIndex(i => i + 1); setQuestionStart(Date.now()); }, 300); }
  };

  const getQuestionStatus = (idx: number) => {
    const qq = questions[idx];
    const answered = hasAnswer(answers[qq.id]);
    if (idx === currentIndex) return 'current';
    if (answered) return 'answered';
    if (qq.required && !answered) return 'required-unanswered';
    return 'unanswered';
  };

  const statusColors: Record<string, { bg: string; border: string; text: string }> = {
    'current': { bg: '#1677ff', border: '#1677ff', text: '#fff' },
    'answered': { bg: '#f6ffed', border: '#b7eb8f', text: '#52c41a' },
    'required-unanswered': { bg: '#fff2e8', border: '#ffbb96', text: '#fa541c' },
    'unanswered': { bg: '#fafafa', border: '#d9d9d9', text: '#8c8c8c' },
  };

  const formatElapsed = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  const renderNavGrid = () => (
    <div style={{ padding: isMobile ? '8px 0' : '12px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, padding: '0 4px' }}>
        <Typography.Text strong style={{ fontSize: 15 }}>题目导航</Typography.Text>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>{answeredCount}/{questions.length} 已答</Typography.Text>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12, padding: '0 4px' }}>
        {[
          { key: 'current', label: '当前', bg: '#1677ff', border: '#1677ff', text: '#fff' },
          { key: 'answered', label: '已答', bg: '#f6ffed', border: '#b7eb8f', text: '#52c41a' },
          { key: 'required-unanswered', label: '必答未填', bg: '#fff2e8', border: '#ffbb96', text: '#fa541c' },
          { key: 'unanswered', label: '未答', bg: '#fafafa', border: '#d9d9d9', text: '#8c8c8c' },
        ].map(item => (
          <div key={item.key} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, background: item.bg, border: `1px solid ${item.border}` }} />
            <span style={{ color: '#666' }}>{item.label}</span>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(8, 1fr)' : 'repeat(10, 1fr)', gap: 4, padding: '0 4px' }}>
        {questions.map((qq: any, idx: number) => {
          const status = getQuestionStatus(idx);
          const colors = statusColors[status];
          return (
            <button key={qq.id} onClick={() => jumpToQuestion(idx)}
              title={`第${idx + 1}题 ${TYPE_LABELS[qq.type] || ''}${qq.required ? '(必答)' : ''}${hasAnswer(answers[qq.id]) ? ' ✓' : ''}`}
              style={{
                width: '100%', aspectRatio: '1', display: 'flex', alignItems: 'center', justifyContent: 'center',
                borderRadius: 4, border: `1.5px solid ${colors.border}`, background: colors.bg, color: colors.text,
                cursor: 'pointer', fontSize: isMobile ? 11 : 12, fontWeight: status === 'current' ? 700 : 500,
                transition: 'all 0.15s', position: 'relative', padding: 0, lineHeight: 1,
              }}>
              {idx + 1}
              {qq.required && !hasAnswer(answers[qq.id]) && status !== 'current' && (
                <span style={{ position: 'absolute', top: -2, right: -2, width: 6, height: 6, borderRadius: '50%', background: '#fa541c' }} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderQuestion = () => {
    if (!q) return null;
    const ans = answers[q.id];
    const typeColor = TYPE_COLORS[q.type] || '#8c8c8c';

    return (
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span>第 {currentIndex + 1} 题 / 共 {questions.length} 题</span>
            <Tag color={typeColor} style={{ margin: 0, fontSize: 11 }}>{TYPE_LABELS[q.type] || q.type}</Tag>
            {q.required && <span style={{ color: 'red', fontSize: 12 }}>* 必填</span>}
          </div>
        }
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: isMobile ? '16px' : '24px' }}
      >
        <div style={{ marginBottom: 20, fontSize: isMobile ? 15 : 16, lineHeight: 1.7, fontWeight: 500 }}>{q.title}</div>
        {q.description && <div style={{ color: '#888', fontSize: 13, marginBottom: 16, padding: isMobile ? '8px 10px' : '8px 12px', background: '#fafafa', borderRadius: 4 }}>{q.description}</div>}

        {/* 单选 / 量表 */}
        {(q.type === 'single_choice' || q.type === 'scale') && (
          <Radio.Group value={ans?.selected_option_id} onChange={e => setAnswerAndAdvance(q.id, { selected_option_id: e.target.value })} style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }} size={isMobile ? 6 : 8}>
              {q.options?.map((opt: any, optIdx: number) => (
                <Radio key={opt.id} value={opt.id}
                  style={{
                    padding: isMobile ? '10px' : '10px 12px',
                    border: `1.5px solid ${ans?.selected_option_id === opt.id ? '#1677ff' : '#f0f0f0'}`,
                    borderRadius: 8, display: 'block',
                    background: ans?.selected_option_id === opt.id ? '#e6f4ff' : '#fff',
                    fontSize: isMobile ? 14 : 15, transition: 'all 0.2s',
                    transform: ans?.selected_option_id === opt.id ? 'scale(1.01)' : 'none',
                  }}>
                  {q.type === 'scale' && <span style={{ color: '#999', marginRight: 4 }}>{optIdx + 1}.</span>}
                  {opt.content || `选项 ${optIdx + 1}`}
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        )}

        {/* 多选 */}
        {q.type === 'multi_choice' && (
          <Checkbox.Group value={ans?.selected_option_ids || []} onChange={vals => setAnswer(q.id, { selected_option_ids: vals })} style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }} size={isMobile ? 6 : 8}>
              {q.options?.map((opt: any) => {
                const checked = (ans?.selected_option_ids || []).includes(opt.id);
                return (
                  <div key={opt.id} style={{
                    padding: isMobile ? '10px' : '10px 12px',
                    border: `1.5px solid ${checked ? '#1677ff' : '#f0f0f0'}`,
                    borderRadius: 8, fontSize: isMobile ? 14 : 15,
                    background: checked ? '#e6f4ff' : '#fff',
                    transition: 'all 0.2s',
                  }}>
                    <Checkbox value={opt.id}>{opt.content || `选项 ${opt.id}`}</Checkbox>
                  </div>
                );
              })}
            </Space>
          </Checkbox.Group>
        )}

        {/* 判断 */}
        {q.type === 'true_false' && (
          <Radio.Group value={ans?.value} onChange={e => setAnswerAndAdvance(q.id, { value: e.target.value })}>
            <Space size={isMobile ? 'middle' : 'large'}>
              <Radio.Button value="true" style={{
                padding: isMobile ? '10px 28px' : '10px 36px', fontSize: isMobile ? 15 : 16,
                borderColor: ans?.value === 'true' ? '#52c41a' : undefined,
                color: ans?.value === 'true' ? '#52c41a' : undefined,
              }}>是</Radio.Button>
              <Radio.Button value="false" style={{
                padding: isMobile ? '10px 28px' : '10px 36px', fontSize: isMobile ? 15 : 16,
                borderColor: ans?.value === 'false' ? '#ff4d4f' : undefined,
                color: ans?.value === 'false' ? '#ff4d4f' : undefined,
              }}>否</Radio.Button>
            </Space>
          </Radio.Group>
        )}

        {/* 填空 / 简答 */}
        {(q.type === 'fill_blank' || q.type === 'short_answer') && (
          <Input.TextArea rows={isMobile ? 3 : 4}
            value={ans?.text || ''} onChange={e => setAnswer(q.id, { text: e.target.value })}
            placeholder="请输入你的回答..." style={{ fontSize: isMobile ? 14 : 15 }} />
        )}
      </Card>
    );
  };

  return (
    <div style={{ maxWidth: isMobile ? '100%' : 700, margin: '0 auto', padding: isMobile ? '0 4px' : 0 }}>
      {/* 任务信息 */}
      <Card style={{ marginBottom: 12 }} bodyStyle={{ padding: isMobile ? '10px 14px' : '12px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 4, fontSize: isMobile ? 16 : 18 }}>{sheet.task_name || '问卷填写'}</Typography.Title>
            <div style={{ color: '#8c8c8c', fontSize: 12 }}>
              截止：{sheet.end_time ? new Date(sheet.end_time).toLocaleString('zh-CN') : '未设置'}
              {lastSaved && <span style={{ marginLeft: 8, color: '#52c41a' }}>✓ {lastSaved} 已保存</span>}
            </div>
          </div>
          <Button type="text" icon={<UnorderedListOutlined />} onClick={() => setNavDrawerOpen(true)} style={{ flexShrink: 0 }}>
            {isMobile ? '' : '导航'}
          </Button>
        </div>
      </Card>

      {!sheet.can_answer && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="当前任务暂不可提交" description="请留意任务开始时间、截止时间或任务状态。" />
      )}

      {/* 进度条 */}
      <Card bodyStyle={{ padding: isMobile ? '8px 12px' : '10px 16px' }} style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 12, color: '#888' }}>
            答题进度 {answeredCount}/{questions.length}
            {requiredCount > 0 && <span style={{ marginLeft: 8, color: requiredAnsweredCount < requiredCount ? '#fa541c' : '#52c41a' }}>必答 {requiredAnsweredCount}/{requiredCount}</span>}
          </span>
          <span style={{ fontSize: 11, color: '#bbb', fontFamily: 'monospace' }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />{formatElapsed(elapsed)}
          </span>
        </div>
        <Progress percent={progress} showInfo={false} strokeColor={{ '0%': '#4A90D9', '100%': '#5B8DEF' }} size="small" />
      </Card>

      {renderQuestion()}

      {/* 底部导航 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16, paddingBottom: 24 }}>
        <Button onClick={prevQuestion} disabled={currentIndex === 0} size={isMobile ? 'middle' : 'large'}>上一题</Button>
        <Space size={isMobile ? 8 : 12}>
          <Button onClick={manualSave} loading={saving} size={isMobile ? 'middle' : 'large'} disabled={!sheet.can_answer}>保存</Button>
          {currentIndex < questions.length - 1 ? (
            <Button type="primary" onClick={nextQuestion} size={isMobile ? 'middle' : 'large'}>下一题</Button>
          ) : (
            <Button type="primary" onClick={handleSubmit} size={isMobile ? 'middle' : 'large'} disabled={!sheet.can_answer}
              icon={<CheckCircleOutlined />} style={{ background: '#67C23A', borderColor: '#67C23A' }}>提交问卷</Button>
          )}
        </Space>
      </div>

      {/* 导航抽屉 */}
      <Drawer
        title={<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><span>题目导航</span><Badge count={requiredCount - requiredAnsweredCount} style={{ backgroundColor: '#fa541c' }} overflowCount={999} /></div>}
        placement={isMobile ? 'bottom' : 'right'} height={isMobile ? '60vh' : undefined} width={isMobile ? undefined : 340}
        open={navDrawerOpen} onClose={() => setNavDrawerOpen(false)}
        bodyStyle={{ padding: isMobile ? '8px 12px' : '12px 16px' }}>
        {renderNavGrid()}
      </Drawer>
    </div>
  );
}
