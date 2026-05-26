import axios from 'axios';
import type { APIResponse } from '../types/common';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    if (error.response?.data?.detail && !error.response.data.message) {
      error.response.data.message = error.response.data.detail;
    }
    return Promise.reject(error);
  }
);

export default client;
