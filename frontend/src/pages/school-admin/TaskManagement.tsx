import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Tag, Modal, Form, Input, DatePicker, Switch, message, Typography, Space, Row, Col, Statistic, Tabs, Select, Progress, Empty, Popconfirm, Descriptions, List } from 'antd';
import { PlusOutlined, EditOutlined, FieldTimeOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import client from '../../api/client';
import { TASK_STATUS_LABELS } from '../../utils/constants';

const statusLabels: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: TASK_STATUS_LABELS.draft },
  active: { color: 'green', label: TASK_STATUS_LABELS.active },
  in_progress: { color: 'green', label: TASK_STATUS_LABELS.in_progress },
  not_started: { color: 'cyan', label: TASK_STATUS_LABELS.not_started },
  ended: { color: 'orange', label: TASK_STATUS_LABELS.ended },
  closed: { color: 'red', label: TASK_STATUS_LABELS.closed },
  archived: { color: 'purple', label: TASK_STATUS_LABELS.archived },
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

  // 编辑任务相关状态
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTask, setEditTask] = useState<any>(null);
  const [editForm] = Form.useForm();

  // 延期相关状态
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendTask, setExtendTask] = useState<any>(null);
  const [extendForm] = Form.useForm();

  // 预览问卷相关状态
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewQuestions, setPreviewQuestions] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

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
        shuffle_questions: values.shuffle_questions !== false,
        shuffle_options: values.shuffle_options !== false,
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

  // 打开编辑弹窗
  const openEdit = (task: any) => {
    setEditTask(task);
    editForm.setFieldsValue({
      name: task.name,
      description: task.description,
      time_range: task.start_time && task.end_time ? [dayjs(task.start_time), dayjs(task.end_time)] : undefined,
    });
    setEditModalOpen(true);
  };

  // 提交编辑
  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields();
      setSubmitting(true);
      const timeRange = values.time_range;
      await client.put(`/tasks/${editTask.id}`, {
        name: values.name,
        description: values.description || '',
        start_time: timeRange?.[0]?.toISOString(),
        end_time: timeRange?.[1]?.toISOString(),
      });
      message.success('任务更新成功');
      setEditModalOpen(false);
      setEditTask(null);
      editForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.message || '更新任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 打开延期弹窗
  const openExtend = (task: any) => {
    setExtendTask(task);
    extendForm.resetFields();
    if (task.end_time) {
      extendForm.setFieldsValue({ new_end_time: dayjs(task.end_time) });
    }
    setExtendModalOpen(true);
  };

  // 提交延期
  const handleExtend = async () => {
    try {
      const values = await extendForm.validateFields();
      setSubmitting(true);
      await client.post(`/tasks/${extendTask.id}/extend`, {
        end_time: values.new_end_time.toISOString(),
      });
      message.success('延期成功');
      setExtendModalOpen(false);
      setExtendTask(null);
      extendForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.message || '延期失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 预览问卷
  const previewQuestionnaire = async (task: any) => {
    setPreviewModalOpen(true);
    setPreviewLoading(true);
    try {
      const r = await client.get(`/questionnaires/${task.questionnaire_id}`);
      setPreviewQuestions(r.data.data?.questions || []);
    } catch {
      message.error('加载问卷预览失败');
      setPreviewQuestions([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', render: (v: string, r: any) => <a onClick={() => viewDetail(r)}>{v}</a> },
    { title: '问卷名称', dataIndex: 'questionnaire_title', key: 'questionnaire_title' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusLabels[v]?.color}>{statusLabels[v]?.label || '未知'}</Tag> },
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
    {
      title: '操作', key: 'actions', width: 340,
      render: (_: any, r: any) => (
        <Space size="small" wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => previewQuestionnaire(r)}>预览</Button>
          {(r.status === 'draft' || r.status === 'not_started') && (
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          )}
          {(r.status === 'active' || r.status === 'in_progress' || r.status === 'not_started') && (
            <Button size="small" icon={<FieldTimeOutlined />} onClick={() => openExtend(r)}>延期</Button>
          )}
          {r.status === 'active' && (
            <Popconfirm title="确定关闭此任务？" description="关闭后学生将无法提交答卷" onConfirm={async () => {
              try { await client.post(`/tasks/${r.id}/close`); message.success('任务已关闭'); fetchData(); }
              catch { message.error('操作失败'); }
            }}><Button size="small" danger>关闭</Button></Popconfirm>
          )}
          {r.status === 'closed' && (
            <Popconfirm title="确定归档此任务？" onConfirm={async () => {
              try { await client.post(`/tasks/${r.id}/archive`); message.success('任务已归档'); fetchData(); }
              catch { message.error('操作失败'); }
            }}><Button size="small">归档</Button></Popconfirm>
          )}
          {(r.status === 'draft' || r.status === 'archived') && (
            <Popconfirm title="确定删除此任务？" description="删除后不可恢复" onConfirm={async () => {
              try { await client.delete(`/tasks/${r.id}`); message.success('任务已删除'); fetchData(); }
              catch (err: any) { message.error(err?.response?.data?.detail || '删除失败'); }
            }}><Button size="small" danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const uncompleted = completions.filter(c => c.status !== 'submitted');
  const completed = completions.filter(c => c.status === 'submitted');
  const completionRate = completions.length > 0 ? Math.round(completed.length / completions.length * 100) : 0;

  // 按班级分组统计
  const classGroups: Record<string, { total: number; completed: number; students: any[] }> = {};
  completions.forEach((c: any) => {
    const cls = c.class_name || '未分班';
    if (!classGroups[cls]) classGroups[cls] = { total: 0, completed: 0, students: [] };
    classGroups[cls].total++;
    if (c.status === 'submitted') classGroups[cls].completed++;
    classGroups[cls].students.push(c);
  });

  const handleSendReminder = async () => {
    if (!selectedTask || uncompleted.length === 0) return;
    try {
      await client.post('/sms/send', {
        type: 'batch_unfinished',
        task_id: selectedTask.id,
      });
      message.success(`已向 ${uncompleted.length} 名未完成学生发送提醒短信`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '发送提醒失败');
    }
  };

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
            { title: '操作', key: 'action', width: 80, render: (_: any, r: any) => (
              <Popconfirm title="确定打回此答卷？" description="打回后学生需重新作答" onConfirm={async () => {
                try {
                  await client.post(`/tasks/${selectedTask?.id}/recall`, { student_id: r.student_id });
                  message.success('已打回');
                  viewDetail(selectedTask);
                  fetchData();
                } catch (err: any) { message.error(err?.response?.data?.detail || '操作失败'); }
              }}><Button size="small" type="link" danger>打回</Button></Popconfirm>
            )},
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
        scroll={{ x: 'max-content' }}
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
            <Form.Item name="shuffle_questions" label="题目随机" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
            <Form.Item name="shuffle_options" label="选项随机" valuePropName="checked" initialValue={true}>
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
        <Row gutter={[16, 16]} style={{ marginBottom: 12 }}>
          <Col xs={12} sm={12} md={6}><Statistic title="已提交" value={completed.length} valueStyle={{ color: '#67C23A' }} loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="未完成" value={uncompleted.length} valueStyle={{ color: '#FF4D4F' }} loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="完成率" value={completionRate} suffix="%" loading={detailLoading} /></Col>
          <Col xs={12} sm={12} md={6}><Statistic title="总人数" value={completions.length} loading={detailLoading} /></Col>
        </Row>
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>整体进度</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>{completed.length}/{completions.length}</Typography.Text>
          </div>
          <Progress percent={completionRate} strokeColor={completionRate >= 80 ? '#52c41a' : completionRate >= 50 ? '#faad14' : '#ff4d4f'} />
        </div>
        {uncompleted.length > 0 && (
          <div style={{ marginBottom: 12, textAlign: 'right' }}>
            <Button size="small" type="primary" onClick={handleSendReminder}>
              发送提醒短信 ({uncompleted.length}人)
            </Button>
          </div>
        )}
        <Tabs items={[
          {
            key: 'progress',
            label: '班级进度',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                {Object.entries(classGroups).map(([cls, data]) => (
                  <div key={cls} style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Typography.Text strong>{cls}</Typography.Text>
                      <Typography.Text type="secondary">{data.completed}/{data.total} ({data.total > 0 ? Math.round(data.completed / data.total * 100) : 0}%)</Typography.Text>
                    </div>
                    <Progress percent={data.total > 0 ? Math.round(data.completed / data.total * 100) : 0} size="small"
                      strokeColor={data.completed === data.total ? '#52c41a' : '#1677ff'} />
                  </div>
                ))}
              </Space>
            ),
          },
          ...detailTabItems,
        ]} />
      </Modal>

      {/* 编辑任务弹窗 */}
      <Modal
        title="编辑任务"
        open={editModalOpen}
        onOk={handleEdit}
        onCancel={() => { setEditModalOpen(false); setEditTask(null); editForm.resetFields(); }}
        confirmLoading={submitting}
        destroyOnHidden
        width={500}
        style={{ maxWidth: '95vw' }}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="输入任务名称" />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} placeholder="填写任务说明" />
          </Form.Item>
          <Form.Item name="time_range" label="起止时间">
            <DatePicker.RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 延期弹窗 */}
      <Modal
        title={`延期 - ${extendTask?.name || ''}`}
        open={extendModalOpen}
        onOk={handleExtend}
        onCancel={() => { setExtendModalOpen(false); setExtendTask(null); extendForm.resetFields(); }}
        confirmLoading={submitting}
        destroyOnHidden
        width={400}
        style={{ maxWidth: '95vw' }}
      >
        <Form form={extendForm} layout="vertical">
          <Form.Item name="new_end_time" label="新截止时间" rules={[{ required: true, message: '请选择新的截止时间' }]}>
            <DatePicker showTime style={{ width: '100%' }} placeholder="选择新的截止时间" />
          </Form.Item>
          {extendTask?.end_time && (
            <div style={{ color: '#888', fontSize: 13 }}>
              当前截止时间：{new Date(extendTask.end_time).toLocaleString('zh-CN')}
            </div>
          )}
        </Form>
      </Modal>

      {/* 预览问卷弹窗 */}
      <Modal
        title="问卷题目预览"
        open={previewModalOpen}
        onCancel={() => { setPreviewModalOpen(false); setPreviewQuestions([]); }}
        footer={null}
        destroyOnHidden
        width={700}
        style={{ maxWidth: '95vw' }}
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : previewQuestions.length === 0 ? (
          <Empty description="暂无题目" />
        ) : (
          <List
            dataSource={previewQuestions}
            renderItem={(item: any, index: number) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <div style={{ fontWeight: 500, marginBottom: 8 }}>
                    {index + 1}. {item.title}
                    {item.required && <span style={{ color: 'red', marginLeft: 4 }}>*</span>}
                  </div>
                  {item.description && (
                    <div style={{ color: '#888', fontSize: 13, marginBottom: 8 }}>{item.description}</div>
                  )}
                  {item.options && item.options.length > 0 && (
                    <div style={{ paddingLeft: 16 }}>
                      {item.options.map((opt: any, optIdx: number) => (
                        <div key={optIdx} style={{ color: '#555', marginBottom: 4 }}>
                          {String.fromCharCode(65 + optIdx)}. {opt.content}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </List.Item>
            )}
          />
        )}
      </Modal>
    </div>
  );
}
