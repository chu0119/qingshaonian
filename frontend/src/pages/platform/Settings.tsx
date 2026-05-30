import { useState, useEffect } from 'react';
import {
  Card, Form, Input, Button, message, Typography, Descriptions, Tag, Statistic,
  Row, Col, Spin, Switch, Select, Space, Tabs, Table, Modal, InputNumber, Popconfirm, Tooltip,
} from 'antd';
import {
  SaveOutlined, BankOutlined, TeamOutlined, UserOutlined, AlertOutlined,
  FileTextOutlined, MessageOutlined, RobotOutlined, SafetyOutlined,
  ControlOutlined, DatabaseOutlined, NotificationOutlined, PlusOutlined,
  KeyOutlined, EditOutlined, ReloadOutlined,
} from '@ant-design/icons';
import client from '../../api/client';

const { TextArea } = Input;

export default function Settings() {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [smsForm] = Form.useForm();
  const [aiForm] = Form.useForm();
  const [securityForm] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [schoolDefaults, setSchoolDefaults] = useState({ admin_password: '' });
  const [sysInfo, setSysInfo] = useState<any>(null);
  const [sysLoading, setSysLoading] = useState(false);
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [dataRetention, setDataRetention] = useState({ data_retention_months: 36, log_retention_months: 12, auto_cleanup_enabled: false });
  const [admins, setAdmins] = useState<any[]>([]);
  const [adminsLoading, setAdminsLoading] = useState(false);
  const [adminModalOpen, setAdminModalOpen] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<any>(null);
  const [adminForm] = Form.useForm();

  useEffect(() => {
    client.get('/platform/settings').then(r => {
      const d = r.data.data || {};
      form.setFieldsValue({ system_name: d.system_name || '金盾护苗 · 青少年关爱帮扶信息管理平台', support_contact: d.support_contact || '' });
      setSchoolDefaults({ admin_password: d.default_admin_password || '' });
      smsForm.setFieldsValue({
        sms_enabled: d.sms_enabled === 'true',
        sms_provider: d.sms_provider || 'aliyun',
        sms_api_url: d.sms_api_url || '',
        sms_api_key: d.sms_api_key || '',
        sms_api_secret: d.sms_api_secret || '',
        sms_template_code: d.sms_template_code || '',
        sms_sign_name: d.sms_sign_name || '',
      });
      aiForm.setFieldsValue({
        ai_provider: d.ai_provider || 'openai',
        ai_api_key: d.ai_api_key || '',
        ai_base_url: d.ai_base_url || '',
        ai_model: d.ai_model || 'gpt-4o-mini',
        ai_system_prompt: d.ai_system_prompt || '',
      });
      securityForm.setFieldsValue({
        password_min_length: d.password_min_length ?? 6,
        password_expire_days: d.password_expire_days ?? 0,
        login_lock_threshold: d.login_lock_threshold ?? 5,
        login_lock_minutes: d.login_lock_minutes ?? 30,
        session_timeout_minutes: d.session_timeout_minutes ?? 480,
      });
      templateForm.setFieldsValue({
        template_risk_alert: d.template_risk_alert || '',
        template_task_assign: d.template_task_assign || '',
        template_password_reset: d.template_password_reset || '',
      });
      setFeatures({
        feature_ai_analysis: d.feature_ai_analysis !== 'false',
        feature_sms_notify: d.feature_sms_notify === 'true',
        feature_student_view_result: d.feature_student_view_result === 'true',
        feature_data_export: d.feature_data_export !== 'false',
        feature_auto_risk_alert: d.feature_auto_risk_alert !== 'false',
      });
      setDataRetention({
        data_retention_months: d.data_retention_months ?? 36,
        log_retention_months: d.log_retention_months ?? 12,
        auto_cleanup_enabled: d.auto_cleanup_enabled === 'true',
      });
    }).catch(() => {});

    setSysLoading(true);
    client.get('/platform/system-info').then(r => setSysInfo(r.data.data)).catch(() => setSysInfo(null)).finally(() => setSysLoading(false));
  }, []);

  const loadAdmins = () => {
    setAdminsLoading(true);
    client.get('/platform/admins?page_size=100').then(r => {
      setAdmins(r.data.data?.items || []);
    }).catch(() => {}).finally(() => setAdminsLoading(false));
  };

  useEffect(() => { loadAdmins(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    setLoading(true);
    try {
      const payload: any = { system_name: values.system_name, support_contact: values.support_contact };
      if (schoolDefaults.admin_password && schoolDefaults.admin_password !== '••••••') {
        payload.default_admin_password = schoolDefaults.admin_password;
      }
      await client.put('/platform/settings', payload);
      message.success('平台设置保存成功');
    } catch { message.error('保存失败'); }
    finally { setLoading(false); }
  };

  const handleSmsSave = async () => {
    const values = await smsForm.validateFields();
    setLoading(true);
    try {
      const payload: any = {
        sms_enabled: values.sms_enabled ? 'true' : 'false',
        sms_provider: values.sms_provider || '',
        sms_api_url: values.sms_api_url || '',
        sms_template_code: values.sms_template_code || '',
        sms_sign_name: values.sms_sign_name || '',
      };
      if (values.sms_api_key && values.sms_api_key !== '••••••') payload.sms_api_key = values.sms_api_key;
      if (values.sms_api_secret && values.sms_api_secret !== '••••••') payload.sms_api_secret = values.sms_api_secret;
      await client.put('/platform/settings', payload);
      message.success('短信配置保存成功');
    } catch { message.error('短信配置保存失败'); }
    finally { setLoading(false); }
  };

  const handleAiSave = async () => {
    const values = await aiForm.validateFields();
    setLoading(true);
    try {
      const payload: any = {
        ai_provider: values.ai_provider || '',
        ai_base_url: values.ai_base_url || '',
        ai_model: values.ai_model || '',
        ai_system_prompt: values.ai_system_prompt || '',
      };
      if (values.ai_api_key && values.ai_api_key !== '••••••') payload.ai_api_key = values.ai_api_key;
      await client.put('/platform/settings', payload);
      message.success('AI 配置保存成功');
    } catch { message.error('AI 配置保存失败'); }
    finally { setLoading(false); }
  };

  const handleSecuritySave = async () => {
    const values = await securityForm.validateFields();
    setLoading(true);
    try {
      await client.put('/platform/settings', {
        password_min_length: values.password_min_length,
        password_expire_days: values.password_expire_days,
        login_lock_threshold: values.login_lock_threshold,
        login_lock_minutes: values.login_lock_minutes,
        session_timeout_minutes: values.session_timeout_minutes,
      });
      message.success('安全设置保存成功');
    } catch { message.error('安全设置保存失败'); }
    finally { setLoading(false); }
  };

  const handleFeatureToggle = async (key: string, checked: boolean) => {
    try {
      await client.put('/platform/settings', { [key]: checked ? 'true' : 'false' });
      setFeatures(prev => ({ ...prev, [key]: checked }));
      message.success('功能开关已更新');
    } catch { message.error('更新失败'); }
  };

  const handleDataRetentionSave = async () => {
    setLoading(true);
    try {
      await client.put('/platform/settings', {
        data_retention_months: dataRetention.data_retention_months,
        log_retention_months: dataRetention.log_retention_months,
        auto_cleanup_enabled: dataRetention.auto_cleanup_enabled ? 'true' : 'false',
      });
      message.success('数据保留策略保存成功');
    } catch { message.error('保存失败'); }
    finally { setLoading(false); }
  };

  const handleTemplateSave = async () => {
    const values = await templateForm.validateFields();
    setLoading(true);
    try {
      await client.put('/platform/settings', {
        template_risk_alert: values.template_risk_alert,
        template_task_assign: values.template_task_assign,
        template_password_reset: values.template_password_reset,
      });
      message.success('通知模板保存成功');
    } catch { message.error('保存失败'); }
    finally { setLoading(false); }
  };

  const handleAdminSubmit = async () => {
    const values = await adminForm.validateFields();
    try {
      if (editingAdmin) {
        await client.put(`/platform/admins/${editingAdmin.id}`, {
          real_name: values.real_name,
          phone: values.phone,
        });
        message.success('管理员信息已更新');
      } else {
        await client.post('/platform/admins', {
          username: values.username,
          real_name: values.real_name,
          phone: values.phone,
          password: values.password,
        });
        message.success('管理员创建成功');
      }
      setAdminModalOpen(false);
      adminForm.resetFields();
      setEditingAdmin(null);
      loadAdmins();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleResetAdminPassword = async (adminId: number) => {
    try {
      const newPwd = `JdHm${Date.now().toString(36).slice(-6)}`;
      await client.put(`/platform/admins/${adminId}/reset-password`, { new_password: newPwd });
      Modal.success({ title: '密码已重置', content: `新密码：${newPwd}，请妥善保管并通知管理员。` });
    } catch { message.error('密码重置失败'); }
  };

  const featureItems = [
    { key: 'feature_ai_analysis', label: 'AI 智能分析', desc: '启用后可对风险学生进行 AI 综合分析' },
    { key: 'feature_sms_notify', label: '短信通知', desc: '启用后系统可通过短信发送通知' },
    { key: 'feature_student_view_result', label: '学生查看结果', desc: '启用后学生可在测评后查看脱敏结果摘要' },
    { key: 'feature_data_export', label: '数据导出', desc: '启用后各级管理员可导出 CSV 数据' },
    { key: 'feature_auto_risk_alert', label: '自动风险预警', desc: '启用后系统自动根据评分生成风险预警' },
  ];

  const adminColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (v: boolean) => v ? <Tag color="green">正常</Tag> : <Tag color="red">已禁用</Tag>,
    },
    {
      title: '最后登录', dataIndex: 'last_login_at', key: 'last_login_at',
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions', width: 220,
      render: (_: unknown, record: any) => (
        <Space size="small">
          <Tooltip title="编辑"><Button size="small" icon={<EditOutlined />} onClick={() => {
            setEditingAdmin(record);
            adminForm.setFieldsValue({ real_name: record.real_name, phone: '' });
            setAdminModalOpen(true);
          }} /></Tooltip>
          <Popconfirm title="确定重置此管理员的密码？" onConfirm={() => handleResetAdminPassword(record.id)} okText="确定" cancelText="取消">
            <Tooltip title="重置密码"><Button size="small" icon={<KeyOutlined />} /></Tooltip>
          </Popconfirm>
          <Popconfirm title={`确定${record.status ? '禁用' : '启用'}此管理员？`} okText="确定" cancelText="取消" onConfirm={async () => {
            await client.put(`/platform/admins/${record.id}`, { status: !record.status });
            message.success('状态已更新');
            loadAdmins();
          }}>
            <Tooltip title={record.status ? '禁用' : '启用'}>
              <Button size="small" danger={record.status} icon={<SafetyOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>平台设置</Typography.Title>

      <Tabs defaultActiveKey="basic" items={[
        {
          key: 'basic',
          label: '基本设置',
          children: (
            <>
              <Card title="平台基本设置" style={{ marginBottom: 24 }}>
                <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
                  <Form.Item name="system_name" label="系统名称" rules={[{ required: true }]}>
                    <Input placeholder="金盾护苗 · 青少年关爱帮扶信息管理平台" />
                  </Form.Item>
                  <Form.Item name="support_contact" label="技术支持联系方式">
                    <Input placeholder="如：联系电话或邮箱（选填）" />
                  </Form.Item>
                </Form>
              </Card>
              <Card title="新学校默认设置" style={{ marginBottom: 24 }}>
                <Form layout="vertical" style={{ maxWidth: 600 }}>
                  <Form.Item label="默认管理员密码" help="创建新学校时，学校管理员账号的默认密码">
                    <Input.Password value={schoolDefaults.admin_password} onChange={e => setSchoolDefaults({ ...schoolDefaults, admin_password: e.target.value })} placeholder="由平台管理员配置" />
                  </Form.Item>
                </Form>
              </Card>
              <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave}>保存基本设置</Button>
            </>
          ),
        },
        {
          key: 'ai',
          label: 'AI 配置',
          children: (
            <Card title={<Space><RobotOutlined />AI 智能分析配置</Space>} style={{ marginBottom: 24 }}>
              <Form form={aiForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="ai_provider" label="AI 服务商">
                  <Select options={[
                    { value: 'openai', label: 'OpenAI 兼容接口' },
                    { value: 'zhipu', label: '智谱 AI' },
                    { value: 'qwen', label: '通义千问' },
                    { value: 'deepseek', label: 'DeepSeek' },
                    { value: 'custom', label: '自定义接口' },
                  ]} />
                </Form.Item>
                <Form.Item name="ai_base_url" label="API Base URL" help="如 https://api.openai.com/v1，使用默认可留空">
                  <Input placeholder="https://api.openai.com/v1" />
                </Form.Item>
                <Form.Item name="ai_api_key" label="API Key">
                  <Input.Password placeholder="sk-..." />
                </Form.Item>
                <Form.Item name="ai_model" label="模型名称">
                  <Input placeholder="如 gpt-4o-mini, glm-4-flash, qwen-turbo" />
                </Form.Item>
                <Form.Item name="ai_system_prompt" label="分析提示词模板" help="自定义 AI 分析时使用的系统提示词，留空使用默认">
                  <TextArea rows={4} placeholder="你是一名专业的青少年行为分析专家，请根据以下数据进行分析..." />
                </Form.Item>
                <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleAiSave}>保存 AI 配置</Button>
              </Form>
            </Card>
          ),
        },
        {
          key: 'sms',
          label: '短信服务',
          children: (
            <Card title={<Space><MessageOutlined />短信服务配置</Space>} style={{ marginBottom: 24 }}>
              <Form form={smsForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="sms_enabled" label="启用短信服务" valuePropName="checked" help="开启后，用户可通过短信验证码重置密码">
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>
                <Form.Item name="sms_provider" label="短信服务商">
                  <Select options={[
                    { value: 'aliyun', label: '阿里云短信' },
                    { value: 'tencent', label: '腾讯云短信' },
                    { value: 'custom', label: '自定义接口' },
                  ]} />
                </Form.Item>
                <Form.Item name="sms_api_url" label="API 地址" help="自定义接口时填写完整 URL，阿里云/腾讯云可留空">
                  <Input placeholder="如 https://dysmsapi.aliyuncs.com" />
                </Form.Item>
                <Row gutter={16}>
                  <Col xs={24} sm={12}>
                    <Form.Item name="sms_api_key" label="AccessKey ID">
                      <Input placeholder="短信服务商的 AccessKey ID" />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item name="sms_api_secret" label="AccessKey Secret">
                      <Input.Password placeholder="短信服务商的 AccessKey Secret" />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col xs={24} sm={12}>
                    <Form.Item name="sms_template_code" label="短信模板编码">
                      <Input placeholder="如 SMS_123456789" />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item name="sms_sign_name" label="短信签名">
                      <Input placeholder="如 金盾护苗" />
                    </Form.Item>
                  </Col>
                </Row>
                <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSmsSave}>保存短信配置</Button>
              </Form>
            </Card>
          ),
        },
        {
          key: 'security',
          label: '安全设置',
          children: (
            <Card title={<Space><SafetyOutlined />安全设置</Space>} style={{ marginBottom: 24 }}>
              <Form form={securityForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Row gutter={16}>
                  <Col xs={24} sm={12}>
                    <Form.Item name="password_min_length" label="密码最小长度">
                      <InputNumber min={6} max={32} style={{ width: '100%' }} addonAfter="位" />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item name="password_expire_days" label="密码过期天数" help="0 表示永不过期">
                      <InputNumber min={0} max={365} style={{ width: '100%' }} addonAfter="天" />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col xs={24} sm={12}>
                    <Form.Item name="login_lock_threshold" label="登录失败锁定阈值">
                      <InputNumber min={3} max={20} style={{ width: '100%' }} addonAfter="次" />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item name="login_lock_minutes" label="锁定时长">
                      <InputNumber min={5} max={1440} style={{ width: '100%' }} addonAfter="分钟" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item name="session_timeout_minutes" label="会话超时时间">
                  <InputNumber min={30} max={1440} style={{ width: '100%', maxWidth: 300 }} addonAfter="分钟" />
                </Form.Item>
                <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSecuritySave}>保存安全设置</Button>
              </Form>
            </Card>
          ),
        },
        {
          key: 'features',
          label: '功能开关',
          children: (
            <Card title={<Space><ControlOutlined />功能开关</Space>} style={{ marginBottom: 24 }}>
              <div style={{ maxWidth: 600 }}>
                {featureItems.map(f => (
                  <div key={f.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{f.label}</div>
                      <div style={{ fontSize: 12, color: '#999' }}>{f.desc}</div>
                    </div>
                    <Switch checked={features[f.key]} onChange={v => handleFeatureToggle(f.key, v)} />
                  </div>
                ))}
              </div>
            </Card>
          ),
        },
        {
          key: 'data',
          label: '数据与通知',
          children: (
            <>
              <Card title={<Space><DatabaseOutlined />数据保留策略</Space>} style={{ marginBottom: 24 }}>
                <div style={{ maxWidth: 600 }}>
                  <Row gutter={16}>
                    <Col xs={24} sm={12}>
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 500, marginBottom: 4 }}>测评数据保留</div>
                        <InputNumber min={6} max={120} value={dataRetention.data_retention_months}
                          onChange={v => setDataRetention(prev => ({ ...prev, data_retention_months: v || 36 }))}
                          style={{ width: '100%' }} addonAfter="个月" />
                      </div>
                    </Col>
                    <Col xs={24} sm={12}>
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 500, marginBottom: 4 }}>操作日志保留</div>
                        <InputNumber min={3} max={60} value={dataRetention.log_retention_months}
                          onChange={v => setDataRetention(prev => ({ ...prev, log_retention_months: v || 12 }))}
                          style={{ width: '100%' }} addonAfter="个月" />
                      </div>
                    </Col>
                  </Row>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '12px 0' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>自动清理过期数据</div>
                      <div style={{ fontSize: 12, color: '#999' }}>定期自动删除超过保留期限的数据</div>
                    </div>
                    <Switch checked={dataRetention.auto_cleanup_enabled}
                      onChange={v => setDataRetention(prev => ({ ...prev, auto_cleanup_enabled: v }))} />
                  </div>
                  <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleDataRetentionSave}>保存数据策略</Button>
                </div>
              </Card>
              <Card title={<Space><NotificationOutlined />通知模板</Space>} style={{ marginBottom: 24 }}>
                <Form form={templateForm} layout="vertical" style={{ maxWidth: 600 }}>
                  <Form.Item name="template_risk_alert" label="风险预警通知模板"
                    help="支持变量：{student_name}、{school_name}、{risk_level}、{date}">
                    <TextArea rows={2} />
                  </Form.Item>
                  <Form.Item name="template_task_assign" label="任务下发通知模板"
                    help="支持变量：{school_name}、{date}">
                    <TextArea rows={2} />
                  </Form.Item>
                  <Form.Item name="template_password_reset" label="密码重置通知模板">
                    <TextArea rows={2} />
                  </Form.Item>
                  <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleTemplateSave}>保存通知模板</Button>
                </Form>
              </Card>
            </>
          ),
        },
        {
          key: 'admins',
          label: '管理员账号',
          children: (
            <Card title={<Space><UserOutlined />平台管理员</Space>}
              extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => {
                setEditingAdmin(null);
                adminForm.resetFields();
                setAdminModalOpen(true);
              }}>新增管理员</Button>}>
              <Table dataSource={admins} columns={adminColumns} rowKey="id" loading={adminsLoading}
                pagination={{ pageSize: 10 }}
                scroll={{ x: 'max-content' }}
              />
            </Card>
          ),
        },
        {
          key: 'info',
          label: '系统信息',
          children: (
            <>
              <Card title="系统信息" style={{ marginBottom: 24 }}>
                {sysLoading ? <Spin /> : sysInfo ? (
                  <>
                    <Descriptions bordered column={{ xs: 1, sm: 2 }} size="middle" style={{ marginBottom: 16 }}>
                      <Descriptions.Item label="版本号">{sysInfo.version}</Descriptions.Item>
                      <Descriptions.Item label="技术架构">{sysInfo.tech_stack}</Descriptions.Item>
                      <Descriptions.Item label="数据库">{sysInfo.db_type}</Descriptions.Item>
                    </Descriptions>
                    <Row gutter={16}>
                      <Col span={4}><Statistic title="学校" value={sysInfo.school_count} prefix={<BankOutlined />} /></Col>
                      <Col span={4}><Statistic title="学生" value={sysInfo.student_count} prefix={<TeamOutlined />} /></Col>
                      <Col span={4}><Statistic title="教师" value={sysInfo.teacher_count} prefix={<UserOutlined />} /></Col>
                      <Col span={4}><Statistic title="任务" value={sysInfo.task_count} prefix={<FileTextOutlined />} /></Col>
                      <Col span={4}><Statistic title="风险预警" value={sysInfo.risk_count} prefix={<AlertOutlined />} valueStyle={{ color: '#ff4d4f' }} /></Col>
                    </Row>
                  </>
                ) : (
                  <Descriptions bordered column={{ xs: 1, sm: 2 }} size="middle">
                    <Descriptions.Item label="版本号">v2.1.0</Descriptions.Item>
                    <Descriptions.Item label="技术架构">Python FastAPI + React 18 + Ant Design 5</Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
              <Card title="功能状态">
                <Descriptions bordered column={{ xs: 1, sm: 3 }} size="small">
                  <Descriptions.Item label="多学校管理"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="专业量表测评"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="数据驱动分析"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="数据大屏"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="答题质量控制"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="风险预警"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="干预督办"><Tag color="green">已启用</Tag></Descriptions.Item>
                  <Descriptions.Item label="数据导出"><Tag color={features.feature_data_export ? 'green' : 'default'}>{features.feature_data_export ? '已启用' : '已关闭'}</Tag></Descriptions.Item>
                  <Descriptions.Item label="审计日志"><Tag color="green">已启用</Tag></Descriptions.Item>
                </Descriptions>
              </Card>
            </>
          ),
        },
      ]} />

      <Modal title={editingAdmin ? '编辑管理员' : '新增平台管理员'}
        open={adminModalOpen}
        onCancel={() => { setAdminModalOpen(false); setEditingAdmin(null); }}
        onOk={handleAdminSubmit} okText={editingAdmin ? '保存' : '创建'} cancelText="取消">
        <Form form={adminForm} layout="vertical">
          {!editingAdmin && (
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input placeholder="登录用户名" />
            </Form.Item>
          )}
          {!editingAdmin && (
            <Form.Item name="password" label="初始密码" rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6位' },
            ]}>
              <Input.Password placeholder="至少6位" />
            </Form.Item>
          )}
          <Form.Item name="real_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="管理员真实姓名" />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input placeholder="联系手机号（选填）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
