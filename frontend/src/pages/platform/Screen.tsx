import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ScreenShell, { useScreenMobile } from '../../components/screen/ScreenShell';
import ScreenCard from '../../components/screen/ScreenCard';
import ScreenKpiCard from '../../components/screen/ScreenKpiCard';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import RankingList from '../../components/screen/RankingList';
import { theme, COLORS, riskLabels } from '../../components/screen/screenTheme';
import client from '../../api/client';

type RankingItem = { name: string; value: number; pct: number };
type RiskRankingItem = { name: string; value: number; suffix: string };

const grid = { left: 36, right: 16, bottom: 26, top: 18, containLabel: true };
const textStyle = { color: theme.textDim, fontSize: 11 };

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

  const kpis = [
    { label: '接入学校', value: data.school_total || 0, color: theme.cyan },
    { label: '启用学校', value: data.enabled_school_total || 0, color: theme.green },
    { label: '停用学校', value: data.disabled_school_total || 0, color: theme.textDim },
    { label: '学生总数', value: data.student_total || 0, color: theme.blue },
    { label: '教师总数', value: data.teacher_total || 0, color: theme.gold },
    { label: '问卷任务', value: data.task_total || 0, color: theme.purple },
    { label: '答卷总数', value: data.answer_sheet_total || 0, color: theme.green },
    { label: '风险提示', value: data.risk_alert_total || 0, color: theme.red },
    { label: '待处理', value: data.pending_risk_total || 0, color: theme.orange },
    { label: 'AI分析', value: data.ai_call_total || 0, color: theme.purple },
    { label: '短信发送', value: data.sms_send_total || 0, color: theme.cyan },
    { label: '完成率', value: data.completion_rate || 0, unit: '%', color: theme.green },
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
    () => (data.recent_active_schools || []).slice(0, 7).map((s: any) => ({
      id: s.id,
      title: s.name,
      status: s.status ? '启用' : '停用',
      statusColor: s.status ? theme.green : theme.textDim,
      time: s.last_active_at ? new Date(s.last_active_at).toLocaleDateString('zh-CN') : '-',
    })),
    [data.recent_active_schools]
  );

  const riskPie = useMemo(() => {
    const entries = Object.entries(data.risk_level_distribution || {}).filter(([, v]) => (v as number) > 0);
    if (!entries.length) return null;
    return {
      tooltip: darkTooltip,
      legend: { bottom: 0, textStyle: { color: theme.textDim, fontSize: 10 }, itemWidth: 10, itemHeight: 6 },
      series: [{
        type: 'pie' as const,
        radius: ['52%', '74%'],
        center: ['50%', '45%'],
        data: entries.map(([k, v]) => ({ name: riskLabels[k] || k, value: v, itemStyle: { color: COLORS[k as keyof typeof COLORS] || theme.textDim } })),
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 10, color: theme.text },
        labelLayout: { hideOverlap: true } as any,
      }],
    };
  }, [data.risk_level_distribution]);

  const completionBar = useMemo(() => {
    if (!rankings.length) return null;
    return {
      tooltip: darkTooltip,
      grid,
      xAxis: { type: 'category' as const, data: rankings.slice(0, 8).map(s => s.name.length > 6 ? `${s.name.slice(0, 6)}…` : s.name), axisLabel: { ...textStyle, rotate: rankings.length > 5 ? 30 : 0 }, axisLine: { lineStyle: { color: theme.border } } },
      yAxis: { type: 'value' as const, max: 100, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: { ...textStyle, formatter: '{value}%' } },
      series: [{ type: 'bar' as const, data: rankings.slice(0, 8).map(s => s.pct), barMaxWidth: 28, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: theme.cyan }, { offset: 1, color: 'rgba(0,184,240,0.25)' }]), borderRadius: [4, 4, 0, 0] } }],
    };
  }, [rankings]);

  const riskBar = useMemo(() => {
    if (!riskRankings.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: 44, right: 18, bottom: 18, top: 10, containLabel: true },
      xAxis: { type: 'value' as const, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: textStyle },
      yAxis: { type: 'category' as const, data: riskRankings.slice(0, 7).map(s => s.name.length > 7 ? `${s.name.slice(0, 7)}…` : s.name).reverse(), axisLabel: { color: theme.text, fontSize: 11 }, axisLine: { lineStyle: { color: theme.border } } },
      series: [{ type: 'bar' as const, data: riskRankings.slice(0, 7).map(s => s.value).reverse(), barMaxWidth: 18, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(229,72,77,0.25)' }, { offset: 1, color: theme.red }]), borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right' as const, color: theme.textDim, fontSize: 10 } }],
    };
  }, [riskRankings]);

  const mobileCards = (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
        {kpis.map(k => <ScreenCard key={k.label}><ScreenKpiCard {...k} /></ScreenCard>)}
      </div>
      <ScreenCard title="学校完成率排名"><RankingList title="" items={rankings} valueLabel="完成率" emptyText="暂无数据" /></ScreenCard>
      <ScreenCard title="学校风险提示排名"><RankingList title="" items={riskRankings} valueLabel="风险提示" emptyText="暂无数据" /></ScreenCard>
      <ScreenCard title="风险等级分布"><ScreenChart option={riskPie} height={240} empty={!riskPie} /></ScreenCard>
      <ScreenCard title="最近活跃学校"><ActiveSchoolList items={activeSchools} /></ScreenCard>
    </div>
  );

  const desktopCards = (
    <div style={{ height: 'calc(100vh - 96px)', minHeight: 640, display: 'grid', gridTemplateColumns: '1fr 1.45fr 1fr', gridTemplateRows: '1fr 1fr', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
          {kpis.slice(0, 6).map(k => <ScreenCard key={k.label}><ScreenKpiCard {...k} /></ScreenCard>)}
        </div>
        <ScreenCard title="学校完成率排名"><RankingList title="" items={rankings} valueLabel="完成率" emptyText="暂无数据" max={8} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: '1.05fr 0.95fr', gap: 12, minHeight: 0 }}>
        <ScreenCard title="区域测评完成态势"><ScreenChart option={completionBar} empty={!completionBar} /></ScreenCard>
        <ScreenCard title="学校风险提示分布"><ScreenChart option={riskBar} empty={!riskBar} /></ScreenCard>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr 1fr', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
          {kpis.slice(6).map(k => <ScreenCard key={k.label}><ScreenKpiCard {...k} /></ScreenCard>)}
        </div>
        <ScreenCard title="风险等级分布"><ScreenChart option={riskPie} empty={!riskPie} /></ScreenCard>
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

function ActiveSchoolList({ items }: { items: { id: number | string; title: string; status: string; statusColor: string; time: string }[] }) {
  if (!items.length) return <div style={{ color: theme.textDim, textAlign: 'center', padding: 20 }}>暂无数据</div>;
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
