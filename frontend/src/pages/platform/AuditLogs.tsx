import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, Tabs } from 'antd';
import client from '../../api/client';
import { ROLE_LABELS as roleLabels, RESULT_LABELS } from '../../utils/constants';

const resultColors: Record<string, string> = { success: 'green', failure: 'red', partial_success: 'orange' };

export default function PlatformAuditLogs() {
  const [tab, setTab] = useState('operations');
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ module: '', action: '', operator_role: '', keyword: '' });
  const [loginFilters, setLoginFilters] = useState({ keyword: '', result: '', user_role: '' });

  const fetchOps = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.module) params.module = filters.module;
      if (filters.action) params.action = filters.action;
      if (filters.operator_role) params.operator_role = filters.operator_role;
      if (filters.keyword) params.keyword = filters.keyword;
      const r = await client.get('/platform/audit-logs', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters]);

  const fetchLogins = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (loginFilters.keyword) params.keyword = loginFilters.keyword;
      if (loginFilters.result) params.result = loginFilters.result;
      if (loginFilters.user_role) params.user_role = loginFilters.user_role;
      const r = await client.get('/platform/audit/login-logs', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, loginFilters]);

  useEffect(() => {
    if (tab === 'operations') fetchOps();
    else fetchLogins();
  }, [tab, fetchOps, fetchLogins]);

  const opColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '模块', dataIndex: 'module_label', key: 'module', width: 100, render: (v: string, r: any) => <Tag>{v || r.module}</Tag> },
    { title: '操作', dataIndex: 'action_label', key: 'action', width: 120, render: (v: string, r: any) => v || r.action },
    { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 120, render: (v: string, r: any) => `${v} (${roleLabels[r.operator_role] || '未知'})` },
    { title: '对象类型', dataIndex: 'object_type_label', key: 'object_type', width: 90, render: (v: string, r: any) => v || r.object_type },
    { title: '对象', dataIndex: 'object_name', key: 'object_name', width: 120 },
    { title: '结果', dataIndex: 'result', key: 'result', width: 70, render: (v: string) => <Tag color={resultColors[v]}>{RESULT_LABELS[v] || '未知'}</Tag> },
    { title: '详情', dataIndex: 'detail', key: 'detail', ellipsis: true, width: 150 },
    { title: 'IP', dataIndex: 'ip', key: 'ip', width: 120 },
  ];

  const loginColumns = [
    { title: '登录时间', dataIndex: 'login_time', key: 'login_time', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '角色', dataIndex: 'user_role', key: 'user_role', width: 100, render: (v: string) => <Tag>{roleLabels[v] || '未知'}</Tag> },
    { title: 'IP', dataIndex: 'login_ip', key: 'login_ip', width: 120 },
    { title: '结果', dataIndex: 'result', key: 'result', width: 80, render: (v: string) => <Tag color={v === 'success' ? 'green' : 'red'}>{v === 'success' ? '成功' : '失败'}</Tag> },
    { title: '失败原因', dataIndex: 'failure_reason', key: 'failure_reason', ellipsis: true, width: 150, render: (v: string) => v || '-' },
  ];

  return (
    <div>
      <Typography.Title level={4}>日志审计</Typography.Title>
      <Tabs activeKey={tab} onChange={k => { setTab(k); setPage(1); }} items={[
        { key: 'operations', label: '操作日志' },
        { key: 'logins', label: '登录日志' },
      ]} />
      {tab === 'operations' && (
        <Space wrap style={{ marginBottom: 16 }}>
          <Select placeholder="模块" allowClear style={{ width: 140 }} value={filters.module || undefined} onChange={v => setFilters(f => ({ ...f, module: v || '' }))}
            options={[
              { value: 'platform_school', label: '学校管理' }, { value: 'auth', label: '认证管理' },
              { value: 'student', label: '学生管理' }, { value: 'teacher', label: '教师管理' },
              { value: 'ai_analysis', label: 'AI研判' }, { value: 'sms', label: '短信管理' },
              { value: 'platform_supervision', label: '监管督办' }, { value: 'system', label: '系统设置' },
              { value: 'intervention', label: '干预管理' }, { value: 'report', label: '报告管理' },
              { value: 'questionnaire', label: '问卷管理' }, { value: 'questionnaire_task', label: '任务管理' },
              { value: 'task', label: '任务' }, { value: 'risk', label: '风险预警' },
              { value: 'risk_alert', label: '风险预警' }, { value: 'class', label: '班级管理' },
              { value: 'export', label: '导出' }, { value: 'task_supervision', label: '任务监管' },
            ]} />
          <Select placeholder="角色" allowClear style={{ width: 120 }} value={filters.operator_role || undefined} onChange={v => setFilters(f => ({ ...f, operator_role: v || '' }))}
            options={Object.entries(roleLabels).map(([k, v]) => ({ value: k, label: v }))} />
          <Input.Search placeholder="搜索" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchOps} />
        </Space>
      )}
      {tab === 'logins' && (
        <Space wrap style={{ marginBottom: 16 }}>
          <Select placeholder="角色" allowClear style={{ width: 120 }} value={loginFilters.user_role || undefined} onChange={v => setLoginFilters(f => ({ ...f, user_role: v || '' }))}
            options={Object.entries(roleLabels).map(([k, v]) => ({ value: k, label: v }))} />
          <Select placeholder="结果" allowClear style={{ width: 100 }} value={loginFilters.result || undefined} onChange={v => setLoginFilters(f => ({ ...f, result: v || '' }))}
            options={[{ value: 'success', label: '成功' }, { value: 'failure', label: '失败' }]} />
          <Input.Search placeholder="搜索用户名" style={{ width: 180 }} value={loginFilters.keyword} onChange={e => setLoginFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchLogins} />
        </Space>
      )}
      <Table rowKey="id" dataSource={data} columns={tab === 'operations' ? opColumns : loginColumns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />
    </div>
  );
}
