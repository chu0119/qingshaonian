import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space } from 'antd';
import client from '../../api/client';

const riskLabels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', urgent: '紧急风险' };
const riskColors: Record<string, string> = { low: '#1890FF', medium: '#FA8C16', high: '#FF4D4F', urgent: '#CF1322' };
const statusLabels: Record<string, string> = { pending: '待处理', in_progress: '处理中', processing: '处理中', follow_up: '持续跟进', ongoing: '持续跟进', completed: '已完成', closed: '已关闭' };

export default function PlatformRiskCenter() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ risk_level: '', status: '', keyword: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.risk_level) params.risk_level = filters.risk_level;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      const r = await client.get('/platform/risk-alerts', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', width: 100 },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120 },
    { title: '年级', dataIndex: 'student_grade', key: 'student_grade', width: 80 },
    { title: '班级', dataIndex: 'student_class', key: 'student_class', width: 80 },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 90, render: (v: string) => <Tag color={riskColors[v]}>{riskLabels[v] || v}</Tag> },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', width: 140, render: (v: string) => <Tag>{v || '-'}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
  ];

  return (
    <div>
      <Typography.Title level={4}>风险预警中心</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="风险等级" allowClear style={{ width: 120 }} value={filters.risk_level || undefined} onChange={v => setFilters(f => ({ ...f, risk_level: v || '' }))}
          options={Object.entries(riskLabels).map(([k, v]) => ({ value: k, label: v }))} />
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
          options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索学生" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />
    </div>
  );
}
