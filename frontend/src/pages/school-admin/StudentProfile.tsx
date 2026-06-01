import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Descriptions, Table, Tag, Timeline, Typography, Spin, Tabs, Space, Button, Empty, message, Row, Col, Statistic, Progress,
} from 'antd';
import { ArrowLeftOutlined, FileTextOutlined, AlertOutlined, MedicineBoxOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, DIMENSION_LABELS, INTERVENTION_STATUS_LABELS, METHOD_LABELS } from '../../utils/constants';

const { Title, Text } = Typography;

/* ---------- label maps ---------- */
const statusLabels = INTERVENTION_STATUS_LABELS;
const methodLabels = METHOD_LABELS;

/* ---------- types ---------- */
interface StudentInfo {
  id: number;
  real_name: string;
  student_no: string;
  gender: string;
  phone: string;
  grade_name: string;
  class_name: string;
  username: string; // 身份证号
}

interface LongitudinalRecord {
  answer_sheet_id: number;
  task_id: number;
  questionnaire_title: string;
  submitted_at: string;
  total_score: number;
  dimension_scores: Record<string, number>;
  risk_level: string;
}

interface RiskItem {
  id: number;
  student_name: string;
  risk_level: string;
  status: string;
  created_at: string;
  risk_type?: string;
  questionnaire_title?: string;
}

interface InterventionItem {
  id: number;
  method: string;
  content: string;
  status: string;
  intervention_time: string;
  student_name: string;
}

/* ---------- helper ---------- */
function maskPhone(phone?: string) {
  if (!phone) return '-';
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

function formatDate(v?: string) {
  if (!v) return '-';
  return new Date(v).toLocaleString('zh-CN');
}

/* ---------- component ---------- */
export default function StudentProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const studentId = Number(id);

  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState<StudentInfo | null>(null);
  const [records, setRecords] = useState<LongitudinalRecord[]>([]);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [interventions, setInterventions] = useState<InterventionItem[]>([]);

  /* fetch all data */
  const fetchAll = useCallback(async () => {
    if (!studentId) return;
    setLoading(true);
    try {
      // 1. Basic student info
      let studentData: StudentInfo | null = null;
      try {
        const sr = await client.get(`/users/students/${studentId}`);
        studentData = sr.data.data as StudentInfo;
      } catch {
        // fallback: search in list
        try {
          const sr = await client.get('/users/students', { params: { page_size: 1, student_id: studentId } });
          const items = sr.data.data?.items || sr.data.data || [];
          if (Array.isArray(items) && items.length > 0) studentData = items[0];
        } catch { /* ignore */ }
      }

      // 2. Longitudinal data (also gives us student name as fallback)
      let longitudinalRecords: LongitudinalRecord[] = [];
      try {
        const lr = await client.get(`/reports/student-longitudinal/${studentId}`);
        longitudinalRecords = lr.data.data?.records || [];
      } catch { /* ignore */ }

      // Fallback student name from longitudinal data
      if (!studentData && longitudinalRecords.length > 0) {
        const lr2 = await client.get(`/reports/student-longitudinal/${studentId}`);
        const name = lr2.data.data?.student_name;
        studentData = { id: studentId, real_name: name || `学生${studentId}`, student_no: '-', gender: '-', phone: '', grade_name: '-', class_name: '-', username: '' };
      }

      setStudent(studentData);
      setRecords(longitudinalRecords);

      // 3. Risks
      let riskItems: RiskItem[] = [];
      try {
        const rr = await client.get('/risks', { params: { student_id: studentId, page_size: 50 } });
        riskItems = rr.data.data?.items || [];
      } catch { /* ignore */ }
      setRisks(riskItems);

      // 4. Interventions
      let intvItems: InterventionItem[] = [];
      try {
        const ir = await client.get('/interventions', { params: { student_id: studentId, page_size: 50 } });
        intvItems = ir.data.data?.items || [];
      } catch { /* ignore */ }
      setInterventions(intvItems);
    } catch {
      message.error('加载学生档案失败');
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  /* ---------- derived ---------- */
  const latestRecord = records.length > 0 ? records[records.length - 1] : null;
  const dimensionKeys = latestRecord?.dimension_scores ? Object.keys(latestRecord.dimension_scores) : [];
  const dimensionValues = latestRecord?.dimension_scores ? Object.values(latestRecord.dimension_scores) : [];

  const riskCounts = { low: 0, medium: 0, high: 0, urgent: 0 };
  risks.forEach(r => { if (riskCounts[r.risk_level as keyof typeof riskCounts] !== undefined) riskCounts[r.risk_level as keyof typeof riskCounts]++; });
  const pendingRisks = risks.filter(r => r.status === 'pending').length;
  const pendingInterventions = interventions.filter(r => r.status === 'pending' || r.status === 'processing').length;

  /* ---------- trend chart ---------- */
  const trendOption = records.length > 1 ? {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['总分', ...dimensionKeys.map(k => DIMENSION_LABELS[k] || k)], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { top: 20, bottom: 60, left: 50, right: 20 },
    xAxis: { type: 'category' as const, data: records.map(r => r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('zh-CN') : ''), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const },
    series: [
      { name: '总分', type: 'line', data: records.map(r => r.total_score), smooth: true, lineStyle: { width: 3 }, itemStyle: { color: '#1677ff' } },
      ...dimensionKeys.map((k, i) => ({
        name: DIMENSION_LABELS[k] || k,
        type: 'line' as const,
        data: records.map(r => r.dimension_scores?.[k] ?? null),
        smooth: true,
        lineStyle: { width: 1.5, type: 'dashed' as const },
      })),
    ],
  } : null;

  /* ---------- radar chart ---------- */
  const radarOption = latestRecord && dimensionKeys.length > 0 ? {
    tooltip: {},
    radar: {
      indicator: dimensionKeys.map((k) => ({ name: DIMENSION_LABELS[k] || k, max: 100 })),
      shape: 'polygon' as const,
      radius: '65%',
    },
    series: [{
      type: 'radar',
      data: [{
        value: dimensionValues,
        name: latestRecord.questionnaire_title,
        areaStyle: { opacity: 0.2 },
        lineStyle: { color: '#1677ff' },
        itemStyle: { color: '#1677ff' },
      }],
    }],
  } : null;

  /* ---------- columns ---------- */
  const riskColumns = [
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 120, render: (v: string) => <Tag color={RISK_COLORS[v] || 'default'}>{RISK_LABELS[v] || v}</Tag> },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', width: 120, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '触发问卷', dataIndex: 'questionnaire_title', key: 'questionnaire_title', render: (v: string) => v || '-' },
    { title: '触发时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: formatDate },
  ];

  const interventionColumns = [
    { title: '干预方式', dataIndex: 'method', key: 'method', width: 130, render: (v: string) => methodLabels[v] || v },
    { title: '干预内容', dataIndex: 'content', key: 'content', render: (v: string) => v ? (v.length > 40 ? v.substring(0, 40) + '...' : v) : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '干预时间', dataIndex: 'intervention_time', key: 'intervention_time', width: 170, render: formatDate },
  ];

  /* ---------- loading guard ---------- */
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!student) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Empty description="未找到学生信息" />
        <Button type="link" onClick={() => navigate(-1)}>返回上一页</Button>
      </div>
    );
  }

  /* ---------- render ---------- */
  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid #f0f0f0',
      }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <div style={{
          width: 4, height: 20, borderRadius: 2,
          background: 'linear-gradient(180deg, #1677ff, #4096ff)',
        }} />
        <Title level={5} style={{ margin: 0, fontWeight: 600 }}>
          学生档案 - {student.real_name}
        </Title>
      </div>

      {/* 1. Basic Info */}
      <Card
        title="基本信息"
        style={{ marginBottom: 16, borderRadius: 10 }}
        styles={{ body: { padding: '16px 24px' } }}
      >
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
          <Descriptions.Item label="姓名">{student.real_name}</Descriptions.Item>
          <Descriptions.Item label="学号">{student.student_no || '-'}</Descriptions.Item>
          <Descriptions.Item label="性别">{student.gender || '-'}</Descriptions.Item>
          <Descriptions.Item label="年级">{student.grade_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="班级">{student.class_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="联系电话">{maskPhone(student.phone)}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, textAlign: 'center' }}>
            <Statistic title="累计测评" value={records.length} suffix="次" prefix={<FileTextOutlined style={{ color: '#1677ff' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, textAlign: 'center' }}>
            <Statistic title="最新风险" value={latestRecord ? (RISK_LABELS[latestRecord.risk_level] || '-') : '-'}
              valueStyle={{ color: latestRecord ? (RISK_COLORS[latestRecord.risk_level] || '#8c8c8c') : '#8c8c8c' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, textAlign: 'center' }}>
            <Statistic title="待处理预警" value={pendingRisks} suffix="条"
              prefix={<AlertOutlined style={{ color: pendingRisks > 0 ? '#ff4d4f' : '#52c41a' }} />}
              valueStyle={{ color: pendingRisks > 0 ? '#ff4d4f' : '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: 10, textAlign: 'center' }}>
            <Statistic title="进行中干预" value={pendingInterventions} suffix="项"
              prefix={<MedicineBoxOutlined style={{ color: pendingInterventions > 0 ? '#faad14' : '#52c41a' }} />}
              valueStyle={{ color: pendingInterventions > 0 ? '#faad14' : '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      {/* Tabs for sections */}
      <Tabs
        defaultActiveKey="assessment"
        items={[
          {
            key: 'assessment',
            label: '测评记录',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {/* 2. Assessment Timeline */}
                <Card
                  title="测评时间线"
                  style={{ borderRadius: 10 }}
                  styles={{ body: { maxHeight: 400, overflowY: 'auto' } }}
                >
                  {records.length === 0 ? (
                    <Empty description="暂无测评记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Timeline
                      mode="left"
                      items={records.map((r) => ({
                        color: RISK_COLORS[r.risk_level] || '#1677ff',
                        children: (
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                              <Text strong>{r.questionnaire_title}</Text>
                              <Tag color={RISK_COLORS[r.risk_level] || 'default'}>
                                {RISK_LABELS[r.risk_level] || r.risk_level}
                              </Tag>
                            </div>
                            <div style={{ color: '#8c8c8c', fontSize: 13, marginTop: 4 }}>
                              {formatDate(r.submitted_at)}
                              {r.total_score != null && (
                                <span style={{ marginLeft: 12 }}>总分: {r.total_score}</span>
                              )}
                            </div>
                          </div>
                        ),
                      }))}
                    />
                  )}
                </Card>

                {/* 5. Dimension Radar Chart */}
                {radarOption && (
                  <Card title="最近一次测评维度分析" style={{ borderRadius: 10 }}>
                    <ReactECharts
                      option={radarOption}
                      style={{ height: 320 }}
                      opts={{ renderer: 'svg' }}
                    />
                  </Card>
                )}

                {/* 6. Longitudinal Trend Chart */}
                {trendOption && (
                  <Card title="历次测评趋势" style={{ borderRadius: 10 }}>
                    <ReactECharts
                      option={trendOption}
                      style={{ height: 350 }}
                      opts={{ renderer: 'svg' }}
                    />
                  </Card>
                )}

                {/* 7. Assessment Detail Table */}
                {records.length > 0 && (
                  <Card title="测评明细" style={{ borderRadius: 10 }} styles={{ body: { padding: 0 } }}>
                    <Table
                      rowKey="answer_sheet_id"
                      dataSource={[...records].reverse()}
                      size="small"
                      scroll={{ x: 'max-content' }}
                      pagination={false}
                      expandable={{
                        expandedRowRender: (r) => r.dimension_scores ? (
                          <div style={{ padding: '8px 16px' }}>
                            <Space wrap>
                              {Object.entries(r.dimension_scores).map(([k, v]) => (
                                <Tag key={k}>{DIMENSION_LABELS[k] || k}: {v}</Tag>
                              ))}
                            </Space>
                          </div>
                        ) : null,
                        rowExpandable: (r) => !!r.dimension_scores && Object.keys(r.dimension_scores).length > 0,
                      }}
                      columns={[
                        { title: '问卷', dataIndex: 'questionnaire_title', ellipsis: true },
                        { title: '提交时间', dataIndex: 'submitted_at', width: 170, render: formatDate },
                        { title: '总分', dataIndex: 'total_score', width: 80, align: 'center' as const },
                        { title: '风险等级', dataIndex: 'risk_level', width: 100, render: (v: string) => <Tag color={RISK_COLORS[v] || 'default'}>{RISK_LABELS[v] || v}</Tag> },
                      ]}
                    />
                  </Card>
                )}
              </Space>
            ),
          },
          {
            key: 'risks',
            label: `风险预警 (${risks.length})`,
            children: (
              <Card style={{ borderRadius: 10 }} styles={{ body: { padding: 0 } }}>
                <Table
                  rowKey="id"
                  dataSource={risks}
                  columns={riskColumns}
                  scroll={{ x: 'max-content' }}
                  size="small"
                  pagination={risks.length > 10 ? { pageSize: 10, showTotal: (t: number) => `共 ${t} 条` } : false}
                  locale={{ emptyText: <Empty description="暂无风险预警记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </Card>
            ),
          },
          {
            key: 'interventions',
            label: `干预记录 (${interventions.length})`,
            children: (
              <Card style={{ borderRadius: 10 }} styles={{ body: { padding: 0 } }}>
                <Table
                  rowKey="id"
                  dataSource={interventions}
                  columns={interventionColumns}
                  scroll={{ x: 'max-content' }}
                  size="small"
                  pagination={interventions.length > 10 ? { pageSize: 10, showTotal: (t: number) => `共 ${t} 条` } : false}
                  locale={{ emptyText: <Empty description="暂无干预记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
