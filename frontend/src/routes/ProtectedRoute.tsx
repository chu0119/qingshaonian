import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../stores/authStore';
import client from '../api/client';

const SCHOOL_ROLES = new Set(['school_admin', 'teacher', 'counselor']);

interface Props {
  children: React.ReactNode;
  roles?: string[];
}

let _userRefreshed = false;

export default function ProtectedRoute({ children, roles }: Props) {
  const { user, token } = useAuthStore();
  const location = useLocation();
  const [refreshing, setRefreshing] = useState(!!token && !!user && !_userRefreshed);

  useEffect(() => {
    if (!token || !user || _userRefreshed) return;
    _userRefreshed = true;
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

  if (user.must_change_password && location.pathname !== '/change-password') {
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
