import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, Drawer, Descriptions, Card, Spin, Button, Empty, Row, Col, Statistic, Timeline, Modal, message } from 'antd';
import { ExportOutlined, EyeOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { maskIdCard, translateRiskType } from '../../utils/maskIdCard';
import AnswerDetail from '../../components/answer/AnswerDetail';
import { RISK_LABELS, RISK_COLORS, INTERVENTION_STATUS_LABELS, METHOD_LABELS } from '../../utils/constants';

const statusLabels = INTERVENTION_STATUS_LABELS;
const methodLabels = METHOD_LABELS;

export default function PlatformKeyStudents() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ risk_level: '', keyword: '', school_id: '' as string | number });
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
  const [answerSheetId, setAnswerSheetId] = useState<number>();

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
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.school_id) params.school_id = filters.school_id;
      const r = await client.get('/platform/key-students', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewProfile = async (record: any) => {
    setDetailLoading(true); setDetailOpen(true); setDetail(null);
    try {
      const r = await client.get(`/platform/key-students/${record.student_id}`);
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
    const header = '学生,身份证号,学校,年级,班级,风险等级,风险类型,测评总分,干预次数,创建时间\n';
    const rows = data.map((r: any) =>
      `${r.student_name},${maskIdCard(r.id_card)},${r.school_name},${r.student_grade},${r.student_class},${RISK_LABELS[r.risk_level] || r.risk_level},${translateRiskType(r.risk_type)},${r.latest_score?.total_score?.toFixed(1) || '-'},${r.latest_score?.intervention_count || 0},${r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}`
    ).join('\n');
    const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `重点学生_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const riskLevelOrder: Record<string, number> = { low: 0, medium: 1, high: 2, urgent: 3 };
  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name', width: 100, sorter: (a: any, b: any) => (a.student_name || '').localeCompare(b.student_name || ''), render: (v: string, r: any) => <a onClick={() => viewProfile(r)}>{v}</a> },
    { title: '身份证号', dataIndex: 'id_card', key: 'id_card', width: 180, render: (v: string, r: any) => renderIdCard(v, r.student_id) },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120, sorter: (a: any, b: any) => (a.school_name || '').localeCompare(b.school_name || '') },
    { title: '年级', dataIndex: 'student_grade', key: 'student_grade', width: 80 },
    { title: '班级', dataIndex: 'student_class', key: 'student_class', width: 80 },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 90, sorter: (a: any, b: any) => (riskLevelOrder[a.risk_level] ?? 9) - (riskLevelOrder[b.risk_level] ?? 9), render: (v: string) => <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', width: 160, render: (v: string) => <span>{translateRiskType(v)}</span> },
    { title: '测评总分', key: 'score', width: 80, sorter: (a: any, b: any) => (a.latest_score?.total_score || 0) - (b.latest_score?.total_score || 0), render: (_: any, r: any) => r.latest_score?.total_score?.toFixed(1) || '-' },
    { title: '干预次数', key: 'interventions', width: 80, sorter: (a: any, b: any) => (a.latest_score?.intervention_count || 0) - (b.latest_score?.intervention_count || 0), render: (_: any, r: any) => <Tag>{r.latest_score?.intervention_count || 0}</Tag> },
    { title: '操作', key: 'action', width: 80, render: (_: any, r: any) => <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewProfile(r)}>画像</Button> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>重点关注学生</Typography.Title>
        <Button icon={<ExportOutlined />} onClick={() => setExportVerifyOpen(true)} disabled={!data.length}>导出 CSV</Button>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 180 }} value={filters.school_id || undefined}
          onChange={v => setFilters(f => ({ ...f, school_id: v || '' }))} options={schools} showSearch optionFilterProp="label" />
        <Select placeholder="风险等级" allowClear style={{ width: 120 }} value={filters.risk_level || undefined}
          onChange={v => setFilters(f => ({ ...f, risk_level: v || '' }))} options={Object.entries(RISK_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索学生姓名" style={{ width: 180 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 名重点学生` }} />

      <Drawer title={`学生画像 - ${detail?.student_name || ''}`} open={detailOpen} onClose={() => setDetailOpen(false)} width={680} destroyOnClose>
        {detailLoading ? <Spin /> : detail ? (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="姓名">{detail.student_name}</Descriptions.Item>
              <Descriptions.Item label="身份证号">{renderIdCard(detail.id_card, detail.student_id)}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school_name}</Descriptions.Item>
              <Descriptions.Item label="年级">{detail.grade || '-'}</Descriptions.Item>
              <Descriptions.Item label="班级">{detail.class || '-'}</Descriptions.Item>
            </Descriptions>

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}><Statistic title="预警次数" value={detail.alerts?.length || 0} valueStyle={{ color: '#FF4D4F' }} /></Col>
              <Col span={8}><Statistic title="干预次数" value={detail.interventions?.length || 0} valueStyle={{ color: '#1890FF' }} /></Col>
              <Col span={8}><Statistic title="测评次数" value={detail.scores?.length || 0} valueStyle={{ color: '#3f8600' }} /></Col>
            </Row>

            <Card title="风险预警历史" size="small" style={{ marginBottom: 16 }}>
              {detail.alerts?.length ? (
                <Timeline items={detail.alerts.map((a: any) => ({
                  color: RISK_COLORS[a.risk_level] || '#999',
                  children: (
                    <div>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                        <Tag color={RISK_COLORS[a.risk_level]}>{RISK_LABELS[a.risk_level]}</Tag>
                        <Tag>{translateRiskType(a.risk_type)}</Tag>
                        <Tag color={a.status === 'completed' || a.status === 'closed' ? 'green' : a.status === 'pending' ? 'red' : 'blue'}>{statusLabels[a.status] || a.status}</Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#999' }}>{a.created_at ? new Date(a.created_at).toLocaleString('zh-CN') : '-'}</div>
                    </div>
                  ),
                }))} />
              ) : <Empty description="暂无预警记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>

            <Card title="评分变化" size="small" style={{ marginBottom: 16 }}>
              {detail.scores?.length ? (
                <Table rowKey={(_: any, i: number | undefined) => String(i)} dataSource={detail.scores} pagination={false} size="small"
                  columns={[
                    { title: '总分', dataIndex: 'total_score', width: 80, render: (v: number) => v?.toFixed(1) || '-' },
                    { title: '风险等级', dataIndex: 'risk_level', width: 100, render: (v: string) => <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> },
                    { title: '时间', dataIndex: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                    { title: '操作', width: 80, render: (_: any, r: any) => {
                      const alert = detail.alerts?.find((a: any) => {
                        const scoreTime = r.created_at ? new Date(r.created_at).getTime() : 0;
                        const alertTime = a.created_at ? new Date(a.created_at).getTime() : 0;
                        return Math.abs(scoreTime - alertTime) < 60000;
                      });
                      return alert ? <Button size="small" type="link" onClick={() => { setAnswerAlertId(alert.id); setAnswerSheetId(undefined); setAnswerOpen(true); }}>详情</Button> : '-';
                    }},
                  ]} />
              ) : <Empty description="暂无评分记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>

            <Card title="干预记录" size="small">
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

      <AnswerDetail alertId={answerAlertId} answerSheetId={answerSheetId} platformMode open={answerOpen} onClose={() => setAnswerOpen(false)} />
    </div>
  );
}
