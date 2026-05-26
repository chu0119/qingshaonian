import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Modal, Form, Input, Select, Switch, message, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import StudentSelect from '../../components/common/StudentSelect';
import client from '../../api/client';

const methodLabels: Record<string, string> = {
  student_talk: '学生谈话', teacher_communication: '班主任沟通', counselor_guidance: '心理老师辅导',
  family_school: '家校沟通', home_visit: '家访', referral: '转介专业机构', observation: '持续观察', other: '其他',
};
const statusLabels: Record<string, string> = {
  pending: '待处理', viewed: '已查看', processing: '处理中', ongoing: '持续跟进', completed: '已完成', closed: '已关闭',
};

export default function InterventionRecords() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const r = await client.get('/interventions', { params: { page, page_size: 20 } });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取干预记录列表失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await client.post('/interventions', values);
      message.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return; // 表单验证错误，不做提示
      message.error(err?.response?.data?.message || '创建干预记录失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name' },
    { title: '干预方式', dataIndex: 'method', key: 'method', render: (v: string) => methodLabels[v] || v },
    { title: '干预内容', dataIndex: 'content', key: 'content', render: (v: string) => v ? v.substring(0, 30) + (v.length > 30 ? '...' : '') : '-' },
    { title: '干预时间', dataIndex: 'intervention_time', key: 'intervention_time', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '持续跟进', dataIndex: 'need_follow_up', key: 'need_follow_up', render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>干预记录</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新增干预记录</Button>
      </div>
      <Table
        rowKey="id"
        dataSource={data}
        columns={columns}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }}
      />

      <Modal
        title="新增干预记录"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        confirmLoading={submitting}
        destroyOnHidden
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="student_id" label="选择学生" rules={[{ required: true, message: '请选择学生' }]}>
            <StudentSelect placeholder="输入姓名或学号搜索学生" />
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
    </div>
  );
}
