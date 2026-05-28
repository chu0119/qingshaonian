import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Select, Typography, Space, message, Popconfirm } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import client from '../../api/client';

const methodLabels: Record<string, string> = { student_talk: '学生谈话', counselor_counsel: '心理辅导', parent_communication: '家校沟通', home_visit: '家访', observation: '持续观察', other: '其他' };
const statusLabels: Record<string, string> = { pending: '待处理', in_progress: '处理中', processing: '处理中', follow_up: '持续跟进', ongoing: '持续跟进', completed: '已完成', closed: '已关闭' };
const statusColors: Record<string, string> = { pending: '#FA8C16', in_progress: '#1890FF', processing: '#1890FF', follow_up: '#722ED1', ongoing: '#722ED1', completed: '#52C41A', closed: '#8C8C8C' };

export default function PlatformInterventionSupervision() {
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
      const r = await client.get('/platform/interventions', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUrge = async (id: number) => {
    await client.put(`/platform/interventions/${id}/urge`);
    message.success('已督促学校处理');
    fetchData();
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', width: 100 },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120 },
    { title: '负责教师', dataIndex: 'teacher_name', key: 'teacher_name', width: 100 },
    { title: '方式', dataIndex: 'method', key: 'method', width: 80, render: (v: string) => methodLabels[v] || v },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: '内容摘要', dataIndex: 'content', key: 'content', ellipsis: true, width: 200 },
    { title: '干预时间', dataIndex: 'intervention_time', key: 'intervention_time', width: 110, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '需跟进', dataIndex: 'need_follow_up', key: 'need_follow_up', width: 70, render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
    { title: '操作', key: 'action', width: 120, render: (_: any, r: any) => (
      <Popconfirm title="确定督促该学校处理此干预？" onConfirm={() => handleUrge(r.id)}>
        <Button size="small" icon={<BellOutlined />} type="primary" danger>督促处理</Button>
      </Popconfirm>
    )},
  ];

  return (
    <div>
      <Typography.Title level={4}>干预督办</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="状态" allowClear style={{ width: 130 }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
          options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />
    </div>
  );
}
