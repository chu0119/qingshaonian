import { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, Input, Typography, message } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { copyQuestionnaire, getQuestionnaires, type QuestionnaireInfo } from '../../api/questionnaires';
import { QUESTIONNAIRE_CATEGORY_LABELS, SOURCE_TYPE_LABELS, QUESTIONNAIRE_STATUS_LABELS } from '../../utils/constants';

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
      setData(r.items || []); setTotal(r.total || 0);
    }).catch(() => message.error('获取问卷列表失败')).finally(() => setLoading(false));
  }, [page, keyword]);

  const handleCopy = async (id: number) => {
    try {
      await copyQuestionnaire(id);
      message.success('复制成功');
      const refreshed = await getQuestionnaires({ page, page_size: 20, keyword });
      setData(refreshed.items || []);
      setTotal(refreshed.total || 0);
    } catch {
      message.error('复制失败');
    }
  };

  const columns = [
    { title: '问卷标题', dataIndex: 'title', render: (v: string, r: QuestionnaireInfo) => <a onClick={() => navigate(`/teacher/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '分类', dataIndex: 'category', render: (v: string) => <Tag>{QUESTIONNAIRE_CATEGORY_LABELS[v] || '未知'}</Tag> },
    { title: '题目数', dataIndex: 'question_count' },
    { title: '适用年级', dataIndex: 'applicable_grades', render: (v: string) => v || '-' },
    {
      title: '来源',
      key: 'source_type',
      render: (_: unknown, r: QuestionnaireInfo) => (
        <Space size={4} wrap>
          {r.is_builtin ? <Tag color="blue">内置问卷</Tag> : <Tag>自建问卷</Tag>}
          <Tag>{SOURCE_TYPE_LABELS[r.source_type] || '未知'}</Tag>
        </Space>
      ),
    },
    { title: '状态', dataIndex: 'status', render: (v: string) => {
      const m: Record<string, any> = { draft: { color: 'default', label: QUESTIONNAIRE_STATUS_LABELS.draft }, active: { color: 'green', label: QUESTIONNAIRE_STATUS_LABELS.active }, inactive: { color: 'red', label: QUESTIONNAIRE_STATUS_LABELS.inactive } };
      return <Tag color={m[v]?.color}>{m[v]?.label || '未知'}</Tag>;
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
