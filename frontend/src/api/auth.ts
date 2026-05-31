import client from './client';
import type { LoginRequest, LoginResponse, UserInfo, CaptchaResponse } from '../types/auth';

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await client.post('/auth/login', data);
  return res.data.data;
}

export async function getMe(): Promise<UserInfo> {
  const res = await client.get('/auth/me');
  return res.data.data;
}

export async function changePassword(old_password: string, new_password: string) {
  const res = await client.put('/auth/change-password', { old_password, new_password });
  return res.data;
}

export async function resetPassword(user_id: number, new_password: string) {
  const res = await client.put(`/auth/reset-password/${user_id}`, { new_password });
  return res.data;
}

export async function enterSchool(school_id: number): Promise<LoginResponse> {
  const res = await client.post(`/platform/schools/${school_id}/enter`);
  return res.data.data;
}

export async function getCaptcha(): Promise<CaptchaResponse> {
  const res = await client.get('/auth/captcha');
  return res.data.data;
}
