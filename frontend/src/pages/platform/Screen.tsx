import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ScreenShell from '../../components/screen/ScreenShell';
import ScreenCard from '../../components/screen/ScreenCard';
import ScreenKpiCard from '../../components/screen/ScreenKpiCard';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import RankingList from '../../components/screen/RankingList';
import { theme, COLORS, riskLabels } from '../../components/screen/screenTheme';
import client from '../../api/client';

const grid = { left: '3%', right: '4%', bottom: '3%', top: 15, containLabel: true };
const textStyle = { color: theme.textDim, fontSize: 11 };

export default function PlatformScreen() {
  const nav = useNavigate();
  const [data, setData] = useState<any>({});

  useEffect(() => {
    client.get('/platform/dashboard').then(r => setData(r.data.data || {})).catch(() => {});
    const t = setInterval(() => client.get('/platform/dashboard').then(r => setData(r.data.data || {})).catch(() => {}), 30000);
    return () => clearInterval(t);
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
  ];

  const rankings: { name: string; value: number; pct: number }[] = useMemo(
    () => (data.completion_rankings || []).map((s: any) => ({ name: s.name, value: s.completed_count || 0, pct: s.completion_rate || 0 })),
    [data.completion_rankings]
  );
  const riskRankings: { name: string; value: number }[] = useMemo(
    () => (data.risk_rankings || []).map((s: any) => ({ name: s.name, value: s.risk_count || 0 })),
    [data.risk_rankings]
  );
  const activeSchools: { id: number | string; title: string; status: string; statusColor: string; time: string }[] = useMemo(
    () => (data.recent_active_schools || []).slice(0, 6).map((s: any) => ({
      id: s.id, title: s.name, status: s.status ? '启用' : '停用', statusColor: s.status ? 'green' : 'default',
      time: s.last_active_at ? new Date(s.last_active_at).toLocaleDateString('zh-CN') : '-',
    })),
    [data.recent_active_schools]
  );

  const barOption = (items: any[], color: string, nameKey = 'name', valueKey = 'value') => ({
    tooltip: darkTooltip,
    grid,
    xAxis: { type: 'category', data: items.map(i => {
      const n = i[nameKey] || '';
      return n.length > 6 ? n.slice(0, 6) + '…' : n;
    }), axisLabel: { ...textStyle, rotate: items.length > 6 ? 35 : 0 }, axisLine: { lineStyle: { color: theme.border } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }, axisLabel: textStyle },
    series: [{ type: 'bar', data: items.map(i => i[valueKey] || 0), itemStyle: { color, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 }],
  });

  const pieOption = (dist: Record<string, number>, labels: Record<string, string>, colorMap: Record<string, string>) => {
    const pieData = Object.entries(dist).map(([k, v]) => ({ name: labels[k] || k, value: v, itemStyle: { color: colorMap[k] || theme.textDim } }));
    return {
      tooltip: darkTooltip,
      series: [{
        type: 'pie', radius: ['45%', '72%'], center: ['50%', '50%'], data: pieData,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 10, color: theme.text, position: 'inside' as const },
        labelLayout: { hideOverlap: true } as any,
      }],
      legend: { bottom: 0, textStyle: { color: theme.textDim, fontSize: 10 }, itemWidth: 10, itemHeight: 6 },
    };
  };

  return (
    <ScreenShell title="青盾 · 公安监管区域风险态势大屏" subtitle="学校接入、测评完成、风险提示、干预督办综合态势" onBack={() => nav('/platform/dashboard')}>
      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 8, marginBottom: 14 }}>
        {kpis.map(k => (
          <ScreenCard key={k.label}><ScreenKpiCard {...k} /></ScreenCard>
        ))}
      </div>

      {/* Charts + lists row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
        <ScreenCard title="学校完成率排名">
          <RankingList title="" items={rankings} valueLabel="完成率" emptyText="暂无数据" />
        </ScreenCard>
        <ScreenCard title="学校风险提示排名">
          <RankingList title="" items={riskRankings.map(r => ({ ...r, pct: undefined }))} valueLabel="条" emptyText="暂无数据" />
        </ScreenCard>
        <ScreenCard title="风险等级分布">
          <ScreenChart option={pieOption(data.risk_level_distribution || {}, riskLabels, COLORS)} empty={!data.risk_level_distribution || Object.keys(data.risk_level_distribution).length === 0} />
        </ScreenCard>
        <ScreenCard title="最近活跃学校">
          {/* reuse LatestList adapted for schools */}
          <div style={{ fontSize: 12 }}>
            {activeSchools.length > 0 ? activeSchools.map((s, i) => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: i < activeSchools.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: theme.text }}>{s.title}</span>
                <span style={{ color: s.statusColor === 'green' ? theme.green : theme.textDim, fontSize: 11, flexShrink: 0 }}>{s.status}</span>
                <span style={{ color: theme.textDim, fontSize: 11, flexShrink: 0 }}>{s.time}</span>
              </div>
            )) : <div style={{ color: theme.textDim, textAlign: 'center', padding: 20 }}>暂无数据</div>}
          </div>
        </ScreenCard>
      </div>
    </ScreenShell>
  );
}
