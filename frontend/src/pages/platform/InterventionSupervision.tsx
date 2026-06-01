import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Select, Typography, Space, message, Popconfirm, Tabs, Drawer, Descriptions, Card, Spin, Empty, Modal, Input } from 'antd';
import { BellOutlined, ExportOutlined, EyeOutlined, SendOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { maskIdCard } from '../../utils/maskIdCard';
import AnswerDetail from '../../components/answer/AnswerDetail';
import { METHOD_LABELS, INTERVENTION_STATUS_LABELS, INTERVENTION_STATUS_COLORS } from '../../utils/constants';

const methodLabels = METHOD_LABELS;
const statusLabels = INTERVENTION_STATUS_LABELS;
const statusColors = INTERVENTION_STATUS_COLORS;

export default function PlatformInterventionSupervision() {
  const [data, setData] = useState<any[]>([]);
  const [overdueData, setOverdueData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState('all');
  const [filters, setFilters] = useState({ status: '', school_id: '' as string | number });
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [exportVerifyOpen, setExportVerifyOpen] = useState(false);
  const [exportPassword, setExportPassword] = useState('');
  const [exportVerifying, setExportVerifying] = useState(false);
  const [answerOpen, setAnswerOpen] = useState(false);
  const [answerAlertId, setAnswerAlertId] = useState<number>();
  const [revealedCards, setRevealedCards] = useState<Map<number, string>>(new Map());
  const [verifyStudentId, setVerifyStudentId] = useState<number>(0);
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [verifyPassword, setVerifyPassword] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'overdue') {
        const r = await client.get('/platform/interventions/overdue');
        setOverdueData(r.data.data || []);
        setTotal((r.data.data || []).length);
      } else {
        const params: Record<string, unknown> = { page, page_size: 20 };
        if (filters.status) params.status = filters.status;
        if (filters.school_id) params.school_id = filters.school_id;
        const r = await client.get('/platform/interventions', { params });
        setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
      }
    } finally { setLoading(false); }
  }, [tab, page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleVerifyIdCard = async () => {
    if (!verifyPassword) { message.warning('请输入密码'); return; }
    setVerifyLoading(true);
    try {
      const r = await client.post(`/platform/students/${verifyStudentId}/reveal-id-card`, { password: verifyPassword });
      setRevealedCards(prev => new Map(prev).set(verifyStudentId, r.data.data.id_card));
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
    if (revealed) return <span style={{ fontFamily: 'monospace' }}>{revealed}</span>;
    return (
      <span>{maskIdCard(v)}{' '}
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={() => { setVerifyStudentId(studentId); setVerifyModalOpen(true); }} />
      </span>
    );
  };

  const handleUrge = async (id: number) => {
    await client.put(`/platform/interventions/${id}/urge`);
    message.success('已督促学校处理');
    fetchData();
  };

  const handleRemind = async (id: number) => {
    try {
      await client.post(`/platform/interventions/${id}/remind`);
      message.success('提醒已发送');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '发送失败');
    }
  };

  const viewDetail = (record: any) => {
    setDetail(record);
    setDetailOpen(true);
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
    const items = tab === 'overdue' ? overdueData : data;
    const header = '学生,身份证号,学校,年级,班级,负责教师,干预方式,状态,内容摘要,干预时间,需跟进\n';
    const rows = items.map((r: any) =>
      `${r.student_name},${maskIdCard(r.id_card)},${r.school_name},${r.student_grade || '-'},${r.student_class || '-'},${r.teacher_name || '-'},${methodLabels[r.method] || '未知'},${statusLabels[r.status] || '未知'},${(r.content || '-').replace(/,/g, '，')},${r.intervention_time || '-'},${r.need_follow_up ? '是' : '否'}`
    ).join('\n');
    const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `干预督办_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const actionColumn = {
    title: '操作', key: 'action', width: 160, render: (_: any, r: any) => (
      <Space>
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewDetail(r)}>详情</Button>
        <Popconfirm title="确定督促该学校处理此干预？" onConfirm={() => handleUrge(r.id)} okText="确定" cancelText="取消">
          <Button size="small" icon={<BellOutlined />} danger>督促</Button>
        </Popconfirm>
        <Button size="small" type="link" icon={<SendOutlined />} onClick={() => handleRemind(r.id)}>提醒</Button>
      </Space>
    ),
  };

  const tableColumns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', width: 100, ellipsis: true, sorter: (a: any, b: any) => (a.student_name || '').localeCompare(b.student_name || ''), render: (v: string, r: any) => <a onClick={() => viewDetail(r)}>{v}</a> },
    { title: '身份证号', dataIndex: 'id_card', key: 'id_card', width: 150, render: (v: string, r: any) => renderIdCard(v, r.student_id) },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 110, ellipsis: true, sorter: (a: any, b: any) => (a.school_name || '').localeCompare(b.school_name || '') },
    { title: '负责教师', dataIndex: 'teacher_name', key: 'teacher_name', width: 90, ellipsis: true, render: (v: string) => v || '-' },
    { title: '方式', dataIndex: 'method', key: 'method', width: 100, render: (v: string) => <Tag style={{ maxWidth: 100 }}>{methodLabels[v] || '未知'}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, sorter: (a: any, b: any) => (a.status || '').localeCompare(b.status || ''), render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || '未知'}</Tag> },
    { title: '内容摘要', dataIndex: 'content', key: 'content', ellipsis: true, width: 180, render: (v: string) => v || '-' },
    { title: '干预时间', dataIndex: 'intervention_time', key: 'intervention_time', width: 110, sorter: (a: any, b: any) => new Date(a.intervention_time || 0).getTime() - new Date(b.intervention_time || 0).getTime(), render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '需跟进', dataIndex: 'need_follow_up', key: 'need_follow_up', width: 70, render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
    actionColumn,
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>干预督办</Typography.Title>
        <Button icon={<ExportOutlined />} onClick={() => setExportVerifyOpen(true)} disabled={!(tab === 'overdue' ? overdueData : data).length}>导出 CSV</Button>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 180 }} value={filters.school_id || undefined}
          onChange={v => setFilters(f => ({ ...f, school_id: v || '' }))} options={schools} showSearch optionFilterProp="label" />
        {tab !== 'overdue' && (
          <Select placeholder="状态" allowClear style={{ width: 130 }} value={filters.status || undefined}
            onChange={v => setFilters(f => ({ ...f, status: v || '' }))} options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
        )}
      </Space>
      <Tabs activeKey={tab} onChange={k => { setTab(k); setPage(1); }} items={[
        { key: 'all', label: '全部干预' },
        { key: 'overdue', label: `逾期未处理 (${overdueData.length})` },
      ]} />
      <Table rowKey="id" dataSource={tab === 'overdue' ? overdueData : data} columns={tableColumns} loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={tab === 'overdue' ? false : { current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

      <Drawer title="干预详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={560} destroyOnClose>
        {detail ? (
          <div>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="学生">{detail.student_name}</Descriptions.Item>
              <Descriptions.Item label="身份证号">{renderIdCard(detail.id_card, detail.student_id)}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school_name}</Descriptions.Item>
              <Descriptions.Item label="负责教师">{detail.teacher_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="干预方式"><Tag>{methodLabels[detail.method] || '未知'}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColors[detail.status]}>{statusLabels[detail.status] || '未知'}</Tag></Descriptions.Item>
              <Descriptions.Item label="需跟进">{detail.need_follow_up ? <Tag color="orange">是</Tag> : <Tag>否</Tag>}</Descriptions.Item>
              <Descriptions.Item label="干预时间" span={2}>{detail.intervention_time ? new Date(detail.intervention_time).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            </Descriptions>
            {detail.content && (
              <Card title="干预内容" size="small" style={{ marginTop: 16 }}>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{detail.content}</div>
              </Card>
            )}
            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <Popconfirm title="确定督促处理？" onConfirm={() => { handleUrge(detail.id); setDetailOpen(false); }} okText="确定" cancelText="取消">
                <Button icon={<BellOutlined />} danger>督促处理</Button>
              </Popconfirm>
              <Button type="primary" icon={<SendOutlined />} onClick={() => handleRemind(detail.id)}>发送提醒</Button>
              {detail.risk_alert_id && (
                <Button onClick={() => { setAnswerAlertId(detail.risk_alert_id); setAnswerOpen(true); }}>查看答题详情</Button>
              )}
            </div>
          </div>
        ) : <Empty />}
      </Drawer>

      <Modal title="导出验证" open={exportVerifyOpen} onOk={handleExportVerify} confirmLoading={exportVerifying}
        onCancel={() => { setExportVerifyOpen(false); setExportPassword(''); }} okText="确定" cancelText="取消" destroyOnClose>
        <p style={{ marginBottom: 12 }}>导出包含敏感信息，请输入登录密码验证身份</p>
        <Input.Password value={exportPassword} onChange={e => setExportPassword(e.target.value)} placeholder="请输入密码" onPressEnter={handleExportVerify} />
      </Modal>

      <Modal title="身份验证" open={verifyModalOpen} onOk={handleVerifyIdCard} confirmLoading={verifyLoading}
        onCancel={() => { setVerifyModalOpen(false); setVerifyPassword(''); }} okText="确定" cancelText="取消" destroyOnClose>
        <p style={{ marginBottom: 12 }}>查看完整身份证号，请输入登录密码验证身份</p>
        <Input.Password value={verifyPassword} onChange={e => setVerifyPassword(e.target.value)} placeholder="请输入密码" onPressEnter={handleVerifyIdCard} />
      </Modal>

      <AnswerDetail alertId={answerAlertId} platformMode open={answerOpen} onClose={() => setAnswerOpen(false)} />
    </div>
  );
}
