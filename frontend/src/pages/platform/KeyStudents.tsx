import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Typography, Space, Progress } from 'antd';
import client from '../../api/client';

const riskLabels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', urgent: '紧急风险' };
const riskColors: Record<string, string> = { low: '#1890FF', medium: '#FA8C16', high: '#FF4D4F', urgent: '#CF1322' };

export default function PlatformKeyStudents() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ risk_level: '', keyword: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.risk_level) params.risk_level = filters.risk_level;
      const r = await client.get('/platform/key-students', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name', width: 100 },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120 },
    { title: '年级', dataIndex: 'student_grade', key: 'student_grade', width: 80 },
    { title: '班级', dataIndex: 'student_class', key: 'student_class', width: 80 },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 90, render: (v: string) => <Tag color={riskColors[v]}>{riskLabels[v] || v}</Tag> },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', width: 140, render: (v: string) => v || '-' },
    { title: '测评总分', key: 'score', width: 80, render: (_: any, r: any) => r.latest_score?.total_score?.toFixed(1) || '-' },
    { title: '干预次数', key: 'interventions', width: 80, render: (_: any, r: any) => <Tag>{r.latest_score?.intervention_count || 0}</Tag> },
  ];

  return (
    <div>
      <Typography.Title level={4}>重点关注学生</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="风险等级" allowClear style={{ width: 120 }} value={filters.risk_level || undefined} onChange={v => setFilters(f => ({ ...f, risk_level: v || '' }))}
          options={Object.entries(riskLabels).map(([k, v]) => ({ value: k, label: v }))} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 名重点学生` }} />
    </div>
  );
}
