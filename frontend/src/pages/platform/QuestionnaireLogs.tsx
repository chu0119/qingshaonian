import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, DatePicker, Button, Drawer, message, Empty } from 'antd';
import { EyeOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, QUALITY_LABELS, VALIDITY_LABELS } from '../../utils/constants';
import AnswerDetail from '../../components/answer/AnswerDetail';

const { RangePicker } = DatePicker;

const statusLabels: Record<string, string> = { submitted: '已提交', in_progress: '进行中' };

function formatDuration(seconds: number) {
  if (!seconds) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins > 0) return `${mins}分${secs}秒`;
  return `${secs}秒`;
}

export default function QuestionnaireLogs() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [grades, setGrades] = useState<{ value: number; label: string }[]>([]);
  const [classes, setClasses] = useState<{ value: number; label: string }[]>([]);
  const [tasks, setTasks] = useState<{ value: number; label: string }[]>([]);
  const [filters, setFilters] = useState({
    school_id: '' as string | number,
    grade_id: '' as string | number,
    class_id: '' as string | number,
    task_id: '' as string | number,
    status: '' as string,
    risk_level: '' as string,
    keyword: '',
    dateRange: null as any,
  });
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailSheetId, setDetailSheetId] = useState<number>();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [sortField, setSortField] = useState('risk_level');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | undefined>('descend');

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  // Load grades and tasks when school changes
  useEffect(() => {
    if (!filters.school_id) { setGrades([]); setClasses([]); setTasks([]); return; }
    client.get('/platform/grades', { params: { school_id: filters.school_id } })
      .then(r => setGrades((r.data.data || []).map((g: any) => ({ value: g.id, label: g.name }))))
      .catch(() => setGrades([]));
    client.get('/platform/tasks', { params: { page: 1, page_size: 200, school_id: filters.school_id } })
      .then(r => setTasks((r.data.data?.items || []).map((t: any) => ({ value: t.id, label: t.name }))))
      .catch(() => {});
    setClasses([]);
    setFilters(f => ({ ...f, grade_id: '', class_id: '' }));
  }, [filters.school_id]);

  // Load classes when grade changes
  useEffect(() => {
    if (!filters.grade_id) { setClasses([]); return; }
    client.get('/platform/classes', { params: { grade_id: filters.grade_id } })
      .then(r => setClasses((r.data.data || []).map((c: any) => ({ value: c.id, label: c.name }))))
      .catch(() => setClasses([]));
    setFilters(f => ({ ...f, class_id: '' }));
  }, [filters.grade_id]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: 20 };
      if (filters.school_id) params.school_id = filters.school_id;
      if (filters.grade_id) params.grade_id = filters.grade_id;
      if (filters.class_id) params.class_id = filters.class_id;
      if (filters.task_id) params.task_id = filters.task_id;
      if (filters.status) params.status = filters.status;
      if (filters.risk_level) params.risk_level = filters.risk_level;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.dateRange && filters.dateRange[0]) params.start_date = filters.dateRange[0].format('YYYY-MM-DD');
      if (filters.dateRange && filters.dateRange[1]) params.end_date = filters.dateRange[1].format('YYYY-MM-DD');
      if (sortField) { params.sort_by = sortField; params.sort_order = sortOrder === 'ascend' ? 'asc' : 'desc'; }
      const r = await client.get('/platform/answer-logs', { params });
      setData(r.data.data?.items || []);
      setTotal(r.data.data?.total || 0);
    } catch {
      message.error('获取问卷日志失败');
    } finally { setLoading(false); }
  }, [page, filters, sortField, sortOrder]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // 自动刷新：30秒轮询
  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      fetchData();
      setLastRefresh(new Date());
    }, 30000);
    return () => clearInterval(timer);
  }, [autoRefresh, fetchData]);

  const updateFilter = (patch: Partial<typeof filters>) => {
    setFilters(f => ({ ...f, ...patch }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({ school_id: '', grade_id: '', class_id: '', task_id: '', status: '', risk_level: '', keyword: '', dateRange: null });
    setPage(1);
  };

  const hasFilter = filters.school_id || filters.grade_id || filters.class_id || filters.task_id || filters.status || filters.risk_level || filters.keyword || filters.dateRange;

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name', width: 80, ellipsis: true, sorter: true },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120, ellipsis: true },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 60 },
    { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 60 },
    { title: '任务', dataIndex: 'task_name', key: 'task_name', width: 120, ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 70,
      render: (v: string) => <Tag color={v === 'submitted' ? 'green' : 'processing'}>{statusLabels[v] || v}</Tag> },
    { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', width: 140, sorter: true,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-' },
    { title: '用时', dataIndex: 'total_duration_seconds', key: 'total_duration_seconds', width: 70, sorter: true,
      render: (v: number) => formatDuration(v) },
    { title: '总分', dataIndex: 'total_score', key: 'total_score', width: 60, align: 'center' as const, sorter: true,
      render: (v: number | null) => v != null ? v.toFixed(1) : '-' },
    { title: '风险', dataIndex: 'risk_level', key: 'risk_level', width: 60, sorter: true,
      render: (v: string | null) => v ? <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> : '-' },
    { title: '质量', dataIndex: 'quality_level', key: 'quality_level', width: 70, sorter: true,
      render: (v: string | null) => v ? <Tag>{QUALITY_LABELS[v] || v}</Tag> : '-' },
    { title: '操作', key: 'action', width: 60, fixed: 'right' as const,
      render: (_: any, r: any) => <Button size="small" type="link" icon={<EyeOutlined />}
        onClick={() => { setDetailSheetId(r.id); setDetailOpen(true); }}>详情</Button> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>问卷日志</Typography.Title>
        <Space>
          <span style={{ fontSize: 12, color: autoRefresh ? '#52c41a' : '#999' }}>
            {autoRefresh ? '● 自动刷新中' : '○ 自动刷新已关闭'}
            {lastRefresh && <span style={{ marginLeft: 6, color: '#999' }}>{lastRefresh.toLocaleTimeString('zh-CN')}</span>}
          </span>
          <Button size="small" onClick={() => setAutoRefresh(v => !v)}>
            {autoRefresh ? '暂停刷新' : '开启刷新'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchData(); setLastRefresh(new Date()); }}>刷新</Button>
          {hasFilter && <Button icon={<ReloadOutlined />} onClick={resetFilters}>重置</Button>}
        </Space>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 160 }} value={filters.school_id || undefined}
          onChange={v => updateFilter({ school_id: v || '' })} options={schools} showSearch optionFilterProp="label" />
        <Select placeholder="年级" allowClear style={{ width: 100 }} value={filters.grade_id || undefined}
          onChange={v => updateFilter({ grade_id: v || '' })} options={grades} disabled={!filters.school_id} />
        <Select placeholder="班级" allowClear style={{ width: 100 }} value={filters.class_id || undefined}
          onChange={v => updateFilter({ class_id: v || '' })} options={classes} disabled={!filters.grade_id} />
        <Select placeholder="任务" allowClear style={{ width: 160 }} value={filters.task_id || undefined}
          onChange={v => updateFilter({ task_id: v || '' })} options={tasks} showSearch optionFilterProp="label" />
        <Select placeholder="状态" allowClear style={{ width: 100 }} value={filters.status || undefined}
          onChange={v => updateFilter({ status: v || '' })}
          options={[{ value: 'submitted', label: '已提交' }, { value: 'in_progress', label: '进行中' }]} />
        <Select placeholder="风险等级" allowClear style={{ width: 100 }} value={filters.risk_level || undefined}
          onChange={v => updateFilter({ risk_level: v || '' })}
          options={Object.entries(RISK_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <RangePicker style={{ width: 240 }} value={filters.dateRange}
          onChange={(dates) => updateFilter({ dateRange: dates })} />
        <Input.Search placeholder="搜索学生姓名" style={{ width: 150 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))}
          onSearch={() => { setPage(1); fetchData(); }}
          enterButton={<><SearchOutlined /> 搜索</>} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 1200 }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }}
        onChange={(_pagination, _filters, sorter: any) => {
          if (sorter.field) {
            setSortField(sorter.field);
            setSortOrder(sorter.order);
          }
        }} />

      <Drawer title="答题详情" open={detailOpen} onClose={() => setDetailOpen(false)}
        width={Math.min(window.innerWidth - 40, 1000)} destroyOnClose>
        <AnswerDetail answerSheetId={detailSheetId} platformMode open={detailOpen} onClose={() => setDetailOpen(false)} />
      </Drawer>
    </div>
  );
}
