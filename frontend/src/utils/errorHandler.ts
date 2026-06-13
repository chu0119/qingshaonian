/**
 * API 错误处理工具
 * 统一提取后端返回的错误信息，提供友好的用户提示
 */
import { message } from 'antd';

/** 后端错误响应格式 */
interface BackendError {
  detail?: string | { message?: string; captcha_required?: boolean; [key: string]: any };
  message?: string;
  code?: number;
}

/** 从 axios error 中提取用户友好的错误信息 */
export function extractErrorMessage(error: any): string {
  // 网络错误
  if (!error.response) {
    if (error.code === 'ECONNABORTED') return '请求超时，请检查网络后重试';
    if (error.message?.includes('Network Error')) return '网络连接失败，请检查网络';
    return '网络异常，请稍后重试';
  }

  const { status, data } = error.response;
  const detail = data?.detail || data?.message;

  // 解析 detail 字段
  let msg = '';
  if (typeof detail === 'object' && detail !== null) {
    msg = detail.message || detail.msg || '';
  } else if (typeof detail === 'string') {
    msg = detail;
  } else if (typeof data === 'string') {
    msg = data;
  }

  // 按状态码补充上下文
  switch (status) {
    case 400:
      return msg || '请求参数错误，请检查输入';
    case 401:
      if (msg.includes('密码') || msg.includes('账号')) return msg;
      return msg || '登录已过期，请重新登录';
    case 403:
      return msg || '无权限执行此操作';
    case 404:
      return msg || '请求的资源不存在';
    case 409:
      return msg || '数据冲突，请刷新后重试';
    case 422:
      return msg || '数据验证失败，请检查输入格式';
    case 423:
      return msg || '账号已被锁定，请稍后重试';
    case 429:
      return msg || '请求过于频繁，请稍后重试';
    case 500:
      return msg || '服务器内部错误，请联系管理员';
    case 502:
      return '服务暂时不可用，请稍后重试';
    case 503:
      return '服务维护中，请稍后重试';
    default:
      return msg || `请求失败 (${status})`;
  }
}

/** 显示错误消息（统一风格） */
export function showError(error: any, duration = 5) {
  const msg = extractErrorMessage(error);
  message.error(msg, duration);
  return msg;
}

/** 显示成功消息 */
export function showSuccess(msg: string, duration = 3) {
  message.success(msg, duration);
}

/** 显示警告消息 */
export function showWarning(msg: string, duration = 4) {
  message.warning(msg, duration);
}

/** 显示加载中提示，返回关闭函数 */
export function showLoading(msg = '加载中...') {
  const hide = message.loading(msg, 0);
  return hide;
}

/** 安全的 API 调用包装器，自动处理错误 */
export async function safeApiCall<T>(
  apiFn: () => Promise<T>,
  options?: {
    successMsg?: string;
    errorMsg?: string;
    onError?: (error: any) => void;
    showSuccess?: boolean;
  }
): Promise<T | null> {
  try {
    const result = await apiFn();
    if (options?.successMsg) {
      showSuccess(options.successMsg);
    } else if (options?.showSuccess) {
      showSuccess('操作成功');
    }
    return result;
  } catch (error: any) {
    const msg = options?.errorMsg || extractErrorMessage(error);
    message.error(msg, 5);
    options?.onError?.(error);
    return null;
  }
}
