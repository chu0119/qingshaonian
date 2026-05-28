import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ScreenShell from '../../components/screen/ScreenShell';
import ScreenCard from '../../components/screen/ScreenCard';
import ScreenKpiCard from '../../components/screen/ScreenKpiCard';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import { theme, COLORS, riskLabels, qualityLabels } from '../../components/screen/screenTheme';
import client from '../../api/client';

const grid = { left: '3%', right: '4%', bottom: '3%', top: 15, containLabel: true };

export default function DataScreen() {
  const navigate = useNavigate();
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
    } catch { /* keep old data */ }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 30000);
    return () => clearInterval(t);
  }, [fetchAll]);

  const stats = data?.stats || {};
  const riskDist = data?.risk_level_distribution || {};
  const qualityDist = data?.quality_distribution || {};
  const riskByStatus = (risks?.by_status || []).filter((s: any) => (s.count || 0) > 0);

  const qualityTotal = Object.values(qualityDist).reduce((s: number, v: any) => s + (v || 0), 0);
  const effectiveRate = quality?.effective_rate ?? (qualityTotal > 0 ? Math.round(((qualityDist.normal || 0) / qualityTotal) * 100) : 100);

  const kpis = [
    { label: '学生总数', value: stats.student_count || 0, color: theme.cyan },
    { label: '教师总数', value: stats.teacher_count || 0, color: theme.blue },
    { label: '班级数量', value: stats.class_count || 0, color: theme.gold },
    { label: '进行中任务', value: stats.active_tasks || 0, color: theme.green },
    { label: '答卷总数', value: stats.total_answer_sheets || 0, color: theme.purple },
    { label: '完成率(%)', value: stats.completion_rate || 0, color: theme.cyan },
    { label: '有效答卷率(%)', value: effectiveRate, color: theme.green },
    { label: '风险提示', value: stats.risk_count || 0, color: theme.red },
    { label: '待处理', value: stats.pending_risks || 0, color: theme.orange },
    { label: '干预完成率(%)', value: stats.intervention_completion_rate || 0, color: theme.blue },
  ];

  const pieOption = (dist: Record<string, number>, labels: Record<string, string>, colorMap: Record<string, string>) => {
    const pieData = Object.entries(dist).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({
      name: labels[k] || k, value: v, itemStyle: { color: colorMap[k] || theme.textDim },
    }));
    if (!pieData.length) return null;
    return {
      tooltip: darkTooltip,
      legend: { bottom: 0, textStyle: { color: theme.textDim, fontSize: 10 }, itemWidth: 10, itemHeight: 6 },
      series: [{
        type: 'pie' as const, radius: ['45%', '70%'], center: ['50%', '45%'], data: pieData,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 10, color: theme.text },
        labelLayout: { hideOverlap: true } as any,
      }],
    };
  };

  const riskPie = useMemo(() => pieOption(riskDist, riskLabels, COLORS), [riskDist]);
  const qualityPie = useMemo(() => pieOption(qualityDist, qualityLabels, { normal: COLORS.normal, mild_anomaly: COLORS.medium, moderate_anomaly: COLORS.high, severe_anomaly: COLORS.urgent }), [qualityDist]);

  const interventionBar = useMemo(() => {
    if (!riskByStatus.length) return null;
    const colors: Record<string, string> = { pending: COLORS.medium, processing: COLORS.low, in_progress: COLORS.low, completed: COLORS.normal, follow_up: theme.purple, closed: theme.textDim };
    const statusLabels: Record<string, string> = { pending: '待处理', in_progress: '处理中', processing: '处理中', follow_up: '持续跟进', completed: '已完成', closed: '已关闭' };
    return {
      tooltip: darkTooltip,
      grid,
      xAxis: { type: 'category' as const, data: riskByStatus.map((s: any) => statusLabels[s.status] || s.status), axisLabel: { color: theme.textDim, fontSize: 11 }, axisLine: { lineStyle: { color: theme.border } } },
      yAxis: { type: 'value' as const, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }, axisLabel: { color: theme.textDim, fontSize: 10 } },
      series: [{ type: 'bar' as const, data: riskByStatus.map((s: any) => ({ value: s.count || 0, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: colors[s.status] || theme.cyan }, { offset: 1, color: (colors[s.status] || theme.cyan) + '33' }]), borderRadius: [3, 3, 0, 0] } })), barMaxWidth: 48 }],
    };
  }, [riskByStatus]);

  // Dimension data - only from API, no fake defaults
  const dimensionBar = useMemo(() => {
    const dims = quality?.dimensions || quality?.dimension_scores;
    if (!dims) return null;
    const items: { name: string; score: number }[] = Array.isArray(dims) ? dims : Object.entries(dims).map(([k, v]) => ({ name: k, score: v as number }));
    if (!items.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: '3%', right: '15%', bottom: '3%', top: 12, containLabel: true },
      xAxis: { type: 'value' as const, axisLabel: { color: theme.textDim, fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      yAxis: { type: 'category' as const, data: items.map(d => d.name.length > 5 ? d.name.slice(0, 5) + '…' : d.name).reverse(), axisLabel: { color: theme.text, fontSize: 10 }, axisLine: { lineStyle: { color: theme.border } } },
      series: [{
        type: 'bar' as const,
        data: items.slice().reverse().map((d, i) => {
          const colors = [theme.purple, theme.cyan, theme.orange, theme.green, theme.blue, theme.gold, '#ff85c0', '#87e8de'].reverse();
          return { value: d.score, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: colors[i] || theme.cyan }, { offset: 1, color: (colors[i] || theme.cyan) + '44' }]), borderRadius: [0, 3, 3, 0] } };
        }),
        barMaxWidth: 14,
        label: { show: true, position: 'right' as const, color: theme.textDim, fontSize: 10 },
      }],
    };
  }, [quality]);

  return (
    <ScreenShell title="学生风险防范数据驾驶舱" subtitle="风险等级分布、答题质量、干预处理综合态势" onBack={() => navigate(-1)}>
      {/* KPI */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: 8, marginBottom: 14 }}>
        {kpis.map(k => <ScreenCard key={k.label}><ScreenKpiCard {...k} /></ScreenCard>)}
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12 }}>
        <ScreenCard title="风险等级分布">
          <ScreenChart option={riskPie} height={280} empty={!riskPie} />
        </ScreenCard>
        <ScreenCard title="答题质量分布">
          <ScreenChart option={qualityPie} height={280} empty={!qualityPie} />
        </ScreenCard>
        <ScreenCard title="维度关注信号分布">
          <ScreenChart option={dimensionBar} height={280} empty={!dimensionBar} />
        </ScreenCard>
        <ScreenCard title="干预处理状态">
          <ScreenChart option={interventionBar} height={280} empty={!interventionBar} />
        </ScreenCard>
      </div>
    </ScreenShell>
  );
}
