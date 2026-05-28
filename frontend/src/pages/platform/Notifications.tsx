import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, Button, Modal, Form, message } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function PlatformSmsCenter() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: '', keyword: '' });
  const [sendOpen, setSendOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [form] = Form.useForm();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      const r = await client.get('/platform/sms-logs', { params });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSend = async () => {
    const values = await form.validateFields();
    setSending(true);
    try {
      await client.post('/platform/send-sms', values);
      message.success('短信发送成功');
      setSendOpen(false); form.resetFields(); fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '发送失败');
    } finally { setSending(false); }
  };

  const columns = [
    { title: '接收人', dataIndex: 'recipient_name', key: 'recipient_name', width: 100, render: (v: string) => v || '-' },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120, render: (v: string) => v ? v.substring(0, 3) + '****' + v.substring(7) : '-' },
    { title: '类型', dataIndex: 'sms_type', key: 'sms_type', width: 80 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <Tag color={v === 'sent' ? 'green' : v === 'failed' ? 'red' : 'default'}>{v}</Tag> },
    { title: '发送时间', dataIndex: 'sent_at', key: 'sent_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '失败原因', dataIndex: 'failure_reason', key: 'failure_reason', ellipsis: true, width: 150 },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>短信通知中心</Typography.Title>
        <Button type="primary" icon={<SendOutlined />} onClick={() => setSendOpen(true)}>发送催办短信</Button>
      </div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
          options={[{ value: 'sent', label: '已发送' }, { value: 'failed', label: '发送失败' }, { value: 'not_configured', label: '未配置' }]} />
        <Input.Search placeholder="搜索手机号" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

      <Modal title="发送催办短信" open={sendOpen} onOk={handleSend} onCancel={() => setSendOpen(false)} confirmLoading={sending} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="phone" label="手机号" rules={[{ required: true, pattern: /^1\d{10}$/, message: '请输入11位手机号' }]}>
            <Input placeholder="请输入接收人手机号" />
          </Form.Item>
          <Form.Item name="content" label="短信内容" rules={[{ required: true, message: '请输入短信内容' }]}>
            <Input.TextArea rows={3} placeholder="请输入催办短信内容" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
