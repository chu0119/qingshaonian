/**
 * Axios 客户端 - 统一错误处理
 * 自动提取后端错误信息，供调用方直接使用
 */
import axios from 'axios';
import { message } from 'antd';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// 请求拦截器：自动添加 token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 从 axios error 中提取用户友好的错误信息
 * 优先级：detail.message > detail(string) > status code 含义
 */
function extractMsg(error: any): string {
  if (!error.response) {
    if (error.code === 'ECONNABORTED') return '请求超时，请检查网络后重试';
    return '网络连接失败，请检查网络';
  }
  const { status, data } = error.response;
  const detail = data?.detail || data?.message;
  let msg = '';
  if (typeof detail === 'object' && detail !== null) {
    msg = detail.message || detail.msg || '';
  } else if (typeof detail === 'string') {
    msg = detail;
  }
  if (msg) return msg;
  switch (status) {
    case 400: return '请求参数错误，请检查输入';
    case 401: return '登录已过期，请重新登录';
    case 403: return '无权限执行此操作';
    case 404: return '请求的资源不存在';
    case 409: return '数据冲突，请刷新后重试';
    case 422: return '数据验证失败，请检查输入格式';
    case 423: return '账号已被锁定，请稍后重试';
    case 429: return '请求过于频繁，请稍后重试';
    case 500: return '服务器内部错误，请联系管理员';
    case 502: return '服务暂时不可用，请稍后重试';
    case 503: return '服务维护中，请稍后重试';
    default: return `请求失败 (${status})`;
  }
}

// 响应拦截器
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const { status } = error.response || {};

    // 401 → 跳转登录
    if (status === 401) {
      const currentPath = window.location.pathname;
      if (currentPath !== '/login') {
        sessionStorage.setItem('redirect_after_login', currentPath);
        const hasPlatform = !!localStorage.getItem('platform_token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        if (!hasPlatform) {
          localStorage.removeItem('platform_token');
          localStorage.removeItem('platform_user');
          localStorage.removeItem('platform_school_name');
        }
        message.warning('登录已过期，请重新登录');
        window.location.href = '/login';
      }
    }

    // 将提取的错误信息挂到 error 上，供调用方使用
    const msg = extractMsg(error);
    if (error.response?.data) {
      error.response.data._extractedMessage = msg;
    }
    error._friendlyMessage = msg;

    // 网络错误自动提示
    if (!error.response) {
      message.error(msg, 5);
    }

    return Promise.reject(error);
  }
);

export default client;
