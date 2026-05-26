import { useState, useEffect } from 'react';
import { Card, Form, Select, Input, Button, DatePicker, Switch, message, Typography, Space, Tabs, Table, Tag, Modal, Empty, Spin, Progress } from 'antd';
import { SendOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function TeacherTasks() {
  const [form] = Form.useForm();
  const [publishLoading, setPublishLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('publish');

  // 任务列表相关 state
  const [taskList, setTaskList] = useState<any[]>([]);
  const [taskLoading, setTaskLoading] = useState(false);
  const [completionModalOpen, setCompletionModalOpen] = useState(false);
  const [completionData, setCompletionData] = useState<any[]>([]);
  const [completionLoading, setCompletionLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [classes, setClasses] = useState<any[]>([]);
  const [questionnaires, setQuestionnaires] = useState<any[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'tasks') {
      fetchTasks();
    }
  }, [activeTab]);

  useEffect(() => {
    fetchPublishOptions();
  }, []);

  const fetchPublishOptions = async () => {
    setOptionsLoading(true);
    try {
      const [classRes, qRes] = await Promise.all([
        client.get('/classes/my'),
        client.get('/questionnaires', { params: { page: 1, page_size: 100 } }),
      ]);
      setClasses(classRes.data.data || []);
      setQuestionnaires(qRes.data.data?.items || qRes.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取可发布范围失败');
    } finally {
      setOptionsLoading(false);
    }
  };

  const fetchTasks = async () => {
    setTaskLoading(true);
    try {
      const r = await client.get('/tasks');
      setTaskList(r.data.data?.items || r.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取任务列表失败');
    } finally {
      setTaskLoading(false);
    }
  };

  const handlePublish = async () => {
    const values = await form.validateFields();
    setPublishLoading(true);
    try {
      await client.post('/tasks', {
        name: values.name,
        questionnaire_id: values.questionnaire_id,
        target_type: 'class',
        target_ids: values.target_ids || [],
        description: values.description || '',
        start_time: values.time_range?.[0]?.toISOString(),
        end_time: values.time_range?.[1]?.toISOString(),
        allow_edit: values.allow_edit || false,
        shuffle_questions: values.shuffle_questions || false,
        shuffle_options: values.shuffle_options || false,
        enable_quality_check: values.enable_quality_check !== false,
        reminder_strategy: values.reminder_strategy ? { type: values.reminder_strategy } : {},
      });
      message.success('任务发布成功');
      form.resetFields();
      setActiveTab('tasks');
      fetchTasks();
    } catch (err: any) {
      message.error(err?.response?.data?.message || '发布失败');
    } finally {
      setPublishLoading(false);
    }
  };

  const handleViewCompletion = async (task: any) => {
    setSelectedTask(task);
    setCompletionModalOpen(true);
    setCompletionLoading(true);
    setCompletionData([]);
    try {
      const r = await client.get(`/tasks/${task.id}/completion`);
      setCompletionData(r.data.data?.items || r.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取完成情况失败');
    } finally {
      setCompletionLoading(false);
    }
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'active':
      case 'in_progress': return <Tag color="blue">进行中</Tag>;
      case 'not_started': return <Tag color="cyan">未开始</Tag>;
      case 'completed': return <Tag color="green">已完成</Tag>;
      case 'draft': return <Tag color="default">草稿</Tag>;
      case 'expired':
      case 'ended': return <Tag color="orange">已截止</Tag>;
      case 'closed': return <Tag color="red">已关闭</Tag>;
      case 'archived': return <Tag color="purple">已归档</Tag>;
      default: return <Tag>{status || '-'}</Tag>;
    }
  };

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string) => (
        <span><FileTextOutlined style={{ marginRight: 6, color: '#4A90D9' }} />{text}</span>
      ),
    },
    {
      title: '问卷',
      dataIndex: 'questionnaire_title',
      key: 'questionnaire_title',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '完成情况',
      key: 'completion',
      width: 180,
      render: (_: any, record: any) => {
        const expected = record.expected_count ?? record.total_count ?? record.target_count ?? 0;
        const completed = record.completed_count || 0;
        return (
          <div>
            <span>{completed} / {expected || '-'}</span>
            <Progress percent={record.completion_rate || 0} size="small" showInfo={false} />
          </div>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: any) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewCompletion(record)}
        >
          查看完成情况
        </Button>
      ),
    },
  ];

  const completionColumns = [
    {
      title: '学生姓名',
      dataIndex: 'student_name',
      key: 'student_name',
      render: (text: string, record: any) => text || record.real_name || '-',
    },
    {
      title: '完成状态',
      dataIndex: 'status',
      key: 'completed',
      width: 100,
      render: (status: string | boolean) => {
        const completed = status === 'submitted' || status === 'completed' || status === true;
        return (
        <Tag color={completed ? 'green' : 'default'}>{completed ? '已完成' : '未完成'}</Tag>
        );
      },
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 180,
      render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '答题用时',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (d: number) => {
        if (d === undefined || d === null) return '-';
        const mins = Math.floor(d / 60);
        const secs = d % 60;
        return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
      },
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>问卷任务</Typography.Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'publish',
          label: '发布任务',
          children: (
            <Card style={{ maxWidth: 600 }}>
              <Form form={form} layout="vertical">
                <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
                  <Input placeholder="如：初一年级心理健康筛查" />
                </Form.Item>
                <Form.Item name="questionnaire_id" label="选择问卷" rules={[{ required: true, message: '请选择问卷' }]}>
                  <Select
                    loading={optionsLoading}
                    placeholder="请选择可发布的问卷"
                    showSearch
                    optionFilterProp="label"
                    options={questionnaires.map((q) => ({ value: q.id, label: q.title || q.name }))}
                  />
                </Form.Item>
                <Form.Item name="target_ids" label="发布班级" rules={[{ required: true, message: '请选择发布班级' }]}>
                  <Select
                    mode="multiple"
                    loading={optionsLoading}
                    placeholder="请选择你负责的班级"
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
                <Form.Item name="shuffle_questions" label="题目顺序随机" valuePropName="checked">
                  <Switch />
                </Form.Item>
                <Form.Item name="shuffle_options" label="选项顺序随机" valuePropName="checked">
                  <Switch />
                </Form.Item>
                <Form.Item name="enable_quality_check" label="开启答题质量检测" valuePropName="checked" initialValue={true}>
                  <Switch />
                </Form.Item>
                <Form.Item name="reminder_strategy" label="提醒策略" initialValue="none">
                  <Select
                    options={[
                      { value: 'none', label: '不自动提醒' },
                      { value: 'deadline_24h', label: '截止前 24 小时提醒未完成学生' },
                      { value: 'deadline_2h', label: '截止前 2 小时提醒未完成学生' },
                    ]}
                  />
                </Form.Item>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handlePublish}
                  loading={publishLoading}
                  block
                >
                  发布任务
                </Button>
              </Form>
            </Card>
          ),
        },
        {
          key: 'tasks',
          label: '我的任务',
          children: (
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Typography.Text strong style={{ fontSize: 15 }}>任务列表</Typography.Text>
                <Button onClick={fetchTasks} size="small">刷新</Button>
              </div>
              <Table
                columns={taskColumns}
                dataSource={taskList}
                rowKey="id"
                loading={taskLoading}
                scroll={{ x: 'max-content' }}
                pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
                locale={{ emptyText: <Empty description="暂无任务" /> }}
              />
            </Card>
          ),
        },
      ]} />

      {/* 任务完成情况弹窗 */}
      <Modal
        title={`${selectedTask?.name || ''} - 完成情况`}
        open={completionModalOpen}
        onCancel={() => setCompletionModalOpen(false)}
        footer={null}
        width={700}
        style={{ maxWidth: '95vw' }}
        destroyOnClose
      >
        {completionLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>
        ) : (
          <Table
            columns={completionColumns}
            dataSource={completionData}
            rowKey={(record) => record.student_id || record.id}
            scroll={{ x: 'max-content' }}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
            locale={{ emptyText: <Empty description="暂无完成数据" /> }}
          />
        )}
      </Modal>
    </div>
  );
}
