import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Table, Tag, Button, Modal, Form, Input, Select, Switch, Space, Drawer, Descriptions, message, Typography } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import StudentSelect from '../../components/common/StudentSelect';
import client from '../../api/client';
import { METHOD_LABELS, INTERVENTION_STATUS_LABELS } from '../../utils/constants';

const methodLabels = METHOD_LABELS;
const statusLabels = INTERVENTION_STATUS_LABELS;

export default function InterventionRecords() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRecord, setDetailRecord] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const [searchParams, setSearchParams] = useSearchParams();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (statusFilter) params.status = statusFilter;
      const r = await client.get('/interventions', { params });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取干预记录列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const studentId = Number(searchParams.get('student_id'));
    const riskAlertId = Number(searchParams.get('risk_alert_id'));
    if (!studentId) return;
    form.setFieldsValue({ student_id: studentId, risk_alert_id: riskAlertId || undefined, method: 'student_talk', status: 'processing' });
    setModalOpen(true);
  }, [form, searchParams]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingRecord) {
        await client.put(`/interventions/${editingRecord.id}`, values);
        message.success('更新成功');
      } else {
        await client.post('/interventions', values);
        message.success('创建成功');
      }
      setModalOpen(false);
      setEditingRecord(null);
      setSearchParams({});
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.message || '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  const openEdit = (record: any) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const openDetail = (record: any) => {
    setDetailRecord(record);
    setDetailOpen(true);
  };

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name' },
    { title: '干预方式', dataIndex: 'method', key: 'method', render: (v: string) => methodLabels[v] || v },
    { title: '干预内容', dataIndex: 'content', key: 'content', render: (v: string) => v ? v.substring(0, 30) + (v.length > 30 ? '...' : '') : '-' },
    { title: '干预时间', dataIndex: 'intervention_time', key: 'intervention_time', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '持续跟进', dataIndex: 'need_follow_up', key: 'need_follow_up', render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
    { title: '操作', key: 'action', width: 150, render: (_: unknown, r: any) => (
      <Space>
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(r)}>详情</Button>
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Typography.Title level={4}>干预记录</Typography.Title>
        <Space>
          <Select
            placeholder="处理状态"
            allowClear
            style={{ width: 130 }}
            value={statusFilter || undefined}
            onChange={v => { setStatusFilter(v || ''); setPage(1); }}
            options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); form.resetFields(); setModalOpen(true); }}>新增干预记录</Button>
        </Space>
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
        title={editingRecord ? '编辑干预记录' : '新增干预记录'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); setEditingRecord(null); setSearchParams({}); form.resetFields(); }}
        confirmLoading={submitting}
        destroyOnHidden
        width={600}
        style={{ maxWidth: '95vw' }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="student_id" label="选择学生" rules={[{ required: true, message: '请选择学生' }]}>
            <StudentSelect placeholder="输入姓名或学号搜索学生" />
          </Form.Item>
          <Form.Item name="risk_alert_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="method" label="干预方式" rules={[{ required: true, message: '请选择干预方式' }]} initialValue="student_talk">
            <Select options={Object.entries(methodLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="content" label="干预内容">
            <Input.TextArea rows={3} placeholder="请输入干预内容" />
          </Form.Item>
          <Form.Item name="result" label="干预结果">
            <Input.TextArea rows={2} placeholder="请输入干预结果" />
          </Form.Item>
          <Form.Item name="follow_up_suggestion" label="后续建议">
            <Input.TextArea rows={2} placeholder="请输入后续建议" />
          </Form.Item>
          <Form.Item name="need_follow_up" label="需持续跟进" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="status" label="处理状态" initialValue="processing">
            <Select options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="干预记录详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={520}>
        {detailRecord && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="学生姓名">{detailRecord.student_name}</Descriptions.Item>
            <Descriptions.Item label="干预方式">{methodLabels[detailRecord.method] || detailRecord.method}</Descriptions.Item>
            <Descriptions.Item label="干预内容">{detailRecord.content || '-'}</Descriptions.Item>
            <Descriptions.Item label="干预结果">{detailRecord.result || '-'}</Descriptions.Item>
            <Descriptions.Item label="后续建议">{detailRecord.follow_up_suggestion || '-'}</Descriptions.Item>
            <Descriptions.Item label="处理状态"><Tag>{statusLabels[detailRecord.status] || detailRecord.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="持续跟进">{detailRecord.need_follow_up ? <Tag color="orange">是</Tag> : <Tag>否</Tag>}</Descriptions.Item>
            <Descriptions.Item label="干预时间">{detailRecord.intervention_time ? new Date(detailRecord.intervention_time).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
}
