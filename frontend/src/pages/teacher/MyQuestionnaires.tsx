import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, Input, Typography, message } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { copyQuestionnaire, getQuestionnaires, type QuestionnaireInfo } from '../../api/questionnaires';

const categoryLabels: Record<string, string> = {
  mental_health: '心理健康筛查', bullying: '校园欺凌排查', internet_addiction: '网络沉迷评估',
  family_relationship: '家庭关系调查', safety_awareness: '安全意识测评', interpersonal: '人际关系测评',
  academic_pressure: '学业压力测评', custom: '综合',
};
const sourceTypeLabels: Record<string, string> = {
  standard_like: '参考标准结构',
  school_custom: '本校自建',
  reference_screening: '参考性筛查',
};

export default function MyQuestionnaires() {
  const navigate = useNavigate();
  const [data, setData] = useState<QuestionnaireInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');

  useEffect(() => {
    setLoading(true);
    getQuestionnaires({ page, page_size: 20, keyword }).then(r => {
      setData(r.items); setTotal(r.total);
    }).finally(() => setLoading(false));
  }, [page, keyword]);

  const handleCopy = async (id: number) => {
    await copyQuestionnaire(id);
    message.success('复制成功');
    const refreshed = await getQuestionnaires({ page, page_size: 20, keyword });
    setData(refreshed.items);
    setTotal(refreshed.total);
  };

  const columns = [
    { title: '问卷标题', dataIndex: 'title', render: (v: string, r: QuestionnaireInfo) => <a onClick={() => navigate(`/teacher/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '分类', dataIndex: 'category', render: (v: string) => <Tag>{categoryLabels[v] || v}</Tag> },
    { title: '题目数', dataIndex: 'question_count' },
    { title: '适用年级', dataIndex: 'applicable_grades', render: (v: string) => v || '-' },
    {
      title: '来源',
      key: 'source_type',
      render: (_: unknown, r: QuestionnaireInfo) => (
        <Space size={4} wrap>
          {r.is_builtin ? <Tag color="blue">内置问卷</Tag> : <Tag>自建问卷</Tag>}
          <Tag>{sourceTypeLabels[r.source_type] || r.source_type}</Tag>
        </Space>
      ),
    },
    { title: '状态', dataIndex: 'status', render: (v: string) => {
      const m: Record<string, any> = { draft: { color: 'default', label: '草稿' }, active: { color: 'green', label: '启用' }, inactive: { color: 'red', label: '停用' } };
      return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
    }},
    {
      title: '操作',
      render: (_: unknown, r: QuestionnaireInfo) => (
        <Space>
          <Button size="small" icon={r.is_builtin ? <EyeOutlined /> : <EditOutlined />} onClick={() => navigate(`/teacher/questionnaires/${r.id}/edit`)}>
            {r.is_builtin ? '预览' : '编辑'}
          </Button>
          <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(r.id)}>复制</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Typography.Title level={4}>我的问卷</Typography.Title>
        <Space>
          <Input.Search placeholder="搜索" value={keyword} onChange={e => setKeyword(e.target.value)} onSearch={() => setPage(1)} style={{ width: '100%', maxWidth: 200 }} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/teacher/questionnaires/new')}>新建问卷</Button>
        </Space>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
    </div>
  );
}
