import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Typography, Space } from 'antd';
import client from '../../api/client';

const statusLabels: Record<string, string> = { draft: '草稿', pending: '未开始', not_started: '未开始', active: '进行中', in_progress: '进行中', ended: '已截止', closed: '已关闭' };
const statusColors: Record<string, string> = { draft: 'default', pending: 'blue', not_started: 'blue', active: 'green', in_progress: 'green', ended: 'red', closed: 'default' };

export default function PlatformTaskSupervision() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.status) params.status = filters.status;
      const r = await client.get('/platform/tasks', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120 },
    { title: '问卷', dataIndex: 'questionnaire_title', key: 'questionnaire_title', width: 160, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: '开始时间', dataIndex: 'start_time', key: 'start_time', width: 110, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '截止时间', dataIndex: 'end_time', key: 'end_time', width: 110, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  return (
    <div>
      <Typography.Title level={4}>测评任务监管</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
          options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 个任务` }} />
    </div>
  );
}
