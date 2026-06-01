import { useEffect, useMemo, useRef, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Typography, Progress, Space, Empty } from 'antd';
import {
  BankOutlined, TeamOutlined, UserOutlined, AlertOutlined, FileTextOutlined,
  BarChartOutlined, CheckCircleOutlined, MessageOutlined, RobotOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS } from '../../utils/constants';

const { Title } = Typography;

function formatTime(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-';
}

export default function Dashboard() {
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const chartsRef = useRef<{ chart: echarts.ECharts; observer: ResizeObserver; el: HTMLElement }[]>([]);

  useEffect(() => {
    setLoading(true);
    client.get('/platform/dashboard')
      .then((r) => setData(r.data.data || {}))
      .catch(() => setData({}))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      chartsRef.current.forEach(({ chart, observer, el }) => {
        chart.dispose();
        observer.disconnect();
        el.remove();
      });
      chartsRef.current = [];
    };
  }, []);

  const initChart = (el: HTMLElement, option: any) => {
    if (!el) return;
    const chart = echarts.init(el);
    chart.setOption(option);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(el);
    chartsRef.current.push({ chart, observer, el });
  };

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

  const riskDist = data.risk_level_distribution || {};
  const riskLabels = RISK_LABELS;
  const riskColors = RISK_COLORS;

  const riskPieOption = useMemo(() => {
    const pieData = Object.entries(riskDist).filter(([, v]) => (v as number || 0) > 0).map(([k, v]) => ({ name: riskLabels[k] || '未知', value: v as number, itemStyle: { color: riskColors[k] } }));
    if (!pieData.length) return null;
    return {
      tooltip: { trigger: 'item' as const },
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      series: [{ type: 'pie' as const, radius: ['45%', '72%'], center: ['50%', '45%'], data: pieData, padAngle: 2, itemStyle: { borderRadius: 4 },
        label: { show: true, formatter: '{b}: {c} ({d}%)', fontSize: 12 } }],
    };
  }, [data.risk_level_distribution]);

  const completionBarOption = useMemo(() => {
    const items = (data.completion_rankings || []).slice(0, 8);
    if (!items.length) return null;
    return {
      tooltip: { trigger: 'axis' as const },
      grid: { left: 40, right: 20, bottom: 40, top: 16, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map((s: any) => s.name.length > 6 ? s.name.slice(0, 6) + '…' : s.name),
        axisLabel: { rotate: items.length > 5 ? 30 : 0, fontSize: 11 } },
      yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%' } },
      series: [{ type: 'bar' as const, data: items.map((s: any) => s.completion_rate || 0),
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#1677ff' }, { offset: 1, color: '#69b1ff' }]), borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 32, label: { show: true, position: 'top' as const, formatter: '{c}%', fontSize: 11 } }],
    };
  }, [data.completion_rankings]);

  const riskBarOption = useMemo(() => {
    const items = (data.risk_rankings || []).slice(0, 8);
    if (!items.length) return null;
    return {
      tooltip: { trigger: 'axis' as const },
      grid: { left: 40, right: 20, bottom: 40, top: 16, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map((s: any) => s.name.length > 6 ? s.name.slice(0, 6) + '…' : s.name),
        axisLabel: { rotate: items.length > 5 ? 30 : 0, fontSize: 11 } },
      yAxis: { type: 'value' as const },
      series: [{ type: 'bar' as const, data: items.map((s: any) => s.risk_count || 0),
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#ff4d4f' }, { offset: 1, color: '#ff7875' }]), borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 32, label: { show: true, position: 'top' as const, fontSize: 11 } }],
    };
  }, [data.risk_rankings]);

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
              <Statistic title={card.title} value={card.value || 0} prefix={card.icon} valueStyle={{ color: card.color }} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="风险等级分布" loading={loading}>
            {riskPieOption ? (
              <div ref={el => { if (el) initChart(el, riskPieOption); }} style={{ height: 280 }} />
            ) : <Empty description="暂无风险数据" />}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="学校完成率排名" loading={loading}>
            {completionBarOption ? (
              <div ref={el => { if (el) initChart(el, completionBarOption); }} style={{ height: 280 }} />
            ) : <Empty description="暂无数据" />}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="学校风险数量对比" loading={loading}>
            {riskBarOption ? (
              <div ref={el => { if (el) initChart(el, riskBarOption); }} style={{ height: 280 }} />
            ) : <Empty description="暂无数据" />}
          </Card>
        </Col>
      </Row>

      {data.quality_distribution && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="答卷质量分布" loading={loading}>
              {Object.entries(data.quality_distribution).map(([level, count]) => {
                const labels: Record<string, string> = { normal: '正常', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '严重异常' };
                const colors: Record<string, string> = { normal: '#52c41a', mild_anomaly: '#faad14', moderate_anomaly: '#fa8c16', severe_anomaly: '#ff4d4f' };
                const total = data.quality_total || 1;
                return (
                  <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ width: 80, fontSize: 13 }}>{labels[level] || level}</span>
                    <Progress percent={Math.round((count as number) / total * 100)} size="small" strokeColor={colors[level] || '#1890ff'} style={{ flex: 1 }} />
                    <span style={{ width: 50, textAlign: 'right', fontSize: 13 }}>{count as number}</span>
                  </div>
                );
              })}
              <div style={{ marginTop: 8, fontSize: 13, color: '#666' }}>
                有效率：<span style={{ fontWeight: 600, color: '#1890ff' }}>{data.quality_effective_rate || 0}%</span>
              </div>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="风险等级分布" loading={loading}>
              {Object.entries(data.risk_level_distribution || {}).map(([level, count]) => (
                <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ width: 80, fontSize: 13 }}>{RISK_LABELS[level] || level}</span>
                  <Progress percent={Math.round((count as number) / Math.max(data.risk_alert_total || 1, 1) * 100)} size="small" strokeColor={RISK_COLORS[level] || '#1890ff'} style={{ flex: 1 }} />
                  <span style={{ width: 50, textAlign: 'right', fontSize: 13 }}>{count as number}</span>
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={<Space><BarChartOutlined />学校完成率详情</Space>} loading={loading}>
            <Table rowKey="id" dataSource={data.completion_rankings || []} columns={completionColumns} pagination={false} scroll={{ x: 'max-content' }}
              locale={{ emptyText: <Empty description="暂无完成率数据" /> }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<Space><AlertOutlined />学校风险提示排名</Space>} loading={loading}>
            <Table rowKey="id" dataSource={data.risk_rankings || []} columns={riskColumns} pagination={false} scroll={{ x: 'max-content' }}
              locale={{ emptyText: <Empty description="暂无风险提示数据" /> }} />
          </Card>
        </Col>
        <Col xs={24}>
          <Card title={<Space><BankOutlined />最近活跃学校</Space>} loading={loading}>
            <Table rowKey="id" dataSource={data.recent_active_schools || []} columns={activeColumns} pagination={false} scroll={{ x: 'max-content' }}
              locale={{ emptyText: <Empty description="暂无活跃记录" /> }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
