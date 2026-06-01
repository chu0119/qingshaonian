import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Typography, Button, Spin, Empty, Card, Row, Col, Statistic, Alert, List, Space, Tabs, message } from 'antd';
import { RobotOutlined, AlertOutlined, CheckCircleOutlined, WarningOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import { theme } from '../../components/screen/screenTheme';
import client from '../../api/client';

import { RISK_LABELS, RISK_COLORS, RESULT_LABELS, ROLE_LABELS, DIMENSION_LABELS, ANALYSIS_TYPE_LABELS } from '../../utils/constants';
const textStyle = { color: theme.textDim, fontSize: 11 };
const axisLine = { lineStyle: { color: theme.border } };
const splitLine = { lineStyle: { color: 'rgba(255,255,255,0.05)' } };

export default function PlatformAIAnalysis() {
  const [logs, setLogs] = useState<any[]>([]);
  const [logTotal, setLogTotal] = useState(0);
  const [logLoading, setLogLoading] = useState(false);
  const [logPage, setLogPage] = useState(1);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  const fetchLogs = useCallback(async () => {
    setLogLoading(true);
    try {
      const r = await client.get('/platform/ai-logs', { params: { page: logPage, page_size: 20 } });
      setLogs(r.data.data?.items || []); setLogTotal(r.data.data?.total || 0);
    } catch { /* ignore */ } finally { setLogLoading(false); }
  }, [logPage]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const runAnalysis = async () => {
    setAnalysisLoading(true);
    try {
      const r = await client.post('/platform/ai-analysis/regional');
      setData(r.data.data);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '分析失败');
    } finally { setAnalysisLoading(false); }
  };

  // Charts derived from analysis data
  const riskDensityChart = () => {
    if (!data?.school_risk_density?.length) return null;
    const items = data.school_risk_density.slice(0, 8);
    return {
      tooltip: darkTooltip,
      grid: { left: 60, right: 24, bottom: 20, top: 10, containLabel: true },
      xAxis: { type: 'value' as const, splitLine, axisLabel: textStyle },
      yAxis: { type: 'category' as const, data: items.map((s: any) => s.name.length > 7 ? s.name.slice(0, 7) + '…' : s.name).reverse(), axisLabel: { color: '#d0dcf0', fontSize: 11 }, axisLine },
      series: [{ type: 'bar' as const, data: items.map((s: any) => s.density).reverse(), barMaxWidth: 22,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(229,72,77,0.2)' }, { offset: 1, color: '#e5484d' }]), borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right' as const, color: '#7084a0', fontSize: 11, formatter: '{c}%' } }],
    };
  };

  const interventionChart = () => {
    if (!data?.school_interventions?.length) return null;
    const items = data.school_interventions.slice(0, 8);
    return {
      tooltip: darkTooltip,
      grid: { left: 60, right: 24, bottom: 20, top: 10, containLabel: true },
      xAxis: { type: 'value' as const, max: 100, splitLine, axisLabel: { ...textStyle, formatter: '{value}%' } },
      yAxis: { type: 'category' as const, data: items.map((s: any) => s.name.length > 7 ? s.name.slice(0, 7) + '…' : s.name).reverse(), axisLabel: { color: '#d0dcf0', fontSize: 11 }, axisLine },
      series: [{ type: 'bar' as const, data: items.map((s: any) => s.resolution_rate).reverse(), barMaxWidth: 22,
        itemStyle: { color: (params: any) => {
          const v = params.value;
          return v >= 70 ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(61,214,140,0.2)' }, { offset: 1, color: '#3dd68c' }]) :
                 v >= 40 ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(240,140,60,0.2)' }, { offset: 1, color: '#f08c3c' }]) :
                 new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(229,72,77,0.2)' }, { offset: 1, color: '#e5484d' }]);
        }, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right' as const, color: '#7084a0', fontSize: 11, formatter: '{c}%' } }],
    };
  };

  const dimensionChart = () => {
    if (!data?.dimension_patterns?.length) return null;
    const items = data.dimension_patterns;
    return {
      tooltip: darkTooltip,
      radar: {
        indicator: items.map((d: any) => ({ name: DIMENSION_LABELS[d.dimension] || '未知', max: 100 })),
        axisName: { color: '#d0dcf0', fontSize: 11 },
        splitArea: { areaStyle: { color: ['rgba(0,184,240,0.02)', 'rgba(0,184,240,0.04)'] } },
        axisLine: { lineStyle: { color: 'rgba(0,184,240,0.15)' } },
        splitLine: { lineStyle: { color: 'rgba(0,184,240,0.1)' } },
      },
      series: [{ type: 'radar' as const, data: [{ value: items.map((d: any) => d.avg_score), name: '警告学生平均分',
        areaStyle: { color: 'rgba(229,72,77,0.15)' }, lineStyle: { color: '#e5484d', width: 2 }, itemStyle: { color: '#e5484d' } }] }],
    };
  };

  const trendChart = () => {
    if (!data?.monthly_risks?.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: 40, right: 20, bottom: 24, top: 14, containLabel: true },
      xAxis: { type: 'category' as const, data: data.monthly_risks.map((m: any) => m.month), axisLabel: textStyle, axisLine },
      yAxis: { type: 'value' as const, splitLine, axisLabel: textStyle },
      series: [{ type: 'line' as const, data: data.monthly_risks.map((m: any) => m.count), smooth: true,
        lineStyle: { color: theme.cyan, width: 2 }, itemStyle: { color: theme.cyan },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0,184,240,0.25)' }, { offset: 1, color: 'rgba(0,184,240,0.02)' }]) },
        label: { show: true, color: '#7084a0', fontSize: 11 } }],
    };
  };

  const riskLevelChart = () => {
    if (!data?.risk_level_dist || !Object.keys(data.risk_level_dist).length) return null;
    const pieData = Object.entries(data.risk_level_dist).filter(([, v]) => ((v as number) || 0) > 0).map(([k, v]) => ({ name: RISK_LABELS[k] || '未知', value: v as number, itemStyle: { color: RISK_COLORS[k] || '#999' } }));
    return {
      tooltip: darkTooltip,
      legend: { bottom: 0, textStyle: { color: '#7084a0', fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
      series: [{ type: 'pie' as const, radius: ['40%', '72%'], center: ['50%', '44%'], data: pieData, padAngle: 2, itemStyle: { borderRadius: 4 },
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 12, color: '#d0dcf0', lineHeight: 16 } }],
    };
  };

  const statusColors: Record<string, string> = { success: 'green', failure: 'red', not_configured: 'default' };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>AI 研判分析</Typography.Title>
        <Button type="primary" icon={<RobotOutlined />} loading={analysisLoading} onClick={runAnalysis}>
          生成区域分析报告
        </Button>
      </div>

      {analysisLoading && <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /><div style={{ marginTop: 12, color: '#888' }}>正在分析区域数据...</div></div>}

      {!data && !analysisLoading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Empty description="点击「生成区域分析报告」查看数据驱动的区域风险态势分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </Card>
      )}

      {data && !analysisLoading && (
        <div>
          {/* Assessment Summary */}
          <Alert
            type={data.assessment?.risk_level === '高' ? 'error' : data.assessment?.risk_level === '中' ? 'warning' : 'success'}
            showIcon
            icon={data.assessment?.risk_level === '高' ? <AlertOutlined /> : data.assessment?.risk_level === '中' ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
            message={<span>区域风险等级：<strong>{data.assessment?.risk_level || '低'}</strong></span>}
            description={
              <div>
                <div style={{ marginBottom: 8 }}>{data.assessment?.summary}</div>
                {data.assessment?.recommendations?.length > 0 && (
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {data.assessment.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                  </ul>
                )}
              </div>
            }
            style={{ marginBottom: 16 }}
          />

          {/* Overview Stats */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}><Card size="small"><Statistic title="接入学校" value={data.overview?.school_total || 0} /></Card></Col>
            <Col span={6}><Card size="small"><Statistic title="学生总数" value={data.overview?.student_total || 0} /></Card></Col>
            <Col span={6}><Card size="small"><Statistic title="风险预警" value={data.overview?.risk_total || 0} valueStyle={{ color: '#FF4D4F' }} /></Card></Col>
            <Col span={6}><Card size="small"><Statistic title="待处理" value={data.overview?.pending_total || 0} valueStyle={{ color: '#FA8C16' }} /></Card></Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            {/* Risk Level Distribution */}
            <Col span={12}>
              <Card title="风险等级分布" size="small" style={{ height: '100%' }}>
                {riskLevelChart() ? <ScreenChart option={riskLevelChart()} height={260} /> : <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
            {/* Monthly Trend */}
            <Col span={12}>
              <Card title="风险预警趋势（近6月）" size="small" style={{ height: '100%' }}>
                {trendChart() ? <ScreenChart option={trendChart()} height={260} /> : <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            {/* Risk Density */}
            <Col span={12}>
              <Card title="学校风险密度（每百人风险数）" size="small" style={{ height: '100%' }}>
                {riskDensityChart() ? <ScreenChart option={riskDensityChart()} height={280} /> : <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
            {/* Intervention Efficiency */}
            <Col span={12}>
              <Card title="学校干预处置率" size="small" style={{ height: '100%' }}>
                {interventionChart() ? <ScreenChart option={interventionChart()} height={280} /> : <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            {/* Dimension Patterns */}
            <Col span={12}>
              <Card title="警告学生维度画像" size="small" style={{ height: '100%' }}>
                {dimensionChart() ? <ScreenChart option={dimensionChart()} height={280} /> : <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
            {/* Anomaly Alerts */}
            <Col span={12}>
              <Card title="异常预警" size="small" style={{ height: '100%' }}>
                {data.anomaly_schools?.length > 0 || data.low_completion_tasks?.length > 0 ? (
                  <div>
                    {data.anomaly_schools?.map((s: any, i: number) => (
                      <div key={i} style={{ display: 'flex', gap: 8, padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                        <WarningOutlined style={{ color: '#FF4D4F', marginTop: 3 }} />
                        <div><strong>{s.name}</strong>：处置率仅 {s.resolution_rate}%，待处理 {s.pending} 条<div style={{ color: '#FF4D4F', fontSize: 12 }}>{s.alert}</div></div>
                      </div>
                    ))}
                    {data.low_completion_tasks?.map((t: any, i: number) => (
                      <div key={`t${i}`} style={{ display: 'flex', gap: 8, padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                        <ExclamationCircleOutlined style={{ color: '#FA8C16', marginTop: 3 }} />
                        <div><strong>{t.school_name}</strong> - {t.task_name}：完成率仅 {t.rate}%（{t.submitted}/{t.total}）</div>
                      </div>
                    ))}
                  </div>
                ) : <Empty description="暂无异常" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              </Card>
            </Col>
          </Row>

          {/* School Risk Level Stacked Bar */}
          {data.school_risk_levels?.length > 0 && (
            <Card title="各学校风险等级构成" size="small" style={{ marginBottom: 16 }}>
              <Table rowKey="name" dataSource={data.school_risk_levels} pagination={false} size="small"
                columns={[
                  { title: '学校', dataIndex: 'name' },
                  { title: '关注', dataIndex: 'low', render: (v: number) => v ? <Tag color="#1890FF">{v}</Tag> : '-' },
                  { title: '预警', dataIndex: 'medium', render: (v: number) => v ? <Tag color="#FA8C16">{v}</Tag> : '-' },
                  { title: '警告', dataIndex: 'high', render: (v: number) => v ? <Tag color="#FF4D4F">{v}</Tag> : '-' },
                  { title: '紧急', dataIndex: 'urgent', render: (v: number) => v ? <Tag color="#CF1322">{v}</Tag> : '-' },
                ]} />
            </Card>
          )}

          <div style={{ color: '#999', fontSize: 12, textAlign: 'center', marginTop: 8 }}>
            本分析基于系统现有数据通过统计算法生成，仅作为教育管理、风险防范和学生关怀参考，不作为医学诊断依据。
          </div>
        </div>
      )}

      {/* History Logs */}
      <Card title="分析历史记录" size="small" style={{ marginTop: 16 }}>
        <Table rowKey="id" dataSource={logs} loading={logLoading} scroll={{ x: 'max-content' }}
          columns={[
            { title: '时间', dataIndex: 'created_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
            { title: '分析类型', dataIndex: 'analysis_type', width: 120, render: (v: string) => ANALYSIS_TYPE_LABELS[v] || '未知' },
            { title: '模型', dataIndex: 'model_name', width: 120, render: (v: string) => v || '-' },
            { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={statusColors[v]}>{RESULT_LABELS[v] || '未知'}</Tag> },
            { title: '耗时(ms)', dataIndex: 'duration_ms', width: 90 },
            { title: '操作人', dataIndex: 'user_role', width: 100, render: (v: string) => ROLE_LABELS[v] || '未知' },
            { title: '错误信息', dataIndex: 'error_message', ellipsis: true, width: 200 },
          ]}
          pagination={{ current: logPage, total: logTotal, pageSize: 20, onChange: setLogPage }}
          locale={{ emptyText: <Empty description="暂无记录" /> }} />
      </Card>
    </div>
  );
}
