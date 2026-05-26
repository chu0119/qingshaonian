import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, Input, Select, Typography } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

const categoryLabels: Record<string, string> = {
  mental_health: '心理健康筛查', bullying: '校园欺凌排查', internet_addiction: '网络沉迷评估',
  family_relationship: '家庭关系调查', safety_awareness: '安全意识测评', interpersonal: '人际关系测评',
  academic_pressure: '学业压力测评', custom: '综合',
};

export default function MyQuestionnaires() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');

  useEffect(() => {
    setLoading(true);
    client.get('/questionnaires', { params: { page, page_size: 20, keyword } }).then(r => {
      setData(r.data.data.items); setTotal(r.data.data.total);
    }).finally(() => setLoading(false));
  }, [page, keyword]);

  const columns = [
    { title: '问卷标题', dataIndex: 'title', render: (v: string, r: any) => <a onClick={() => navigate(`/teacher/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '分类', dataIndex: 'category', render: (v: string) => <Tag>{categoryLabels[v] || v}</Tag> },
    { title: '题目数', dataIndex: 'question_count' },
    { title: '状态', dataIndex: 'status', render: (v: string) => {
      const m: Record<string, any> = { draft: { color: 'default', label: '草稿' }, active: { color: 'green', label: '启用' }, inactive: { color: 'red', label: '停用' } };
      return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
    }},
    { title: '操作', render: (_: any, r: any) => <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/teacher/questionnaires/${r.id}/edit`)}>编辑</Button> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>我的问卷</Typography.Title>
        <Space>
          <Input.Search placeholder="搜索" value={keyword} onChange={e => setKeyword(e.target.value)} onSearch={() => setPage(1)} style={{ width: 200 }} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/teacher/questionnaires/new')}>新建问卷</Button>
        </Space>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  );
}
