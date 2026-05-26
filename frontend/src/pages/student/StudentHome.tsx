import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, List, Button, Tag, Typography, message, Space } from 'antd';
import { FormOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

export default function StudentHome() {
  const navigate = useNavigate();
  const [pending, setPending] = useState<any[]>([]);
  const [completedCount, setCompletedCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    client.get('/student/tasks/pending').then(r => {
      const tasks = r.data.data || [];
      setPending(tasks.filter((t: any) => t.status !== 'submitted').slice(0, 5));
      setPendingCount(tasks.filter((t: any) => t.status !== 'submitted').length);
      setCompletedCount(tasks.filter((t: any) => t.status === 'submitted').length);
    }).catch(() => message.error('获取任务列表失败'));
  }, []);

  return (
    <div>
      <Typography.Title level={4}>欢迎回来</Typography.Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8}><Card><Statistic title="待填写问卷" value={pendingCount} prefix={<FormOutlined />} valueStyle={{ color: '#4A90D9' }} /></Card></Col>
        <Col xs={12} sm={8}><Card><Statistic title="已完成问卷" value={completedCount} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#67C23A' }} /></Card></Col>
        <Col xs={24} sm={8}><Card><Statistic title="待填写" value={pendingCount} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#E6A23C' }} /></Card></Col>
      </Row>

      <Typography.Title level={5}>待填写问卷</Typography.Title>
      {pending.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无待填写问卷</Card>
      ) : (
        <List dataSource={pending} renderItem={(item: any) => (
          <Card size="small" style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500 }}>{item.questionnaire_title}</div>
                <div style={{ color: '#888', fontSize: 13 }}>{item.task_name} · 截止: {item.end_time?.split('T')[0] || '无'}</div>
              </div>
              <Button type="primary" onClick={() => {
                if (item.answer_sheet_id) {
                  navigate(`/student/answer/${item.answer_sheet_id}`);
                } else {
                  client.post(`/student/tasks/${item.task_id}/start`).then(r => {
                    navigate(`/student/answer/${r.data.data.answer_sheet_id}`);
                  }).catch(() => message.error('开始答题失败，请重试'));
                }
              }}>
                {item.status === 'in_progress' ? '继续填写' : '开始填写'}
              </Button>
            </div>
          </Card>
        )} />
      )}
    </div>
  );
}
