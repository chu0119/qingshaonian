import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, Drawer, Descriptions, Card, Spin, Button, Progress, Empty, Row, Col, Statistic, Modal, message } from 'antd';
import { ExportOutlined, EyeOutlined, RobotOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { maskIdCard, translateRiskType } from '../../utils/maskIdCard';
import AnswerDetail from '../../components/answer/AnswerDetail';
import AiAnalysisModal from '../../components/ai/AiAnalysisModal';
import { RISK_LABELS, RISK_COLORS, TRIGGER_METHOD_LABELS, INTERVENTION_STATUS_LABELS, METHOD_LABELS, QUALITY_LABELS, DIMENSION_LABELS } from '../../utils/constants';

const statusLabels = INTERVENTION_STATUS_LABELS;
const methodLabels = METHOD_LABELS;
const qualityLabels = QUALITY_LABELS;
const dimensionLabels = DIMENSION_LABELS;

export default function PlatformRiskCenter() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ risk_level: '', status: '', keyword: '', school_id: '' as string | number });
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [revealedCards, setRevealedCards] = useState<Map<number, string>>(new Map());
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [verifyStudentId, setVerifyStudentId] = useState<number>(0);
  const [verifyPassword, setVerifyPassword] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [exportVerifyOpen, setExportVerifyOpen] = useState(false);
  const [exportPassword, setExportPassword] = useState('');
  const [exportVerifying, setExportVerifying] = useState(false);
  const [answerOpen, setAnswerOpen] = useState(false);
  const [answerAlertId, setAnswerAlertId] = useState<number>();
  const [aiModalOpen, setAiModalOpen] = useState(false);

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.risk_level) params.risk_level = filters.risk_level;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.school_id) params.school_id = filters.school_id;
      const r = await client.get('/platform/risk-alerts', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewDetail = async (record: any) => {
    setDetailLoading(true); setDetailOpen(true); setDetail(null);
    try {
      const r = await client.get(`/platform/risks/${record.id}`);
      setDetail(r.data.data);
    } catch { setDetail(null); }
    finally { setDetailLoading(false); }
  };

  const handleVerify = async () => {
    if (!verifyPassword) { message.warning('请输入密码'); return; }
    setVerifyLoading(true);
    try {
      const r = await client.post(`/platform/students/${verifyStudentId}/reveal-id-card`, { password: verifyPassword });
      const realIdCard = r.data.data.id_card;
      setRevealedCards(prev => new Map(prev).set(verifyStudentId, realIdCard));
      setVerifyModalOpen(false);
      setVerifyPassword('');
      message.success('验证通过');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '密码错误');
    } finally { setVerifyLoading(false); }
  };

  const renderIdCard = (v: string, studentId: number) => {
    if (!v) return '-';
    const revealed = revealedCards.get(studentId);
    if (revealed) return revealed;
    return (
      <span>{maskIdCard(v)}{' '}
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={() => { setVerifyStudentId(studentId); setVerifyModalOpen(true); }} />
      </span>
    );
  };

  const handleExportVerify = async () => {
    if (!exportPassword) { message.warning('请输入密码'); return; }
    setExportVerifying(true);
    try {
      await client.post('/platform/verify-password', { password: exportPassword });
      setExportVerifyOpen(false);
      setExportPassword('');
      message.success('验证通过，开始导出');
      doExportCSV();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '密码错误');
    } finally { setExportVerifying(false); }
  };

  const doExportCSV = () => {
    const header = '学生,身份证号,学校,年级,班级,风险等级,风险类型,状态,创建时间\n';
    const rows = data.map((r: any) =>
      `${r.student_name},${maskIdCard(r.id_card)},${r.school_name},${r.student_grade},${r.student_class},${RISK_LABELS[r.risk_level] || r.risk_level},${translateRiskType(r.risk_type, RISK_LABELS)},${statusLabels[r.status] || r.status},${r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}`
    ).join('\n');
    const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `风险预警_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const riskLevelOrder: Record<string, number> = { low: 0, medium: 1, high: 2, urgent: 3 };
  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', width: 100, sorter: (a: any, b: any) => (a.student_name || '').localeCompare(b.student_name || '') },
    { title: '身份证号', dataIndex: 'id_card', key: 'id_card', width: 180, render: (v: string, r: any) => renderIdCard(v, r.student_id) },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120, sorter: (a: any, b: any) => (a.school_name || '').localeCompare(b.school_name || '') },
    { title: '年级', dataIndex: 'student_grade', key: 'student_grade', width: 80 },
    { title: '班级', dataIndex: 'student_class', key: 'student_class', width: 80 },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 90, sorter: (a: any, b: any) => (riskLevelOrder[a.risk_level] ?? 9) - (riskLevelOrder[b.risk_level] ?? 9), render: (v: string) => <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', width: 160, render: (v: string) => <span>{translateRiskType(v, RISK_LABELS)}</span> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, sorter: (a: any, b: any) => (a.status || '').localeCompare(b.status || ''), render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 110, sorter: (a: any, b: any) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime(), render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '操作', key: 'action', width: 80, render: (_: any, r: any) => <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewDetail(r)}>详情</Button> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>风险预警中心</Typography.Title>
        <Button icon={<ExportOutlined />} onClick={() => setExportVerifyOpen(true)} disabled={!data.length}>导出 CSV</Button>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 180 }} value={filters.school_id || undefined}
          onChange={v => setFilters(f => ({ ...f, school_id: v || '' }))} options={schools} showSearch optionFilterProp="label" />
        <Select placeholder="风险等级" allowClear style={{ width: 120 }} value={filters.risk_level || undefined}
          onChange={v => setFilters(f => ({ ...f, risk_level: v || '' }))} options={Object.entries(RISK_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined}
          onChange={v => setFilters(f => ({ ...f, status: v || '' }))} options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索学生" style={{ width: 180 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

      <Drawer title="风险预警详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={640} destroyOnClose>
        {detailLoading ? <Spin /> : detail ? (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="学生">{detail.student_name}</Descriptions.Item>
              <Descriptions.Item label="身份证号">{renderIdCard(detail.id_card, detail.student_id)}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school_name}</Descriptions.Item>
              <Descriptions.Item label="风险等级">
                <Tag color={RISK_COLORS[detail.risk_level]}>{RISK_LABELS[detail.risk_level] || detail.risk_level}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="风险类型">{translateRiskType(detail.risk_type, RISK_LABELS)}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag>{statusLabels[detail.status] || detail.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="触发方式">{TRIGGER_METHOD_LABELS[detail.trigger_method] || detail.trigger_method || '-'}</Descriptions.Item>
              <Descriptions.Item label="生成时间" span={2}>{detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            </Descriptions>

            <Card title="评分详情" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16} style={{ marginBottom: 12 }}>
                <Col><Statistic title="总分" value={detail.total_score || 0} /></Col>
              </Row>
              {detail.dimension_scores && Object.keys(detail.dimension_scores).length > 0 ? (
                Object.entries(detail.dimension_scores).map(([key, val]) => {
                  const score = val as number;
                  const maxScore = 100;
                  return (
                    <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ width: 70, fontSize: 13 }}>{dimensionLabels[key] || key}</span>
                      <Progress percent={Math.round(score / maxScore * 100)} size="small" style={{ flex: 1 }}
                        strokeColor={score > 70 ? '#FF4D4F' : score > 40 ? '#FA8C16' : '#1890FF'} />
                      <span style={{ fontSize: 13, width: 40 }}>{score}</span>
                    </div>
                  );
                })
              ) : <Empty description="暂无评分数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>

            <Card title="答卷质量" size="small" style={{ marginBottom: 16 }}>
              {detail.quality_level ? (
                <>
                  <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                    <Col span={8}><Statistic title="质量评分" value={detail.quality_score || 0} suffix="分"
                      valueStyle={{ color: (detail.quality_score || 0) >= 70 ? '#67C23A' : (detail.quality_score || 0) >= 50 ? '#E6A23C' : '#FF4D4F', fontSize: 20 }} /></Col>
                    <Col span={8}><Statistic title="质量等级" value={qualityLabels[detail.quality_level] || detail.quality_level}
                      valueStyle={{ fontSize: 20 }} /></Col>
                    <Col span={8}><Statistic title="建议复测" value={detail.suggest_retest ? '是' : '否'}
                      valueStyle={{ color: detail.suggest_retest ? '#FF4D4F' : '#67C23A', fontSize: 20 }} /></Col>
                  </Row>
                  <Descriptions bordered size="small" column={2}>
                    <Descriptions.Item label="答题时长">{detail.quality_duration || '-'}</Descriptions.Item>
                    <Descriptions.Item label="有效性">{qualityLabels[detail.validity] || detail.validity || '-'}</Descriptions.Item>
                    {detail.attention_passed !== undefined && <Descriptions.Item label="注意力检测">{detail.attention_passed ? '通过' : '未通过'}</Descriptions.Item>}
                    {detail.max_consecutive_same !== undefined && <Descriptions.Item label="连续同选">{detail.max_consecutive_same} 题</Descriptions.Item>}
                    {detail.contradiction_count !== undefined && <Descriptions.Item label="矛盾检测">{detail.contradiction_count} 组</Descriptions.Item>}
                    {detail.pattern_detected !== undefined && <Descriptions.Item label="规律作答">{detail.pattern_detected ? '检测到' : '未检测到'}</Descriptions.Item>}
                    {detail.fast_question_count !== undefined && <Descriptions.Item label="快速作答">{detail.fast_question_count} 题</Descriptions.Item>}
                  </Descriptions>
                  {detail.quality_deductions?.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {detail.quality_deductions.map((d: string, i: number) => (
                        <Tag key={i} color="orange" style={{ marginBottom: 4 }}>{d}</Tag>
                      ))}
                    </div>
                  )}
                </>
              ) : <Empty description="暂无质量评估" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>

            {detail.risk_description && (
              <Card title="综合评估" size="small" style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, lineHeight: 1.8, color: '#666' }}>{detail.risk_description}</div>
              </Card>
            )}

            {detail.dimension_analysis?.filter((item: any) => item && (item.dimension || item.label || item.risk_tag)).length > 0 && (
              <Card title="维度分析" size="small" style={{ marginBottom: 16 }}>
                {detail.dimension_analysis.filter((item: any) => item && (item.dimension || item.label || item.risk_tag)).map((item: any, i: number) => (
                  <div key={i} style={{ marginBottom: 8, padding: '6px 10px', background: '#fafafa', borderRadius: 4 }}>
                    <Space>
                      <Tag color={item.level === 'high' ? 'red' : item.level === 'medium' ? 'orange' : 'blue'}>
                        {dimensionLabels[item.dimension] || item.dimension || item.risk_tag || ''}
                      </Tag>
                      <span style={{ fontSize: 13 }}>{item.label || item.suggestion || ''}</span>
                    </Space>
                  </div>
                ))}
              </Card>
            )}

            <Card title={`干预记录 (${detail.interventions?.length || 0})`} size="small">
              {detail.interventions?.length ? (
                detail.interventions.map((iv: any, idx: number) => (
                  <div key={iv.id} style={{ padding: '8px 0', borderBottom: idx < detail.interventions.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Tag>{methodLabels[iv.method] || iv.method}</Tag>
                      <Tag color={iv.status === 'completed' ? 'green' : iv.status === 'pending' ? 'red' : 'blue'}>{statusLabels[iv.status] || iv.status}</Tag>
                    </div>
                    {iv.content && <div style={{ fontSize: 13, color: '#666', marginBottom: 4 }}>{iv.content}</div>}
                    <div style={{ fontSize: 12, color: '#999' }}>{iv.created_at ? new Date(iv.created_at).toLocaleString('zh-CN') : '-'}</div>
                  </div>
                ))
              ) : <Empty description="暂无干预记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>

            <Space style={{ marginTop: 16 }}>
              <Button type="primary" onClick={() => { setAnswerAlertId(detail.id); setAnswerOpen(true); }}>查看原始答题详情</Button>
              <Button icon={<RobotOutlined />} onClick={() => setAiModalOpen(true)}>AI 分析</Button>
            </Space>
          </div>
        ) : <Empty description="加载失败" />}
      </Drawer>

      <Modal title="身份验证" open={verifyModalOpen} onOk={handleVerify} confirmLoading={verifyLoading}
        onCancel={() => { setVerifyModalOpen(false); setVerifyPassword(''); }} okText="确定" cancelText="取消" destroyOnClose>
        <p style={{ marginBottom: 12 }}>请输入您的登录密码以查看完整身份证号</p>
        <Input.Password value={verifyPassword} onChange={e => setVerifyPassword(e.target.value)} placeholder="请输入密码" onPressEnter={handleVerify} />
      </Modal>

      <Modal title="导出验证" open={exportVerifyOpen} onOk={handleExportVerify} confirmLoading={exportVerifying}
        onCancel={() => { setExportVerifyOpen(false); setExportPassword(''); }} okText="确定" cancelText="取消" destroyOnClose>
        <p style={{ marginBottom: 12 }}>导出包含敏感信息，请输入登录密码验证身份</p>
        <Input.Password value={exportPassword} onChange={e => setExportPassword(e.target.value)} placeholder="请输入密码" onPressEnter={handleExportVerify} />
      </Modal>

      <AnswerDetail alertId={answerAlertId} platformMode open={answerOpen} onClose={() => setAnswerOpen(false)} />

      {detail && (
        <AiAnalysisModal
          open={aiModalOpen}
          type="student_risk"
          title={`AI 风险分析 - ${detail.student_name}`}
          data={{
            student_id: detail.student_id, student_name: detail.student_name,
            risk_level: detail.risk_level, risk_type: detail.risk_type,
            total_score: detail.total_score, dimension_scores: detail.dimension_scores,
            quality_level: detail.quality_level, quality_score: detail.quality_score,
            risk_description: detail.risk_description,
          }}
          onClose={() => setAiModalOpen(false)}
        />
      )}
    </div>
  );
}
