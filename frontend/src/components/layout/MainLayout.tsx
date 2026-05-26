import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Avatar, Drawer, Modal, Form, Input, message, Typography } from 'antd';
import {
  DashboardOutlined, TeamOutlined, UserOutlined, FileTextOutlined,
  AlertOutlined, SettingOutlined, BarChartOutlined,
  LogoutOutlined, KeyOutlined, MenuOutlined,
  BankOutlined, SafetyOutlined, ScheduleOutlined, CheckSquareOutlined, ContactsOutlined,
  FundOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { changePassword } from '../../api/auth';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isMobile;
}

const menuConfigs: Record<string, { key: string; icon: React.ReactNode; label: string; path: string }[]> = {
  school_admin: [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '首页看板', path: '/school-admin/dashboard' },
    { key: 'classes', icon: <BankOutlined />, label: '班级管理', path: '/school-admin/classes' },
    { key: 'students', icon: <TeamOutlined />, label: '学生管理', path: '/school-admin/students' },
    { key: 'teachers', icon: <ContactsOutlined />, label: '教师管理', path: '/school-admin/teachers' },
    { key: 'questionnaires', icon: <FileTextOutlined />, label: '问卷库', path: '/school-admin/questionnaires' },
    { key: 'tasks', icon: <ScheduleOutlined />, label: '问卷任务', path: '/school-admin/tasks' },
    { key: 'risks', icon: <AlertOutlined />, label: '风险预警', path: '/school-admin/risks' },
    { key: 'interventions', icon: <SafetyOutlined />, label: '干预记录', path: '/school-admin/interventions' },
    { key: 'reports', icon: <BarChartOutlined />, label: '数据报表', path: '/school-admin/reports' },
    { key: 'screen', icon: <FundOutlined />, label: '数据大屏', path: '/school-admin/screen' },
    { key: 'settings', icon: <SettingOutlined />, label: '系统设置', path: '/school-admin/settings' },
  ],
  teacher: [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '教师首页', path: '/teacher/dashboard' },
    { key: 'classes', icon: <BankOutlined />, label: '我的班级', path: '/teacher/classes' },
    { key: 'questionnaires', icon: <FileTextOutlined />, label: '我的问卷', path: '/teacher/questionnaires' },
    { key: 'tasks', icon: <ScheduleOutlined />, label: '发布问卷', path: '/teacher/tasks' },
    { key: 'completion', icon: <CheckSquareOutlined />, label: '完成情况', path: '/teacher/completion' },
    { key: 'risks', icon: <AlertOutlined />, label: '风险学生', path: '/teacher/risks' },
    { key: 'interventions', icon: <SafetyOutlined />, label: '干预记录', path: '/teacher/interventions' },
    { key: 'reports', icon: <BarChartOutlined />, label: '班级报告', path: '/teacher/reports' },
  ],
  platform_admin: [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '平台首页', path: '/platform/dashboard' },
    { key: 'schools', icon: <BankOutlined />, label: '学校管理', path: '/platform/schools' },
    { key: 'screen', icon: <FundOutlined />, label: '平台大屏', path: '/platform/screen' },
    { key: 'settings', icon: <SettingOutlined />, label: '平台设置', path: '/platform/settings' },
  ],
  counselor: [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '心理老师首页', path: '/counselor/dashboard' },
    { key: 'risks', icon: <AlertOutlined />, label: '风险学生', path: '/counselor/risks' },
    { key: 'interventions', icon: <SafetyOutlined />, label: '辅导记录', path: '/counselor/interventions' },
  ],
};

const roleLabels: Record<string, string> = { school_admin: '学校管理员', teacher: '教师', counselor: '心理老师', platform_admin: '平台管理员' };

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdForm] = Form.useForm();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useIsMobile();

  if (!user) return null;

  const effectiveRole = user.role;
  const menuItems = menuConfigs[effectiveRole] || [];
  const currentKey = menuItems.find((item) => location.pathname.startsWith(item.path))?.key || 'dashboard';

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
    { key: 'info', label: (<div style={{ padding: '4px 0' }}><div style={{ fontWeight: 600, fontSize: 14, color: '#262626' }}>{user.real_name}</div><div style={{ fontSize: 12, color: '#8c8c8c' }}>{roleLabels[user.role] || user.role}</div></div>), disabled: true },
    { type: 'divider' as const },
    { key: 'changePassword', icon: <KeyOutlined />, label: '修改密码' },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') { logout(); navigate('/login'); }
    else if (key === 'changePassword') { pwdForm.resetFields(); setPwdModalOpen(true); }
  };

  const navMenu = (
    <Menu
      mode="inline"
      theme="dark"
      selectedKeys={[currentKey]}
      items={menuItems.map((item) => ({
        key: item.key,
        icon: item.icon,
        label: item.label,
        onClick: () => { navigate(item.path); setDrawerOpen(false); },
      }))}
      style={{ background: 'transparent', borderInlineEnd: 'none', marginTop: 4 }}
    />
  );

  const logoArea = (
    <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'linear-gradient(135deg, rgba(22,119,255,0.15) 0%, rgba(0,21,41,0) 100%)', marginBottom: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg, #1677ff, #4096ff)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 8px rgba(22,119,255,0.4)', flexShrink: 0 }}>
          <SafetyOutlined style={{ fontSize: 20, color: '#fff' }} />
        </div>
        <span style={{ fontSize: 17, fontWeight: 700, color: '#ffffff', whiteSpace: 'nowrap', letterSpacing: 1 }}>青盾</span>
      </div>
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* PC: 固定侧边栏 */}
      {!isMobile && (
        <Sider trigger={null} collapsible collapsed={collapsed} width={240} collapsedWidth={64}
          style={{ background: '#001529', boxShadow: '2px 0 8px 0 rgba(0,0,0,0.12)', overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 100 }}
        >
          {logoArea}
          {navMenu}
          {!collapsed && (
            <div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, textAlign: 'center', color: 'rgba(255,255,255,0.25)', fontSize: 12, padding: '0 16px' }}>
              <Typography.Text style={{ color: 'rgba(255,255,255,0.25)', fontSize: 12 }}>青少年风险防范测评 v1.0</Typography.Text>
            </div>
          )}
        </Sider>
      )}

      {/* 移动端: Drawer */}
      {isMobile && (
        <Drawer placement="left" width={240} open={drawerOpen} onClose={() => setDrawerOpen(false)}
          styles={{ body: { padding: 0, background: '#001529' } }}>
          {logoArea}
          {navMenu}
        </Drawer>
      )}

      <Layout style={{ marginLeft: isMobile ? 0 : (collapsed ? 64 : 240), transition: 'margin-left 0.2s' }}>
        <Header style={{ padding: isMobile ? '0 12px' : '0 24px', background: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64, borderBottom: '1px solid #f0f0f0', boxShadow: '0 1px 4px 0 rgba(0,0,0,0.04)', position: 'sticky', top: 0, zIndex: 50 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile ? (
              <Button type="text" icon={<MenuOutlined style={{ fontSize: 18 }} />} onClick={() => setDrawerOpen(true)}
                style={{ width: 40, height: 40, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />
            ) : (
              <Button type="text"
                icon={collapsed ? <SettingOutlined style={{ fontSize: 18 }} /> : <SettingOutlined style={{ fontSize: 18, transform: 'rotate(180deg)' }} />}
                onClick={() => setCollapsed(!collapsed)}
                style={{ width: 40, height: 40, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />
            )}
            {!isMobile && <div style={{ height: 24, width: 1, background: '#f0f0f0' }} />}
            <Typography.Text strong style={{ fontSize: isMobile ? 14 : 16, color: '#262626' }}>
              {menuItems.find((item) => location.pathname.startsWith(item.path))?.label || ''}
            </Typography.Text>
          </div>

          <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight" trigger={['click']}>
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px 4px 4px', borderRadius: 10, transition: 'all 0.2s', background: 'transparent' }}>
              <Avatar icon={<UserOutlined />} size={isMobile ? 30 : 34} style={{ backgroundColor: '#1677ff', boxShadow: '0 2px 6px rgba(22,119,255,0.3)' }} />
              {!isMobile && (
                <div style={{ lineHeight: 1.3 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#262626' }}>{user.real_name}</div>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>{roleLabels[user.role] || ''}</div>
                </div>
              )}
            </div>
          </Dropdown>
        </Header>

        <Content style={{ margin: isMobile ? '12px 8px' : '20px 24px 24px', padding: isMobile ? 16 : 24, background: '#ffffff', borderRadius: 12, minHeight: 280, boxShadow: '0 1px 3px 0 rgba(0,0,0,0.04)' }}>
          <Outlet />
        </Content>

        <div style={{ textAlign: 'center', padding: `0 ${isMobile ? 8 : 24}px 16px`, color: 'rgba(0,0,0,0.3)', fontSize: 12 }}>
          陕西安楠云芯科技有限公司 &nbsp;
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>陕ICP备2026008842号-1</a>
        </div>
      </Layout>

      <Modal title="修改密码" open={pwdModalOpen} onOk={handleChangePassword} onCancel={() => setPwdModalOpen(false)} destroyOnClose okText="确认修改" cancelText="取消">
        <Form form={pwdForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}><Input.Password placeholder="请输入原密码" /></Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: '新密码至少6位' }]}><Input.Password placeholder="请输入新密码（至少6位）" /></Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" dependencies={['new_password']} rules={[{ required: true, message: '请再次输入新密码' }, ({ getFieldValue }) => ({ validator(_, value) { if (!value || getFieldValue('new_password') === value) return Promise.resolve(); return Promise.reject(new Error('两次输入的密码不一致')); } })]}><Input.Password placeholder="请再次输入新密码" /></Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
