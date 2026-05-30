import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Button, Select, Space, message, Typography } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import client from '../../api/client';
import AnswerDetail from '../../components/answer/AnswerDetail';
import { RISK_LABELS, RISK_COLORS, INTERVENTION_STATUS_LABELS } from '../../utils/constants';
import { translateRiskType } from '../../utils/maskIdCard';

const statusLabels = INTERVENTION_STATUS_LABELS;

export default function RiskWarning() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: '', risk_level: '' });
  const [answerOpen, setAnswerOpen] = useState(false);
  const [answerAlertId, setAnswerAlertId] = useState<number>();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.status) params.status = filters.status;
      if (filters.risk_level) params.risk_level = filters.risk_level;
      const r = await client.get('/risks', { params });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取风险预警列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name' },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name' },
    { title: '班级', dataIndex: 'class_name', key: 'class_name' },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', render: (v: string) => translateRiskType(v, RISK_LABELS) },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', render: (v: string) => <Tag color={RISK_COLORS[v] || 'default'}>{RISK_LABELS[v] || v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '触发时间', dataIndex: 'created_at', key: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '触发问卷', dataIndex: 'questionnaire_title', key: 'questionnaire_title', render: (v: string) => v || '-' },
    { title: '操作', key: 'action', width: 150, render: (_: unknown, r: any) => (
      <Space>
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/school-admin/risks/${r.id}`)}>详情</Button>
        <Button type="link" size="small" onClick={() => { setAnswerAlertId(r.id); setAnswerOpen(true); }}>答题</Button>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Typography.Title level={4}>风险预警</Typography.Title>
        <Space>
          <Select
            placeholder="风险等级"
            allowClear
            style={{ width: 120 }}
            value={filters.risk_level || undefined}
            onChange={v => setFilters(f => ({ ...f, risk_level: v || '' }))}
            options={Object.entries(RISK_LABELS).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Select
            placeholder="处理状态"
            allowClear
            style={{ width: 130 }}
            value={filters.status || undefined}
            onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
            options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))}
          />
        </Space>
      </div>
      <Table
        rowKey="id"
        dataSource={data}
        columns={columns}
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }}
      />

      <AnswerDetail alertId={answerAlertId} open={answerOpen} onClose={() => setAnswerOpen(false)} />
    </div>
  );
}
