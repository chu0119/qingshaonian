import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space } from 'antd';
import client from '../../api/client';

export default function PlatformAuditLogs() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ module: '', action: '', operator_role: '', keyword: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.module) params.module = filters.module;
      if (filters.action) params.action = filters.action;
      if (filters.operator_role) params.operator_role = filters.operator_role;
      if (filters.keyword) params.keyword = filters.keyword;
      const r = await client.get('/platform/audit-logs', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const roleLabels: Record<string, string> = { school_admin: '学校管理员', teacher: '教师', counselor: '心理老师', platform_admin: '平台管理员', student: '学生' };
  const resultColors: Record<string, string> = { success: 'green', failure: 'red', partial_success: 'orange' };

  const columns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '模块', dataIndex: 'module', key: 'module', width: 100 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 100 },
    { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 100, render: (v: string, r: any) => `${v} (${roleLabels[r.operator_role] || r.operator_role})` },
    { title: '对象类型', dataIndex: 'object_type', key: 'object_type', width: 100 },
    { title: '对象', dataIndex: 'object_name', key: 'object_name', width: 120 },
    { title: '结果', dataIndex: 'result', key: 'result', width: 70, render: (v: string) => <Tag color={resultColors[v]}>{v}</Tag> },
    { title: '详情', dataIndex: 'detail', key: 'detail', ellipsis: true, width: 150 },
    { title: 'IP', dataIndex: 'ip', key: 'ip', width: 120 },
  ];

  return (
    <div>
      <Typography.Title level={4}>操作日志审计</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="模块" allowClear style={{ width: 120 }} value={filters.module || undefined} onChange={v => setFilters(f => ({ ...f, module: v || '' }))}
          options={['platform_school', 'auth', 'student', 'teacher', 'ai_analysis', 'sms', 'platform_supervision'].map(v => ({ value: v, label: v }))} />
        <Select placeholder="角色" allowClear style={{ width: 120 }} value={filters.operator_role || undefined} onChange={v => setFilters(f => ({ ...f, operator_role: v || '' }))}
          options={Object.entries(roleLabels).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />
    </div>
  );
}
