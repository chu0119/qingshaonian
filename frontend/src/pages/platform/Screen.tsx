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
const splitLine = { lineStyle: { color: 'rgba(255,255,255,0.05)' } };

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

  const topKpis = [
    { label: '接入学校', value: data.school_total || 0, color: theme.cyan },
    { label: '启用学校', value: data.enabled_school_total || 0, color: theme.green },
    { label: '停用学校', value: data.disabled_school_total || 0, color: theme.textDim },
    { label: '学生总数', value: data.student_total || 0, color: theme.blue },
    { label: '教师总数', value: data.teacher_total || 0, color: theme.gold },
    { label: '问卷任务', value: data.task_total || 0, color: theme.purple },
  ];
  const sideKpis = [
    { label: '测评完成率', value: completionRate, unit: '%', color: theme.green },
    { label: '答卷总数', value: data.answer_sheet_total || 0, color: theme.green },
    { label: '风险提示', value: riskTotal, color: theme.red },
    { label: '待处理风险', value: pendingRisks, color: theme.orange },
    { label: 'AI分析', value: data.ai_call_total || 0, color: theme.purple },
    { label: '短信发送', value: data.sms_send_total || 0, color: theme.cyan },
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
      grid: { left: 34, right: 18, bottom: 22, top: 12, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map(i => i.name), axisLabel: textStyle, axisLine },
      yAxis: { type: 'value' as const, axisLabel: textStyle, splitLine },
      series: [{ type: 'bar' as const, data: items.map(i => ({ value: i.value, itemStyle: { color: i.color, borderRadius: [4, 4, 0, 0] } })), barMaxWidth: 30, label: { show: true, position: 'top' as const, color: theme.textDim, fontSize: 10 } }],
    };
  }, [data.risk_level_distribution]);

  const completionBar = useMemo(() => {
    if (!rankings.length) return null;
    const items = rankings.slice(0, 8);
    return {
      tooltip: darkTooltip,
      grid: { left: 34, right: 16, bottom: 28, top: 14, containLabel: true },
      xAxis: { type: 'category' as const, data: items.map(s => s.name.length > 6 ? `${s.name.slice(0, 6)}…` : s.name), axisLabel: { ...textStyle, rotate: items.length > 5 ? 30 : 0 }, axisLine },
      yAxis: { type: 'value' as const, max: 100, splitLine, axisLabel: { ...textStyle, formatter: '{value}%' } },
      series: [{ type: 'bar' as const, data: items.map(s => s.pct), barMaxWidth: 28, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: theme.cyan }, { offset: 1, color: 'rgba(0,184,240,0.25)' }]), borderRadius: [4, 4, 0, 0] }, label: { show: true, position: 'top' as const, color: theme.textDim, fontSize: 10, formatter: '{c}%' } }],
    };
  }, [rankings]);

  const riskBar = useMemo(() => horizontalBarOption(riskRankings.slice(0, 8)), [riskRankings]);

  const cockpitGauge = useMemo(() => ({
    tooltip: darkTooltip,
    series: [
      gaugeSeries('学校启用', enabledRate, theme.green, ['18%', '52%']),
      gaugeSeries('测评完成', completionRate, theme.cyan, ['50%', '52%']),
      gaugeSeries('风险处置', riskTotal ? Math.max(0, Math.round(((riskTotal - pendingRisks) / riskTotal) * 100)) : 100, theme.blue, ['82%', '52%']),
    ],
  }), [completionRate, enabledRate, pendingRisks, riskTotal]);

  const mobileCards = (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
        {[...topKpis, ...sideKpis].map(k => <CompactKpi key={k.label} {...k} />)}
      </div>
      <ScreenCard title="监管核心态势"><ScreenChart option={cockpitGauge} height={260} /></ScreenCard>
      <ScreenCard title="学校完成率排名"><RankingOrSoftEmpty items={rankings} valueLabel="完成率" /></ScreenCard>
      <ScreenCard title="学校风险提示排名"><RankingOrSoftEmpty items={riskRankings} valueLabel="风险提示" /></ScreenCard>
      <ScreenCard title="风险等级分布"><ChartOrSoftEmpty option={riskPie} height={240} /></ScreenCard>
      <ScreenCard title="最近活跃学校"><ActiveSchoolList items={activeSchools} /></ScreenCard>
    </div>
  );

  const desktopCards = (
    <div style={{ height: 'calc(100vh - 96px)', minHeight: 620, display: 'grid', gridTemplateColumns: '0.95fr 1.36fr 0.95fr', gridTemplateRows: '100%', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateRows: '128px 1fr 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {topKpis.map(k => <CompactKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="学校完成率排名"><RankingOrSoftEmpty items={rankings} valueLabel="完成率" max={8} /></ScreenCard>
        <ScreenCard title="风险等级结构"><ChartOrSoftEmpty option={riskPie} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: '128px 1.3fr 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
          {sideKpis.map(k => <CompactKpi key={k.label} {...k} />)}
        </div>
        <ScreenCard title="区域监管核心态势" style={{ background: 'linear-gradient(180deg, rgba(4,26,58,0.96), rgba(6,22,48,0.86))' }}>
          <div style={{ height: '100%', display: 'grid', gridTemplateRows: '1fr auto', gap: 8, minHeight: 0 }}>
            <ScreenChart option={cockpitGauge} />
            <StatusStrip enabledRate={enabledRate} completionRate={completionRate} riskTotal={riskTotal} pendingRisks={pendingRisks} aiTotal={data.ai_call_total || 0} smsTotal={data.sms_send_total || 0} />
          </div>
        </ScreenCard>
        <ScreenCard title="区域测评完成态势"><ChartOrSoftEmpty option={completionBar} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr 1fr', gap: 12, minHeight: 0 }}>
        <ScreenCard title="学校风险提示排名"><RankingOrSoftEmpty items={riskRankings} valueLabel="风险提示" max={8} /></ScreenCard>
        <ScreenCard title="学校风险提示分布"><ChartOrSoftEmpty option={riskBar} /></ScreenCard>
        <ScreenCard title="最近活跃学校"><ActiveSchoolList items={activeSchools} /></ScreenCard>
      </div>
    </div>
  );

  return (
    <ScreenShell title="青盾 · 公安监管区域风险态势大屏" subtitle="学校接入、测评完成、风险提示、干预督办综合态势" onBack={() => nav('/platform/dashboard')}>
      {isMobile ? mobileCards : desktopCards}
    </ScreenShell>
  );
}

function CompactKpi({ label, value, unit, color }: { label: string; value: number; unit?: string; color: string }) {
  return (
    <div style={{ minHeight: 56, border: `1px solid ${theme.border}`, borderRadius: theme.radius, background: 'linear-gradient(180deg, rgba(8,32,67,0.92), rgba(5,20,45,0.82))', boxShadow: 'inset 0 0 18px rgba(0,184,240,0.05)', padding: '8px 10px', display: 'flex', flexDirection: 'column', justifyContent: 'center', overflow: 'hidden' }}>
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
        <div key={item.label} style={{ padding: '8px 6px', border: `1px solid ${theme.border}`, borderRadius: 6, background: 'rgba(0,20,44,0.48)', textAlign: 'center', minWidth: 0 }}>
          <div style={{ color: item.color, fontFamily: theme.numberFont, fontWeight: 800, fontSize: 17, lineHeight: 1 }}>{item.value}</div>
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

function RankingOrSoftEmpty({ items, valueLabel, max = 10 }: { items: any[]; valueLabel: string; max?: number }) {
  if (items.length) return <RankingList title="" items={items} valueLabel={valueLabel} emptyText="暂无数据" max={max} />;
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

function ActiveSchoolList({ items }: { items: { id: number | string; title: string; status: string; statusColor: string; time: string }[] }) {
  if (!items.length) return <SoftEmpty />;
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-around', fontSize: 12 }}>
      {items.map((s, i) => (
        <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: i < items.length - 1 ? `1px solid ${theme.border}` : 'none', minWidth: 0 }}>
          <span style={{ width: 18, color: i < 3 ? theme.gold : theme.textDim, textAlign: 'center', flexShrink: 0 }}>{i + 1}</span>
          <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: theme.text }}>{s.title}</span>
          <span style={{ color: s.statusColor, fontSize: 11, flexShrink: 0 }}>{s.status}</span>
          <span style={{ color: theme.textDim, fontSize: 11, flexShrink: 0 }}>{s.time}</span>
        </div>
      ))}
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
    series: [{ type: 'pie' as const, radius: ['50%', '72%'], center: ['50%', '43%'], data: pieData, label: { show: true, formatter: '{b}\n{d}%', fontSize: 10, color: theme.text }, labelLayout: { hideOverlap: true } as any }],
  };
}

function horizontalBarOption(items: RiskRankingItem[]) {
  if (!items.length) return null;
  return {
    tooltip: darkTooltip,
    grid: { left: 44, right: 28, bottom: 18, top: 10, containLabel: true },
    xAxis: { type: 'value' as const, splitLine, axisLabel: textStyle },
    yAxis: { type: 'category' as const, data: items.map(s => s.name.length > 7 ? `${s.name.slice(0, 7)}…` : s.name).reverse(), axisLabel: { color: theme.text, fontSize: 11 }, axisLine },
    series: [{ type: 'bar' as const, data: items.map(s => s.value).reverse(), barMaxWidth: 18, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(229,72,77,0.25)' }, { offset: 1, color: theme.red }]), borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right' as const, color: theme.textDim, fontSize: 10 } }],
  };
}
