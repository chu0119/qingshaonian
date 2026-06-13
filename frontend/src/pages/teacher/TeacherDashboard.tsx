import { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Typography, message, List, Tag, Empty, Spin } from 'antd';
import { TeamOutlined, FileTextOutlined, AlertOutlined, SafetyOutlined, BankOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, METHOD_LABELS } from '../../utils/constants';

export default function TeacherDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [pendingRisks, setPendingRisks] = useState<any[]>([]);
  const [risksLoading, setRisksLoading] = useState(false);
  const [pendingInterventions, setPendingInterventions] = useState<any[]>([]);
  const [interventionsLoading, setInterventionsLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const r = await client.get('/dashboard/teacher');
        setData(r.data.data);
      } catch (err: any) {
        message.error(err._friendlyMessage || '获取看板数据失败');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    const fetchPendingRisks = async () => {
      setRisksLoading(true);
      try {
        const r = await client.get('/risks', { params: { status: 'pending', page_size: 5 } });
        const items = r.data.data?.items || r.data.data || [];
        setPendingRisks(items.slice(0, 5));
      } catch (err: any) {
        message.error(err?.response?.data?.message || '获取待处理预警失败');
      } finally {
        setRisksLoading(false);
      }
    };
    fetchPendingRisks();
  }, []);

  useEffect(() => {
    const fetchPendingInterventions = async () => {
      setInterventionsLoading(true);
      try {
        const r = await client.get('/interventions', { params: { page_size: 20 } });
        const items = r.data.data?.items || r.data.data || [];
        setPendingInterventions(items.filter((item: any) => item.need_follow_up || ['pending', 'processing', 'follow_up', 'ongoing'].includes(item.status)).slice(0, 5));
      } catch (err: any) {
        message.error(err?.response?.data?.message || '获取待跟进干预失败');
      } finally {
        setInterventionsLoading(false);
      }
    };
    fetchPendingInterventions();
  }, []);

  const stats = data?.stats || {};

  const getRiskLevelTag = (level: string) => {
    return <Tag color={RISK_COLORS[level] || 'default'}>{RISK_LABELS[level] || '-'}</Tag>;
  };

  return (
    <div>
      <Typography.Title level={4}>教师首页看板</Typography.Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="我的班级数" value={stats.my_classes || 0} prefix={<BankOutlined />} valueStyle={{ color: '#4A90D9', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="我的学生数" value={stats.my_students || 0} prefix={<TeamOutlined />} valueStyle={{ color: '#67C23A', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="进行中任务" value={stats.active_tasks || 0} prefix={<FileTextOutlined />} valueStyle={{ color: '#E6A23C', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="待处理预警" value={stats.pending_risks || 0} prefix={<AlertOutlined />} valueStyle={{ color: '#FF4D4F', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="待跟进干预" value={stats.pending_interventions || 0} prefix={<SafetyOutlined />} valueStyle={{ color: '#FA8C16', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="平均完成率" value={stats.average_completion_rate || 0} suffix="%" valueStyle={{ color: '#13C2C2', fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card loading={loading}>
            <Statistic title="未完成学生数" value={stats.uncompleted_students || 0} valueStyle={{ color: '#FA8C16', fontSize: 24 }} />
          </Card>
        </Col>
      </Row>

      {/* 待处理预警列表 和 待跟进干预列表 */}
      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={12}>
          <Card
            title={<span><AlertOutlined style={{ color: '#FF4D4F', marginRight: 8 }} />待处理风险提示</span>}
            bordered
          >
            {risksLoading ? (
              <div style={{ textAlign: 'center', padding: 30 }}><Spin /></div>
            ) : pendingRisks.length === 0 ? (
              <Empty description="暂无待处理风险提示" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                size="small"
                dataSource={pendingRisks}
                renderItem={(item: any) => (
                  <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate('/teacher/risks')}>
                    <List.Item.Meta
                      title={
                        <span>
                          {item.student_name || '未知学生'}
                          {getRiskLevelTag(item.risk_level)}
                        </span>
                      }
                      description={item.risk_reason || item.reason || '-'}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<span><SafetyOutlined style={{ color: '#FA8C16', marginRight: 8 }} />待跟进干预</span>}
            bordered
          >
            {interventionsLoading ? (
              <div style={{ textAlign: 'center', padding: 30 }}><Spin /></div>
            ) : pendingInterventions.length === 0 ? (
              <Empty description="暂无待跟进干预" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                size="small"
                dataSource={pendingInterventions}
                renderItem={(item: any) => (
                  <List.Item style={{ cursor: 'pointer' }} onClick={() => navigate('/teacher/interventions')}>
                    <List.Item.Meta
                      title={
                        <span>
                          {item.student_name || '未知学生'}
                          <Tag color="orange" style={{ marginLeft: 8 }}>待跟进</Tag>
                        </span>
                      }
                      description={METHOD_LABELS[item.intervention_type || item.method] || '未知'}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
