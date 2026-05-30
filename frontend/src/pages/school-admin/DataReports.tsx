import { useState, useEffect, useCallback } from 'react';
import {
  Card, Tabs, Table, Typography, Statistic, Row, Col,
  Progress, Button, Tag, Spin, Space, message, Select, Input,
} from 'antd';
import { ExportOutlined, ReloadOutlined, RobotOutlined, LineChartOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
import {
  getSchoolOverview, getRiskSummary, getQualityStats,
  type SchoolOverviewData, type GradeOverview,
  type RiskSummaryData, type RiskLevelItem, type RiskStatusItem,
  type QualityStatsData, type QualityLevelItem,
  getStudentLongitudinal, type LongitudinalData,
} from '../../api/reports';
import { getQuestionnaires, type QuestionnaireInfo } from '../../api/questionnaires';
import AiAnalysisModal from '../../components/ai/AiAnalysisModal';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, DIMENSION_LABELS, QUALITY_LABELS, QUESTIONNAIRE_CATEGORY_LABELS, QUESTIONNAIRE_STATUS_LABELS } from '../../utils/constants';

const qualityLevelLabels: Record<string, { label: string; color: string }> = {
  normal: { label: QUALITY_LABELS.normal, color: '#52c41a' },
  questionable: { label: QUALITY_LABELS.questionable, color: '#e8b339' },
  mild_anomaly: { label: QUALITY_LABELS.mild_anomaly, color: '#faad14' },
  moderate_anomaly: { label: QUALITY_LABELS.moderate_anomaly, color: '#fa8c16' },
  severe_anomaly: { label: QUALITY_LABELS.severe_anomaly, color: '#ff4d4f' },
};

const riskLevelColors = RISK_COLORS;

const riskStatusColors: Record<string, string> = {
  pending: '#faad14',
  processing: '#1890ff',
  resolved: '#52c41a',
  closed: '#d9d9d9',
};

const questionnaireCategoryLabels = QUESTIONNAIRE_CATEGORY_LABELS;

const questionnaireStatusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: QUESTIONNAIRE_STATUS_LABELS.draft, color: '#d9d9d9' },
  active: { label: QUESTIONNAIRE_STATUS_LABELS.active, color: '#52c41a' },
  inactive: { label: QUESTIONNAIRE_STATUS_LABELS.inactive, color: '#ff4d4f' },
};

export default function DataReports() {
  const [activeTab, setActiveTab] = useState('school');

  // ---- 学校综合报表 ----
  const [overviewData, setOverviewData] = useState<SchoolOverviewData | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // ---- 风险预警报表 ----
  const [riskData, setRiskData] = useState<RiskSummaryData | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  // ---- 答题质量报表 ----
  const [qualityData, setQualityData] = useState<QualityStatsData | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // ---- 问卷统计 ----
  const [questionnaires, setQuestionnaires] = useState<QuestionnaireInfo[]>([]);
  const [questionnaireLoading, setQuestionnaireLoading] = useState(false);

  // ---- AI分析弹窗 ----
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiType, setAiType] = useState<'overall_report' | 'quality_report'>('overall_report');
  const [aiData, setAiData] = useState<Record<string, any>>({});
  const [aiTitle, setAiTitle] = useState('');

  // ---- 学生纵向追踪 ----
  const [longitudinalStudentId, setLongitudinalStudentId] = useState<number | null>(null);
  const [longitudinalData, setLongitudinalData] = useState<LongitudinalData | null>(null);
  const [longitudinalLoading, setLongitudinalLoading] = useState(false);
  const [studentSearchResults, setStudentSearchResults] = useState<any[]>([]);

  const openAiModal = (type: 'overall_report' | 'quality_report', data: Record<string, any>, title: string) => {
    setAiType(type);
    setAiData(data);
    setAiTitle(title);
    setAiModalOpen(true);
  };

  // ==================== data fetching ====================

  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await getSchoolOverview();
      setOverviewData(data);
    } catch {
      message.error('获取学校报表数据失败');
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const fetchRiskData = useCallback(async () => {
    setRiskLoading(true);
    try {
      const data = await getRiskSummary();
      setRiskData(data);
    } catch {
      message.error('获取风险报表数据失败');
    } finally {
      setRiskLoading(false);
    }
  }, []);

  const fetchQualityData = useCallback(async () => {
    setQualityLoading(true);
    try {
      const data = await getQualityStats();
      setQualityData(data);
    } catch {
      message.error('获取答题质量数据失败');
    } finally {
      setQualityLoading(false);
    }
  }, []);

  const fetchQuestionnaires = useCallback(async () => {
    setQuestionnaireLoading(true);
    try {
      const result = await getQuestionnaires({ page_size: 100 });
      setQuestionnaires(result?.items || []);
    } catch {
      message.error('获取问卷列表失败');
    } finally {
      setQuestionnaireLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
    fetchRiskData();
    fetchQualityData();
    fetchQuestionnaires();
  }, [fetchOverview, fetchRiskData, fetchQualityData, fetchQuestionnaires]);

  const searchStudents = useCallback(async (keyword: string) => {
    if (!keyword.trim()) { setStudentSearchResults([]); return; }
    try {
      const res = await client.get('/users/students', { params: { keyword, page_size: 10 } });
      setStudentSearchResults(res.data?.data?.items || []);
    } catch { setStudentSearchResults([]); }
  }, []);

  const fetchLongitudinal = useCallback(async (studentId: number) => {
    setLongitudinalLoading(true);
    try {
      const data = await getStudentLongitudinal(studentId);
      setLongitudinalData(data);
    } catch { message.error('获取纵向数据失败'); setLongitudinalData(null); }
    finally { setLongitudinalLoading(false); }
  }, []);

  // ==================== 学校综合报表 columns ====================

  const gradeColumns: ColumnsType<GradeOverview> = [
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 120 },
    {
      title: '学生数', dataIndex: 'student_count', key: 'student_count', width: 90,
      align: 'center' as const,
    },
    {
      title: '已完成', dataIndex: 'completed_count', key: 'completed_count', width: 90,
      align: 'center' as const,
    },
    {
      title: '完成率', dataIndex: 'completion_rate', key: 'completion_rate', width: 200,
      render: (rate: number) => (
        <Progress percent={rate} size="small" status={rate === 100 ? 'success' : 'active'} />
      ),
    },
  ];

  const expandedRowRender = (record: GradeOverview) => {
    const classColumns: ColumnsType<GradeOverview['classes'][number]> = [
      { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 120 },
      {
        title: '学生数', dataIndex: 'student_count', key: 'student_count', width: 90,
        align: 'center' as const,
      },
      {
        title: '已完成', dataIndex: 'completed_count', key: 'completed_count', width: 90,
        align: 'center' as const,
      },
      {
        title: '完成率', dataIndex: 'completion_rate', key: 'completion_rate', width: 220,
        render: (rate: number) => (
          <Progress percent={rate} size="small" status={rate === 100 ? 'success' : 'active'} />
        ),
      },
    ];
    return (
      <Table
        rowKey="class_name"
        columns={classColumns}
        dataSource={record.classes}
        pagination={false}
        size="small"
        style={{ margin: '0 24px' }}
        scroll={{ x: 'max-content' }}
      />
    );
  };

  // ==================== tab items ====================

  const tabItems = [
    // ---- Tab 1: 学校综合报表 ----
    {
      key: 'school',
      label: '学校综合报表',
      children: (
        <Spin spinning={overviewLoading}>
          {overviewData && (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small">
                    <Statistic title="学生总数" value={overviewData?.total_students || 0} suffix="人" />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small">
                    <Statistic title="已完成测评" value={overviewData?.total_completed || 0} suffix="人" />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small">
                    <Statistic
                      title="整体完成率"
                      value={overviewData?.overall_completion_rate || 0}
                      suffix="%"
                      precision={1}
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={24}>
                  <Progress
                    percent={overviewData?.overall_completion_rate || 0}
                    status={(overviewData?.overall_completion_rate || 0) === 100 ? 'success' : 'active'}
                    strokeWidth={14}
                    format={() => `整体完成率: ${overviewData?.overall_completion_rate || 0}%`}
                  />
                </Col>
              </Row>

              <Table
                rowKey="grade_name"
                columns={gradeColumns}
                dataSource={overviewData?.grades || []}
                expandable={{ expandedRowRender, defaultExpandAllRows: true }}
                pagination={false}
                size="small"
                locale={{ emptyText: '暂无年级数据' }}
                scroll={{ x: 'max-content' }}
              />

              <Space style={{ marginTop: 16 }}>
                <Button icon={<ReloadOutlined />} onClick={fetchOverview}>
                  刷新
                </Button>
                <Button
                  icon={<RobotOutlined />}
                  onClick={() => openAiModal('overall_report', {
                    school_name: overviewData?.school_name || '本校',
                    total_students: overviewData?.total_students,
                    completed_count: overviewData?.total_completed,
                    completion_rate: overviewData?.overall_completion_rate,
                    risk_distribution: JSON.stringify(riskData?.by_level?.map((l: RiskLevelItem) => `${l.label}: ${l.count}条(${l.percentage}%)`).join('；') || '暂无'),
                    grade_overview: JSON.stringify(overviewData?.grades?.map((g: GradeOverview) => `${g.grade_name}: 完成${g.completion_rate}%(${g.completed_count}/${g.student_count})`).join('；') || '暂无'),
                    dimension_avg_scores: '暂无（需在各班级报告中查看）',
                    quality_overview: JSON.stringify(qualityData?.by_level?.map((q: QualityLevelItem) => {
                      const info = qualityLevelLabels[q.level] || { label: q.level };
                      return `${info.label}: ${q.count}份`;
                    }).join('；') || '暂无'),
                  }, 'AI分析 - 学校综合报表')}
                  style={{ borderColor: '#00d4ff', color: '#00d4ff' }}
                >
                  AI分析报告
                </Button>
              </Space>
            </>
          )}
          {!overviewData && !overviewLoading && (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无学校综合报表数据
            </div>
          )}
        </Spin>
      ),
    },

    // ---- Tab 2: 风险预警报表 ----
    {
      key: 'risk',
      label: '风险预警报表',
      children: (
        <Spin spinning={riskLoading}>
          {riskData && (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={12} sm={6}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic title="风险警报总数" value={riskData?.total || 0} suffix="条" />
                  </Card>
                </Col>
              </Row>

              <Card title="风险等级分布" size="small" style={{ marginBottom: 16 }}>
                <Row gutter={[16, 16]}>
                  {(riskData?.by_level || []).map((item: RiskLevelItem) => (
                    <Col xs={24} sm={12} key={item.level}>
                      <Row align="middle" justify="space-between" style={{ marginBottom: 4 }}>
                        <Col>
                          <Tag color={riskLevelColors[item.level] || '#999'}>{item.label}</Tag>
                        </Col>
                        <Col>
                          <Typography.Text>
                            {item.count} 条 ({item.percentage}%)
                          </Typography.Text>
                        </Col>
                      </Row>
                      <Progress
                        percent={item.percentage}
                        strokeColor={riskLevelColors[item.level] || '#999'}
                        showInfo={false}
                        size="small"
                      />
                    </Col>
                  ))}
                  {(riskData?.by_level || []).length === 0 && (
                    <Col span={24}>
                      <Typography.Text type="secondary">暂无风险等级数据</Typography.Text>
                    </Col>
                  )}
                </Row>
              </Card>

              <Card title="风险处理状态分布" size="small" style={{ marginBottom: 16 }}>
                <Row gutter={[16, 16]}>
                  {(riskData?.by_status || []).map((item: RiskStatusItem) => (
                    <Col xs={24} sm={12} key={item.status}>
                      <Row align="middle" justify="space-between" style={{ marginBottom: 4 }}>
                        <Col>
                          <Tag color={riskStatusColors[item.status] || '#999'}>{item.label}</Tag>
                        </Col>
                        <Col>
                          <Typography.Text>
                            {item.count} 条 ({item.percentage}%)
                          </Typography.Text>
                        </Col>
                      </Row>
                      <Progress
                        percent={item.percentage}
                        strokeColor={riskStatusColors[item.status] || '#999'}
                        showInfo={false}
                        size="small"
                      />
                    </Col>
                  ))}
                  {(riskData?.by_status || []).length === 0 && (
                    <Col span={24}>
                      <Typography.Text type="secondary">暂无处理状态数据</Typography.Text>
                    </Col>
                  )}
                </Row>
              </Card>

              <Space>
                <Button icon={<ReloadOutlined />} onClick={fetchRiskData}>
                  刷新
                </Button>
                <Button
                  icon={<RobotOutlined />}
                  onClick={() => openAiModal('overall_report', {
                    school_name: '本校',
                    total_students: overviewData?.total_students || '未知',
                    completed_count: overviewData?.total_completed || '未知',
                    completion_rate: overviewData?.overall_completion_rate || '未知',
                    risk_distribution: JSON.stringify(riskData?.by_level?.map((l: RiskLevelItem) => `${l.label}: ${l.count}条(${l.percentage}%)`).join('；') || '暂无'),
                    grade_overview: JSON.stringify(overviewData?.grades?.map((g: GradeOverview) => `${g.grade_name}: 完成${g.completion_rate}%`).join('；') || '暂无'),
                    dimension_avg_scores: '暂无',
                    quality_overview: JSON.stringify(riskData?.by_status?.map((s: RiskStatusItem) => `${s.label}: ${s.count}条(${s.percentage}%)`).join('；') || '暂无'),
                  }, 'AI分析 - 风险预警报表')}
                  style={{ borderColor: '#00d4ff', color: '#00d4ff' }}
                >
                  AI分析报告
                </Button>
              </Space>
            </>
          )}
          {!riskData && !riskLoading && (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无风险预警报表数据
            </div>
          )}
        </Spin>
      ),
    },

    // ---- Tab 3: 答题质量报表 ----
    {
      key: 'quality',
      label: '答题质量报表',
      children: (
        <Spin spinning={qualityLoading}>
          {qualityData && (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic title="答卷总数" value={qualityData?.total || 0} suffix="份" />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic
                      title="有效答卷率"
                      value={qualityData?.effective_rate || 0}
                      suffix="%"
                      precision={1}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic
                      title="建议复测人数"
                      value={qualityData?.suggest_retest_count || 0}
                      suffix="人"
                      valueStyle={{ color: (qualityData?.suggest_retest_count || 0) > 0 ? '#ff4d4f' : undefined }}
                    />
                  </Card>
                </Col>
              </Row>

              <Card title="质量等级分布" size="small" style={{ marginBottom: 16 }}>
                <Row gutter={[16, 16]}>
                  {(qualityData?.by_level || []).map((item: QualityLevelItem) => {
                    const info = qualityLevelLabels[item.level] || { label: item.level, color: '#999' };
                    const total = qualityData?.total || 0;
                    const pct = total > 0
                      ? Math.round((item.count / total) * 100 * 10) / 10
                      : 0;
                    return (
                      <Col xs={24} sm={12} key={item.level}>
                        <Row align="middle" justify="space-between" style={{ marginBottom: 4 }}>
                          <Col>
                            <Tag color={info.color}>{info.label}</Tag>
                          </Col>
                          <Col>
                            <Typography.Text>
                              {item.count} 份 ({pct}%)
                            </Typography.Text>
                          </Col>
                        </Row>
                        <Progress
                          percent={pct}
                          strokeColor={info.color}
                          showInfo={false}
                          size="small"
                        />
                      </Col>
                    );
                  })}
                  {(qualityData?.by_level || []).length === 0 && (
                    <Col span={24}>
                      <Typography.Text type="secondary">暂无质量等级数据</Typography.Text>
                    </Col>
                  )}
                </Row>
              </Card>

              <Space>
                <Button icon={<ReloadOutlined />} onClick={fetchQualityData}>
                  刷新
                </Button>
              </Space>
            </>
          )}
          {!qualityData && !qualityLoading && (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无答题质量报表数据
            </div>
          )}
        </Spin>
      ),
    },

    // ---- Tab 4: 问卷统计 ----
    {
      key: 'questionnaire',
      label: '问卷统计',
      children: (
        <Spin spinning={questionnaireLoading}>
          {questionnaires.length > 0 ? (
            <Table
              rowKey="id"
              dataSource={questionnaires}
              scroll={{ x: 'max-content' }}
              columns={[
                { title: '问卷标题', dataIndex: 'title', key: 'title', ellipsis: true },
                {
                  title: '分类', dataIndex: 'category', key: 'category', width: 110,
                  render: (cat: string) => (
                    <Tag>{questionnaireCategoryLabels[cat] || cat}</Tag>
                  ),
                },
                {
                  title: '题目数', dataIndex: 'question_count', key: 'question_count',
                  width: 80, align: 'center' as const,
                },
                {
                  title: '状态', dataIndex: 'status', key: 'status', width: 90,
                  render: (status: string) => {
                    const s = questionnaireStatusLabels[status] || { label: status, color: '#999' };
                    return <Tag color={s.color}>{s.label}</Tag>;
                  },
                },
                {
                  title: '适用年级', dataIndex: 'applicable_grades', key: 'applicable_grades',
                  width: 120, ellipsis: true,
                },
                {
                  title: '类型', dataIndex: 'is_builtin', key: 'is_builtin', width: 80,
                  render: (v: boolean) => v ? <Tag color="blue">内置</Tag> : <Tag>自定义</Tag>,
                },
              ]}
              pagination={{ pageSize: 20, showSizeChanger: false }}
              size="small"
              locale={{ emptyText: '暂无问卷数据' }}
            />
          ) : !questionnaireLoading ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无问卷数据
            </div>
          ) : null}
        </Spin>
      ),
    },

    // ---- Tab 5: 学生纵向追踪 ----
    {
      key: 'longitudinal',
      label: '学生纵向追踪',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }} wrap>
            <Select
              showSearch
              style={{ width: 260 }}
              placeholder="搜索学生姓名"
              filterOption={false}
              onSearch={searchStudents}
              onChange={(val: number) => { setLongitudinalStudentId(val); fetchLongitudinal(val); }}
              options={studentSearchResults.map((s: any) => ({ value: s.id, label: `${s.real_name} (${s.student_no || s.username})` }))}
              notFoundContent="输入姓名搜索"
            />
          </Space>

          <Spin spinning={longitudinalLoading}>
            {longitudinalData ? (
              longitudinalData.records.length > 0 ? (
                <>
                  <Typography.Text strong style={{ marginBottom: 16, display: 'block' }}>
                    {longitudinalData.student_name} — 共 {longitudinalData.records.length} 次测评记录
                  </Typography.Text>
                  <ReactECharts style={{ height: 350, marginBottom: 16 }} option={{
                    tooltip: { trigger: 'axis' },
                    legend: { data: ['总分', ...(longitudinalData.records[0]?.dimension_scores ? Object.keys(longitudinalData.records[0].dimension_scores).map(dim => DIMENSION_LABELS[dim] || dim) : [])], bottom: 0 },
                    grid: { left: 50, right: 20, top: 20, bottom: 60 },
                    xAxis: { type: 'category', data: longitudinalData.records.map(r => r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('zh-CN') : '-') },
                    yAxis: { type: 'value' },
                    series: [
                      { name: '总分', type: 'line', data: longitudinalData.records.map(r => r.total_score), smooth: true, lineStyle: { width: 3 } },
                      ...Object.keys(longitudinalData.records[0]?.dimension_scores || {}).map(dim => ({
                        name: DIMENSION_LABELS[dim] || dim, type: 'line' as const, smooth: true,
                        data: longitudinalData.records.map(r => (r.dimension_scores as Record<string, number>)?.[dim] ?? null),
                      })),
                    ],
                  }} />
                  <Table
                    rowKey="answer_sheet_id"
                    dataSource={longitudinalData.records}
                    size="small"
                    scroll={{ x: 'max-content' }}
                    pagination={false}
                    columns={[
                      { title: '测评时间', dataIndex: 'submitted_at', width: 120, render: (v: string) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
                      { title: '问卷', dataIndex: 'questionnaire_title', ellipsis: true },
                      { title: '总分', dataIndex: 'total_score', width: 80 },
                      { title: '风险等级', dataIndex: 'risk_level', width: 100, render: (v: string) => v ? <Tag color={RISK_COLORS[v]}>{RISK_LABELS[v] || v}</Tag> : '-' },
                    ]}
                  />
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>该学生暂无测评记录</div>
              )
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>请选择一位学生查看纵向追踪数据</div>
            )}
          </Spin>
        </div>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>数据报表</Typography.Title>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      <AiAnalysisModal
        open={aiModalOpen}
        type={aiType}
        data={aiData}
        title={aiTitle}
        onClose={() => setAiModalOpen(false)}
      />
    </div>
  );
}
