import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ScreenShell, { useScreenMobile } from '../../components/screen/ScreenShell';
import ScreenCard from '../../components/screen/ScreenCard';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import RankingList from '../../components/screen/RankingList';
import { theme, COLORS, fmtNumber, riskLabels, qualityLabels } from '../../components/screen/screenTheme';
import client from '../../api/client';

const textStyle = { color: theme.textDim, fontSize: 11 };
const axisLine = { lineStyle: { color: theme.border } };
const splitLine = { lineStyle: { color: 'rgba(255,255,255,0.05)' } };

export default function DataScreen() {
  const navigate = useNavigate();
  const isMobile = useScreenMobile();
  const [data, setData] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [risks, setRisks] = useState<any>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [dRes, qRes, rRes] = await Promise.all([
        client.get('/dashboard/school'),
        client.get('/quality/statistics/school'),
        client.get('/reports/risk-summary'),
      ]);
      setData(dRes.data.data);
      setQuality(qRes.data.data);
      setRisks(rRes.data.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchAll();
    const timer = setInterval(fetchAll, 30000);
    return () => clearInterval(timer);
  }, [fetchAll]);

  const stats = data?.stats || {};
  const riskDist = data?.risk_level_distribution || {};
  const qualityDist = data?.quality_distribution || {};
  const riskByStatus = (risks?.by_status || []).filter((s: any) => (s.count || 0) > 0);
  const qualityTotal = Object.values(qualityDist).reduce((sum: number, v: any) => sum + (v || 0), 0);
  const effectiveRate = quality?.effective_rate ?? (qualityTotal > 0 ? Math.round(((qualityDist.normal || 0) / qualityTotal) * 100) : 0);
  const completionRate = Math.round(stats.completion_rate || 0);
  const interventionRate = Math.round(stats.intervention_completion_rate || 0);
  const riskCount = stats.risk_count || 0;
  const pendingRisks = stats.pending_risks || 0;

  const topKpis = [
    { label: '学生总数', value: stats.student_count || 0, color: theme.cyan },
    { label: '教师总数', value: stats.teacher_count || 0, color: theme.blue },
    { label: '班级数量', value: stats.class_count || 0, color: theme.gold },
    { label: '进行中任务', value: stats.active_tasks || 0, color: theme.green },
    { label: '答卷总数', value: stats.total_answer_sheets || 0, color: theme.purple },
    { label: '风险提示', value: riskCount, color: theme.red },
  ];
  const sideKpis = [
    { label: '测评完成率', value: completionRate, unit: '%', color: theme.cyan },
    { label: '有效答卷率', value: effectiveRate, unit: '%', color: theme.green },
    { label: '待处理风险', value: pendingRisks, color: theme.orange },
    { label: '干预完成率', value: interventionRate, unit: '%', color: theme.blue },
  ];

  const dimensionItems = useMemo(() => {
    const dims = quality?.dimensions || quality?.dimension_scores;
    if (!dims) return [];
    return (Array.isArray(dims) ? dims : Object.entries(dims).map(([k, v]) => ({ name: k, score: v as number })))
      .filter((d: any) => d.score !== undefined)
      .slice(0, 8);
  }, [quality]);

  const riskPie = useMemo(() => pieOption(riskDist, riskLabels, COLORS), [riskDist]);
  const qualityPie = useMemo(() => pieOption(qualityDist, qualityLabels, { normal: COLORS.normal, mild_anomaly: COLORS.medium, moderate_anomaly: COLORS.high, severe_anomaly: COLORS.urgent }), [qualityDist]);
  const dimensionBar = useMemo(() => horizontalBarOption(dimensionItems, 'score'), [dimensionItems]);
  const interventionBar = useMemo(() => statusBarOption(riskByStatus), [riskByStatus]);

  const cockpitGauge = useMemo(() => ({
    tooltip: darkTooltip,
    series: [
      gaugeSeries('测评完成', completionRate, theme.cyan, ['18%', '52%']),
      gaugeSeries('答卷有效', effectiveRate, theme.green, ['50%', '52%']),
      gaugeSeries('干预完成', interventionRate, theme.blue, ['82%', '52%']),
    ],
  }), [completionRate, effectiveRate, interventionRate]);

  const riskLevelBar = useMemo(() => {
    const items = Object.entries(riskDist).map(([key, value]) => ({ name: riskLabels[key] || key, value: value as number, color: COLORS[key as keyof typeof COLORS] || theme.textDim })).filter(i => i.value > 0);
    if (!items.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: 34, right: 18, bottom: 22, top: 12, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map(i => i.name), axisLabel: textStyle, axisLine },
      yAxis: { type: 'value' as const, axisLabel: textStyle, splitLine },
      series: [{ type: 'bar' as const, data: items.map(i => ({ value: i.value, itemStyle: { color: i.color, borderRadius: [4, 4, 0, 0] } })), barMaxWidth: 30, label: { show: true, position: 'top' as const, color: theme.textDim, fontSize: 10 } }],
    };
  }, [riskDist]);

  const qualityRanking = useMemo(() => dimensionItems.map((d: any) => ({ name: d.name, value: Math.round(d.score || 0), suffix: '分' })), [dimensionItems]);

  const mobileCards = (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
        {[...topKpis, ...sideKpis].map(k => <CompactKpi key={k.label} {...k} />)}
      </div>
      <ScreenCard title="核心态势"><ScreenChart option={cockpitGauge} height={260} /></ScreenCard>
      <ScreenCard title="风险等级分布"><ChartOrSoftEmpty option={riskPie} height={240} /></ScreenCard>
      <ScreenCard title="答题质量分布"><ChartOrSoftEmpty option={qualityPie} height={240} /></ScreenCard>
      <ScreenCard title="维度关注信号"><ChartOrSoftEmpty option={dimensionBar} height={280} /></ScreenCard>
      <ScreenCard title="干预处理状态"><ChartOrSoftEmpty option={interventionBar} height={240} /></ScreenCard>
    </div>
  );

  const desktopCards = (
    <div style={{ height: 'calc(100vh - 96px)', minHeight: 620, display: 'grid', gridTemplateColumns: '0.95fr 1.36fr 0.95fr', gridTemplateRows: '100%', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateRows: '128px 1fr 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {topKpis.slice(0, 6).map(k => <CompactKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="风险等级结构"><ChartOrSoftEmpty option={riskPie} /></ScreenCard>
        <ScreenCard title="风险等级柱状分布"><ChartOrSoftEmpty option={riskLevelBar} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: '128px 1.3fr 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8 }}>
          {sideKpis.map(k => <CompactKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="学校测评核心态势" style={{ background: 'linear-gradient(180deg, rgba(4,26,58,0.96), rgba(6,22,48,0.86))' }}>
          <div style={{ height: '100%', display: 'grid', gridTemplateRows: '1fr auto', gap: 8, minHeight: 0 }}>
            <ScreenChart option={cockpitGauge} />
            <StatusStrip completionRate={completionRate} effectiveRate={effectiveRate} interventionRate={interventionRate} riskCount={riskCount} pendingRisks={pendingRisks} />
          </div>
        </ScreenCard>
        <ScreenCard title="维度关注信号分布"><ChartOrSoftEmpty option={dimensionBar} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr 1fr', gap: 12, minHeight: 0 }}>
        <ScreenCard title="答题质量分布"><ChartOrSoftEmpty option={qualityPie} /></ScreenCard>
        <ScreenCard title="干预处理状态"><ChartOrSoftEmpty option={interventionBar} /></ScreenCard>
        <ScreenCard title="维度得分排行"><RankingOrSoftEmpty items={qualityRanking} /></ScreenCard>
      </div>
    </div>
  );

  return (
    <ScreenShell title="学生风险防范数据驾驶舱" subtitle="风险等级分布、答题质量、干预处理综合态势" onBack={() => navigate(-1)}>
      {isMobile ? mobileCards : desktopCards}
    </ScreenShell>
  );
}

function CompactKpi({ label, value, unit, color }: { label: string; value: number; unit?: string; color: string }) {
  return (
    <div style={{
      minHeight: 56,
      border: `1px solid ${theme.border}`,
      borderRadius: theme.radius,
      background: 'linear-gradient(180deg, rgba(8,32,67,0.92), rgba(5,20,45,0.82))',
      boxShadow: 'inset 0 0 18px rgba(0,184,240,0.05)',
      padding: '8px 10px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, minWidth: 0 }}>
        <span style={{ fontFamily: theme.numberFont, color: '#f0fbff', fontSize: 'clamp(18px, 1.3vw, 28px)', fontWeight: 800, lineHeight: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fmtNumber(value)}</span>
        {unit && <span style={{ color, fontSize: 11, flexShrink: 0 }}>{unit}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 7, minWidth: 0 }}>
        <span style={{ width: 18, height: 2, borderRadius: 2, background: color, boxShadow: `0 0 10px ${color}`, flexShrink: 0 }} />
        <span style={{ color: theme.textDim, fontSize: 'clamp(10px, 0.68vw, 12px)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
      </div>
    </div>
  );
}

function StatusStrip({ completionRate, effectiveRate, interventionRate, riskCount, pendingRisks }: { completionRate: number; effectiveRate: number; interventionRate: number; riskCount: number; pendingRisks: number }) {
  const items = [
    { label: '测评完成', value: `${completionRate}%`, color: theme.cyan },
    { label: '答卷有效', value: `${effectiveRate}%`, color: theme.green },
    { label: '风险提示', value: fmtNumber(riskCount), color: theme.red },
    { label: '待处理', value: fmtNumber(pendingRisks), color: theme.orange },
    { label: '干预完成', value: `${interventionRate}%`, color: theme.blue },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 8, flexShrink: 0 }}>
      {items.map(item => (
        <div key={item.label} style={{ padding: '8px 6px', border: `1px solid ${theme.border}`, borderRadius: 6, background: 'rgba(0,20,44,0.48)', textAlign: 'center', minWidth: 0 }}>
          <div style={{ color: item.color, fontFamily: theme.numberFont, fontWeight: 800, fontSize: 18, lineHeight: 1 }}>{item.value}</div>
          <div style={{ color: theme.textDim, fontSize: 11, marginTop: 5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

function ChartOrSoftEmpty({ option, height }: { option: any; height?: number }) {
  if (option) return <ScreenChart option={option} height={height} />;
  return <SoftEmpty height={height} />;
}

function RankingOrSoftEmpty({ items }: { items: { name: string; value: number; suffix?: string }[] }) {
  if (items.length) return <RankingList title="" items={items} valueLabel="分" emptyText="暂无数据" max={8} />;
  return <SoftEmpty />;
}

function SoftEmpty({ height }: { height?: number }) {
  return (
    <div style={{ height: height ? `${height}px` : '100%', minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '72%', maxWidth: 240, padding: '18px 12px', border: `1px dashed ${theme.border}`, borderRadius: 10, background: 'rgba(0,184,240,0.035)', textAlign: 'center' }}>
        <div style={{ width: 48, height: 48, margin: '0 auto 10px', borderRadius: '50%', border: `1px solid ${theme.border}`, boxShadow: 'inset 0 0 18px rgba(0,184,240,0.12)' }} />
        <div style={{ color: theme.textDim, fontSize: 12 }}>暂无数据</div>
      </div>
    </div>
  );
}

function gaugeSeries(name: string, value: number, color: string, center: [string, string]) {
  return {
    type: 'gauge' as const,
    center,
    radius: '58%',
    min: 0,
    max: 100,
    startAngle: 210,
    endAngle: -30,
    splitNumber: 4,
    progress: { show: true, width: 9, itemStyle: { color } },
    axisLine: { lineStyle: { width: 9, color: [[1, 'rgba(255,255,255,0.08)']] } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { show: false },
    pointer: { show: false },
    anchor: { show: false },
    detail: { valueAnimation: true, formatter: '{value}%', color: '#f0fbff', fontSize: 22, fontWeight: 800, offsetCenter: [0, '-2%'] },
    title: { color: theme.textDim, fontSize: 12, offsetCenter: [0, '34%'] },
    data: [{ value, name }],
  };
}

function pieOption(dist: Record<string, number>, labels: Record<string, string>, colorMap: Record<string, string>) {
  const pieData = Object.entries(dist).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({ name: labels[k] || k, value: v, itemStyle: { color: colorMap[k] || theme.textDim } }));
  if (!pieData.length) return null;
  return {
    tooltip: darkTooltip,
    legend: { bottom: 0, textStyle: { color: theme.textDim, fontSize: 10 }, itemWidth: 10, itemHeight: 6 },
    series: [{
      type: 'pie' as const,
      radius: ['50%', '72%'],
      center: ['50%', '43%'],
      data: pieData,
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 10, color: theme.text },
      labelLayout: { hideOverlap: true } as any,
    }],
  };
}

function horizontalBarOption(items: any[], valueKey: string) {
  if (!items.length) return null;
  const colors = [theme.purple, theme.cyan, theme.orange, theme.green, theme.blue, theme.gold, '#ff85c0', '#87e8de'];
  const sliced = items.slice(0, 8);
  return {
    tooltip: darkTooltip,
    grid: { left: 52, right: 34, bottom: 18, top: 10, containLabel: true },
    xAxis: { type: 'value' as const, axisLabel: textStyle, splitLine },
    yAxis: { type: 'category' as const, data: sliced.map((d: any) => d.name.length > 6 ? `${d.name.slice(0, 6)}…` : d.name).reverse(), axisLabel: { color: theme.text, fontSize: 11 }, axisLine },
    series: [{
      type: 'bar' as const,
      data: sliced.slice().reverse().map((d: any, i: number) => ({ value: d[valueKey], itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `${colors[i] || theme.cyan}33` }, { offset: 1, color: colors[i] || theme.cyan }]), borderRadius: [0, 4, 4, 0] } })),
      barMaxWidth: 18,
      label: { show: true, position: 'right' as const, color: theme.textDim, fontSize: 10 },
    }],
  };
}

function statusBarOption(items: any[]) {
  if (!items.length) return null;
  const colors: Record<string, string> = { pending: COLORS.medium, processing: COLORS.low, in_progress: COLORS.low, completed: COLORS.normal, follow_up: theme.purple, closed: theme.textDim };
  const labels: Record<string, string> = { pending: '待处理', in_progress: '处理中', processing: '处理中', follow_up: '持续跟进', completed: '已完成', closed: '已关闭' };
  return {
    tooltip: darkTooltip,
    grid: { left: 34, right: 18, bottom: 24, top: 14, containLabel: true },
    xAxis: { type: 'category' as const, data: items.map((s: any) => labels[s.status] || s.status), axisLabel: textStyle, axisLine },
    yAxis: { type: 'value' as const, splitLine, axisLabel: textStyle },
    series: [{ type: 'bar' as const, data: items.map((s: any) => ({ value: s.count || 0, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: colors[s.status] || theme.cyan }, { offset: 1, color: `${colors[s.status] || theme.cyan}33` }]), borderRadius: [4, 4, 0, 0] } })), barMaxWidth: 34, label: { show: true, position: 'top' as const, color: theme.textDim, fontSize: 10 } }],
  };
}
