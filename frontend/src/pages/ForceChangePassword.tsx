import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, Typography, Card, Descriptions, Alert } from 'antd';
import { LockOutlined, UserOutlined, SafetyOutlined } from '@ant-design/icons';
import client from '../api/client';
import { useAuthStore } from '../stores/authStore';

export default function ForceChangePassword() {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();
  const { user, logout, updateUser } = useAuthStore();
  const [form] = Form.useForm();

  const onFinish = async (values: { old_password: string; new_password: string }) => {
    setLoading(true);
    setErrorMsg('');
    try {
      await client.put('/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      updateUser({ must_change_password: false });
      message.success('密码修改成功');
      const rolePathMap: Record<string, string> = {
        school_admin: '/school-admin/dashboard',
        teacher: '/teacher/dashboard',
        counselor: '/counselor/dashboard',
        student: '/student/home',
        platform_admin: '/platform/dashboard',
      };
      navigate(rolePathMap[user?.role || ''] || '/', { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      let msg = '密码修改失败';
      let hint = '';
      if (typeof detail === 'object' && detail?.message) {
        msg = detail.message;
      } else if (typeof detail === 'string') {
        msg = detail;
      }
      if (msg.includes('原密码错误') || msg.includes('当前密码')) {
        hint = '请确认当前密码是否正确';
      } else if (msg.includes('长度') || msg.includes('6位')) {
        hint = '新密码需要至少6个字符';
      } else if (msg.includes('相同') || msg.includes('一致')) {
        hint = '请确保两次输入的新密码一致';
      }
      setErrorMsg(msg);
      if (hint) message.warning(hint, 4);
      else message.error(msg, 5);
    } finally {
      setLoading(false);
    }
  };

  const roleLabels: Record<string, string> = {
    school_admin: '学校管理员',
    teacher: '教师',
    counselor: '心理老师',
    student: '学生',
    platform_admin: '平台管理员',
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, #020a1f 0%, #0a1a3a 25%, #0d2456 55%, #10306e 100%)' }}>
      <Card style={{ width: 'min(460px, 90vw)', borderRadius: 16, border: '1px solid rgba(0,212,255,0.2)', background: 'rgba(0,20,60,0.5)', backdropFilter: 'blur(20px)' }}>
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <SafetyOutlined style={{ fontSize: 40, color: '#00d4ff', marginBottom: 8 }} />
          <Typography.Title level={3} style={{ color: '#e8f4ff', marginBottom: 4 }}>
            设置新密码
          </Typography.Title>
          <Typography.Paragraph style={{ color: '#6a8aaf', marginBottom: 0 }}>
            你的账号使用的是初始密码，为确保安全，请设置一个新密码。
          </Typography.Paragraph>
        </div>

        {user && (
          <Descriptions size="small" column={1} style={{ marginBottom: 20 }}
            contentStyle={{ color: '#c0d8f0' }}
            labelStyle={{ color: '#6a8aaf' }}>
            <Descriptions.Item label={<><UserOutlined style={{ marginRight: 4 }} />账号</>}>{user.username}</Descriptions.Item>
            <Descriptions.Item label="姓名">{user.real_name}</Descriptions.Item>
            <Descriptions.Item label="角色">{roleLabels[user.role] || user.role}</Descriptions.Item>
          </Descriptions>
        )}

        <Form form={form} layout="vertical" onFinish={onFinish} size="large">
          {errorMsg && (
            <Alert
              type="error"
              showIcon
              closable
              onClose={() => setErrorMsg('')}
              message={errorMsg}
              style={{ marginBottom: 16, borderRadius: 8 }}
            />
          )}
          <Form.Item name="old_password" label={<span style={{ color: '#c0d8f0' }}>当前密码</span>}
            rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" />
          </Form.Item>
          <Form.Item name="new_password" label={<span style={{ color: '#c0d8f0' }}>新密码</span>} rules={[
            { required: true, message: '请输入新密码' },
            { min: 6, message: '密码长度不能少于6位' },
          ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="请设置新密码（至少6位）" />
          </Form.Item>
          <Form.Item name="confirm" label={<span style={{ color: '#c0d8f0' }}>确认新密码</span>} dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({ validator(_, value) { return value === getFieldValue('new_password') ? Promise.resolve() : Promise.reject(new Error('两次密码输入不一致')); } }),
            ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block
              style={{ height: 48, borderRadius: 10, background: 'linear-gradient(135deg, #00d4ff, #0088cc)', border: 'none' }}>
              确认修改并进入系统
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
