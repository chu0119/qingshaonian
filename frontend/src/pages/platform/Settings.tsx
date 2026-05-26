import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Typography, Descriptions, Tag } from 'antd';
import { SaveOutlined, SafetyOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function Settings() {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [schoolDefaults, setSchoolDefaults] = useState({ admin_password: '' });

  useEffect(() => {
    // 加载平台设置
    client.get('/platform/settings').then(r => {
      const d = r.data.data || {};
      form.setFieldsValue({ system_name: d.system_name || '青盾 · 青少年风险防范测评管理系统', support_contact: d.support_contact || '' });
      setSchoolDefaults({ admin_password: d.default_admin_password || '' });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    setLoading(true);
    try {
      await client.put('/platform/settings', {
        system_name: values.system_name,
        support_contact: values.support_contact,
        default_admin_password: schoolDefaults.admin_password,
      });
      message.success('平台设置保存成功');
    } catch { message.error('保存失败'); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <Typography.Title level={4}>平台设置</Typography.Title>

      <Card title="平台基本设置" style={{ marginBottom: 24 }}>
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item name="system_name" label="系统名称" rules={[{ required: true }]}>
            <Input placeholder="青盾 · 青少年风险防范测评管理系统" />
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

      <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave} size="large" style={{ marginBottom: 24 }}>
        保存设置
      </Button>

      <Card title="系统信息" style={{ marginBottom: 24 }}>
        <Descriptions bordered column={{ xs: 1, sm: 2 }} size="middle">
          <Descriptions.Item label="版本号">v2.0.0</Descriptions.Item>
          <Descriptions.Item label="技术架构">Python FastAPI + React 18 + Ant Design 5</Descriptions.Item>
          <Descriptions.Item label="数据库">SQLite / MySQL</Descriptions.Item>
          <Descriptions.Item label="服务端口">前端3000 / 后端8000</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="功能状态">
        <Descriptions bordered column={{ xs: 1, sm: 3 }} size="small">
          <Descriptions.Item label="多学校管理"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="20套专业量表"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="AI智能分析"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="数据大屏"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="答题质量控制"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="短信验证码"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="风险预警"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="数据报表"><Tag color="green">已启用</Tag></Descriptions.Item>
          <Descriptions.Item label="批量导入导出"><Tag color="green">已启用</Tag></Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
