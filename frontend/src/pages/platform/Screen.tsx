import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ScreenShell, { useScreenMobile } from '../../components/screen/ScreenShell';
import ScreenCard from '../../components/screen/ScreenCard';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import RankingList from '../../components/screen/RankingList';
import { theme, COLORS, fmtNumber, riskLabels } from '../../components/screen/screenTheme';
import client from '../../api/client';

type RankingItem = { name: string; value: number; pct: number };
type RiskRankingItem = { name: string; value: number; suffix: string };

const textStyle = { color: theme.textDim, fontSize: 11 };
const axisLine = { lineStyle: { color: theme.border } };
const splitLine = { lineStyle: { color: 'rgba(255,255,255,0.04)' } };

export default function PlatformScreen() {
  const nav = useNavigate();
  const isMobile = useScreenMobile();
  const [data, setData] = useState<any>({});

  useEffect(() => {
    const fetchData = () => client.get('/platform/dashboard').then(r => setData(r.data.data || {})).catch(() => {});
    fetchData();
    const timer = setInterval(fetchData, 30000);
    return () => clearInterval(timer);
  }, []);

  const completionRate = Math.round(data.completion_rate || 0);
  const enabledRate = data.school_total ? Math.round(((data.enabled_school_total || 0) / data.school_total) * 100) : 0;
  const pendingRisks = data.pending_risk_total || 0;
  const riskTotal = data.risk_alert_total || 0;
  const riskDisposeRate = riskTotal ? Math.max(0, Math.round(((riskTotal - pendingRisks) / riskTotal) * 100)) : 100;

  const topKpis = [
    { label: '接入学校', value: data.school_total || 0, color: theme.cyan, icon: '🏫' },
    { label: '启用学校', value: data.enabled_school_total || 0, color: theme.green, icon: '✓' },
    { label: '学生总数', value: data.student_total || 0, color: theme.blue, icon: '👥' },
    { label: '教师总数', value: data.teacher_total || 0, color: theme.gold, icon: '👤' },
    { label: '问卷任务', value: data.task_total || 0, color: theme.purple, icon: '📋' },
    { label: '答卷总数', value: data.answer_sheet_total || 0, color: theme.cyan, icon: '📊' },
  ];
  const sideKpis = [
    { label: '测评完成率', value: completionRate, unit: '%', color: theme.green },
    { label: '风险提示', value: riskTotal, color: theme.red },
    { label: '待处理风险', value: pendingRisks, color: theme.orange },
    { label: 'AI分析', value: data.ai_call_total || 0, color: theme.purple },
    { label: '短信发送', value: data.sms_send_total || 0, color: theme.cyan },
    { label: '停用学校', value: data.disabled_school_total || 0, color: theme.textDim },
  ];

  const rankings: RankingItem[] = useMemo(
    () => (data.completion_rankings || []).map((s: any) => ({ name: s.name, value: s.completed_count || 0, pct: s.completion_rate || 0 })),
    [data.completion_rankings]
  );
  const riskRankings: RiskRankingItem[] = useMemo(
    () => (data.risk_rankings || []).map((s: any) => ({ name: s.name, value: s.risk_count || 0, suffix: '条' })),
    [data.risk_rankings]
  );
  const activeSchools = useMemo(
    () => (data.recent_active_schools || []).slice(0, 8).map((s: any) => ({
      id: s.id,
      title: s.name,
      status: s.status ? '启用' : '停用',
      statusColor: s.status ? theme.green : theme.textDim,
      time: s.last_active_at ? new Date(s.last_active_at).toLocaleDateString('zh-CN') : '-',
    })),
    [data.recent_active_schools]
  );

  const riskPie = useMemo(() => pieOption(data.risk_level_distribution || {}, riskLabels, COLORS), [data.risk_level_distribution]);
  const riskLevelBar = useMemo(() => {
    const items = Object.entries(data.risk_level_distribution || {}).map(([key, value]) => ({ name: riskLabels[key] || key, value: value as number, color: COLORS[key as keyof typeof COLORS] || theme.textDim })).filter(i => i.value > 0);
    if (!items.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: 36, right: 20, bottom: 24, top: 14, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map(i => i.name), axisLabel: { ...textStyle, fontSize: 12 }, axisLine },
      yAxis: { type: 'value' as const, axisLabel: textStyle, splitLine },
      series: [{
        type: 'bar' as const,
        data: items.map(i => ({
          value: i.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: i.color }, { offset: 1, color: `${i.color}33` }]),
            borderRadius: [6, 6, 0, 0],
            shadowColor: `${i.color}44`,
            shadowBlur: 8,
            shadowOffsetY: -2,
          },
        })),
        barMaxWidth: 40,
        label: { show: true, position: 'top' as const, color: theme.text, fontSize: 12, fontWeight: 600 },
      }],
    };
  }, [data.risk_level_distribution]);

  const completionBar = useMemo(() => {
    if (!rankings.length) return null;
    const items = rankings.slice(0, 8);
    return {
      tooltip: { ...darkTooltip, formatter: (p: any) => `${p.name}<br/>完成率: <b>${p.value}%</b>` },
      grid: { left: 36, right: 18, bottom: 30, top: 16, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map(s => s.name.length > 5 ? `${s.name.slice(0, 5)}…` : s.name), axisLabel: { ...textStyle, fontSize: 11, rotate: items.length > 5 ? 25 : 0 }, axisLine },
      yAxis: { type: 'value' as const, max: 100, splitLine, axisLabel: { ...textStyle, formatter: '{value}%' } },
      series: [{
        type: 'bar' as const,
        data: items.map(s => ({
          value: s.pct,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: theme.cyan }, { offset: 1, color: 'rgba(0,184,240,0.15)' }]),
            borderRadius: [6, 6, 0, 0],
            shadowColor: 'rgba(0,184,240,0.3)',
            shadowBlur: 6,
          },
        })),
        barMaxWidth: 36,
        label: { show: true, position: 'top' as const, color: theme.textDim, fontSize: 11, formatter: '{c}%' },
      }],
    };
  }, [rankings]);

  const riskBar = useMemo(() => horizontalBarOption(riskRankings.slice(0, 8)), [riskRankings]);

  const cockpitGauge = useMemo(() => ({
    tooltip: darkTooltip,
    series: [
      gaugeSeries('学校启用', enabledRate, theme.green, ['17%', '55%']),
      gaugeSeries('测评完成', completionRate, theme.cyan, ['50%', '55%']),
      gaugeSeries('风险处置', riskDisposeRate, theme.blue, ['83%', '55%']),
    ],
  }), [completionRate, enabledRate, riskDisposeRate]);

  const mobileCards = (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
        {[...topKpis, ...sideKpis].map(k => <GlowKpi key={k.label} {...k} />)}
      </div>
      <ScreenCard title="监管核心态势"><ScreenChart option={cockpitGauge} height={280} /></ScreenCard>
      <ScreenCard title="学校完成率排名"><RankingOrSoftEmpty items={rankings} valueLabel="完成率" /></ScreenCard>
      <ScreenCard title="学校风险提示排名"><RankingOrSoftEmpty items={riskRankings} valueLabel="风险提示" /></ScreenCard>
      <ScreenCard title="风险等级分布"><ChartOrSoftEmpty option={riskPie} height={260} /></ScreenCard>
      <ScreenCard title="最近活跃学校"><ActiveSchoolList items={activeSchools} /></ScreenCard>
    </div>
  );

  const desktopCards = (
    <div style={{
      height: 'calc(100vh - 96px)',
      minHeight: 620,
      display: 'grid',
      gridTemplateColumns: '1fr 1.4fr 1fr',
      gridTemplateRows: '100%',
      gap: 14,
    }}>
      {/* Left column */}
      <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr 1fr', gap: 14, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {topKpis.slice(0, 6).map(k => <GlowKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="学校完成率排名">
          <RankingOrSoftEmpty items={rankings} valueLabel="完成率" max={8} />
        </ScreenCard>
        <ScreenCard title="风险等级分布" glow={theme.red}>
          <ChartOrSoftEmpty option={riskPie} />
        </ScreenCard>
      </div>

      {/* Center column */}
      <div style={{ display: 'grid', gridTemplateRows: 'auto 1.4fr 1fr', gap: 14, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {sideKpis.slice(0, 3).map(k => <GlowKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="区域监管核心态势" style={{ background: 'linear-gradient(180deg, rgba(4,26,58,0.96), rgba(6,22,48,0.86))' }}>
          <div style={{ height: '100%', display: 'grid', gridTemplateRows: '1fr auto', gap: 10, minHeight: 0 }}>
            <ScreenChart option={cockpitGauge} />
            <StatusStrip enabledRate={enabledRate} completionRate={completionRate} riskTotal={riskTotal} pendingRisks={pendingRisks} aiTotal={data.ai_call_total || 0} smsTotal={data.sms_send_total || 0} />
          </div>
        </ScreenCard>
        <ScreenCard title="区域测评完成态势">
          <ChartOrSoftEmpty option={completionBar} />
        </ScreenCard>
      </div>

      {/* Right column */}
      <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr 1fr', gap: 14, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {sideKpis.slice(3).map(k => <GlowKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="学校风险提示排名" glow={theme.orange}>
          <RankingOrSoftEmpty items={riskRankings} valueLabel="风险提示" max={8} />
        </ScreenCard>
        <ScreenCard title="最近活跃学校">
          <ActiveSchoolList items={activeSchools} />
        </ScreenCard>
      </div>
    </div>
  );

  return (
    <ScreenShell title="金盾护苗 · 公安监管区域风险态势大屏" subtitle="学校接入、测评完成、风险提示、干预督办综合态势" onBack={() => nav('/platform/dashboard')}>
      {isMobile ? mobileCards : desktopCards}
    </ScreenShell>
  );
}

/* ─── KPI card with glow effect ─── */
function GlowKpi({ label, value, unit, color }: { label: string; value: number; unit?: string; color: string }) {
  return (
    <div style={{
      minHeight: 58,
      border: `1px solid ${color}22`,
      borderRadius: theme.radius,
      background: `linear-gradient(135deg, ${color}08 0%, rgba(6,22,48,0.9) 100%)`,
      boxShadow: `inset 0 1px 0 ${color}15, 0 2px 12px ${color}10`,
      padding: '10px 12px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
      position: 'relative',
      textAlign: 'center',
    }}>
      <div style={{
        position: 'absolute',
        top: 8,
        right: 8,
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 8px ${color}88`,
        opacity: 0.7,
      }} />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, justifyContent: 'center' }}>
        <span style={{
          fontFamily: theme.numberFont,
          color: '#f0fbff',
          fontSize: theme.kpiFontSize,
          fontWeight: 800,
          lineHeight: 1,
          textShadow: `0 0 20px ${color}33`,
        }}>{fmtNumber(value)}</span>
        {unit && <span style={{ color, fontSize: 13, flexShrink: 0, fontWeight: 600 }}>{unit}</span>}
      </div>
      <div style={{ marginTop: 6, minWidth: 0 }}>
        <span style={{ color: theme.textDim, fontSize: theme.kpiLabelSize, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
      </div>
    </div>
  );
}

/* ─── Status strip below gauge ─── */
function StatusStrip({ enabledRate, completionRate, riskTotal, pendingRisks, aiTotal, smsTotal }: { enabledRate: number; completionRate: number; riskTotal: number; pendingRisks: number; aiTotal: number; smsTotal: number }) {
  const items = [
    { label: '学校启用', value: `${enabledRate}%`, color: theme.green },
    { label: '测评完成', value: `${completionRate}%`, color: theme.cyan },
    { label: '风险提示', value: fmtNumber(riskTotal), color: theme.red },
    { label: '待处理', value: fmtNumber(pendingRisks), color: theme.orange },
    { label: 'AI分析', value: fmtNumber(aiTotal), color: theme.purple },
    { label: '短信发送', value: fmtNumber(smsTotal), color: theme.cyan },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: 8, flexShrink: 0 }}>
      {items.map(item => (
        <div key={item.label} style={{
          padding: '10px 6px',
          border: `1px solid ${item.color}22`,
          borderRadius: 6,
          background: `linear-gradient(135deg, ${item.color}08, rgba(0,20,44,0.5))`,
          textAlign: 'center',
          minWidth: 0,
        }}>
          <div style={{ color: item.color, fontFamily: theme.numberFont, fontWeight: 800, fontSize: theme.stripNumSize, lineHeight: 1, textShadow: `0 0 12px ${item.color}33` }}>{item.value}</div>
          <div style={{ color: theme.textDim, fontSize: 12, marginTop: 5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ─── Chart or empty ─── */
function ChartOrSoftEmpty({ option, height }: { option: any; height?: number }) {
  if (option) return <ScreenChart option={option} height={height} />;
  return <SoftEmpty height={height} />;
}

function RankingOrSoftEmpty({ items, valueLabel, max = 10 }: { items: any[]; valueLabel: string; max?: number }) {
  if (items.length) return <RankingList title="" items={items} valueLabel={valueLabel} emptyText="暂无数据" max={max} />;
  return <SoftEmpty />;
}

function SoftEmpty({ height }: { height?: number }) {
  return (
    <div style={{ height: height ? `${height}px` : '100%', minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{
        width: '72%',
        maxWidth: 240,
        padding: '20px 14px',
        border: `1px dashed ${theme.border}`,
        borderRadius: 10,
        background: 'rgba(0,184,240,0.03)',
        textAlign: 'center',
      }}>
        <div style={{
          width: 48,
          height: 48,
          margin: '0 auto 10px',
          borderRadius: '50%',
          border: `1px solid ${theme.border}`,
          boxShadow: 'inset 0 0 18px rgba(0,184,240,0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: theme.textDim,
          fontSize: 20,
        }}>--</div>
        <div style={{ color: theme.textDim, fontSize: 12 }}>暂无数据</div>
      </div>
    </div>
  );
}

/* ─── Active school list ─── */
function ActiveSchoolList({ items }: { items: { id: number | string; title: string; status: string; statusColor: string; time: string }[] }) {
  if (!items.length) return <SoftEmpty />;
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-around', fontSize: 12 }}>
      {items.map((s, i) => (
        <div key={s.id} style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 0',
          borderBottom: i < items.length - 1 ? `1px solid ${theme.border}` : 'none',
          minWidth: 0,
        }}>
          <span style={{
            width: 20,
            height: 20,
            borderRadius: 4,
            background: i < 3 ? `linear-gradient(135deg, ${theme.gold}, ${theme.orange})` : 'rgba(255,255,255,0.06)',
            color: i < 3 ? '#fff' : theme.textDim,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 11,
            fontWeight: 700,
            flexShrink: 0,
            fontFamily: theme.numberFont,
          }}>{i + 1}</span>
          <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: theme.text }}>{s.title}</span>
          <span style={{ color: s.statusColor, fontSize: 11, flexShrink: 0, padding: '1px 6px', borderRadius: 3, background: `${s.statusColor}15` }}>{s.status}</span>
          <span style={{ color: theme.textDim, fontSize: 11, flexShrink: 0 }}>{s.time}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Gauge series config ─── */
function gaugeSeries(name: string, value: number, color: string, center: [string, string]) {
  return {
    type: 'gauge' as const,
    center,
    radius: '42%',
    min: 0,
    max: 100,
    startAngle: 220,
    endAngle: -40,
    splitNumber: 5,
    progress: {
      show: true,
      width: 12,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `${color}66` }, { offset: 1, color }]),
        shadowColor: `${color}55`,
        shadowBlur: 10,
      },
    },
    axisLine: { lineStyle: { width: 12, color: [[1, 'rgba(255,255,255,0.04)']] } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { show: false },
    pointer: { show: false },
    anchor: { show: false },
    detail: {
      valueAnimation: true,
      formatter: '{value}%',
      color: '#f0fbff',
      fontSize: theme.gaugeDetailSize,
      fontWeight: 800,
      fontFamily: theme.numberFont,
      offsetCenter: [0, '-5%'],
      textShadowColor: `${color}44`,
      textShadowBlur: 12,
    },
    title: { color: theme.textDim, fontSize: 13, offsetCenter: [0, '30%'] },
    data: [{ value, name }],
  };
}

/* ─── Pie chart option ─── */
function pieOption(dist: Record<string, number>, labels: Record<string, string>, colorMap: Record<string, string>) {
  const pieData = Object.entries(dist).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({
    name: labels[k] || k,
    value: v,
    itemStyle: { color: colorMap[k] || theme.textDim },
  }));
  if (!pieData.length) return null;
  return {
    tooltip: darkTooltip,
    legend: { bottom: 0, textStyle: { color: theme.textDim, fontSize: 11 }, itemWidth: 12, itemHeight: 8, itemGap: 14 },
    series: [{
      type: 'pie' as const,
      radius: ['38%', '72%'],
      center: ['50%', '42%'],
      data: pieData,
      padAngle: 2,
      itemStyle: { borderRadius: 5 },
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 12, color: theme.text, lineHeight: 16 },
      emphasis: {
        scaleSize: 8,
        itemStyle: { shadowBlur: 16, shadowColor: 'rgba(0,0,0,0.4)' },
      },
      labelLayout: { hideOverlap: true } as any,
    }],
  };
}

/* ─── Horizontal bar option ─── */
function horizontalBarOption(items: RiskRankingItem[]) {
  if (!items.length) return null;
  return {
    tooltip: darkTooltip,
    grid: { left: 52, right: 32, bottom: 18, top: 10, containLabel: true },
    xAxis: { type: 'value' as const, splitLine, axisLabel: textStyle },
    yAxis: {
      type: 'category' as const,
      data: items.map(s => s.name.length > 7 ? `${s.name.slice(0, 7)}…` : s.name).reverse(),
      axisLabel: { color: theme.text, fontSize: 12 },
      axisLine,
    },
    series: [{
      type: 'bar' as const,
      data: items.map(s => s.value).reverse(),
      barMaxWidth: 24,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(229,72,77,0.15)' }, { offset: 1, color: theme.red }]),
        borderRadius: [0, 6, 6, 0],
        shadowColor: 'rgba(229,72,77,0.25)',
        shadowBlur: 6,
      },
      label: { show: true, position: 'right' as const, color: theme.textDim, fontSize: 11 },
    }],
  };
}
