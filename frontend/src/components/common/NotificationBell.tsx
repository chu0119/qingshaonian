import { useState, useEffect, useCallback } from 'react';
import { Badge, Popover, List, Button, Typography, Space, Empty, Tag, message } from 'antd';
import { BellOutlined, CheckOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface NotificationItem {
  id: number;
  type: string;
  title: string;
  content: string;
  related_type?: string;
  related_id?: number;
  is_read: boolean;
  created_at?: string;
}

const typeLabels: Record<string, { color: string; label: string }> = {
  task: { color: 'blue', label: '任务' },
  risk: { color: 'red', label: '预警' },
  intervention: { color: 'orange', label: '干预' },
  system: { color: 'default', label: '系统' },
};

export default function NotificationBell() {
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const r = await client.get('/notifications/unread-count');
      setUnreadCount(r.data.data?.count || 0);
    } catch { /* silent */ }
  }, []);

  const fetchItems = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    try {
      const r = await client.get('/notifications', { params: { page: 1, page_size: 15 } });
      setItems(r.data.data?.items || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [open]);

  useEffect(() => { fetchUnreadCount(); }, [fetchUnreadCount]);
  useEffect(() => { fetchItems(); }, [fetchItems]);

  // Poll unread count every 60 seconds
  useEffect(() => {
    const timer = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(timer);
  }, [fetchUnreadCount]);

  const handleMarkRead = async (id: number) => {
    try {
      await client.put(`/notifications/${id}/read`);
      setItems(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch { /* silent */ }
  };

  const handleNotificationClick = async (item: NotificationItem) => {
    if (!item.is_read) await handleMarkRead(item.id);
    setOpen(false);
    if (item.related_type === 'task' && item.related_id) {
      const path = window.location.pathname;
      if (path.startsWith('/student')) navigate('/student/pending');
      else if (path.startsWith('/platform')) navigate('/platform/tasks');
      else navigate('/school-admin/tasks');
    } else if (item.related_type === 'risk' && item.related_id) {
      const path = window.location.pathname;
      if (path.startsWith('/platform')) navigate('/platform/risks');
      else navigate('/school-admin/risks');
    } else if (item.related_type === 'intervention' && item.related_id) {
      const path = window.location.pathname;
      if (path.startsWith('/teacher') || path.startsWith('/counselor')) navigate('/teacher/interventions');
      else navigate('/school-admin/interventions');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await client.put('/notifications/read-all');
      setItems(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      message.success('全部已读');
    } catch { message.error('操作失败'); }
  };

  const formatTime = (v?: string) => {
    if (!v) return '';
    const d = new Date(v);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return d.toLocaleDateString('zh-CN');
  };

  const content = (
    <div style={{ width: Math.min(360, window.innerWidth - 48), maxHeight: 480, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, padding: '0 4px' }}>
        <Typography.Text strong>消息通知</Typography.Text>
        {unreadCount > 0 && (
          <Button type="link" size="small" icon={<CheckOutlined />} onClick={handleMarkAllRead}>全部已读</Button>
        )}
      </div>
      {items.length === 0 ? (
        <Empty description="暂无消息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          loading={loading}
          dataSource={items}
          size="small"
          renderItem={(item) => (
            <List.Item
              style={{
                padding: '8px 4px', cursor: 'pointer',
                background: item.is_read ? 'transparent' : '#f6f8ff',
                borderRadius: 4,
              }}
              onClick={() => handleNotificationClick(item)}
            >
              <List.Item.Meta
                title={
                  <Space size={4}>
                    <Tag color={typeLabels[item.type]?.color || 'default'} style={{ marginRight: 0 }}>
                      {typeLabels[item.type]?.label || item.type}
                    </Tag>
                    <Typography.Text strong={!item.is_read} style={{ fontSize: 13 }}>{item.title}</Typography.Text>
                  </Space>
                }
                description={
                  <div>
                    {item.content && <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{item.content.slice(0, 60)}</div>}
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>{formatTime(item.created_at)}</Typography.Text>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  return (
    <Popover content={content} trigger="click" open={open} onOpenChange={setOpen} placement="bottomRight">
      <Badge count={unreadCount} size="small" offset={[-2, 2]}>
        <BellOutlined style={{ fontSize: 18, cursor: 'pointer', padding: '4px 8px' }} />
      </Badge>
    </Popover>
  );
}
