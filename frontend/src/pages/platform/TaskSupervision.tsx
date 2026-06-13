import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Typography, Space, Drawer, Descriptions, Card, Spin, Button, Empty, Progress, Row, Col, Statistic, Popconfirm, Modal, DatePicker, Form, Input, message, Tabs, Collapse, List } from 'antd';
import { ExportOutlined, EyeOutlined, CloseCircleOutlined, FieldTimeOutlined, EditOutlined, DeleteOutlined, MessageOutlined, FileTextOutlined, CopyOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import client from '../../api/client';
import { TASK_STATUS_LABELS } from '../../utils/constants';

const statusLabels = TASK_STATUS_LABELS;
const statusColors: Record<string, string> = { draft: 'default', pending: 'blue', not_started: 'blue', active: 'green', in_progress: 'green', ended: 'red', closed: 'default', archived: 'default' };

export default function PlatformTaskSupervision() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: '', school_id: '' as string | number });
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 延期相关状态
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendTask, setExtendTask] = useState<any>(null);
  const [extendForm] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // 编辑相关状态
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTask, setEditTask] = useState<any>(null);
  const [editForm] = Form.useForm();

  // 发布任务相关状态
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [createClasses, setCreateClasses] = useState<any[]>([]);
  const [createQuestionnaires, setCreateQuestionnaires] = useState<any[]>([]);
  const [createSchoolId, setCreateSchoolId] = useState<number | null>(null);

  // 问卷预览相关状态
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // 短信发送中状态
  const [smsSending, setSmsSending] = useState(false);
  const [sortField, setSortField] = useState('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | undefined>(undefined);

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.status) params.status = filters.status;
      if (filters.school_id) params.school_id = filters.school_id;
      if (sortField) { params.sort_by = sortField; params.sort_order = sortOrder === 'ascend' ? 'asc' : 'desc'; }
      const r = await client.get('/platform/tasks', { params });
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters, sortField, sortOrder]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewDetail = async (record: any) => {
    setDetailLoading(true); setDetailOpen(true); setDetail(null);
    try {
      const r = await client.get(`/platform/tasks/${record.id}`);
      setDetail(r.data.data);
    } catch { setDetail(null); }
    finally { setDetailLoading(false); }
  };

  const exportCSV = () => {
    const header = '任务名称,学校,问卷,状态,开始时间,截止时间\n';
    const rows = data.map((r: any) =>
      `${r.name},${r.school_name},${r.questionnaire_title || '-'},${statusLabels[r.status] || '未知'},${r.start_time || '-'},${r.end_time || '-'}`
    ).join('\n');
    const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `任务监管_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  // 关闭任务
  const handleClose = async (task: any) => {
    try {
      await client.post(`/platform/tasks/${task.id}/close`);
      message.success('任务已关闭');
      fetchData();
    } catch {
      message.error('操作失败');
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
      await client.post(`/platform/tasks/${extendTask.id}/extend`, {
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

  // 打开编辑弹窗
  const openEdit = (task: any) => {
    setEditTask(task);
    editForm.setFieldsValue({
      name: task.name,
      description: task.description,
      start_time: task.start_time ? dayjs(task.start_time) : null,
      end_time: task.end_time ? dayjs(task.end_time) : null,
    });
    setEditModalOpen(true);
  };

  // 提交编辑
  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields();
      setSubmitting(true);
      await client.put(`/platform/tasks/${editTask.id}`, {
        name: values.name,
        description: values.description,
        start_time: values.start_time?.toISOString() || null,
        end_time: values.end_time?.toISOString() || null,
      });
      message.success('编辑成功');
      setEditModalOpen(false);
      setEditTask(null);
      editForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.message || '编辑失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 发布任务 - 学校变更时加载班级和问卷
  const handleCreateSchoolChange = async (schoolId: number) => {
    setCreateSchoolId(schoolId);
    createForm.setFieldsValue({ target_ids: undefined, questionnaire_id: undefined });
    setCreateClasses([]);
    setCreateQuestionnaires([]);
    if (!schoolId) return;
    try {
      const [classRes, qRes] = await Promise.all([
        client.get(`/platform/schools/${schoolId}/classes`),
        client.get('/platform/questionnaires', { params: { page: 1, page_size: 200, status: 'active' } }),
      ]);
      setCreateClasses(classRes.data.data || []);
      setCreateQuestionnaires((qRes.data.data?.items || []).filter((q: any) => q.status === 'active'));
    } catch { message.error('加载班级或问卷失败'); }
  };

  // 发布任务 - 提交
  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      setSubmitting(true);
      const timeRange = values.time_range;
      await client.post('/platform/tasks', {
        school_id: values.school_id,
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
      setCreateModalOpen(false);
      createForm.resetFields();
      setCreateSchoolId(null);
      setCreateClasses([]);
      setCreateQuestionnaires([]);
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail || '发布失败');
    } finally { setSubmitting(false); }
  };

  // 归档任务
  const handleArchive = async (task: any) => {
    try {
      await client.post(`/platform/tasks/${task.id}/archive`);
      message.success('任务已归档');
      fetchData();
    } catch {
      message.error('操作失败');
    }
  };

  // 复制任务
  const handleDuplicate = async (task: any) => {
    try {
      await client.post(`/tasks/${task.id}/duplicate`);
      message.success('任务复制成功');
      fetchData();
    } catch (err: any) { message.error(err?.response?.data?.detail || '复制失败'); }
  };

  // 删除任务
  const handleDelete = async (task: any) => {
    try {
      await client.delete(`/platform/tasks/${task.id}`);
      message.success('任务已删除');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.message || '删除失败');
    }
  };

  // 发送未完成提醒短信
  const handleSendReminderSms = (task: any) => {
    Modal.confirm({
      title: '发送提醒短信',
      content: `确定要向任务「${task.name}」的所有未完成学生发送提醒短信吗？`,
      okText: '确定发送',
      cancelText: '取消',
      onOk: async () => {
        setSmsSending(true);
        try {
          const r = await client.post('/platform/sms/send', {
            type: 'batch_uncompleted',
            task_id: task.id,
          });
          const data = r.data.data;
          message.success(data?.message || '短信发送完成');
        } catch (err: any) {
          message.error(err?.response?.data?.detail || '短信发送失败');
        } finally {
          setSmsSending(false);
        }
      },
    });
  };

  // 预览问卷
  const handlePreviewQuestionnaire = async (questionnaireId: number) => {
    setPreviewOpen(true);
    setPreviewLoading(true);
    setPreviewData(null);
    try {
      const r = await client.get(`/platform/questionnaires/${questionnaireId}`);
      setPreviewData(r.data.data);
    } catch {
      message.error('加载问卷失败');
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name', width: 200, sorter: true, render: (v: string, r: any) => <a onClick={() => viewDetail(r)}>{v}</a> },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 120, sorter: true },
    { title: '问卷', dataIndex: 'questionnaire_title', key: 'questionnaire_title', width: 160, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, sorter: true, render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || '未知'}</Tag> },
    { title: '完成进度', key: 'progress', width: 140, render: (_: any, r: any) => {
      const exp = r.expected_count || 0, comp = r.completed_count || 0;
      return exp > 0 ? <span>{comp}/{exp} <Progress percent={Math.round(comp / exp * 100)} size="small" style={{ width: 60, display: 'inline-block', marginLeft: 4 }} /></span> : <span>-</span>;
    }},
    { title: '开始时间', dataIndex: 'start_time', key: 'start_time', width: 110, sorter: true, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '截止时间', dataIndex: 'end_time', key: 'end_time', width: 110, sorter: true, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
    { title: '操作', key: 'action', width: 280, render: (_: any, r: any) => (
      <Space size="small" wrap>
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewDetail(r)}>详情</Button>
        {(r.status === 'draft' || r.status === 'not_started') && (
          <Button size="small" type="link" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
        )}
        {(r.status === 'active' || r.status === 'in_progress' || r.status === 'not_started') && (
          <Popconfirm title="确定关闭此任务？" description="关闭后学生将无法提交答卷" onConfirm={() => handleClose(r)}>
            <Button size="small" type="link" danger icon={<CloseCircleOutlined />}>关闭</Button>
          </Popconfirm>
        )}
        {(r.status === 'active' || r.status === 'in_progress' || r.status === 'not_started') && (
          <Button size="small" type="link" icon={<FieldTimeOutlined />} onClick={() => openExtend(r)}>延期</Button>
        )}
        {r.status === 'closed' && (
          <Popconfirm title="确定归档此任务？" onConfirm={() => handleArchive(r)}>
            <Button size="small" type="link">归档</Button>
          </Popconfirm>
        )}
        <Button size="small" type="link" icon={<CopyOutlined />} onClick={() => handleDuplicate(r)}>复制</Button>
        {(r.status === 'draft' || r.status === 'archived') && (
          <Popconfirm title="确定删除此任务？" description="删除后不可恢复" onConfirm={() => handleDelete(r)}>
            <Button size="small" type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        )}
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>测评任务监管</Typography.Title>
        <Space>
          <Button type="primary" onClick={() => setCreateModalOpen(true)}>发布任务</Button>
          <Button icon={<ExportOutlined />} onClick={exportCSV} disabled={!data.length}>导出 CSV</Button>
        </Space>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="学校" allowClear style={{ width: 180 }} value={filters.school_id || undefined}
          onChange={v => setFilters(f => ({ ...f, school_id: v || '' }))} options={schools} showSearch optionFilterProp="label" />
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined}
          onChange={v => setFilters(f => ({ ...f, status: v || '' }))} options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 个任务` }}
        onChange={(_pagination, _filters, sorter: any) => {
          if (sorter.field) { setSortField(sorter.field); setSortOrder(sorter.order); }
        }} />

      <Drawer title="任务详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={640} style={{ maxWidth: '95vw' }} destroyOnHidden>
        {detailLoading ? <Spin /> : detail ? (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="任务名称" span={2}>{detail.name}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school_name}</Descriptions.Item>
              <Descriptions.Item label="问卷">
                {detail.questionnaire_title || '-'}
                {detail.questionnaire_id && (
                  <Button size="small" type="link" icon={<FileTextOutlined />} style={{ marginLeft: 8 }}
                    onClick={() => handlePreviewQuestionnaire(detail.questionnaire_id)}>预览问卷</Button>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColors[detail.status]}>{statusLabels[detail.status] || '未知'}</Tag></Descriptions.Item>
              <Descriptions.Item label="目标类型">{detail.target_type === 'all' ? '全校' : detail.target_type === 'grade' ? '年级' : detail.target_type === 'class' ? '班级' : '个人'}</Descriptions.Item>
              <Descriptions.Item label="开始时间">{detail.start_time ? new Date(detail.start_time).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="截止时间">{detail.end_time ? new Date(detail.end_time).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              {detail.description && <Descriptions.Item label="说明" span={2}>{detail.description}</Descriptions.Item>}
            </Descriptions>

            <Card title="完成情况" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16} style={{ marginBottom: 12 }}>
                <Col span={8}><Statistic title="目标学生" value={detail.total_students} /></Col>
                <Col span={8}><Statistic title="已提交" value={detail.submitted} valueStyle={{ color: '#3f8600' }} /></Col>
                <Col span={8}><Statistic title="完成率" value={detail.completion_rate} suffix="%" valueStyle={{ color: detail.completion_rate >= 80 ? '#3f8600' : '#cf1322' }} /></Col>
              </Row>
              <Progress percent={detail.completion_rate} strokeColor={detail.completion_rate >= 80 ? '#52c41a' : detail.completion_rate >= 50 ? '#faad14' : '#ff4d4f'} />
            </Card>

            {detail.student_details?.length > 0 && (() => {
              const allStudents = detail.student_details as any[];
              const classStats = detail.class_stats as any[] || [];
              const completed = allStudents.filter((s: any) => s.status === 'submitted');
              const uncompleted = allStudents.filter((s: any) => s.status !== 'submitted');
              const studentColumns = [
                { title: '学生', dataIndex: 'student_name' },
                { title: '班级', dataIndex: 'class_name', width: 100 },
                { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => v === 'submitted' ? <Tag color="green">已提交</Tag> : v === 'in_progress' ? <Tag color="blue">答题中</Tag> : <Tag>未开始</Tag> },
                { title: '提交时间', dataIndex: 'submitted_at', width: 150, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                { title: '操作', key: 'action', width: 80, render: (_: any, r: any) => r.status === 'submitted' ? (
                  <Popconfirm title="确定打回此答卷？" description="打回后学生需重新作答" onConfirm={async () => {
                    try {
                      await client.post(`/platform/tasks/${detail.id}/recall`, { student_id: r.student_id });
                      message.success('已打回');
                      viewDetail({ id: detail.id });
                    } catch (err: any) { message.error(err?.response?.data?.detail || '操作失败'); }
                  }}><Button size="small" type="link" danger>打回</Button></Popconfirm>
                ) : null },
              ];
              return (
                <Tabs defaultActiveKey="class" items={[
                  { key: 'class', label: `按班级 (${classStats.length})`, children: (
                    <Collapse accordion>
                      {classStats.map((cs: any) => (
                        <Collapse.Panel key={cs.class_name} header={
                          <span>{cs.class_name} <Tag>{cs.grade_name}</Tag> {cs.submitted}/{cs.total} <Progress percent={cs.rate} size="small" style={{ width: 80, display: 'inline-block', marginLeft: 8 }} /></span>
                        }>
                          <Table rowKey="student_id" dataSource={allStudents.filter((s: any) => s.class_name === cs.class_name)} pagination={false} size="small" columns={studentColumns.filter(c => c.dataIndex !== 'class_name')} />
                        </Collapse.Panel>
                      ))}
                    </Collapse>
                  )},
                  { key: 'completed', label: `已完成 (${completed.length})`, children: (
                    <Table rowKey="student_id" dataSource={completed} pagination={false} size="small" columns={studentColumns} />
                  )},
                  { key: 'uncompleted', label: `未完成 (${uncompleted.length})`, children: (
                    <div>
                      {uncompleted.length > 0 && (
                        <div style={{ marginBottom: 12 }}>
                          <Button type="primary" icon={<MessageOutlined />} loading={smsSending}
                            onClick={() => handleSendReminderSms(detail)}>
                            发送提醒短信
                          </Button>
                        </div>
                      )}
                      <Table rowKey="student_id" dataSource={uncompleted} pagination={false} size="small" columns={studentColumns} />
                    </div>
                  )},
                ]} />
              );
            })()}
          </div>
        ) : <Empty description="加载失败" />}
      </Drawer>

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

      {/* 编辑弹窗 */}
      <Modal
        title={`编辑 - ${editTask?.name || ''}`}
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
            <Input placeholder="请输入任务名称" />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} placeholder="请输入任务说明" />
          </Form.Item>
          <Form.Item name="start_time" label="开始时间">
            <DatePicker showTime style={{ width: '100%' }} placeholder="选择开始时间" />
          </Form.Item>
          <Form.Item name="end_time" label="截止时间">
            <DatePicker showTime style={{ width: '100%' }} placeholder="选择截止时间" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 发布任务弹窗 */}
      <Modal
        title="发布测评任务"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); setCreateSchoolId(null); setCreateClasses([]); setCreateQuestionnaires([]); }}
        confirmLoading={submitting}
        destroyOnClose
        width={600}
        style={{ maxWidth: '95vw' }}
        okText="发布"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="school_id" label="选择学校" rules={[{ required: true, message: '请选择学校' }]}>
            <Select
              placeholder="先选择学校"
              options={schools}
              showSearch
              optionFilterProp="label"
              onChange={handleCreateSchoolChange}
            />
          </Form.Item>
          <Form.Item name="questionnaire_id" label="选择问卷" rules={[{ required: true, message: '请选择问卷' }]}>
            <Select
              placeholder={createSchoolId ? '请选择问卷' : '请先选择学校'}
              disabled={!createSchoolId}
              options={createQuestionnaires.map((q: any) => ({ value: q.id, label: q.title }))}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="target_ids" label="发布班级" rules={[{ required: true, message: '请选择班级' }]}>
            <Select
              mode="multiple"
              placeholder={createSchoolId ? '请选择班级' : '请先选择学校'}
              disabled={!createSchoolId}
              options={createClasses.map((c: any) => ({ value: c.id, label: c.grade_name ? `${c.grade_name} ${c.name}` : c.name }))}
            />
          </Form.Item>
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
            <Input placeholder="如：初一年级心理健康筛查" />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} placeholder="填写给学生查看的任务说明，可留空" />
          </Form.Item>
          <Form.Item name="time_range" label="起止时间">
            <DatePicker.RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="allow_edit" label="允许提交后修改" valuePropName="checked">
            <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} defaultValue={false} />
          </Form.Item>
          <Space wrap>
            <Form.Item name="shuffle_questions" label="题目随机" valuePropName="checked" initialValue={true}>
              <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} defaultValue={true} />
            </Form.Item>
            <Form.Item name="shuffle_options" label="选项随机" valuePropName="checked" initialValue={true}>
              <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} defaultValue={true} />
            </Form.Item>
            <Form.Item name="enable_quality_check" label="质量检测" valuePropName="checked" initialValue={true}>
              <Select options={[{ value: true, label: '开' }, { value: false, label: '关' }]} defaultValue={true} />
            </Form.Item>
          </Space>
          <Form.Item name="reminder_strategy" label="提醒策略" initialValue="none">
            <Select
              options={[
                { value: 'none', label: '不自动提醒' },
                { value: 'deadline_24h', label: '截止前 24 小时提醒' },
                { value: 'deadline_2h', label: '截止前 2 小时提醒' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 问卷预览弹窗 */}
      <Modal
        title={`问卷预览 - ${previewData?.title || ''}`}
        open={previewOpen}
        onCancel={() => { setPreviewOpen(false); setPreviewData(null); }}
        footer={null}
        width={700}
        style={{ maxWidth: '95vw' }}
        destroyOnHidden
      >
        {previewLoading ? <Spin style={{ display: 'block', margin: '40px auto' }} /> : previewData ? (
          <div>
            {previewData.category && <Tag color="blue" style={{ marginBottom: 12 }}>{previewData.category}</Tag>}
            {previewData.description && <Typography.Paragraph type="secondary">{previewData.description}</Typography.Paragraph>}
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              共 {previewData.questions?.length || 0} 题
            </Typography.Text>
            <List
              dataSource={previewData.questions || []}
              renderItem={(q: any, idx: number) => (
                <List.Item style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                  <div style={{ width: '100%' }}>
                    <Space align="start" style={{ marginBottom: 4 }}>
                      <Typography.Text strong>{idx + 1}. {q.title}</Typography.Text>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        [{q.type === 'single' ? '单选' : q.type === 'multiple' ? '多选' : q.type === 'text' ? '文本' : q.type === 'score' ? '评分' : q.type}]
                      </Typography.Text>
                    </Space>
                    {q.description && <Typography.Paragraph type="secondary" style={{ margin: '2px 0 6px', fontSize: 12 }}>{q.description}</Typography.Paragraph>}
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 4 }}>
                      {q.dimension && <Typography.Text type="secondary" style={{ fontSize: 12 }}>维度: {q.dimension}</Typography.Text>}
                      {q.risk_tag && <Tag color="red" style={{ fontSize: 11 }}>{q.risk_tag}</Tag>}
                      {q.is_reverse && <Tag style={{ fontSize: 11 }}>反向题</Tag>}
                    </div>
                    {q.options?.length > 0 && (
                      <div style={{ marginTop: 6 }}>
                        {q.options.map((opt: any) => (
                          <div key={opt.id} style={{ padding: '2px 0', color: opt.is_risk_option ? '#ff4d4f' : undefined }}>
                            {opt.content} {opt.score != null && <Typography.Text type="secondary" style={{ fontSize: 12 }}>({opt.score}分)</Typography.Text>}
                            {opt.is_risk_option && <Tag color="red" style={{ fontSize: 10, marginLeft: 4 }}>风险选项</Tag>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </List.Item>
              )}
            />
          </div>
        ) : <Empty description="加载失败" />}
      </Modal>
    </div>
  );
}
