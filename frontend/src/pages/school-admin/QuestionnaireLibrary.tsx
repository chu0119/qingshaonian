import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Space, Tag, message, Popconfirm, Input, Select, Card } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined, EyeOutlined } from '@ant-design/icons';
import { getQuestionnaires, deleteQuestionnaire, copyQuestionnaire, updateQuestionnaire, type QuestionnaireInfo } from '../../api/questionnaires';

const categoryLabels: Record<string, string> = {
  mental_health: '心理健康筛查', bullying: '校园欺凌排查', internet_addiction: '网络沉迷评估',
  family_relationship: '家庭关系调查', safety_awareness: '安全意识测评', interpersonal: '人际关系测评',
  academic_pressure: '学业压力测评', custom: '综合',
};

export default function QuestionnaireLibrary() {
  const navigate = useNavigate();
  const [data, setData] = useState<QuestionnaireInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ category: '', status: '', keyword: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.category) params.category = filters.category;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      const res = await getQuestionnaires(params);
      setData(res.items);
      setTotal(res.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDelete = async (id: number) => { await deleteQuestionnaire(id); message.success('删除成功'); fetchData(); };
  const handleCopy = async (id: number) => { await copyQuestionnaire(id); message.success('复制成功'); fetchData(); };
  const handleToggleStatus = async (record: QuestionnaireInfo) => {
    const newStatus = record.status === 'active' ? 'inactive' : 'active';
    await updateQuestionnaire(record.id, { status: newStatus });
    message.success(newStatus === 'active' ? '已启用' : '已停用');
    fetchData();
  };

  const columns = [
    { title: '问卷标题', dataIndex: 'title', key: 'title', width: 260, render: (v: string, r: QuestionnaireInfo) => <a onClick={() => navigate(`/school-admin/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '分类', dataIndex: 'category', key: 'category', render: (v: string) => <Tag>{categoryLabels[v] || v}</Tag> },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count' },
    { title: '类型', dataIndex: 'is_builtin', key: 'is_builtin', render: (v: boolean) => v ? <Tag color="blue">内置</Tag> : <Tag>自定义</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const m: Record<string, { color: string; label: string }> = { draft: { color: 'default', label: '草稿' }, active: { color: 'green', label: '启用' }, inactive: { color: 'red', label: '停用' } };
      return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
    }},
    { title: '操作', key: 'action', width: 280, render: (_: unknown, r: QuestionnaireInfo) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/school-admin/questionnaires/${r.id}/edit`)}>编辑</Button>
          <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(r.id)}>复制</Button>
          <Button size="small" onClick={() => handleToggleStatus(r)}>{r.status === 'active' ? '停用' : '启用'}</Button>
          {r.status === 'draft' && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Select placeholder="分类" allowClear style={{ width: 140 }} value={filters.category || undefined} onChange={v => setFilters(f => ({ ...f, category: v || '' }))}
            options={Object.entries(categoryLabels).map(([k, v]) => ({ value: k, label: v }))} />
          <Select placeholder="状态" allowClear style={{ width: 100 }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
            options={[{ value: 'draft', label: '草稿' }, { value: 'active', label: '启用' }, { value: 'inactive', label: '停用' }]} />
          <Input.Search placeholder="搜索" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/school-admin/questionnaires/new')}>新建问卷</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />
    </div>
  );
}
