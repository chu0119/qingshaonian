import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, message, Result, Button } from 'antd';
import client from '../../api/client';

export default function QREntry() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'error' | 'done'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setErrorMsg('无效的二维码链接');
      return;
    }

    // 验证 token 并获取任务信息
    client.get('/auth/me').then(() => {
      // 已登录，直接跳转到待办列表
      message.success('扫码成功，请开始答题');
      navigate('/student/pending');
    }).catch(() => {
      // 未登录，跳转到登录页并携带 token
      message.info('请先登录后开始答题');
      navigate(`/login?redirect=/student/pending&qr_token=${token}`);
    });
  }, [searchParams, navigate]);

  if (status === 'loading') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="正在验证二维码..." />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Result
        status="error"
        title="扫码失败"
        subTitle={errorMsg}
        extra={<Button type="primary" onClick={() => navigate('/login')}>返回登录</Button>}
      />
    </div>
  );
}
