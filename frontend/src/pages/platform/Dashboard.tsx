import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Typography, Progress, Space, Empty } from 'antd';
import {
  BankOutlined, TeamOutlined, UserOutlined, AlertOutlined, FileTextOutlined,
  BarChartOutlined, CheckCircleOutlined, MessageOutlined, RobotOutlined,
} from '@ant-design/icons';
import client from '../../api/client';

const { Title } = Typography;

function formatTime(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-';
}

export default function Dashboard() {
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    client.get('/platform/dashboard')
      .then((r) => setData(r.data.data || {}))
      .catch(() => setData({}))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    { title: '学校总数', value: data.school_total, icon: <BankOutlined />, color: '#1677ff' },
    { title: '启用学校', value: data.enabled_school_total, icon: <CheckCircleOutlined />, color: '#52c41a' },
    { title: '停用学校', value: data.disabled_school_total, icon: <BankOutlined />, color: '#8c8c8c' },
    { title: '学生总数', value: data.student_total, icon: <TeamOutlined />, color: '#13c2c2' },
    { title: '教师总数', value: data.teacher_total, icon: <UserOutlined />, color: '#722ed1' },
    { title: '问卷任务', value: data.task_total, icon: <FileTextOutlined />, color: '#faad14' },
    { title: '答卷总数', value: data.answer_sheet_total, icon: <BarChartOutlined />, color: '#2f54eb' },
    { title: '风险提示', value: data.risk_alert_total, icon: <AlertOutlined />, color: '#ff7a45' },
    { title: '待处理提示', value: data.pending_risk_total, icon: <AlertOutlined />, color: '#ff4d4f' },
    { title: 'AI 调用', value: data.ai_call_total, icon: <RobotOutlined />, color: '#eb2f96' },
    { title: '短信发送', value: data.sms_send_total, icon: <MessageOutlined />, color: '#08979c' },
  ];

  const completionColumns = [
    { title: '学校', dataIndex: 'name', key: 'name' },
    { title: '完成率', dataIndex: 'completion_rate', key: 'completion_rate', render: (v: number) => <Progress percent={v || 0} size="small" /> },
    { title: '应填', dataIndex: 'expected_count', key: 'expected_count', width: 70 },
    { title: '已填', dataIndex: 'completed_count', key: 'completed_count', width: 70 },
  ];

  const riskColumns = [
    { title: '学校', dataIndex: 'name', key: 'name' },
    { title: '风险提示', dataIndex: 'risk_count', key: 'risk_count', width: 90, render: (v: number) => <Tag color={v > 0 ? 'orange' : 'default'}>{v || 0}</Tag> },
    { title: '待处理', dataIndex: 'pending_risk_count', key: 'pending_risk_count', width: 90, render: (v: number) => <Tag color={v > 0 ? 'red' : 'default'}>{v || 0}</Tag> },
    { title: '处理进度', dataIndex: 'intervention_completion_rate', key: 'intervention_completion_rate', render: (v: number) => <Progress percent={v || 0} size="small" /> },
  ];

  const activeColumns = [
    { title: '学校', dataIndex: 'name', key: 'name' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag> },
    { title: '学生', dataIndex: 'student_count', key: 'student_count', width: 70 },
    { title: '教师', dataIndex: 'teacher_count', key: 'teacher_count', width: 70 },
    { title: '最近活跃', dataIndex: 'last_active_at', key: 'last_active_at', render: formatTime },
  ];

  return (
    <div>
      <Title level={4}>平台总览</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {cards.map((card) => (
          <Col xs={12} sm={8} lg={6} xl={4} key={card.title}>
            <Card loading={loading}>
              <Statistic
                title={card.title}
                value={card.value || 0}
                prefix={card.icon}
                valueStyle={{ color: card.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={<Space><BarChartOutlined />学校完成率排名</Space>} loading={loading}>
            <Table
              rowKey="id"
              dataSource={data.completion_rankings || []}
              columns={completionColumns}
              pagination={false}
              locale={{ emptyText: <Empty description="暂无完成率数据" /> }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<Space><AlertOutlined />学校风险提示排名</Space>} loading={loading}>
            <Table
              rowKey="id"
              dataSource={data.risk_rankings || []}
              columns={riskColumns}
              pagination={false}
              locale={{ emptyText: <Empty description="暂无风险提示数据" /> }}
            />
          </Card>
        </Col>
        <Col xs={24}>
          <Card title={<Space><BankOutlined />最近活跃学校</Space>} loading={loading}>
            <Table
              rowKey="id"
              dataSource={data.recent_active_schools || []}
              columns={activeColumns}
              pagination={false}
              locale={{ emptyText: <Empty description="暂无活跃记录" /> }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
