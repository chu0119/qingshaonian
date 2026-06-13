import client from './client';

export async function getNotifications(params?: Record<string, unknown>) {
  const res = await client.get('/notifications', { params });
  return res.data.data;
}

export async function getUnreadCount() {
  const res = await client.get('/notifications/unread-count');
  return res.data.data as { count: number };
}

export async function markRead(id: number) {
  const res = await client.put(`/notifications/${id}/read`);
  return res.data;
}

export async function markAllRead() {
  const res = await client.put('/notifications/read-all');
  return res.data;
}

export async function createNotification(data: Record<string, unknown>) {
  const res = await client.post('/notifications', data);
  return res.data;
}

export async function deleteNotification(id: number) {
  const res = await client.delete(`/notifications/${id}`);
  return res.data;
}
