import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Tag, Modal, Form, Input, DatePicker, Switch, message, Typography, Space, Row, Col, Statistic, Tabs, Select, Progress, Empty } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import client from '../../api/client';

const statusLabels: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  active: { color: 'green', label: '进行中' },
  in_progress: { color: 'green', label: '进行中' },
  not_started: { color: 'cyan', label: '未开始' },
  ended: { color: 'orange', label: '已截止' },
  closed: { color: 'red', label: '已关闭' },
  archived: { color: 'purple', label: '已归档' },
};

export default function TaskManagement() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [completions, setCompletions] = useState<any[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [classes, setClasses] = useState<any[]>([]);
  const [questionnaires, setQuestionnaires] = useState<any[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionErrors, setOptionErrors] = useState<{ classes?: string; questionnaires?: string }>({});
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const r = await client.get('/tasks', { params: { page, page_size: 20 } });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const fetchPublishOptions = useCallback(async () => {
    setOptionsLoading(true);
    const [classRes, qRes] = await Promise.allSettled([
      client.get('/classes', { params: { page: 1, page_size: 200 } }),
      client.get('/questionnaires', { params: { page: 1, page_size: 100 } }),
    ]);
    const errors: { classes?: string; questionnaires?: string } = {};
    if (classRes.status === 'fulfilled') setClasses(classRes.value.data.data?.items || []);
    else { setClasses([]); errors.classes = '班级加载失败，请重试'; }
    if (qRes.status === 'fulfilled') setQuestionnaires(qRes.value.data.data?.items || qRes.value.data.data || []);
    else { setQuestionnaires([]); errors.questionnaires = '问卷加载失败，请重试'; }
    setOptionErrors(errors);
    if (errors.classes || errors.questionnaires) message.error('发布任务所需数据加载失败');
    setOptionsLoading(false);
  }, []);

  useEffect(() => { fetchPublishOptions(); }, [fetchPublishOptions]);

  const handlePublish = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const timeRange = values.time_range;
      await client.post('/tasks', {
        name: values.name,
        questionnaire_id: values.questionnaire_id,
        target_type: 'class',
        target_ids: values.target_ids || [],
        description: values.description || '',
        start_time: timeRange?.[0]?.toISOString(),
        end_time: timeRange?.[1]?.toISOString(),
        allow_edit: values.allow_edit || false,
        shuffle_questions: values.shuffle_questions || false,
        shuffle_options: values.shuffle_options || false,
        enable_quality_check: values.enable_quality_check !== false,
        reminder_strategy: values.reminder_strategy ? { type: values.reminder_strategy } : {},
      });
      message.success('任务发布成功');
      setModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return; // 表单验证错误，不做提示
      message.error(err?.response?.data?.message || '发布任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  const publishBlockedReason = optionErrors.questionnaires || optionErrors.classes || (!optionsLoading && questionnaires.length === 0 ? '暂无可发布问卷' : '') || (!optionsLoading && classes.length === 0 ? '暂无可发布班级' : '');

  const viewDetail = async (task: any) => {
    setSelectedTask(task);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const r = await client.get(`/tasks/${task.id}/completion`);
      setCompletions(r.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取完成情况失败');
      setCompletions([]);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', render: (v: string, r: any) => <a onClick={() => viewDetail(r)}>{v}</a> },
    { title: '问卷名称', dataIndex: 'questionnaire_title', key: 'questionnaire_title' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusLabels[v]?.color}>{statusLabels[v]?.label || v}</Tag> },
    {
      title: '完成情况',
      key: 'completion',
      width: 170,
      render: (_: any, r: any) => (
        <div>
          <span>{r.completed_count || 0} / {r.expected_count || 0}</span>
          <Progress percent={r.completion_rate || 0} size="small" showInfo={false} />
        </div>
      ),
    },
    { title: '题目随机', dataIndex: 'shuffle_questions', key: 'shuffle_questions', render: (v: boolean) => v ? <Tag color="blue">是</Tag> : <Tag>否</Tag> },
    { title: '质量检测', dataIndex: 'enable_quality_check', key: 'enable_quality_check', render: (v: boolean) => v !== false ? <Tag color="green">开</Tag> : <Tag>关</Tag> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
  ];

  const uncompleted = completions.filter(c => c.status !== 'submitted');
  const completed = completions.filter(c => c.status === 'submitted');

  const detailTabItems = [
    {
      key: 'completed',
      label: `已完成 (${completed.length})`,
      children: (
        <Table
          rowKey="student_id"
          dataSource={completed}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="暂无已完成学生" /> }}
          columns={[
            { title: '学生', dataIndex: 'student_name', key: 'student_name' },
            { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
          ]}
        />
      ),
    },
    {
      key: 'uncompleted',
      label: `未完成 (${uncompleted.length})`,
      children: (
        <Table
          rowKey="student_id"
          dataSource={uncompleted}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="暂无未完成学生" /> }}
          columns={[
            { title: '学生', dataIndex: 'student_name', key: 'student_name' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => v === 'in_progress' ? <Tag color="blue">答题中</Tag> : <Tag>未开始</Tag> },
          ]}
        />
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>问卷任务管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>发布新任务</Button>
      </div>
      <Table
        rowKey="id"
        dataSource={data}
        columns={columns}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }}
      />

      <Modal
        title="发布问卷任务"
        open={modalOpen}
        onOk={handlePublish}
        okButtonProps={{ disabled: !!publishBlockedReason }}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        confirmLoading={submitting}
        destroyOnHidden
        width={560}
        style={{ maxWidth: '95vw' }}
      >
        <Form form={form} layout="vertical">
          {publishBlockedReason && (
            <Button size="small" onClick={fetchPublishOptions} loading={optionsLoading} style={{ marginBottom: 12 }}>
              {publishBlockedReason}，点击重试
            </Button>
          )}
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="如：初一年级心理健康筛查" />
          </Form.Item>
          <Form.Item name="questionnaire_id" label="选择问卷" rules={[{ required: true, message: '请选择问卷' }]}>
            <Select
              loading={optionsLoading}
              placeholder={optionErrors.questionnaires || (questionnaires.length ? '请选择问卷' : '暂无可发布问卷')}
              disabled={!!optionErrors.questionnaires || questionnaires.length === 0}
              showSearch
              optionFilterProp="label"
              options={questionnaires.map((q) => ({ value: q.id, label: q.title || q.name }))}
            />
          </Form.Item>
          <Form.Item name="target_ids" label="发布班级" rules={[{ required: true, message: '请选择发布班级' }]}>
            <Select
              mode="multiple"
              loading={optionsLoading}
              placeholder={optionErrors.classes || (classes.length ? '请选择班级' : '暂无可发布班级')}
              disabled={!!optionErrors.classes || classes.length === 0}
              options={classes.map((c) => ({ value: c.id, label: c.grade_name ? `${c.grade_name} ${c.name}` : c.name }))}
            />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} placeholder="填写给学生查看的任务说明，可留空" />
          </Form.Item>
          <Form.Item name="time_range" label="起止时间">
            <DatePicker.RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="allow_edit" label="允许提交后修改" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Space wrap>
            <Form.Item name="shuffle_questions" label="题目随机" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="shuffle_options" label="选项随机" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="enable_quality_check" label="质量检测" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="reminder_strategy" label="提醒策略" initialValue="none">
            <Select
              options={[
                { value: 'none', label: '不自动提醒' },
                { value: 'deadline_24h', label: '截止前 24 小时提醒未完成学生' },
                { value: 'deadline_2h', label: '截止前 2 小时提醒未完成学生' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`任务详情 - ${selectedTask?.name || ''}`}
        open={detailOpen}
        onCancel={() => { setDetailOpen(false); setCompletions([]); }}
        destroyOnHidden
        width={800}
        style={{ maxWidth: '95vw' }}
        footer={null}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={12} md={6}><Statistic title="已提交" value={completed.length} valueStyle={{ color: '#67C23A' }} loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="未完成" value={uncompleted.length} valueStyle={{ color: '#FF4D4F' }} loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="完成率" value={completions.length > 0 ? Math.round(completed.length / completions.length * 100) : 0} suffix="%" loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="总人数" value={completions.length} loading={detailLoading} /></Col>
        </Row>
        <Tabs items={detailTabItems} />
      </Modal>
    </div>
  );
}
