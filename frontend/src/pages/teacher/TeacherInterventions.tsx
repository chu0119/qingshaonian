import { useState, useEffect } from 'react';
import { Table, Tag, Button, Modal, Form, Input, Select, message, Typography, DatePicker, Switch, Popconfirm, Descriptions } from 'antd';
import { useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import StudentSelect from '../../components/common/StudentSelect';
import client from '../../api/client';
import { METHOD_LABELS, INTERVENTION_STATUS_LABELS } from '../../utils/constants';

const methodLabels = METHOD_LABELS;
const statusLabels = INTERVENTION_STATUS_LABELS;

export default function TeacherInterventions() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [detailRecord, setDetailRecord] = useState<any>(null);
  const [form] = Form.useForm();

  const fetchData = () => {
    setLoading(true);
    client.get('/interventions', { params: { page, page_size: 20 } }).then(r => {
      setData(r.data.data?.items || []); setTotal(r.data.data?.total || 0);
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
      const payload = {
        ...values,
        intervention_time: values.intervention_time?.toISOString(),
        next_follow_up_time: values.next_follow_up_time?.toISOString(),
        status: values.need_follow_up ? 'follow_up' : values.status,
      };
      if (editingRecord) {
        await client.put(`/interventions/${editingRecord.id}`, payload);
        message.success('更新成功');
      } else {
        await client.post('/interventions', payload);
        message.success('创建成功');
      }
      setModalOpen(false); form.resetFields(); setEditingRecord(null); fetchData();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('保存失败');
    }
  };

  const handleEdit = (record: any) => {
    setEditingRecord(record);
    form.setFieldsValue({
      student_id: record.student_id,
      method: record.method,
      content: record.content,
      result: record.result,
      follow_up_suggestion: record.follow_up_suggestion,
      need_follow_up: record.need_follow_up,
      status: record.status,
      risk_alert_id: record.risk_alert_id,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await client.delete(`/interventions/${id}`);
      message.success('删除成功');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  const showDetail = (record: any) => {
    setDetailRecord(record);
    setDetailOpen(true);
  };

  const columns = [
    { title: '学生', dataIndex: 'student_name' },
    { title: '方式', dataIndex: 'method', render: (v: string) => methodLabels[v] || v },
    { title: '内容', dataIndex: 'content', render: (v: string) => (v || '').substring(0, 30) + (v?.length > 30 ? '...' : '') },
    { title: '时间', dataIndex: 'intervention_time', render: (v: string) => v?.split('T')[0] || '' },
    { title: '状态', dataIndex: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '跟进', dataIndex: 'need_follow_up', render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
    { title: '下次跟进', dataIndex: 'next_follow_up_time', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '操作', key: 'action', width: 200, render: (_: any, r: any) => (
      <>
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(r)}>查看</Button>
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)}>编辑</Button>
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)} okText="确定" cancelText="取消">
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>干预记录</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); form.resetFields(); setModalOpen(true); }}>新增</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />
      <Modal title={editingRecord ? '编辑干预记录' : '新增干预记录'} open={modalOpen} onOk={handleCreate} onCancel={() => { setModalOpen(false); setEditingRecord(null); form.resetFields(); }} okText="确定" cancelText="取消" width={600} style={{ maxWidth: '95vw' }}>
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

      {/* 详情弹窗 */}
      <Modal title="干预记录详情" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={600} style={{ maxWidth: '95vw' }}>
        {detailRecord && (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="学生">{detailRecord.student_name}</Descriptions.Item>
            <Descriptions.Item label="干预方式">{methodLabels[detailRecord.method] || detailRecord.method}</Descriptions.Item>
            <Descriptions.Item label="干预时间">{detailRecord.intervention_time ? new Date(detailRecord.intervention_time).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag>{statusLabels[detailRecord.status] || detailRecord.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="干预内容">{detailRecord.content}</Descriptions.Item>
            <Descriptions.Item label="处理结果">{detailRecord.result || '-'}</Descriptions.Item>
            <Descriptions.Item label="后续建议">{detailRecord.follow_up_suggestion || '-'}</Descriptions.Item>
            <Descriptions.Item label="需要跟进">{detailRecord.need_follow_up ? '是' : '否'}</Descriptions.Item>
            {detailRecord.next_follow_up_time && <Descriptions.Item label="下次跟进时间">{new Date(detailRecord.next_follow_up_time).toLocaleString('zh-CN')}</Descriptions.Item>}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
