import { useEffect, useRef, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../stores/authStore';
import client from '../api/client';

const SCHOOL_ROLES = new Set(['school_admin', 'teacher', 'counselor']);

interface Props {
  children: React.ReactNode;
  roles?: string[];
}

export default function ProtectedRoute({ children, roles }: Props) {
  const { user, token } = useAuthStore();
  const location = useLocation();
  const userRefreshed = useRef(false);
  const [refreshing, setRefreshing] = useState(!!token && !!user && !userRefreshed.current);

  useEffect(() => {
    if (!token || !user || userRefreshed.current) return;
    userRefreshed.current = true;
    setRefreshing(true);
    client.get('/auth/me').then(r => {
      const serverUser = r.data.data;
      if (serverUser) {
        useAuthStore.getState().updateUser({ must_change_password: serverUser.must_change_password });
      }
    }).catch(() => {
      // token 无效，清除状态
      useAuthStore.getState().logout();
    }).finally(() => setRefreshing(false));
  }, [token, user]);

  if (refreshing) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>;
  }

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.must_change_password && location.pathname !== '/change-password' && !sessionStorage.getItem('skip_password_change')) {
    return <Navigate to="/change-password" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    if (user.role === 'platform_admin' && roles.some(r => SCHOOL_ROLES.has(r))) {
      return <>{children}</>;
    }
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
