/**
 * 学校端数据大屏 - 丰富数据展示
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import * as echarts from 'echarts';
import ScreenShell from '../../components/screen/ScreenShell';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import { Card, CardHeader, KpiBig, StatusRow, MiniStat, EmptyBox, RiskLegend, ListItem, Tag } from '../../components/screen/ScreenComponents';
import { screenTheme as T, riskLabels, qualityLabels } from '../../components/screen/theme';
import { DIMENSION_LABELS, INTERVENTION_STATUS_LABELS } from '../../utils/constants';
import client from '../../api/client';

const axLine = { lineStyle: { color: 'rgba(64,158,255,0.1)' } };
const spLine = { lineStyle: { color: 'rgba(255,255,255,0.03)' } };

export default function DataScreen() {
  const [data, setData] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [risks, setRisks] = useState<any>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [dRes, qRes, rRes] = await Promise.all([client.get('/dashboard/school'), client.get('/quality/statistics/school'), client.get('/reports/risk-summary')]);
      setData(dRes.data?.data || {}); setQuality(qRes.data?.data || {}); setRisks(rRes.data?.data || {});
    } catch { /* */ }
  }, []);

  useEffect(() => { fetchAll(); const t = setInterval(fetchAll, 30000); return () => clearInterval(t); }, [fetchAll]);

  const s = data?.stats || {};
  const riskDist = data?.risk_level_distribution || {};
  const qualityDist = data?.quality_distribution || {};
  const riskByStatus = (risks?.by_status || []).filter((x: any) => (x.count || 0) > 0);
  const qualityTotalCount = (Object.values(qualityDist) as number[]).reduce((a, v) => a + (v || 0), 0);
  const effectiveRate = quality?.effective_rate ?? (qualityTotalCount > 0 ? Math.round(((qualityDist.normal || 0) / qualityTotalCount) * 100) : 0);
  const completionRate = Math.round(s.completion_rate || 0);
  const interventionRate = Math.round(s.intervention_completion_rate || 0);

  const dimensionItems = useMemo(() => {
    const dims = quality?.dimensions || quality?.dimension_scores;
    if (!dims) return [];
    return (Array.isArray(dims) ? dims : Object.entries(dims).map(([k, v]) => ({ name: DIMENSION_LABELS[k] || k, score: v as number })))
      .filter((d: any) => d.score !== undefined).slice(0, 8);
  }, [quality]);

  const dimBar = useMemo(() => {
    if (!dimensionItems.length) return null;
    return {
      tooltip: darkTooltip, grid: { left: 110, right: 48, bottom: 4, top: 4, containLabel: false },
      xAxis: { type: 'value' as const, max: 100, axisLabel: { color: T.textMuted, fontSize: 10 }, splitLine: spLine },
      yAxis: { type: 'category' as const, data: dimensionItems.map(d => d.name.length > 5 ? d.name.slice(0, 5) + '…' : d.name).reverse(), axisLabel: { color: T.text, fontSize: 12 }, axisLine: axLine },
      series: [{ type: 'bar' as const, data: dimensionItems.slice().reverse().map((d: any, i: number) => ({ value: d.score, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `${T.chartColors[i % T.chartColors.length]}15` }, { offset: 1, color: T.chartColors[i % T.chartColors.length] }]), borderRadius: [0, 3, 3, 0] } })), barMaxWidth: 16, label: { show: true, position: 'right' as const, color: T.textSecondary, fontSize: 11 } }],
    };
  }, [dimensionItems]);

  const makePie = (dist: Record<string, number>, labels: Record<string, string>, colors: Record<string, string>) => {
    const pieData = Object.entries(dist as Record<string, number>).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({ name: labels[k] || k, value: v, itemStyle: { color: colors[k] || T.textMuted } }));
    if (!pieData.length) return null;
    return { tooltip: darkTooltip, legend: { show: false }, series: [{ type: 'pie' as const, radius: ['40%', '68%'], center: ['38%', '50%'], data: pieData, padAngle: 2, itemStyle: { borderRadius: 5 }, label: { show: false } }] };
  };

  const riskPie = useMemo(() => makePie(riskDist, riskLabels, T.riskColors), [riskDist]);
  const qualityPie = useMemo(() => makePie(qualityDist, qualityLabels, T.qualityColors), [qualityDist]);

  const statusChart = useMemo(() => {
    if (!riskByStatus.length) return null;
    const sc: Record<string, string> = { pending: T.warning, in_progress: T.primary, completed: T.success, follow_up: '#9b59b6', closed: T.info };
    return {
      tooltip: darkTooltip, grid: { left: 48, right: 16, bottom: 32, top: 12, containLabel: false },
      xAxis: { type: 'category' as const, data: riskByStatus.map((x: any) => INTERVENTION_STATUS_LABELS[x.status] || x.status), axisLabel: { color: T.textSecondary, fontSize: 10 }, axisLine: axLine },
      yAxis: { type: 'value' as const, splitLine: spLine, axisLabel: { color: T.textMuted, fontSize: 10 } },
      series: [{ type: 'bar' as const, data: riskByStatus.map((x: any) => ({ value: x.count || 0, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: sc[x.status] || T.primary }, { offset: 1, color: `${sc[x.status] || T.primary}20` }]), borderRadius: [3, 3, 0, 0] } })), barMaxWidth: 32, label: { show: true, position: 'top' as const, color: T.textSecondary, fontSize: 11 } }],
    };
  }, [riskByStatus]);

  const classCompletion = useMemo(() => {
    const items = (data?.class_completion || []).slice(0, 6);
    if (!items.length) return null;
    return {
      tooltip: { ...darkTooltip, formatter: (p: any) => `${p.name}<br/>完成率: <b>${p.value}%</b>` },
      grid: { left: 90, right: 48, bottom: 4, top: 4, containLabel: false },
      xAxis: { type: 'value' as const, max: 100, axisLabel: { color: T.textMuted, fontSize: 10 }, splitLine: spLine },
      yAxis: { type: 'category' as const, data: items.map((c: any) => c.name?.length > 5 ? c.name.slice(0, 5) + '…' : c.name).reverse(), axisLabel: { color: T.text, fontSize: 12 }, axisLine: axLine },
      series: [{ type: 'bar' as const, data: items.slice().reverse().map((c: any) => ({ value: Math.round(c.completion_rate || 0), itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `${T.primary}20` }, { offset: 1, color: T.primary }]), borderRadius: [0, 3, 3, 0] } })), barMaxWidth: 16, label: { show: true, position: 'right' as const, color: T.textSecondary, fontSize: 11, formatter: '{c}%' } }],
    };
  }, [data]);

  return (
    <ScreenShell title="金盾护苗 · 学生关爱数据驾驶舱" subtitle="风险预警 · 答题质量 · 干预处理综合态势" backTo="/school-admin/dashboard">
      {/* KPI 条 - 8个 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 'var(--gap)', marginBottom: 'var(--gap)', flexShrink: 0 }}>
        <KpiBig label="学生总数" value={s.student_count || 0} icon="👨‍🎓" color={T.primary} />
        <KpiBig label="教师总数" value={s.teacher_count || 0} icon="👨‍🏫" color="#9b59b6" />
        <KpiBig label="班级数量" value={s.class_count || 0} icon="🏫" color={T.success} />
        <KpiBig label="完成率" value={completionRate} suffix="%" icon="📊" color={T.primary} />
        <KpiBig label="风险提示" value={s.risk_count || 0} icon="⚠️" color={T.warning} />
        <KpiBig label="待处理" value={s.pending_risks || 0} icon="🔔" color={T.danger} />
        <KpiBig label="有效率" value={effectiveRate} suffix="%" icon="✅" color={T.success} />
        <KpiBig label="干预率" value={interventionRate} suffix="%" icon="🔄" color={T.info} />
      </div>

      {/* 中间4栏 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr 1fr 1fr', gap: 'var(--gap)', flex: 1, minHeight: 0, marginBottom: 'var(--gap)' }}>
        <Card>
          <CardHeader title="维度关注信号" icon="📊" />
          <div style={{ flex: 1, minHeight: 0, padding: 'var(--gap-sm)' }}>{dimBar ? <ScreenChart option={dimBar} /> : <EmptyBox />}</div>
        </Card>

        <Card>
          <CardHeader title="风险结构" icon="🎯" />
          <div style={{ flex: 1, display: 'flex', minHeight: 0, padding: 'var(--pad-sm) 0' }}>
            <div style={{ flex: 1 }}>{riskPie ? <ScreenChart option={riskPie} /> : <EmptyBox />}</div>
            <RiskLegend dist={riskDist} labels={riskLabels} colors={T.riskColors} />
          </div>
        </Card>

        <Card>
          <CardHeader title="运行态势" icon="⚙️" />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)', padding: 'var(--pad-sm) var(--pad)' }}>
            <StatusRow label="测评完成率" value={completionRate} color={T.primary} />
            <StatusRow label="答卷有效率" value={effectiveRate} color={T.success} />
            <StatusRow label="干预完成率" value={interventionRate} color={T.info} />
            <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 'var(--gap-sm)', marginTop: 'auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap-sm)' }}>
                <MiniStat label="待处理" value={s.pending_risks || 0} color={T.danger} />
                <MiniStat label="已处置" value={Math.max(0, (s.risk_count || 0) - (s.pending_risks || 0))} color={T.success} />
                <MiniStat label="总任务" value={s.task_count || 0} color={T.primary} />
                <MiniStat label="答卷数" value={s.total_answer_sheets || 0} color="#9b59b6" />
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="质量分布" icon="📋" />
          <div style={{ flex: 1, display: 'flex', minHeight: 0, padding: 'var(--pad-sm) 0' }}>
            <div style={{ flex: 1 }}>{qualityPie ? <ScreenChart option={qualityPie} /> : <EmptyBox />}</div>
            <RiskLegend dist={qualityDist} labels={qualityLabels} colors={T.qualityColors} />
          </div>
        </Card>
      </div>

      {/* 底部4栏 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--gap)', height: 'calc(var(--kpi-h) * 3.5)', flexShrink: 0 }}>
        <Card>
          <CardHeader title="班级完成率" icon="🏆" extra={<span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>TOP {(data?.class_completion || []).length}</span>} />
          <div style={{ flex: 1, minHeight: 0, padding: '0 var(--gap-sm)' }}>
            {classCompletion ? <ScreenChart option={classCompletion} /> : <EmptyBox />}
          </div>
        </Card>

        <Card>
          <CardHeader title="干预状态" icon="🔄" />
          <div style={{ flex: 1, minHeight: 0, padding: '0 var(--gap-sm)' }}>
            {statusChart ? <ScreenChart option={statusChart} /> : <EmptyBox />}
          </div>
        </Card>

        <Card>
          <CardHeader title="风险详情" icon="⚠️" extra={<Tag color={T.danger}>{(risks?.items || []).filter((r: any) => r.status === 'pending').length} 待处理</Tag>} />
          <div style={{ flex: 1, overflow: 'hidden', padding: 'var(--gap-sm) var(--pad)' }}>
            {(risks?.items || []).slice(0, 6).length > 0 ? (risks?.items || []).slice(0, 6).map((r: any, i: number) => (
              <ListItem key={i} index={i}>
                <Tag color={T.riskColors[r.risk_level as keyof typeof T.riskColors] || T.textMuted}>{riskLabels[r.risk_level] || r.risk_level}</Tag>
                <span style={{ fontSize: 'var(--fs-body)', color: T.text, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.student_name || '-'}</span>
                <span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>{r.class_name || ''}</span>
              </ListItem>
            )) : <EmptyBox text="暂无风险" />}
          </div>
        </Card>

        <Card>
          <CardHeader title="最近答卷" icon="📝" extra={<span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>RECENT</span>} />
          <div style={{ flex: 1, overflow: 'hidden', padding: 'var(--gap-sm) var(--pad)' }}>
            {(data?.recent_sheets || []).slice(0, 6).length > 0 ? (data?.recent_sheets || []).slice(0, 6).map((sh: any, i: number) => (
              <ListItem key={i} index={i}>
                <span style={{ fontSize: 'var(--fs-body)', color: T.text, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sh.student_name || '-'}</span>
                <Tag color={sh.status === 'submitted' ? T.success : T.warning}>{sh.status === 'submitted' ? '已提交' : '进行中'}</Tag>
                <span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted, fontFamily: T.fontMono }}>{sh.submitted_at ? new Date(sh.submitted_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}</span>
              </ListItem>
            )) : <EmptyBox text="暂无答卷" />}
          </div>
        </Card>
      </div>
    </ScreenShell>
  );
}
