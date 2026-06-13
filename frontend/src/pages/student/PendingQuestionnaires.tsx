import { useState, useEffect } from 'react';
import { Card, List, Button, Tag, message, Typography, Empty, Space } from 'antd';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

export default function PendingQuestionnaires() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    client.get('/student/tasks/pending').then(r => {
      setTasks((r.data.data || []).filter((t: any) => t.status !== 'submitted'));
    }).catch((err: any) => {
      message.error(err._friendlyMessage || '获取待填写问卷失败');
    }).finally(() => setLoading(false));
  }, []);

  const statusTag = (item: any) => {
    if (!item.can_answer) return <Tag color="default">暂不可填写</Tag>;
    if (item.status === 'in_progress') return <Tag color="blue">已保存进度</Tag>;
    return <Tag color="green">待填写</Tag>;
  };

  const startOrContinue = (item: any) => {
    if (!item.can_answer) {
      message.info('当前任务暂不可填写，请留意开始时间和截止时间');
      return;
    }
    if (item.answer_sheet_id) {
      navigate(`/student/answer/${item.answer_sheet_id}`);
      return;
    }
    client.post(`/student/tasks/${item.task_id}/start`).then(r => {
      navigate(`/student/answer/${r.data.data.answer_sheet_id}`);
    }).catch((err: any) => message.error(err?.response?.data?.message || '开始答题失败，请重试'));
  };

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>待填写问卷</Typography.Title>
      {tasks.length === 0 ? (
        <Card loading={loading} style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          <Empty description="暂无待填写问卷" />
        </Card>
      ) : (
        <List dataSource={tasks} renderItem={(item: any) => (
          <Card size="small" style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <Space style={{ marginBottom: 4 }}>
                  <span style={{ fontWeight: 600 }}>{item.questionnaire_title}</span>
                  {statusTag(item)}
                </Space>
                <div style={{ color: '#595959', fontSize: 13 }}>{item.task_name}</div>
                <div style={{ color: '#8c8c8c', fontSize: 13 }}>
                  截止时间：{item.end_time ? new Date(item.end_time).toLocaleString('zh-CN') : '未设置'}
                </div>
                {item.description && <div style={{ color: '#8c8c8c', fontSize: 13, marginTop: 4 }}>{item.description}</div>}
              </div>
              <Button type="primary" disabled={!item.can_answer} onClick={() => startOrContinue(item)}>
                {item.status === 'in_progress' ? '继续填写' : '开始填写'}
              </Button>
            </div>
          </Card>
        )} />
      )}
    </div>
  );
}
