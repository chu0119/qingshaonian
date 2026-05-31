import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Radio, Checkbox, Button, Space, Progress, Typography, message, Modal, Result, Alert, Input, Checkbox as AntCheckbox } from 'antd';
import { CheckCircleOutlined, SafetyOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function AnswerPage() {
  const { answerSheetId } = useParams<{ answerSheetId: string }>();
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<any>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [durations, setDurations] = useState<Record<number, number>>({});
  const [questionStart, setQuestionStart] = useState(Date.now());
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [consented, setConsented] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const autoSaveRef = useRef<ReturnType<typeof setInterval>>();
  const answersRef = useRef<Record<number, any>>({});
  const durationsRef = useRef<Record<number, number>>({});

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  useEffect(() => {
    durationsRef.current = durations;
  }, [durations]);

  // 自动保存（每30秒）
  useEffect(() => {
    autoSaveRef.current = setInterval(() => {
      if (sheet && sheet.status === 'in_progress') {
        saveToServer(answersRef.current, false);
      }
    }, 30000);
    return () => { if (autoSaveRef.current) clearInterval(autoSaveRef.current); };
  }, [sheet]);

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
    }).catch(() => message.error('加载答卷失败'));
    setQuestionStart(Date.now());
  }, [answerSheetId]);

  const saveToServer = async (ans: Record<number, any>, showMsg = false) => {
    const answerList = Object.entries(ans).map(([qid, content]) => ({
      question_id: Number(qid), answer_content: content,
      duration_seconds: durationsRef.current[Number(qid)] || 0, displayed_order: 0,
    }));
    try {
      await client.put(`/student/answer-sheets/${answerSheetId}/save`, { answers: answerList });
      if (showMsg) message.success('进度已保存');
    } catch { /* silent fail for auto-save */ }
  };

  const manualSave = async () => {
    setSaving(true);
    try {
      await saveToServer(answers, true);
    } finally {
      setSaving(false);
    }
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
      message.warning('当前任务暂不可提交，请留意任务状态和截止时间');
      return;
    }
    const unansweredRequired = sheet.questions.filter((q: any) => q.required && !hasAnswer(answers[q.id]));
    if (unansweredRequired.length > 0) {
      message.warning(`还有 ${unansweredRequired.length} 道必答题未回答`);
      return;
    }
    Modal.confirm({
      title: '确认提交', content: sheet.allow_edit ? '确认提交本次问卷吗？提交后仍可按任务设置修改。' : '提交后将无法修改答案，确定要提交吗？',
      okText: '确认提交', cancelText: '继续检查',
      onOk: async () => {
        setSaving(true);
        try {
          await saveToServer(answers, false);
          await client.post(`/student/answer-sheets/${answerSheetId}/submit`);
          setSubmitted(true);
        } catch { message.error('提交失败，请重试'); }
        finally { setSaving(false); }
      },
    });
  };

  if (!consented && sheet) {
    return (
      <div style={{ maxWidth: 600, margin: '40px auto' }}>
        <Card>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <SafetyOutlined style={{ fontSize: 48, color: '#4A90D9', marginBottom: 12 }} />
            <Typography.Title level={4} style={{ marginTop: 0 }}>测评知情同意书</Typography.Title>
          </div>
          <div style={{ lineHeight: 1.8, color: '#333', marginBottom: 24, padding: '16px', background: '#fafafa', borderRadius: 8 }}>
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
            <label style={{ cursor: 'pointer' }}>
              <AntCheckbox checked={consentChecked} onChange={e => setConsentChecked(e.target.checked)} style={{ marginRight: 8 }} />
              我已阅读并理解以上内容，自愿参与本次测评
            </label>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Button type="primary" disabled={!consentChecked} onClick={() => setConsented(true)} size="large">
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
          <Button type="primary" key="back" onClick={() => navigate('/student/completed')}>查看已完成问卷</Button>,
          <Button key="home" onClick={() => navigate('/student/home')}>返回首页</Button>,
        ]} />
    );
  }

  if (!sheet) return <div style={{ textAlign: 'center', padding: 60 }}><Typography.Text type="secondary">加载中...</Typography.Text></div>;

  const questions = sheet.questions;
  const q = questions[currentIndex];
  const answeredCount = Object.keys(answers).filter(k => answers[Number(k)]).length;
  const progress = questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0;

  const recordTime = () => {
    const now = Date.now();
    const spent = Math.round((now - questionStart) / 1000);
    if (q) setDurations(d => ({ ...d, [q.id]: (d[q.id] || 0) + spent }));
  };

  const nextQuestion = () => {
    recordTime();
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setQuestionStart(Date.now());
    }
  };

  const prevQuestion = () => {
    recordTime();
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setQuestionStart(Date.now());
    }
  };

  const setAnswer = (qid: number, value: any) => {
    setAnswers(a => ({ ...a, [qid]: value }));
  };

  const renderQuestion = () => {
    if (!q) return null;
    const ans = answers[q.id];

    return (
      <Card title={`第 ${currentIndex + 1} 题 / 共 ${questions.length} 题`}
        extra={q.required ? <span style={{ color: 'red' }}>* 必填</span> : <span style={{ color: '#888' }}>非必填</span>}
        style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 20, fontSize: 15, lineHeight: 1.6 }}>
          {q.title}
        </div>
        {q.description && <div style={{ color: '#888', fontSize: 13, marginBottom: 16, padding: '8px 12px', background: '#fafafa', borderRadius: 4 }}>{q.description}</div>}

        {(q.type === 'single_choice' || q.type === 'scale') && (
          <Radio.Group value={ans?.selected_option_id} onChange={e => setAnswer(q.id, { selected_option_id: e.target.value })}
            style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {q.options?.map((opt: any) => (
                <Radio key={opt.id} value={opt.id}
                  style={{ padding: '10px 12px', border: '1px solid #f0f0f0', borderRadius: 6, marginBottom: 4, display: 'block', background: ans?.selected_option_id === opt.id ? '#E6F7FF' : '#fff' }}>
                  {opt.content || `选项 ${opt.id}`}
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        )}
        {q.type === 'multi_choice' && (
          <Checkbox.Group value={ans?.selected_option_ids || []} onChange={vals => setAnswer(q.id, { selected_option_ids: vals })}
            style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {q.options?.map((opt: any) => (
                <div key={opt.id} style={{ padding: '10px 12px', border: '1px solid #f0f0f0', borderRadius: 6, marginBottom: 4 }}>
                  <Checkbox value={opt.id}>{opt.content || `选项 ${opt.id}`}</Checkbox>
                </div>
              ))}
            </Space>
          </Checkbox.Group>
        )}
        {q.type === 'true_false' && (
          <Radio.Group value={ans?.value} onChange={e => setAnswer(q.id, { value: e.target.value })}>
            <Space size="large">
              <Radio.Button value="true" style={{ padding: '8px 32px' }}>是</Radio.Button>
              <Radio.Button value="false" style={{ padding: '8px 32px' }}>否</Radio.Button>
            </Space>
          </Radio.Group>
        )}
        {(q.type === 'fill_blank' || q.type === 'short_answer') && (
          <Input.TextArea rows={4}
            value={ans?.text || ''} onChange={e => setAnswer(q.id, { text: e.target.value })} placeholder="请输入你的回答..." />
        )}
      </Card>
    );
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16 }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>{sheet.task_name || '问卷填写'}</Typography.Title>
        {sheet.description && <div style={{ color: '#595959', marginTop: 8 }}>{sheet.description}</div>}
        <div style={{ color: '#8c8c8c', fontSize: 13, marginTop: 8 }}>
          截止时间：{sheet.end_time ? new Date(sheet.end_time).toLocaleString('zh-CN') : '未设置'}
        </div>
      </Card>
      {!sheet.can_answer && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="当前任务暂不可提交"
          description="请留意任务开始时间、截止时间或任务状态。如有疑问，可以联系老师。"
        />
      )}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 13, color: '#888' }}>答题进度</span>
          <span style={{ fontSize: 13, color: '#888' }}>{answeredCount}/{questions.length} 已答</span>
        </div>
        <Progress percent={progress} showInfo={false} strokeColor={{ '0%': '#4A90D9', '100%': '#5B8DEF' }} />
      </div>

      {renderQuestion()}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16, padding: '0 0 24px' }}>
        <Button onClick={prevQuestion} disabled={currentIndex === 0} size="large">上一题</Button>
        <Space>
          <Button onClick={manualSave} loading={saving} size="large" disabled={!sheet.can_answer}>保存进度</Button>
          {currentIndex < questions.length - 1 ? (
            <Button type="primary" onClick={nextQuestion} size="large">下一题</Button>
          ) : (
            <Button type="primary" onClick={handleSubmit} size="large" disabled={!sheet.can_answer} icon={<CheckCircleOutlined />} style={{ background: '#67C23A', borderColor: '#67C23A' }}>提交问卷</Button>
          )}
        </Space>
      </div>
    </div>
  );
}
