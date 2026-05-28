import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const SCHOOL_ROLES = new Set(['school_admin', 'teacher', 'counselor']);

interface Props {
  children: React.ReactNode;
  roles?: string[];
}

export default function ProtectedRoute({ children, roles }: Props) {
  const { user, token } = useAuthStore();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    // 平台管理员代入学校上下文时可访问所有学校级页面
    if (user.role === 'platform_admin' && roles.some(r => SCHOOL_ROLES.has(r))) {
      return <>{children}</>;
    }
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
