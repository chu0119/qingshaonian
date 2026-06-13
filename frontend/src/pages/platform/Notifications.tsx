/**
 * 短信通知中心 — 平台管理端
 * 支持：查看模板、发送短信、查看记录、批量发送
 */
import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, Input, Typography, Space, Button, Modal, Form, message, Card, Row, Col, Statistic, Tabs, Descriptions, Alert, Empty } from 'antd';
import { SendOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, MessageOutlined, SettingOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { SMS_TYPE_LABELS, SMS_STATUS_LABELS } from '../../utils/constants';

const { Search } = Input;

interface SmsTemplate {
  code: string;
  name: string;
  content: string;
  params: string[];
  category: string;
  template_id_configured: boolean;
  tencent_template_id: string;
}

interface SmsLog {
  id: number;
  recipient_name: string;
  phone: string;
  sms_type: string;
  template_code: string;
  content: string;
  status: string;
  failure_reason: string;
  sent_at: string;
  created_at: string;
}

export default function PlatformSmsCenter() {
  // 模板相关
  const [templates, setTemplates] = useState<SmsTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);

  // 发送相关
  const [sendOpen, setSendOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [form] = Form.useForm();
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');

  // 记录相关
  const [logs, setLogs] = useState<SmsLog[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsPage, setLogsPage] = useState(1);
  const [logsFilter, setLogsFilter] = useState({ status: '', sms_type: '', keyword: '' });

  // 统计
  const [stats, setStats] = useState({ total: 0, sent: 0, failed: 0, not_configured: 0, sms_enabled: false });

  // 用户搜索
  const [userSearch, setUserSearch] = useState('');
  const [userResults, setUserResults] = useState<any[]>([]);
  const [searchingUser, setSearchingUser] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);

  // 加载模板
  const fetchTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      const r = await client.get('/sms/templates');
      setTemplates(r.data.data || []);
    } catch (err: any) {
      message.error(err._friendlyMessage || '获取模板失败');
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  // 加载记录
  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const params: Record<string, any> = { page: logsPage, page_size: 15 };
      if (logsFilter.status) params.status = logsFilter.status;
      if (logsFilter.sms_type) params.sms_type = logsFilter.sms_type;
      if (logsFilter.keyword) params.keyword = logsFilter.keyword;
      const r = await client.get('/sms/logs', { params });
      setLogs(r.data.data?.items || []);
      setLogsTotal(r.data.data?.total || 0);
    } catch (err: any) {
      message.error(err._friendlyMessage || '获取记录失败');
    } finally {
      setLogsLoading(false);
    }
  }, [logsPage, logsFilter]);

  // 加载统计
  const fetchStats = useCallback(async () => {
    try {
      const r = await client.get('/sms/stats');
      setStats(r.data.data || {});
    } catch { /* */ }
  }, []);

  useEffect(() => { fetchTemplates(); fetchStats(); }, [fetchTemplates, fetchStats]);
  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // 搜索用户
  const searchUsers = async (keyword: string) => {
    if (!keyword || keyword.length < 2) { setUserResults([]); return; }
    setSearchingUser(true);
    try {
      const r = await client.get('/users', { params: { page: 1, page_size: 10, keyword } });
      setUserResults(r.data.data?.items || []);
    } catch { setUserResults([]); }
    finally { setSearchingUser(false); }
  };

  // 模板选择
  const handleTemplateChange = (code: string) => {
    setSelectedTemplate(code);
    const tpl = templates.find(t => t.code === code);
    if (tpl) {
      form.setFieldsValue({ content: tpl.content });
    }
  };

  // 发送短信
  const handleSend = async () => {
    const values = await form.validateFields();
    if (!selectedUser) { message.warning('请选择接收人'); return; }
    setSending(true);
    try {
      await client.post('/sms/send', {
        recipient_user_id: selectedUser.id,
        template_code: selectedTemplate || 'task_publish',
        content: values.content,
      });
      message.success('短信发送请求已提交');
      setSendOpen(false);
      form.resetFields();
      setSelectedUser(null);
      setSelectedTemplate('');
      fetchLogs();
      fetchStats();
    } catch (err: any) {
      message.error(err._friendlyMessage || '发送失败');
    } finally {
      setSending(false);
    }
  };

  // 重试
  const handleRetry = async (logId: number) => {
    try {
      await client.post(`/sms/logs/${logId}/retry`);
      message.success('重试请求已提交');
      fetchLogs();
      fetchStats();
    } catch (err: any) {
      message.error(err._friendlyMessage || '重试失败');
    }
  };

  // 表格列
  const logColumns = [
    { title: '接收人', dataIndex: 'recipient_name', key: 'recipient_name', width: 100, render: (v: string) => v || '-' },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120 },
    { title: '类型', dataIndex: 'sms_type', key: 'sms_type', width: 100,
      render: (v: string) => <Tag>{SMS_TYPE_LABELS[v] || v}</Tag> },
    { title: '模板', dataIndex: 'template_code', key: 'template_code', width: 100,
      render: (v: string) => {
        const tpl = templates.find(t => t.code === v);
        return tpl ? tpl.name : v;
      }},
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const colors: Record<string, string> = { sent: 'green', failed: 'red', not_configured: 'orange', pending: 'blue' };
        return <Tag color={colors[v] || 'default'}>{SMS_STATUS_LABELS[v] || v}</Tag>;
      }},
    { title: '内容', dataIndex: 'content', key: 'content', ellipsis: true, width: 200 },
    { title: '失败原因', dataIndex: 'failure_reason', key: 'failure_reason', ellipsis: true, width: 180,
      render: (v: string) => v ? <span style={{ color: '#ff4d4f' }}>{v}</span> : '-' },
    { title: '发送时间', dataIndex: 'sent_at', key: 'sent_at', width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '操作', key: 'action', width: 80,
      render: (_: unknown, record: SmsLog) => (
        record.status === 'failed' ? (
          <Button type="link" size="small" onClick={() => handleRetry(record.id)}>重试</Button>
        ) : null
      )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>短信通知中心</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchLogs(); fetchStats(); }}>刷新</Button>
          <Button type="primary" icon={<SendOutlined />} onClick={() => setSendOpen(true)}>发送短信</Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="短信状态" value={stats.sms_enabled ? '已启用' : '未启用'}
              valueStyle={{ color: stats.sms_enabled ? '#52c41a' : '#ff4d4f', fontSize: 18 }}
              prefix={stats.sms_enabled ? <CheckCircleOutlined /> : <CloseCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="发送成功" value={stats.sent} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="发送失败" value={stats.failed} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="未配置" value={stats.not_configured} valueStyle={{ color: '#faad14' }} prefix={<WarningOutlined />} />
          </Card>
        </Col>
      </Row>

      {!stats.sms_enabled && (
        <Alert message="短信服务未启用" description="请在「系统设置 → 短信服务配置」中启用短信服务并配置相关参数" type="warning" showIcon style={{ marginBottom: 16 }} />
      )}

      <Tabs defaultActiveKey="logs" items={[
        {
          key: 'logs', label: '发送记录',
          children: (
            <>
              <Space wrap style={{ marginBottom: 12 }}>
                <Select placeholder="状态" allowClear style={{ width: 120 }}
                  value={logsFilter.status || undefined}
                  onChange={v => { setLogsFilter(f => ({ ...f, status: v || '' })); setLogsPage(1); }}
                  options={[{ value: 'sent', label: '已发送' }, { value: 'failed', label: '发送失败' }, { value: 'not_configured', label: '未配置' }]} />
                <Select placeholder="类型" allowClear style={{ width: 120 }}
                  value={logsFilter.sms_type || undefined}
                  onChange={v => { setLogsFilter(f => ({ ...f, sms_type: v || '' })); setLogsPage(1); }}
                  options={Object.entries(SMS_TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
                <Search placeholder="搜索手机号/姓名" style={{ width: 180 }}
                  value={logsFilter.keyword}
                  onChange={e => setLogsFilter(f => ({ ...f, keyword: e.target.value }))}
                  onSearch={() => { setLogsPage(1); fetchLogs(); }} />
              </Space>
              <Table rowKey="id" dataSource={logs} columns={logColumns} loading={logsLoading}
                scroll={{ x: 'max-content' }} size="small"
                pagination={{ current: logsPage, total: logsTotal, pageSize: 15, onChange: setLogsPage, showTotal: t => `共 ${t} 条` }} />
            </>
          ),
        },
        {
          key: 'templates', label: '短信模板',
          children: (
            <div>
              <Alert message="短信模板需要在腾讯云短信平台申请并通过审核后，将模板ID填写到系统设置中" type="info" showIcon style={{ marginBottom: 16 }} />
              <Table rowKey="code" dataSource={templates} loading={templatesLoading} size="small" pagination={false}>
                <Table.Column title="模板名称" dataIndex="name" width={120} />
                <Table.Column title="分类" dataIndex="category" width={100} render={(v: string) => <Tag>{v}</Tag>} />
                <Table.Column title="模板内容" dataIndex="content" render={(v: string) => <span style={{ fontSize: 13 }}>{v}</span>} />
                <Table.Column title="变量" dataIndex="params" width={120} render={(v: string[]) => v.join(', ')} />
                <Table.Column title="模板ID" dataIndex="tencent_template_id" width={120}
                  render={(v: string) => v ? <Tag color="green">{v}</Tag> : <Tag color="orange">未配置</Tag>} />
              </Table>
            </div>
          ),
        },
      ]} />

      {/* 发送短信弹窗 */}
      <Modal title="发送短信" open={sendOpen} onOk={handleSend} onCancel={() => { setSendOpen(false); setSelectedUser(null); setSelectedTemplate(''); form.resetFields(); }}
        confirmLoading={sending} destroyOnHidden okText="发送" cancelText="取消" width={520}>
        <Form form={form} layout="vertical">
          <Form.Item label="接收人" required>
            <Select
              showSearch
              placeholder="输入姓名或手机号搜索"
              filterOption={false}
              onSearch={searchUsers}
              loading={searchingUser}
              notFoundContent="请输入至少2个字符搜索"
              options={userResults.map(u => ({ value: u.id, label: `${u.real_name} (${u.phone || '无手机号'})` }))}
              onChange={(val) => {
                const user = userResults.find(u => u.id === val);
                setSelectedUser(user || null);
              }}
              style={{ width: '100%' }}
            />
            {selectedUser && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                已选择：{selectedUser.real_name} | {selectedUser.phone || '无手机号'}
                {selectedUser.phone ? '' : ' ⚠️ 该用户未配置手机号，短信将发送失败'}
              </div>
            )}
          </Form.Item>

          <Form.Item label="短信模板">
            <Select placeholder="选择预设模板（可选）" allowClear style={{ width: '100%' }}
              value={selectedTemplate || undefined}
              onChange={handleTemplateChange}
              options={templates.map(t => ({
                value: t.code,
                label: `${t.name} (${t.template_id_configured ? '已配置' : '未配置'})`,
                disabled: !t.template_id_configured,
              }))} />
            {selectedTemplate && !templates.find(t => t.code === selectedTemplate)?.template_id_configured && (
              <Alert message="该模板的腾讯云模板ID未配置，短信将无法发送" type="warning" showIcon style={{ marginTop: 8 }} />
            )}
          </Form.Item>

          <Form.Item name="content" label="短信内容" rules={[{ required: true, message: '请输入短信内容' }]}>
            <Input.TextArea rows={3} placeholder="请输入短信内容" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
