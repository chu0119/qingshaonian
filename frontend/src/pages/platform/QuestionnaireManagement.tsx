import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Select, Input, Typography, Space, Button, Drawer, Descriptions, Card, Modal, message, Row, Col, Statistic, Empty, Spin } from 'antd';
import { CopyOutlined, DeleteOutlined, EyeOutlined, PlusOutlined, EditOutlined, SendOutlined, FileTextOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { QUESTIONNAIRE_STATUS_LABELS, QUESTIONNAIRE_CATEGORY_LABELS, QUESTION_TYPE_LABELS, SOURCE_TYPE_LABELS, DIMENSION_LABELS } from '../../utils/constants';

export default function PlatformQuestionnaireManagement() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ category: '', status: '', keyword: '', source_type: '' });
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [usageOpen, setUsageOpen] = useState(false);
  const [usage, setUsage] = useState<any>(null);
  const [pushOpen, setPushOpen] = useState(false);
  const [pushQid, setPushQid] = useState<number>();
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [selectedSchools, setSelectedSchools] = useState<number[]>([]);
  const [pushLoading, setPushLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [stats, setStats] = useState({ total: 0, builtin: 0, platform: 0, school: 0 });

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.category) params.category = filters.category;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.source_type) params.source_type = filters.source_type;
      const r = await client.get('/platform/questionnaires', { params });
      const items = r.data.data?.items || [];
      setData(items);
      setTotal(r.data.data?.total || 0);
      setStats({
        total: r.data.data?.total || 0,
        builtin: items.filter((i: any) => i.is_builtin).length,
        platform: items.filter((i: any) => !i.is_builtin && !i.school_id).length,
        school: items.filter((i: any) => i.school_id).length,
      });
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewDetail = async (qid: number) => {
    setDetailLoading(true); setDetailOpen(true); setDetail(null);
    try {
      const r = await client.get(`/platform/questionnaires/${qid}`);
      setDetail(r.data.data);
    } catch { setDetail(null); }
    finally { setDetailLoading(false); }
  };

  const viewUsage = async (qid: number) => {
    try {
      const r = await client.get(`/platform/questionnaires/${qid}/usage`);
      setUsage(r.data.data);
      setUsageOpen(true);
    } catch { message.error('获取使用统计失败'); }
  };

  const handleCopy = async (qid: number) => {
    try {
      const r = await client.post(`/platform/questionnaires/${qid}/copy`);
      message.success(r.data.message || '复制成功');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '复制失败');
    }
  };

  const handleDelete = async (qid: number) => {
    try {
      await client.delete(`/platform/questionnaires/${qid}`);
      message.success('删除成功');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  const handlePush = async () => {
    if (!selectedSchools.length) { message.warning('请选择目标学校'); return; }
    setPushLoading(true);
    try {
      const r = await client.post(`/platform/questionnaires/${pushQid}/push`, { school_ids: selectedSchools });
      message.success(r.data.message || '推送成功');
      setPushOpen(false);
      setSelectedSchools([]);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '推送失败');
    } finally { setPushLoading(false); }
  };

  const handleCreate = async () => {
    setCreateOpen(false);
    message.info('问卷已创建，请在学校端编辑题目');
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', width: 200, ellipsis: true,
      render: (v: string, r: any) => <a onClick={() => viewDetail(r.id)}>{v}</a> },
    { title: '类别', dataIndex: 'category', key: 'category', width: 90,
      render: (v: string) => <Tag>{QUESTIONNAIRE_CATEGORY_LABELS[v] || v || '-'}</Tag> },
    { title: '来源', key: 'source', width: 100,
      render: (_: any, r: any) => {
        if (r.is_builtin) return <Tag color="blue">内置</Tag>;
        if (r.school_id) return <Tag color="green">学校</Tag>;
        return <Tag color="orange">平台</Tag>;
      },
    },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count', width: 70, align: 'center' as const },
    { title: '使用次数', dataIndex: 'task_count', key: 'task_count', width: 80, align: 'center' as const },
    { title: '答卷数', dataIndex: 'answer_count', key: 'answer_count', width: 70, align: 'center' as const },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={v === 'published' ? 'green' : v === 'draft' ? 'default' : 'blue'}>{QUESTIONNAIRE_STATUS_LABELS[v] || v}</Tag> },
    { title: '操作', key: 'action', width: 260, render: (_: any, r: any) => (
      <Space>
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewDetail(r.id)}>详情</Button>
        <Button size="small" type="link" onClick={() => viewUsage(r.id)}>统计</Button>
        {!r.is_builtin && <Button size="small" type="link" icon={<EditOutlined />} onClick={() => navigate(`/platform/questionnaires/${r.id}/edit`)}>编辑</Button>}
        {!r.is_builtin && <Button size="small" type="link" icon={<CopyOutlined />} onClick={() => handleCopy(r.id)}>复制</Button>}
        <Button size="small" type="link" icon={<SendOutlined />} onClick={() => { setPushQid(r.id); setPushOpen(true); }}>推送</Button>
        {!r.is_builtin && r.status === 'draft' && (
          <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => Modal.confirm({
            title: '确定删除？', content: '删除后不可恢复', onOk: () => handleDelete(r.id),
          })}>删除</Button>
        )}
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>问卷管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/platform/questionnaires/new')}>新建问卷</Button>
      </div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="问卷总数" value={stats.total} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="内置问卷" value={stats.builtin} valueStyle={{ color: '#1890FF' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="平台问卷" value={stats.platform} valueStyle={{ color: '#FA8C16' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="学校问卷" value={stats.school} valueStyle={{ color: '#52C41A' }} /></Card></Col>
      </Row>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="类别" allowClear style={{ width: 130 }} value={filters.category || undefined}
          onChange={v => setFilters(f => ({ ...f, category: v || '' }))}
          options={Object.entries(QUESTIONNAIRE_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Select placeholder="来源" allowClear style={{ width: 130 }} value={filters.source_type || undefined}
          onChange={v => setFilters(f => ({ ...f, source_type: v || '' }))}
          options={Object.entries(SOURCE_TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索问卷标题" style={{ width: 200 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 套问卷` }} />

      <Drawer title="问卷详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={720} destroyOnClose>
        {detailLoading ? <Spin /> : detail ? (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="标题" span={2}>{detail.title}</Descriptions.Item>
              <Descriptions.Item label="类别">{QUESTIONNAIRE_CATEGORY_LABELS[detail.category] || detail.category || '-'}</Descriptions.Item>
              <Descriptions.Item label="来源">{detail.is_builtin ? '内置' : detail.school_id ? '学校' : '平台'}</Descriptions.Item>
              <Descriptions.Item label="状态">{QUESTIONNAIRE_STATUS_LABELS[detail.status] || detail.status}</Descriptions.Item>
              <Descriptions.Item label="题目数">{detail.questions?.length || 0}</Descriptions.Item>
              <Descriptions.Item label="说明" span={2}>{detail.description || '-'}</Descriptions.Item>
              {detail.applicable_grades && <Descriptions.Item label="适用年级" span={2}>{detail.applicable_grades}</Descriptions.Item>}
            </Descriptions>

            {detail.questions?.length ? (
              <Card title={`题目列表 (${detail.questions.length} 题)`} size="small">
                <Table rowKey="id" dataSource={detail.questions} pagination={false} size="small" scroll={{ y: 500 }}
                  columns={[
                    { title: '序号', width: 50, render: (_: any, __: any, i: number) => i + 1 },
                    { title: '题目', dataIndex: 'title', ellipsis: true },
                    { title: '类型', dataIndex: 'type', width: 80, render: (v: string) => QUESTION_TYPE_LABELS[v] || v },
                    { title: '维度', dataIndex: 'dimension', width: 80, render: (v: string) => DIMENSION_LABELS[v] || v || '-' },
                    { title: '选项数', width: 60, render: (_: any, r: any) => r.options?.length || 0 },
                  ]}
                />
              </Card>
            ) : null}
          </div>
        ) : <Empty />}
      </Drawer>

      <Modal title="使用统计" open={usageOpen} onCancel={() => setUsageOpen(false)} footer={null} width={500} destroyOnClose>
        {usage ? (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}><Statistic title="关联任务" value={usage.task_count} /></Col>
              <Col span={8}><Statistic title="答卷数" value={usage.answer_count} /></Col>
              <Col span={8}><Statistic title="已提交" value={usage.submitted} /></Col>
            </Row>
            {usage.copies > 0 && <p>已推送到 {usage.copies} 所学校的副本</p>}
            {usage.schools?.length ? (
              <Card title="使用学校" size="small">
                {usage.schools.map((s: any) => <Tag key={s.id}>{s.name}</Tag>)}
              </Card>
            ) : <Empty description="暂无学校使用" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </div>
        ) : null}
      </Modal>

      <Modal title="推送到学校" open={pushOpen} onCancel={() => { setPushOpen(false); setSelectedSchools([]); }}
        onOk={handlePush} confirmLoading={pushLoading} destroyOnClose width={500} okText="推送" cancelText="取消">
        <p style={{ marginBottom: 12 }}>选择要推送此问卷的学校（已推送的学校不会重复推送）</p>
        <Select mode="multiple" placeholder="选择学校" style={{ width: '100%' }}
          value={selectedSchools} onChange={setSelectedSchools}
          options={schools} showSearch optionFilterProp="label" />
      </Modal>
    </div>
  );
}
