import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Select, Input, Typography, Space, Drawer, Descriptions, Button, Modal, message, Empty } from 'antd';
import { ExportOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { maskIdCard } from '../../utils/maskIdCard';
import AnswerDetail from '../../components/answer/AnswerDetail';
import { RISK_LABELS, RISK_COLORS } from '../../utils/constants';

const statusLabels: Record<string, string> = { true: '正常', false: '已禁用' };

export default function PlatformStudentManagement() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ school_id: '' as string | number, keyword: '' });
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [revealedCards, setRevealedCards] = useState<Map<number, string>>(new Map());
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [verifyStudentId, setVerifyStudentId] = useState<number>(0);
  const [verifyPassword, setVerifyPassword] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [exportVerifyOpen, setExportVerifyOpen] = useState(false);
  const [exportPassword, setExportPassword] = useState('');
  const [exportVerifying, setExportVerifying] = useState(false);
  const [answerOpen, setAnswerOpen] = useState(false);
  const [answerSheetId, setAnswerSheetId] = useState<number>();
  const [studentSheets, setStudentSheets] = useState<any[]>([]);
  const [sheetsModalOpen, setSheetsModalOpen] = useState(false);

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.school_id) params.school_id = filters.school_id;
      if (filters.keyword) params.keyword = filters.keyword;
      const r = await client.get('/platform/students', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewDetail = async (record: any) => {
    setDetailOpen(true); setDetail(null);
    try {
      const r = await client.get(`/platform/students/${record.id}`);
      setDetail(r.data.data);
    } catch { setDetail(null); }
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
    const header = '学生姓名,学号,身份证号,学校,年级,班级,手机号,性别,状态,创建时间\n';
    const rows = data.map((r: any) =>
      `${r.student_name},${r.student_no},${maskIdCard(r.id_card)},${r.school_name},${r.grade_name || '-'},${r.class_name || '-'},${r.phone ? r.phone.slice(0, 3) + '****' + r.phone.slice(-4) : '-'},${r.gender || '-'},${r.status ? '正常' : '已禁用'},${r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}`
    ).join('\n');
    const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `学生信息_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name', width: 100 },
    { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 120 },
    { title: '身份证号', dataIndex: 'id_card', key: 'id_card', width: 180, render: (v: string, r: any) => renderIdCard(v, r.id) },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120 },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 80 },
    { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 100 },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120, render: (v: string) => v ? v.slice(0, 3) + '****' + v.slice(-4) : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 70, render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '正常' : '已禁用'}</Tag> },
    { title: '操作', key: 'action', width: 170, render: (_: any, r: any) => (
      <Space>
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewDetail(r)}>详情</Button>
        <Button size="small" type="link" icon={<FileTextOutlined />} onClick={() => navigate(`/platform/students/${r.id}`)}>档案</Button>
        <Button size="small" type="link" onClick={async () => {
          try {
            const res = await client.get(`/platform/students/${r.id}/answer-sheets`);
            setStudentSheets(res.data.data || []);
            setSheetsModalOpen(true);
          } catch { setStudentSheets([]); }
        }}>答题</Button>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>学生管理</Typography.Title>
        <Button icon={<ExportOutlined />} onClick={() => setExportVerifyOpen(true)} disabled={!data.length}>导出 CSV</Button>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 180 }} value={filters.school_id || undefined}
          onChange={v => setFilters(f => ({ ...f, school_id: v || '' }))} options={schools} showSearch optionFilterProp="label" />
        <Input.Search placeholder="搜索姓名/学号/身份证号" style={{ width: 220 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 名学生` }} />

      <Drawer title="学生详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={520} destroyOnClose>
        {detail ? (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="学生姓名">{detail.student_name}</Descriptions.Item>
            <Descriptions.Item label="学号">{detail.student_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="身份证号">{renderIdCard(detail.id_card, detail.id)}</Descriptions.Item>
            <Descriptions.Item label="学校">{detail.school_name}</Descriptions.Item>
            <Descriptions.Item label="年级">{detail.grade_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="班级">{detail.class_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="手机号">{detail.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="性别">{detail.gender || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={detail.status ? 'green' : 'red'}>{detail.status ? '正常' : '已禁用'}</Tag></Descriptions.Item>
            <Descriptions.Item label="创建时间">{detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
          </Descriptions>
        ) : null}
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

      <Modal title="学生答题记录" open={sheetsModalOpen} onCancel={() => setSheetsModalOpen(false)} footer={null} width={600} destroyOnClose>
        {studentSheets.length ? (
          <Table rowKey="answer_sheet_id" dataSource={studentSheets} pagination={false} size="small"
            columns={[
              { title: '问卷', dataIndex: 'questionnaire_title', ellipsis: true },
              { title: '总分', dataIndex: 'total_score', width: 70, render: (v: number) => v?.toFixed(1) || '-' },
              { title: '风险等级', dataIndex: 'risk_level', width: 90, render: (v: string) => <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> },
              { title: '提交时间', dataIndex: 'submitted_at', width: 140, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
              { title: '操作', width: 70, render: (_: any, r: any) => <Button size="small" type="link" onClick={() => { setAnswerSheetId(r.answer_sheet_id); setAnswerOpen(true); setSheetsModalOpen(false); }}>详情</Button> },
            ]}
          />
        ) : <Empty description="暂无答题记录" />}
      </Modal>

      <AnswerDetail answerSheetId={answerSheetId} platformMode open={answerOpen} onClose={() => setAnswerOpen(false)} />
    </div>
  );
}
