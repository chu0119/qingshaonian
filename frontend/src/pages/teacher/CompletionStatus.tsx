import { useState, useEffect } from 'react';
import { Table, Tag, Typography, Select, message } from 'antd';
import client from '../../api/client';

export default function CompletionStatus() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskLoading, setTaskLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<number | null>(null);
  const [completions, setCompletions] = useState<any[]>([]);

  useEffect(() => {
    const fetchTasks = async () => {
      setTaskLoading(true);
      try {
        const r = await client.get('/tasks', { params: { page: 1, page_size: 50 } });
        setTasks(r.data.data.items || []);
      } catch (err: any) {
        message.error(err._friendlyMessage || '获取任务列表失败');
      } finally {
        setTaskLoading(false);
      }
    };
    fetchTasks();
  }, []);

  useEffect(() => {
    if (!selectedTask) {
      setCompletions([]);
      return;
    }
    const fetchCompletions = async () => {
      setLoading(true);
      try {
        const r = await client.get(`/tasks/${selectedTask}/completion`);
        setCompletions(r.data.data || []);
      } catch (err: any) {
        message.error(err?.response?.data?.message || '获取完成情况失败');
      } finally {
        setLoading(false);
      }
    };
    fetchCompletions();
  }, [selectedTask]);

  const columns = [
    { title: '学生', dataIndex: 'student_name', key: 'student_name' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'submitted' ? 'green' : 'default'}>{v === 'submitted' ? '已完成' : '未完成'}</Tag> },
    { title: '提交时间', dataIndex: 'submitted_at', key: 'submitted_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
  ];

  return (
    <div>
      <Typography.Title level={4}>完成情况</Typography.Title>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>选择任务：</span>
        <Select
          placeholder="请选择任务"
          style={{ width: '100%', maxWidth: 360 }}
          value={selectedTask}
          onChange={v => setSelectedTask(v)}
          loading={taskLoading}
          allowClear
          options={tasks.map((t: any) => ({
            value: t.id,
            label: `${t.name} (${t.completed_count || 0}人已提交)`,
          }))}
        />
      </div>
      {selectedTask && (
        <Table
          rowKey="student_id"
          dataSource={completions}
          columns={columns}
          loading={loading}
          scroll={{ x: 'max-content' }}
          pagination={false}
        />
      )}
    </div>
  );
}
