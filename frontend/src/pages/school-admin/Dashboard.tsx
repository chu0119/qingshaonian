import { useState, useEffect } from 'react';
import {
  Row, Col, Card, Typography, Progress, Table, Space, Button, Tag, message, Empty,
  Skeleton,
} from 'antd';
import {
  TeamOutlined, UserOutlined, BankOutlined,
  FileTextOutlined, CheckCircleOutlined, WarningOutlined,
  RiseOutlined, ArrowRightOutlined, SettingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, QUALITY_LABELS } from '../../utils/constants';

const { Title, Text } = Typography;

const riskLabels = RISK_LABELS;
const riskColors: Record<string, string> = {
  low: '#1677ff', medium: '#faad14', high: '#ff7a45', urgent: '#ff4d4f',
};
const riskBgColors: Record<string, string> = {
  low: '#e6f4ff', medium: '#fffbe6', high: '#fff2e8', urgent: '#fff1f0',
};

const qLabels: Record<string, string> = {
  normal: '正常', questionable: '存疑', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '高度异常',
};
const qColors: Record<string, string> = {
  normal: '#52c41a', questionable: '#e8b339', mild_anomaly: '#faad14', moderate_anomaly: '#fa8c16', severe_anomaly: '#ff4d4f',
};

// 统计卡片配置
interface StatCardConfig {
  key: string;
  title: string;
  icon: React.ReactNode;
  gradient: string;
  valueKey: string;
  suffix?: string;
}

const statCards: StatCardConfig[] = [
  {
    key: 'students',
    title: '学生总数',
    icon: <TeamOutlined />,
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    valueKey: 'student_count',
  },
  {
    key: 'teachers',
    title: '教师总数',
    icon: <UserOutlined />,
    gradient: 'linear-gradient(135deg, #1677ff 0%, #4096ff 100%)',
    valueKey: 'teacher_count',
  },
  {
    key: 'classes',
    title: '班级数量',
    icon: <BankOutlined />,
    gradient: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
    valueKey: 'class_count',
  },
  {
    key: 'tasks',
    title: '进行中任务',
    icon: <FileTextOutlined />,
    gradient: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)',
    valueKey: 'active_tasks',
  },
  {
    key: 'sheets',
    title: '答卷总数',
    icon: <CheckCircleOutlined />,
    gradient: 'linear-gradient(135deg, #13c2c2 0%, #36cfc9 100%)',
    valueKey: 'total_answer_sheets',
  },
  {
    key: 'risks',
    title: '待处理预警',
    icon: <WarningOutlined />,
    gradient: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
    valueKey: 'pending_risks',
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [recentRisks, setRecentRisks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      try {
        const [dashboardRes, risksRes] = await Promise.all([
          client.get('/dashboard/school'),
          client.get('/risks', { params: { page: 1, page_size: 5, status: 'pending' } }),
        ]);
        if (!cancelled) {
          setData(dashboardRes.data.data);
          setRecentRisks(risksRes.data.data.items || []);
        }
      } catch (err: any) {
        if (!cancelled) {
          message.error(err?.response?.data?.message || '获取看板数据失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = data?.stats || {};
  const riskDist = data?.risk_level_distribution || {};
  const qualityDist = data?.quality_distribution || {};
  const riskTotal =
    (riskDist.low || 0) + (riskDist.medium || 0) + (riskDist.high || 0) + (riskDist.urgent || 0);
  const qualityTotal =
    (qualityDist.normal || 0) +
    (qualityDist.mild_anomaly || 0) +
    (qualityDist.moderate_anomaly || 0) +
    (qualityDist.severe_anomaly || 0);
  const effectiveRate =
    qualityTotal > 0 ? Math.round(((qualityDist.normal || 0) / qualityTotal) * 100) : null;

  const riskColumns = [
    {
      title: '学生',
      dataIndex: 'student_name',
      key: 'student_name',
      width: 100,
    },
    {
      title: '班级',
      dataIndex: 'class_name',
      key: 'class_name',
      width: 100,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (v: string) => (
        <Tag
          color={riskColors[v] || 'default'}
          style={{ borderRadius: 4, fontWeight: 500 }}
        >
          {riskLabels[v] || v}
        </Tag>
      ),
    },
    {
      title: '触发问卷',
      dataIndex: 'questionnaire_title',
      key: 'questionnaire_title',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, r: any) => (
        <Button
          type="link"
          size="small"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate(`/school-admin/risks/${r.id}`)}
        >
          查看
        </Button>
      ),
    },
  ];

  // 风险评估摘要
  const urgentCount = riskDist.urgent || 0;
  const highCount = riskDist.high || 0;
  const interventionNeeded = urgentCount + highCount;

  return (
    <div>
      {/* 页面标题 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
          paddingBottom: 16,
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 4,
              height: 20,
              borderRadius: 2,
              background: 'linear-gradient(180deg, #1677ff, #4096ff)',
            }}
          />
          <Title level={5} style={{ margin: 0, fontWeight: 600, color: '#262626' }}>
            学校首页看板
          </Title>
        </div>
        <Space>
          <Button size="small" onClick={() => navigate('/school-admin/settings')} icon={<SettingOutlined />}>
            系统设置
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      {loading ? (
        <Row gutter={[16, 16]}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Col xs={12} sm={8} lg={4} key={i}>
              <Card style={{ borderRadius: 12 }}>
                <Skeleton active paragraph={{ rows: 1 }} title={{ width: '60%' }} />
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <Row gutter={[16, 16]}>
          {statCards.map((card) => (
            <Col xs={12} sm={8} lg={4} key={card.key}>
              <Card
                style={{
                  borderRadius: 12,
                  overflow: 'hidden',
                  border: '1px solid #f0f0f0',
                  transition: 'all 0.3s ease',
                }}
                bodyStyle={{ padding: '20px 16px' }}
                hoverable
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ flex: 1 }}>
                    <Text
                      type="secondary"
                      style={{ fontSize: 13, display: 'block', marginBottom: 8 }}
                    >
                      {card.title}
                    </Text>
                    <div
                      style={{
                        fontSize: 32,
                        fontWeight: 700,
                        background: card.gradient,
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                        lineHeight: 1.2,
                      }}
                    >
                      {stats[card.valueKey] ?? 0}
                    </div>
                  </div>
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 14,
                      background: card.gradient,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 22,
                      color: '#fff',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      transition: 'transform 0.3s ease',
                      animation: 'none',
                    }}
                    className="stat-icon"
                  >
                    {card.icon}
                  </div>
                </div>

                {/* 特殊处理：待处理预警显示严重度 */}
                {card.key === 'risks' && stats.pending_risks > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div
                      style={{
                        height: 4,
                        borderRadius: 2,
                        background: card.gradient,
                        width: '100%',
                        opacity: 0.3,
                      }}
                    />
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 风险摘要提示 */}
      {interventionNeeded > 0 && !loading && (
        <Card
          style={{
            marginTop: 16,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #fff1f0 0%, #fff2e8 100%)',
            border: '1px solid #ffccc7',
          }}
          bodyStyle={{ padding: '12px 20px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <WarningOutlined style={{ color: '#ff4d4f', fontSize: 18 }} />
              <Text strong style={{ color: '#cf1322' }}>
                当前有 {urgentCount} 条危急关注信号和 {highCount} 条警告关注信号需要关注
              </Text>
            </Space>
            <Button
              size="small"
              danger
              onClick={() => navigate('/school-admin/risks')}
            >
              立即处理
            </Button>
          </div>
        </Card>
      )}

      {/* 风险和答题质量分布 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <RiseOutlined style={{ color: '#1677ff' }} />
                <span>风险等级分布</span>
              </Space>
            }
            extra={
              <Button type="link" size="small" onClick={() => navigate('/school-admin/risks')}>
                查看全部 <ArrowRightOutlined />
              </Button>
            }
            loading={loading}
            style={{ borderRadius: 12 }}
          >
            {riskTotal > 0 ? (
              <div style={{ padding: '8px 0' }}>
                {Object.entries(riskLabels).map(([level, label]) => {
                  const count = riskDist[level] || 0;
                  const pct = riskTotal > 0 ? Math.round((count / riskTotal) * 100) : 0;
                  return (
                    <div key={level} style={{ marginBottom: 16 }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: 6,
                          alignItems: 'center',
                        }}
                      >
                        <Space size={8}>
                          <span
                            style={{
                              display: 'inline-block',
                              width: 10,
                              height: 10,
                              borderRadius: 3,
                              background: riskColors[level],
                            }}
                          />
                          <Text style={{ fontSize: 14 }}>{label}</Text>
                        </Space>
                        <Space size={4}>
                          <Text strong style={{ fontSize: 16, color: riskColors[level] }}>
                            {count}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 13 }}>
                            人 ({pct}%)
                          </Text>
                        </Space>
                      </div>
                      <Progress
                        percent={pct}
                        showInfo={false}
                        strokeColor={{
                          '0%': riskColors[level],
                          '100%': riskColors[level],
                        }}
                        trailColor={riskBgColors[level]}
                        strokeWidth={8}
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <Empty description="暂无风险数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <span>答题质量分布</span>
              </Space>
            }
            extra={
              <Button type="link" size="small" onClick={() => navigate('/school-admin/reports')}>
                详情 <ArrowRightOutlined />
              </Button>
            }
            loading={loading}
            style={{ borderRadius: 12 }}
          >
            <div
              style={{
                textAlign: 'center',
                marginBottom: 20,
                padding: '16px 0',
                background: effectiveRate === null ? '#f5f5f5' : (effectiveRate >= 80 ? '#f6ffed' : '#fffbe6'),
                borderRadius: 10,
                border: `1px solid ${effectiveRate === null ? '#d9d9d9' : (effectiveRate >= 80 ? '#b7eb8f' : '#ffe58f')}`,
              }}
            >
              <Text style={{ fontSize: 15 }}>
                有效答卷率：
              </Text>
              <strong
                style={{
                  fontSize: 28,
                  color: effectiveRate === null ? '#999' : (effectiveRate >= 80 ? '#52c41a' : '#faad14'),
                  margin: '0 4px',
                }}
              >
                {effectiveRate === null ? '暂无数据' : `${effectiveRate}%`}
              </strong>
            </div>
            {qualityTotal > 0 ? (
              <div style={{ padding: '8px 0' }}>
                {Object.entries(qLabels).map(([level, label]) => {
                  const count = qualityDist[level] || 0;
                  const pct = qualityTotal > 0 ? Math.round((count / qualityTotal) * 100) : 0;
                  return (
                    <div key={level} style={{ marginBottom: 14 }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: 6,
                          alignItems: 'center',
                        }}
                      >
                        <Space size={8}>
                          <span
                            style={{
                              display: 'inline-block',
                              width: 10,
                              height: 10,
                              borderRadius: 3,
                              background: qColors[level],
                            }}
                          />
                          <Text style={{ fontSize: 14 }}>{label}</Text>
                        </Space>
                        <Space size={4}>
                          <Text strong style={{ fontSize: 16, color: qColors[level] }}>
                            {count}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 13 }}>
                            份 ({pct}%)
                          </Text>
                        </Space>
                      </div>
                      <Progress
                        percent={pct}
                        showInfo={false}
                        strokeColor={qColors[level]}
                        strokeWidth={8}
                        trailColor="#f5f5f5"
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <Empty description="暂无质量数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      {/* 待处理预警列表 */}
      <Card
        title={
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            <span>待处理预警</span>
            <Tag color="warning" style={{ borderRadius: 4 }}>
              {recentRisks.length} 条
            </Tag>
          </Space>
        }
        style={{ marginTop: 16, borderRadius: 12 }}
        loading={loading}
      >
        {recentRisks.length === 0 ? (
          <Empty
            description="暂无待处理预警"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '24px 0' }}
          />
        ) : (
          <Table
            rowKey="id"
            dataSource={recentRisks}
            columns={riskColumns}
            pagination={false}
            size="middle"
            style={{ marginTop: -8 }}
            scroll={{ x: 'max-content' }}
          />
        )}
      </Card>
    </div>
  );
}
