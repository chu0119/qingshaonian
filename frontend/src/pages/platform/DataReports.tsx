import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Tabs, Table, Statistic, Row, Col, Progress, Input, Tag,
  Spin, Empty, message,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, QUALITY_LABELS, QUESTIONNAIRE_STATUS_LABELS, QUESTIONNAIRE_CATEGORY_LABELS } from '../../utils/constants';

// ---- types ----

interface SchoolOverviewItem {
  school_id: number;
  school_name: string;
  student_count: number;
  completed_count: number;
  completion_rate: number;
  risk_count: number;
}

interface OverviewData {
  total_students: number;
  total_completed: number;
  overall_completion_rate: number;
  schools: SchoolOverviewItem[];
}

interface RiskLevelItem {
  level: string;
  label: string;
  count: number;
  percentage: number;
}

interface RiskStatusItem {
  status: string;
  label: string;
  count: number;
  percentage: number;
}

interface RiskSummaryData {
  total: number;
  by_level: RiskLevelItem[];
  by_status: RiskStatusItem[];
}

interface QualityLevelItem {
  level: string;
  label: string;
  count: number;
  percentage: number;
}

interface QualitySummaryData {
  total_sheets: number;
  effective_rate: number;
  retest_count: number;
  by_level: QualityLevelItem[];
}

interface QuestionnaireStatItem {
  id: number;
  title: string;
  category: string;
  question_count: number;
  task_count: number;
  answer_count: number;
  submitted_count: number;
  status: string;
}

interface LongitudinalRecord {
  submitted_at: string;
  total_score: number;
  risk_level: string;
  quality_level: string;
}

interface LongitudinalData {
  student_id: number;
  student_name: string;
  records: LongitudinalRecord[];
}

// ---- helpers ----

const qualityLevelColors: Record<string, string> = {
  normal: '#52c41a',
  questionable: '#faad14',
  mild_anomaly: '#fa8c16',
  moderate_anomaly: '#ff7a45',
  severe_anomaly: '#ff4d4f',
};

const riskStatusColors: Record<string, string> = {
  pending: '#faad14',
  viewed: '#1890ff',
  assigned: '#1890ff',
  processing: '#1890ff',
  in_progress: '#1890ff',
  resolved: '#52c41a',
  completed: '#52c41a',
  closed: '#d9d9d9',
};

// ---- component ----

export default function PlatformDataReports() {
  const [activeTab, setActiveTab] = useState('overview');

  // tab 1: overview
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // tab 2: risk
  const [riskData, setRiskData] = useState<RiskSummaryData | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  // tab 3: quality
  const [qualityData, setQualityData] = useState<QualitySummaryData | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // tab 4: questionnaires
  const [questionnaires, setQuestionnaires] = useState<QuestionnaireStatItem[]>([]);
  const [questionnaireLoading, setQuestionnaireLoading] = useState(false);

  // tab 5: longitudinal
  const [longitudinalInput, setLongitudinalInput] = useState('');
  const [longitudinalData, setLongitudinalData] = useState<LongitudinalData | null>(null);
  const [longitudinalLoading, setLongitudinalLoading] = useState(false);

  // ==================== fetchers ====================

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const res = await client.get('/platform/reports/overview');
      setOverviewData(res.data?.data || res.data);
    } catch {
      message.error('获取区域总览数据失败');
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const fetchRiskSummary = useCallback(async () => {
    setRiskLoading(true);
    try {
      const res = await client.get('/platform/reports/risk-summary');
      setRiskData(res.data?.data || res.data);
    } catch {
      message.error('获取风险预警数据失败');
    } finally {
      setRiskLoading(false);
    }
  }, []);

  const fetchQualitySummary = useCallback(async () => {
    setQualityLoading(true);
    try {
      const res = await client.get('/platform/reports/quality-summary');
      setQualityData(res.data?.data || res.data);
    } catch {
      message.error('获取答卷质量数据失败');
    } finally {
      setQualityLoading(false);
    }
  }, []);

  const fetchQuestionnaireStats = useCallback(async () => {
    setQuestionnaireLoading(true);
    try {
      const res = await client.get('/platform/reports/questionnaire-stats');
      setQuestionnaires(res.data?.data || res.data || []);
    } catch {
      message.error('获取问卷统计数据失败');
    } finally {
      setQuestionnaireLoading(false);
    }
  }, []);

  const fetchLongitudinal = useCallback(async (studentId: string) => {
    const id = studentId.trim();
    if (!id) {
      message.warning('请输入学生ID');
      return;
    }
    setLongitudinalLoading(true);
    setLongitudinalData(null);
    try {
      const res = await client.get(`/platform/reports/student-longitudinal/${id}`);
      setLongitudinalData(res.data?.data || res.data);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        message.warning('未找到该学生');
      } else {
        message.error('获取学生追踪数据失败');
      }
      setLongitudinalData(null);
    } finally {
      setLongitudinalLoading(false);
    }
  }, []);

  // load first 3 tabs on mount
  useEffect(() => {
    fetchOverview();
    fetchRiskSummary();
    fetchQualitySummary();
    fetchQuestionnaireStats();
  }, [fetchOverview, fetchRiskSummary, fetchQualitySummary, fetchQuestionnaireStats]);

  // ==================== tab 1: overview columns ====================

  const overviewColumns: ColumnsType<SchoolOverviewItem> = [
    { title: '学校名称', dataIndex: 'school_name', key: 'school_name', fixed: 'left' },
    {
      title: '学生数', dataIndex: 'student_count', key: 'student_count',
      width: 90, align: 'center' as const,
    },
    {
      title: '已完成', dataIndex: 'completed_count', key: 'completed_count',
      width: 90, align: 'center' as const,
    },
    {
      title: '完成率', dataIndex: 'completion_rate', key: 'completion_rate', width: 200,
      render: (rate: number) => (
        <Progress
          percent={Math.round(rate || 0)}
          size="small"
          status={(rate || 0) === 100 ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '风险数', dataIndex: 'risk_count', key: 'risk_count',
      width: 90, align: 'center' as const,
      render: (v: number) => (
        <Tag color={(v || 0) > 0 ? '#ff4d4f' : '#d9d9d9'}>{v || 0}</Tag>
      ),
    },
  ];

  // ==================== tab 2: risk columns ====================

  const riskLevelColumns: ColumnsType<RiskLevelItem> = [
    {
      title: '等级', dataIndex: 'level', key: 'level', width: 100,
      render: (level: string) => (
        <Tag color={RISK_COLORS[level] || '#999'}>{RISK_LABELS[level] || level}</Tag>
      ),
    },
    { title: '标签', dataIndex: 'label', key: 'label', width: 120 },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80, align: 'center' as const },
    {
      title: '占比', dataIndex: 'percentage', key: 'percentage', width: 220,
      render: (pct: number) => (
        <Progress
          percent={pct || 0}
          size="small"
          strokeColor={RISK_COLORS['high']}
        />
      ),
    },
  ];

  const riskStatusColumns: ColumnsType<RiskStatusItem> = [
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => (
        <Tag color={riskStatusColors[status] || '#999'}>{status}</Tag>
      ),
    },
    { title: '标签', dataIndex: 'label', key: 'label', width: 120 },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80, align: 'center' as const },
    {
      title: '占比', dataIndex: 'percentage', key: 'percentage', width: 150,
      render: (pct: number) => <Progress percent={pct || 0} size="small" showInfo />,
    },
  ];

  // ==================== tab 3: quality columns ====================

  const qualityLevelColumns: ColumnsType<QualityLevelItem> = [
    {
      title: '等级', dataIndex: 'level', key: 'level', width: 100,
      render: (level: string) => (
        <Tag color={qualityLevelColors[level] || '#999'}>
          {QUALITY_LABELS[level] || level}
        </Tag>
      ),
    },
    { title: '标签', dataIndex: 'label', key: 'label', width: 120 },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80, align: 'center' as const },
    {
      title: '占比', dataIndex: 'percentage', key: 'percentage', width: 220,
      render: (pct: number, record: QualityLevelItem) => (
        <Progress
          percent={pct || 0}
          size="small"
          strokeColor={qualityLevelColors[record.level] || '#999'}
        />
      ),
    },
  ];

  // ==================== tab 4: questionnaire columns ====================

  const questionnaireColumns: ColumnsType<QuestionnaireStatItem> = [
    { title: '问卷标题', dataIndex: 'title', key: 'title', ellipsis: true, fixed: 'left' },
    {
      title: '分类', dataIndex: 'category', key: 'category', width: 110,
      render: (cat: string) => (
        <Tag>{QUESTIONNAIRE_CATEGORY_LABELS[cat] || '未知'}</Tag>
      ),
    },
    {
      title: '题目数', dataIndex: 'question_count', key: 'question_count',
      width: 80, align: 'center' as const,
    },
    {
      title: '任务数', dataIndex: 'task_count', key: 'task_count',
      width: 80, align: 'center' as const,
    },
    {
      title: '答卷数', dataIndex: 'answer_count', key: 'answer_count',
      width: 80, align: 'center' as const,
    },
    {
      title: '已提交', dataIndex: 'submitted_count', key: 'submitted_count',
      width: 80, align: 'center' as const,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (status: string) => {
        const s = QUESTIONNAIRE_STATUS_LABELS[status] || status;
        const color = status === 'active' ? 'green' : status === 'draft' ? 'default' : 'orange';
        return <Tag color={color}>{s}</Tag>;
      },
    },
  ];

  // ==================== tab 5: longitudinal chart ====================

  const longitudinalChartOption = useMemo(() => {
    if (!longitudinalData?.records?.length) return null;
    const records = longitudinalData.records;
    return {
      tooltip: { trigger: 'axis' as const },
      grid: { left: 50, right: 20, top: 30, bottom: 40 },
      xAxis: {
        type: 'category' as const,
        data: records.map((r) =>
          r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('zh-CN') : '-'
        ),
        axisLabel: { fontSize: 11 },
      },
      yAxis: { type: 'value' as const },
      series: [
        {
          name: '总分',
          type: 'line' as const,
          data: records.map((r) => r.total_score),
          smooth: true,
          lineStyle: { width: 3 },
          itemStyle: { color: '#1677ff' },
          areaStyle: { color: 'rgba(22,119,255,0.08)' },
        },
      ],
    };
  }, [longitudinalData]);

  const longitudinalDetailColumns: ColumnsType<LongitudinalRecord> = [
    {
      title: '测评时间', dataIndex: 'submitted_at', key: 'submitted_at', width: 130,
      render: (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '-'),
    },
    { title: '总分', dataIndex: 'total_score', key: 'total_score', width: 90, align: 'center' as const },
    {
      title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 100,
      render: (v: string) =>
        v ? <Tag color={RISK_COLORS[v] || '#999'}>{RISK_LABELS[v] || v}</Tag> : '-',
    },
    {
      title: '质量等级', dataIndex: 'quality_level', key: 'quality_level', width: 110,
      render: (v: string) =>
        v ? <Tag color={qualityLevelColors[v] || '#999'}>{QUALITY_LABELS[v] || v}</Tag> : '-',
    },
  ];

  // ==================== tab items ====================

  const tabItems = [
    // ---- Tab 1: 区域总览 ----
    {
      key: 'overview',
      label: '区域总览',
      children: (
        <Spin spinning={overviewLoading}>
          {overviewData ? (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic title="学生总数" value={overviewData.total_students || 0} suffix="人" />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic title="已完成测评" value={overviewData.total_completed || 0} suffix="人" />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="整体完成率"
                      value={overviewData.overall_completion_rate || 0}
                      suffix="%"
                      precision={1}
                    />
                  </Card>
                </Col>
              </Row>

              <Table
                rowKey="school_id"
                columns={overviewColumns}
                dataSource={overviewData.schools || []}
                pagination={false}
                size="small"
                scroll={{ x: 'max-content' }}
                locale={{ emptyText: <Empty description="暂无学校数据" /> }}
              />
            </>
          ) : !overviewLoading ? (
            <Empty description="暂无区域总览数据" />
          ) : null}
        </Spin>
      ),
    },

    // ---- Tab 2: 风险预警 ----
    {
      key: 'risk',
      label: '风险预警',
      children: (
        <Spin spinning={riskLoading}>
          {riskData ? (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic title="风险预警总数" value={riskData.total || 0} suffix="条" />
                  </Card>
                </Col>
              </Row>

              <Card title="风险等级分布" size="small" style={{ marginBottom: 16 }}>
                <Table
                  rowKey="level"
                  columns={riskLevelColumns}
                  dataSource={riskData.by_level || []}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  locale={{ emptyText: <Empty description="暂无风险等级数据" /> }}
                />
              </Card>

              <Card title="风险状态分布" size="small">
                <Table
                  rowKey="status"
                  columns={riskStatusColumns}
                  dataSource={riskData.by_status || []}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  locale={{ emptyText: <Empty description="暂无风险状态数据" /> }}
                />
              </Card>
            </>
          ) : !riskLoading ? (
            <Empty description="暂无风险预警数据" />
          ) : null}
        </Spin>
      ),
    },

    // ---- Tab 3: 答卷质量 ----
    {
      key: 'quality',
      label: '答卷质量',
      children: (
        <Spin spinning={qualityLoading}>
          {qualityData ? (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic title="答卷总数" value={qualityData.total_sheets || 0} suffix="份" />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="有效率"
                      value={qualityData.effective_rate || 0}
                      suffix="%"
                      precision={1}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="建议复测"
                      value={qualityData.retest_count || 0}
                      suffix="人"
                      valueStyle={{ color: (qualityData.retest_count || 0) > 0 ? '#ff4d4f' : undefined }}
                    />
                  </Card>
                </Col>
              </Row>

              <Card title="质量等级分布" size="small">
                <Table
                  rowKey="level"
                  columns={qualityLevelColumns}
                  dataSource={qualityData.by_level || []}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  locale={{ emptyText: <Empty description="暂无质量等级数据" /> }}
                />
              </Card>
            </>
          ) : !qualityLoading ? (
            <Empty description="暂无答卷质量数据" />
          ) : null}
        </Spin>
      ),
    },

    // ---- Tab 4: 问卷统计 ----
    {
      key: 'questionnaire',
      label: '问卷统计',
      children: (
        <Spin spinning={questionnaireLoading}>
          <Table
            rowKey="id"
            columns={questionnaireColumns}
            dataSource={questionnaires}
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="small"
            scroll={{ x: 'max-content' }}
            locale={{ emptyText: <Empty description="暂无问卷统计数据" /> }}
          />
        </Spin>
      ),
    },

    // ---- Tab 5: 学生追踪 ----
    {
      key: 'longitudinal',
      label: '学生追踪',
      children: (
        <div>
          <Input.Search
            placeholder="输入学生ID搜索"
            enterButton="查询"
            style={{ maxWidth: 400, marginBottom: 24 }}
            value={longitudinalInput}
            onChange={(e) => setLongitudinalInput(e.target.value)}
            onSearch={fetchLongitudinal}
            prefix={<SearchOutlined />}
          />

          <Spin spinning={longitudinalLoading}>
            {longitudinalData ? (
              longitudinalData.records?.length > 0 ? (
                <>
                  <Card size="small" style={{ marginBottom: 16 }}>
                    <Statistic
                      title={longitudinalData.student_name || `学生 #${longitudinalData.student_id}`}
                      value={longitudinalData.records.length}
                      suffix="次测评记录"
                    />
                  </Card>

                  <Card size="small" style={{ marginBottom: 16 }}>
                    {longitudinalChartOption ? (
                      <ReactECharts
                        option={longitudinalChartOption}
                        style={{ height: 350 }}
                      />
                    ) : (
                      <Empty description="暂无图表数据" />
                    )}
                  </Card>

                  <Card title="测评详情" size="small">
                    <Table
                      rowKey={(_, i) => String(i)}
                      columns={longitudinalDetailColumns}
                      dataSource={longitudinalData.records}
                      pagination={false}
                      size="small"
                      scroll={{ x: 'max-content' }}
                    />
                  </Card>
                </>
              ) : (
                <Empty description="该学生暂无测评记录" />
              )
            ) : (
              <Empty description="请输入学生ID查询纵向追踪数据" />
            )}
          </Spin>
        </div>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  );
}
