import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Typography, message, Modal, Space } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons';
import { login } from '../api/auth';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isMobile;
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotStep, setForgotStep] = useState<'form' | 'code'>('form');
  const [resetPhone, setResetPhone] = useState('');
  const [resetUsername, setResetUsername] = useState('');
  const [sendingCode, setSendingCode] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const isMobile = useIsMobile();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const result = await login(values);
      setAuth(result.user, result.access_token);
      message.success('登录成功');
      const rolePathMap: Record<string, string> = {
        school_admin: '/school-admin/dashboard',
        teacher: '/teacher/dashboard',
        counselor: '/counselor/dashboard',
        student: '/student/home',
      };
      navigate(rolePathMap[result.user.role] || '/', { replace: true });
    } catch {
      message.error('账号或密码错误，请重试');
    } finally {
      setLoading(false);
    }
  };

  const leftPanel = (
    <div
      style={{
        flex: isMobile ? undefined : 1,
        minHeight: isMobile ? undefined : '100%',
        background: 'linear-gradient(160deg, #020a1f 0%, #0a1a3a 25%, #0d2456 55%, #10306e 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: isMobile ? '40px 24px' : 60,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <style>{`
        @keyframes gridMove { 0% { transform: translate(0, 0); } 100% { transform: translate(50px, 50px); } }
        @keyframes floatParticle { 0%, 100% { transform: translateY(0) scale(1); opacity: 0.2; } 25% { transform: translateY(-18px) scale(1.3); opacity: 0.35; } 50% { transform: translateY(-8px) scale(0.85); opacity: 0.25; } 75% { transform: translateY(12px) scale(1.15); opacity: 0.3; } }
        @keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 0.85; } }
        @keyframes scanLineV { 0% { top: -2px; } 100% { top: 100%; } }
      `}</style>

      <div
        style={{
          position: 'absolute', top: -50, left: -50, right: -50, bottom: -50,
          backgroundImage: `linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px)`,
          backgroundSize: '50px 50px', animation: 'gridMove 25s linear infinite', zIndex: 0,
        }}
      />

      {!isMobile && Array.from({ length: 25 }).map((_, i) => (
        <div key={i} style={{ position: 'absolute', width: `${2+Math.random()*5}px`, height: `${2+Math.random()*5}px`, borderRadius: '50%', background: i%3===0 ? 'rgba(0,212,255,0.6)' : i%3===1 ? 'rgba(0,245,255,0.5)' : 'rgba(255,255,255,0.35)', left: `${3+Math.random()*94}%`, top: `${3+Math.random()*94}%`, animation: `floatParticle ${7+Math.random()*14}s ease-in-out infinite`, animationDelay: `${Math.random()*6}s`, boxShadow: i%3===0 ? '0 0 8px rgba(0,212,255,0.5)' : i%3===1 ? '0 0 6px rgba(0,245,255,0.4)' : '0 0 4px rgba(255,255,255,0.3)', zIndex: 0 }} />
      ))}

      {!isMobile && (
        <>
          <div style={{ position: 'absolute', top: -120, right: -80, width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,212,255,0.12) 0%, rgba(0,212,255,0) 70%)', zIndex: 0 }} />
          <div style={{ position: 'absolute', bottom: -90, left: -50, width: 320, height: 320, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,245,255,0.08) 0%, rgba(0,245,255,0) 70%)', zIndex: 0 }} />
          <div style={{ position: 'absolute', left: 0, right: 0, height: 1, background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.12), transparent)', animation: 'scanLineV 8s linear infinite', pointerEvents: 'none', zIndex: 0 }} />
        </>
      )}

      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <div style={{ width: isMobile ? 72 : 110, height: isMobile ? 72 : 110, borderRadius: isMobile ? 20 : 30, background: 'rgba(0,212,255,0.08)', backdropFilter: 'blur(30px)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: `0 auto ${isMobile ? 24 : 40}px`, border: '1px solid rgba(0,212,255,0.25)', boxShadow: '0 0 40px rgba(0,212,255,0.12), 0 8px 32px rgba(0,0,0,0.25)' }}>
          <SafetyOutlined style={{ fontSize: isMobile ? 36 : 54, color: '#00d4ff' }} />
        </div>

        <Title level={1} style={{ color: '#fff', marginBottom: 8, fontSize: isMobile ? 36 : 52, fontWeight: 800, letterSpacing: isMobile ? 6 : 12, fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif", textShadow: '0 0 60px rgba(0,212,255,0.3)' }}>
          青盾
        </Title>

        <Text style={{ color: 'rgba(0,212,255,0.85)', fontSize: isMobile ? 14 : 18, letterSpacing: isMobile ? 2 : 6, fontWeight: 500, display: 'block', marginBottom: isMobile ? 24 : 36 }}>
          青少年风险防范测评管理系统
        </Text>

        <div style={{ width: 100, height: 2, background: 'linear-gradient(90deg, rgba(0,212,255,0), rgba(0,212,255,0.5), rgba(0,212,255,0))', borderRadius: 2, margin: '0 auto 30px' }} />

        <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: isMobile ? 14 : 16, letterSpacing: isMobile ? 4 : 8, marginBottom: 12 }}>
          守护青春，预见未来
        </p>
      </div>

      <div style={{ position: isMobile ? 'relative' : 'absolute', bottom: isMobile ? undefined : 48, left: isMobile ? undefined : 60, right: isMobile ? undefined : 60, display: 'flex', flexWrap: 'wrap', gap: 24, zIndex: 1, marginTop: isMobile ? 24 : 0, justifyContent: 'center' }}>
        {[
          { title: '专业测评工具', desc: '标准化评估量表' },
          { title: '智能风险识别', desc: 'AI 辅助分析预警' },
          { title: '答题质量检测', desc: '自动筛选有效答卷' },
          { title: '数据驱动决策', desc: '可视化数据报表' },
        ].map((item, i) => (
          <div key={i} style={{ flex: isMobile ? '0 0 calc(50% - 24px)' : 1, minWidth: isMobile ? 100 : 0, textAlign: 'center', color: 'rgba(255,255,255,0.45)' }}>
            <div style={{ width: '100%', height: 1, background: 'linear-gradient(90deg, rgba(0,212,255,0), rgba(0,212,255,0.2), rgba(0,212,255,0))', marginBottom: 12 }} />
            <div style={{ fontSize: 14, fontWeight: 500, color: 'rgba(0,212,255,0.7)', marginBottom: 4 }}>{item.title}</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );

  const rightPanel = (
    <div style={{ width: isMobile ? '100%' : 480, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: isMobile ? '40px 20px' : 60, background: 'linear-gradient(180deg, #0c1932 0%, #091222 100%)', position: 'relative', minHeight: isMobile ? undefined : '100vh' }}>
      {!isMobile && (
        <div style={{ position: 'absolute', top: 60, right: -40, width: 200, height: 200, background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
      )}

      <div style={{ width: '100%', maxWidth: 360, position: 'relative', zIndex: 1 }}>
        <div style={{ marginBottom: 40 }}>
          <Title level={3} style={{ marginBottom: 8, fontWeight: 700, color: '#e8f4ff', letterSpacing: 2 }}>欢迎登录</Title>
          <Text style={{ color: '#6a8aaf', fontSize: 14 }}>请输入您的账号密码进入系统</Text>
        </div>

        <div style={{ background: 'rgba(0,20,60,0.5)', backdropFilter: 'blur(20px)', borderRadius: 16, border: '1px solid rgba(0,212,255,0.2)', padding: '36px 28px', boxShadow: '0 0 30px rgba(0,212,255,0.06), 0 4px 24px rgba(0,0,0,0.3)' }}>
          <Form name="login" onFinish={onFinish} size="large" autoComplete="off">
            <Form.Item name="username" rules={[{ required: true, message: '请输入账号' }]}>
              <Input prefix={<UserOutlined style={{ color: '#5a8aaf' }} />} placeholder="请输入账号"
                style={{ height: 50, borderRadius: 10, fontSize: 15, background: 'rgba(0,16,40,0.5)', border: '1px solid rgba(0,212,255,0.15)', color: '#e0f0ff' }} />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#5a8aaf' }} />} placeholder="请输入密码"
                style={{ height: 50, borderRadius: 10, fontSize: 15, background: 'rgba(0,16,40,0.5)', border: '1px solid rgba(0,212,255,0.15)', color: '#e0f0ff' }} />
            </Form.Item>
            <div style={{ textAlign: 'right', marginTop: -12, marginBottom: 16 }}>
              <a onClick={() => setForgotOpen(true)} style={{ color: '#5a8aaf', fontSize: 13 }}>忘记密码？</a>
            </div>
            <Form.Item style={{ marginBottom: 20 }}>
              <Button type="primary" htmlType="submit" loading={loading} block
                style={{ height: 50, borderRadius: 10, fontSize: 16, fontWeight: 600, background: 'linear-gradient(135deg, #00d4ff, #0088cc)', border: 'none', boxShadow: '0 4px 24px rgba(0,212,255,0.35)', letterSpacing: 8, color: '#fff' }}>
                登录
              </Button>
            </Form.Item>
          </Form>
          <div style={{ textAlign: 'center', padding: '16px 0 0', color: '#5a8aaf', fontSize: 12, borderTop: '1px solid rgba(0,212,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <SafetyOutlined style={{ fontSize: 14, color: '#00d4ff' }} />
            <span>安全加密传输 · 数据严格保密</span>
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center', padding: '16px 0 0', color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>
        陕西安楠云芯科技有限公司 &nbsp;
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>陕ICP备2026008842号-1</a>
      </div>
    </div>
  );

  return (
    <>
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: isMobile ? 'column' : 'row', background: '#020617' }}>
      {isMobile ? rightPanel : leftPanel}
      {isMobile ? leftPanel : rightPanel}
    </div>

    <Modal title="重置密码" open={forgotOpen} onCancel={() => { setForgotOpen(false); setForgotStep('form'); }}
      footer={null} width={isMobile ? undefined : 420} destroyOnHidden centered>
      {forgotStep === 'form' ? (
        <Form layout="vertical" onFinish={async (vals: any) => {
          setResetPhone(vals.phone); setResetUsername(vals.username);
          setSendingCode(true);
          try {
            await fetch('/api/v1/auth/send-sms-code', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: vals.phone, purpose: 'reset_password' }) });
            message.success('验证码已发送'); setForgotStep('code');
          } catch { message.error('发送失败'); }
          finally { setSendingCode(false); }
        }}>
          <Form.Item name="username" label="登录账号" rules={[{ required: true }]}><Input placeholder="请输入账号" /></Form.Item>
          <Form.Item name="phone" label="手机号" rules={[{ required: true, pattern: /^1\d{10}$/, message: '请输入11位手机号' }]}><Input placeholder="请输入绑定的手机号" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={sendingCode} block>获取验证码</Button>
        </Form>
      ) : (
        <Form layout="vertical" onFinish={async (vals: any) => {
          setResetLoading(true);
          try {
            const res = await fetch('/api/v1/auth/reset-password-by-sms', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: resetPhone, username: resetUsername, code: vals.code, new_password: vals.new_password }) });
            const data = await res.json();
            if (res.ok && data.code === 200) { message.success('密码重置成功，请用新密码登录'); setForgotOpen(false); setForgotStep('form'); }
            else { message.error(data.detail || data.message || '重置失败'); }
          } catch { message.error('重置失败，请重试'); }
          finally { setResetLoading(false); }
        }}>
          <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f6ffed', borderRadius: 6, fontSize: 13, color: '#52c41a' }}>
            验证码已发送至 {resetPhone}
          </div>
          <Form.Item name="code" label="短信验证码" rules={[{ required: true }]}><Input placeholder="请输入6位验证码" maxLength={6} /></Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}><Input.Password placeholder="请设置新密码（至少6位）" /></Form.Item>
          <Space style={{ width: '100%' }} direction="vertical">
            <Button type="primary" htmlType="submit" loading={resetLoading} block>重置密码</Button>
            <Button type="link" block onClick={() => setForgotStep('form')}>返回上一步</Button>
          </Space>
        </Form>
      )}
    </Modal>
    </>
  );
}
