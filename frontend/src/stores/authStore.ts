import { create } from 'zustand';
import type { UserInfo } from '../types/auth';

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  setAuth: (user: UserInfo, token: string) => void;
  updateUser: (user: Partial<UserInfo>) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  savePlatformSession: () => void;
  restorePlatformSession: () => boolean;
  hasPlatformSession: () => boolean;
  platformSchoolName: () => string;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('access_token'),

  setAuth: (user, token) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('access_token', token);
    set({ user, token });
  },

  updateUser: (partial) => {
    const current = get().user;
    if (!current) return;
    const updated = { ...current, ...partial };
    localStorage.setItem('user', JSON.stringify(updated));
    set({ user: updated });
  },

  logout: () => {
    const hasPlatform = !!localStorage.getItem('platform_token');
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    if (!hasPlatform) {
      localStorage.removeItem('platform_token');
      localStorage.removeItem('platform_user');
      localStorage.removeItem('platform_school_name');
    }
    set({ user: null, token: null });
  },

  savePlatformSession: () => {
    const { token, user } = get();
    if (token && user) {
      localStorage.setItem('platform_token', token);
      localStorage.setItem('platform_user', JSON.stringify(user));
    }
  },

  restorePlatformSession: () => {
    const token = localStorage.getItem('platform_token');
    const user = JSON.parse(localStorage.getItem('platform_user') || 'null');
    if (token && user) {
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('access_token', token);
      localStorage.removeItem('platform_token');
      localStorage.removeItem('platform_user');
      localStorage.removeItem('platform_school_name');
      return true;
    }
    return false;
  },

  hasPlatformSession: () => {
    return !!localStorage.getItem('platform_token');
  },

  platformSchoolName: () => {
    return localStorage.getItem('platform_school_name') || '';
  },

  isAuthenticated: () => {
    return !!get().token;
  },
}));
