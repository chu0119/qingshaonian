import { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Layout, Button, Dropdown, Avatar, theme, Modal, Form, Input, message } from 'antd';
import { UserOutlined, LogoutOutlined, HomeOutlined, FormOutlined, CheckCircleOutlined, KeyOutlined, MenuOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { changePassword } from '../../api/auth';
import type { MenuProps } from 'antd';

const { Header, Content } = Layout;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isMobile;
}

export default function StudentLayout() {
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdForm] = Form.useForm();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { token: themeToken } = theme.useToken();
  const isMobile = useIsMobile();

  if (!user) return null;

  const handleChangePassword = async () => {
    try {
      const values = await pwdForm.validateFields();
      await changePassword(values.old_password, values.new_password);
      message.success('密码修改成功，请重新登录');
      setPwdModalOpen(false);
      pwdForm.resetFields();
      logout();
      navigate('/login');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('密码修改失败，请重试');
    }
  };

  const userMenuItems: MenuProps['items'] = [
    { key: 'changePassword', icon: <KeyOutlined />, label: '修改密码' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const navItems: MenuProps['items'] = [
    { key: 'home', icon: <HomeOutlined />, label: '首页' },
    { key: 'pending', icon: <FormOutlined />, label: '待填写' },
    { key: 'completed', icon: <CheckCircleOutlined />, label: '已完成' },
  ];

  const handleNavClick: MenuProps['onClick'] = ({ key }) => {
    const map: Record<string, string> = { home: '/student/home', pending: '/student/pending', completed: '/student/completed' };
    if (map[key]) navigate(map[key]);
  };

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') { logout(); navigate('/login'); }
    else if (key === 'changePassword') { pwdForm.resetFields(); setPwdModalOpen(true); }
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#F5F7FA' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#FFFFFF',
        padding: isMobile ? '0 8px' : '0 16px', borderBottom: `1px solid ${themeToken.colorBorderSecondary}`, height: 56 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 24 }}>
          <span style={{ fontSize: isMobile ? 15 : 17, fontWeight: 600, color: themeToken.colorPrimary, whiteSpace: 'nowrap' }}>
            {isMobile ? '青盾' : '青盾 · 青少年风险防范测评'}
          </span>
          {isMobile ? (
            <Dropdown menu={{ items: navItems, onClick: handleNavClick }} trigger={['click']}>
              <Button type="text" icon={<MenuOutlined />} size="small" />
            </Dropdown>
          ) : (
            <div style={{ display: 'flex', gap: 4 }}>
              <Button type="text" icon={<HomeOutlined />} onClick={() => navigate('/student/home')}>首页</Button>
              <Button type="text" icon={<FormOutlined />} onClick={() => navigate('/student/pending')}>待填写</Button>
              <Button type="text" icon={<CheckCircleOutlined />} onClick={() => navigate('/student/completed')}>已完成</Button>
            </div>
          )}
        </div>
        <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
          <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#5B8DEF' }} size="small" />
            {!isMobile && <span style={{ fontSize: 14 }}>{user.real_name}</span>}
          </div>
        </Dropdown>
      </Header>
      <Content style={{ margin: isMobile ? '8px' : '16px auto', padding: isMobile ? 12 : 24, maxWidth: 800, width: '100%', minHeight: 280 }}>
        <Outlet />
      </Content>

      <div style={{ textAlign: 'center', paddingBottom: 16, color: 'rgba(0, 0, 0, 0.3)', fontSize: 12 }}>
        陕西安楠云芯科技有限公司 &nbsp;
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>
          陕ICP备2026008842号-1
        </a>
      </div>

      <Modal title="修改密码" open={pwdModalOpen} onOk={handleChangePassword} onCancel={() => setPwdModalOpen(false)} destroyOnClose>
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: '新密码至少6位' }]}><Input.Password /></Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" dependencies={['new_password']}
            rules={[{ required: true }, ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                return Promise.reject(new Error('两次密码不一致'));
              },
            })]}><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
