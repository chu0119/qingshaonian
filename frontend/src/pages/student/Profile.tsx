import { useState, useEffect } from 'react';
import { Card, Descriptions, Button, Typography, List, Tag, Modal, Form, Input, message, Empty, Spin } from 'antd';
import { CheckCircleOutlined, KeyOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { changePassword } from '../../api/auth';
import client from '../../api/client';

export default function Profile() {
  const { user, logout } = useAuthStore();
  const [records, setRecords] = useState<any[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdForm] = Form.useForm();

  useEffect(() => {
    const fetchRecords = async () => {
      setRecordsLoading(true);
      try {
        const r = await client.get('/student/tasks/completed');
        setRecords(r.data.data || []);
      } catch (err: any) {
        message.error(err?.response?.data?.message || '获取测评记录失败');
      } finally {
        setRecordsLoading(false);
      }
    };
    fetchRecords();
  }, []);

  const handleChangePassword = async () => {
    try {
      const values = await pwdForm.validateFields();
      setPwdLoading(true);
      await changePassword(values.old_password, values.new_password);
      message.success('密码修改成功，请重新登录');
      setPwdModalOpen(false);
      pwdForm.resetFields();
      logout();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('密码修改失败，请重试');
    } finally {
      setPwdLoading(false);
    }
  };

  const openPasswordModal = () => {
    pwdForm.resetFields();
    setPwdModalOpen(true);
  };

  const formatDuration = (seconds: number) => {
    if (!seconds && seconds !== 0) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) return `${mins}分${secs}秒`;
    return `${secs}秒`;
  };

  if (!user) return null;

  return (
    <div>
      <Typography.Title level={4}>个人中心</Typography.Title>

      {/* 用户信息卡片 */}
      <Card
        title="基本信息"
        extra={
          <Button
            type="primary"
            icon={<KeyOutlined />}
            onClick={openPasswordModal}
            ghost
          >
            修改密码
          </Button>
        }
        style={{ marginBottom: 20 }}
      >
        <Descriptions column={{ xs: 1, sm: 2 }} bordered>
          <Descriptions.Item label="姓名">{user.real_name}</Descriptions.Item>
          <Descriptions.Item label="账号">{user.username}</Descriptions.Item>
          <Descriptions.Item label="角色">
            <Tag color="blue">{user.role === 'student' ? '学生' : user.role}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="学号">{user.student_no || '-'}</Descriptions.Item>
          <Descriptions.Item label="性别">{user.gender || '-'}</Descriptions.Item>
          <Descriptions.Item label="手机号">{user.phone || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 最近测评记录 */}
      <Card title="最近测评记录">
        {recordsLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : records.length === 0 ? (
          <Empty description="暂无已完成测评" />
        ) : (
          <List
            dataSource={records}
            renderItem={(item: any) => (
              <List.Item>
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ fontSize: 24, color: '#4A90D9' }} />}
                  title={item.questionnaire_title || '未命名问卷'}
                  description={item.task_name || '-'}
                />
                <div style={{ textAlign: 'right' }}>
                  <Tag color="green" icon={<CheckCircleOutlined />}>已完成</Tag>
                  <div style={{ color: '#888', fontSize: 13, marginTop: 4 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    提交时间: {item.submitted_at ? new Date(item.submitted_at).toLocaleString('zh-CN') : '-'}
                  </div>
                  {item.duration !== undefined && item.duration !== null && (
                    <div style={{ color: '#888', fontSize: 13 }}>
                      答题用时: {formatDuration(item.duration)}
                    </div>
                  )}
                </div>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={pwdModalOpen}
        onOk={handleChangePassword}
        onCancel={() => setPwdModalOpen(false)}
        confirmLoading={pwdLoading}
        destroyOnClose
        okText="确认修改"
        cancelText="取消"
      >
        <Form form={pwdForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item
            name="old_password"
            label="原密码"
            rules={[{ required: true, message: '请输入原密码' }]}
          >
            <Input.Password placeholder="请输入原密码" />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, min: 6, message: '新密码至少6位' }]}
          >
            <Input.Password placeholder="请输入新密码（至少6位）" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
