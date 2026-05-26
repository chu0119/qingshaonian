import { useState, useEffect } from 'react';
import { Table, Tag, Button, Modal, Form, Input, Select, message, Typography, DatePicker, Switch } from 'antd';
import { useSearchParams } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import StudentSelect from '../../components/common/StudentSelect';
import client from '../../api/client';

const methodLabels: Record<string, string> = { student_talk: '学生谈话', teacher_communication: '班主任沟通', counselor_guidance: '心理老师辅导', family_school: '家校沟通', home_visit: '家访', referral: '转介专业机构', observation: '持续观察', other: '其他' };
const statusLabels: Record<string, string> = { pending: '待处理', processing: '处理中', follow_up: '持续跟进', ongoing: '持续跟进', completed: '已完成', closed: '已关闭' };

export default function TeacherInterventions() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = () => {
    setLoading(true);
    client.get('/interventions', { params: { page, page_size: 20 } }).then(r => {
      setData(r.data.data.items); setTotal(r.data.data.total);
    }).catch(() => {
      message.error('获取干预记录失败');
    }).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [page]);

  useEffect(() => {
    const studentId = searchParams.get('student_id');
    const riskAlertId = searchParams.get('risk_alert_id');
    if (studentId) {
      form.setFieldsValue({
        student_id: Number(studentId),
        risk_alert_id: riskAlertId ? Number(riskAlertId) : undefined,
        status: 'processing',
        need_follow_up: true,
      });
      setModalOpen(true);
      setSearchParams({});
    }
  }, [form, searchParams, setSearchParams]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await client.post('/interventions', {
        ...values,
        intervention_time: values.intervention_time?.toISOString(),
        next_follow_up_time: values.next_follow_up_time?.toISOString(),
        status: values.need_follow_up ? 'follow_up' : values.status,
      });
      message.success('创建成功');
      setModalOpen(false); form.resetFields(); fetchData();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('创建失败，请重试');
    }
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name' },
    { title: '方式', dataIndex: 'method', render: (v: string) => methodLabels[v] || v },
    { title: '内容', dataIndex: 'content', render: (v: string) => (v || '').substring(0, 30) + (v?.length > 30 ? '...' : '') },
    { title: '时间', dataIndex: 'intervention_time', render: (v: string) => v?.split('T')[0] || '' },
    { title: '状态', dataIndex: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '跟进', dataIndex: 'need_follow_up', render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
    { title: '下次跟进', dataIndex: 'next_follow_up_time', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>干预记录</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新增</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title="新增干预记录" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600} style={{ maxWidth: '95vw' }}>
        <Form form={form} layout="vertical">
          <Form.Item name="risk_alert_id" hidden><Input /></Form.Item>
          <Form.Item name="student_id" label="选择学生" rules={[{ required: true }]}>
            <StudentSelect placeholder="输入姓名或学号搜索学生" />
          </Form.Item>
          <Form.Item name="method" label="干预方式" initialValue="student_talk">
            <Select options={Object.entries(methodLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="intervention_time" label="干预时间">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="content" label="干预内容"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="result" label="处理结果"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="follow_up_suggestion" label="后续建议"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="need_follow_up" label="需要持续跟进" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item shouldUpdate noStyle>
            {({ getFieldValue }) => getFieldValue('need_follow_up') && (
              <Form.Item name="next_follow_up_time" label="下次跟进时间" rules={[{ required: true, message: '请选择下次跟进时间' }]}>
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
            )}
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="processing">
            <Select options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
