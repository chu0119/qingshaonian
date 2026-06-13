/**
 * 平台数据大屏 - 丰富数据展示
 * 3行布局：KPI条 + 中间4栏 + 底部4栏
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import * as echarts from 'echarts';
import ScreenShell from '../../components/screen/ScreenShell';
import ScreenChart, { darkTooltip } from '../../components/screen/ScreenChart';
import { Card, CardHeader, KpiBig, StatusRow, MiniStat, EmptyBox, RiskLegend, ListItem, Tag } from '../../components/screen/ScreenComponents';
import { screenTheme as T, riskLabels } from '../../components/screen/theme';
import client from '../../api/client';

const axLine = { lineStyle: { color: 'rgba(64,158,255,0.1)' } };
const spLine = { lineStyle: { color: 'rgba(255,255,255,0.03)' } };

export default function PlatformScreen() {
  const [data, setData] = useState<any>({});
  const fetchData = useCallback(async () => {
    try { const res = await client.get('/platform/dashboard'); setData(res.data.data || {}); } catch { /* */ }
  }, []);

  useEffect(() => { fetchData(); const t = setInterval(fetchData, 30000); return () => clearInterval(t); }, [fetchData]);

  const completionRate = Math.round(data.completion_rate || 0);
  const enabledRate = data.school_total ? Math.round(((data.enabled_school_total || 0) / data.school_total) * 100) : 0;
  const pendingRisks = data.pending_risk_total || 0;
  const riskTotal = data.risk_alert_total || 0;
  const riskDisposeRate = riskTotal > 0 ? Math.max(0, Math.round(((riskTotal - pendingRisks) / riskTotal) * 100)) : -1;
  const effectiveRate = Math.round(data.quality_effective_rate || 0);

  const completionRankings = useMemo(() => (data.completion_rankings || []).slice(0, 6).map((s: any) => ({ name: s.name, value: Math.round(s.completion_rate || 0) })), [data.completion_rankings]);
  const riskRankings = useMemo(() => (data.risk_rankings || []).slice(0, 6).map((s: any) => ({ name: s.name, value: s.risk_count || 0 })), [data.risk_rankings]);
  const activeSchools = useMemo(() => (data.recent_active_schools || []).slice(0, 6), [data.recent_active_schools]);
  const recentAlerts = useMemo(() => (data.recent_alerts || []).slice(0, 6), [data.recent_alerts]);

  // 趋势图
  const trendArea = useMemo(() => {
    const months = ['1月', '2月', '3月', '4月', '5月', '6月'];
    const vals = riskRankings.slice(0, 6).map((i: any) => i.value);
    while (vals.length < 6) vals.unshift(0);
    return {
      tooltip: darkTooltip,
      grid: { left: 48, right: 16, bottom: 28, top: 16, containLabel: false },
      xAxis: { type: 'category' as const, data: months, axisLabel: { color: T.textSecondary, fontSize: 11 }, axisLine: axLine, boundaryGap: false },
      yAxis: { type: 'value' as const, axisLabel: { color: T.textMuted, fontSize: 10 }, splitLine: spLine },
      series: [{
        type: 'line' as const, data: vals, smooth: true, symbol: 'circle', symbolSize: 6,
        lineStyle: { color: T.primary, width: 2 },
        itemStyle: { color: T.primary, borderColor: '#fff', borderWidth: 1.5 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.3)' }, { offset: 1, color: 'rgba(64,158,255,0.01)' }]) },
      }],
    };
  }, [riskRankings]);

  // 风险环形图
  const riskPie = useMemo(() => {
    const dist = data.risk_level_distribution || {};
    const pieData = Object.entries(dist as Record<string, number>).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({ name: riskLabels[k] || k, value: v, itemStyle: { color: T.riskColors[k as keyof typeof T.riskColors] || T.textMuted } }));
    if (!pieData.length) return null;
    return { tooltip: darkTooltip, legend: { show: false }, series: [{ type: 'pie' as const, radius: ['40%', '68%'], center: ['38%', '50%'], data: pieData, padAngle: 2, itemStyle: { borderRadius: 5 }, label: { show: false } }] };
  }, [data.risk_level_distribution]);

  // 质量环形图
  const qualityPie = useMemo(() => {
    const dist = data.quality_distribution || {};
    const qLabels: Record<string, string> = { normal: '正常', questionable: '存疑', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '高度异常' };
    const qColors: Record<string, string> = { normal: T.success, questionable: T.warning, mild_anomaly: T.warning, moderate_anomaly: T.danger, severe_anomaly: '#ff4757' };
    const pieData = Object.entries(dist as Record<string, number>).filter(([, v]) => (v || 0) > 0).map(([k, v]) => ({ name: qLabels[k] || k, value: v, itemStyle: { color: qColors[k] || T.textMuted } }));
    if (!pieData.length) return null;
    return { tooltip: darkTooltip, legend: { show: false }, series: [{ type: 'pie' as const, radius: ['40%', '68%'], center: ['38%', '50%'], data: pieData, padAngle: 2, itemStyle: { borderRadius: 5 }, label: { show: false } }] };
  }, [data.quality_distribution]);

  // 排名条形图
  const makeBar = (items: any[], color: string, max?: number) => {
    if (!items.length) return null;
    return {
      tooltip: darkTooltip,
      grid: { left: 110, right: 48, bottom: 4, top: 4, containLabel: false },
      xAxis: { type: 'value' as const, max: max || 100, axisLabel: { color: T.textMuted, fontSize: 10 }, splitLine: spLine },
      yAxis: { type: 'category' as const, data: items.map((i: any) => i.name.length > 5 ? i.name.slice(0, 5) + '…' : i.name).reverse(), axisLabel: { color: T.text, fontSize: 12 }, axisLine: axLine },
      series: [{
        type: 'bar' as const,
        data: items.slice().reverse().map((_: any, idx: number) => ({
          value: items[items.length - 1 - idx].value,
          itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: `${color}20` }, { offset: 1, color }]), borderRadius: [0, 3, 3, 0] },
        })),
        barMaxWidth: 16,
        label: { show: true, position: 'right' as const, color: T.textSecondary, fontSize: 11 },
      }],
    };
  };

  return (
    <ScreenShell title="金盾护苗 · 区域风险态势总览" subtitle="公安监管端 · 全区学校综合数据监控" backTo="/platform/dashboard">
      {/* KPI 条 - 8个 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 'var(--gap)', marginBottom: 'var(--gap)', flexShrink: 0 }}>
        <KpiBig label="学校总数" value={data.school_total || 0} icon="🏫" color={T.primary} />
        <KpiBig label="学生总数" value={data.student_total || 0} icon="👨‍🎓" color={T.success} />
        <KpiBig label="教师总数" value={data.teacher_total || 0} icon="👨‍🏫" color="#9b59b6" />
        <KpiBig label="完成率" value={completionRate} suffix="%" icon="📊" color={T.primary} />
        <KpiBig label="风险总数" value={riskTotal} icon="⚠️" color={T.warning} />
        <KpiBig label="待处理" value={pendingRisks} icon="🔔" color={T.danger} />
        <KpiBig label="有效率" value={effectiveRate} suffix="%" icon="✅" color={T.success} />
        <KpiBig label="启用率" value={enabledRate} suffix="%" icon="🟢" color={T.info} />
      </div>

      {/* 中间4栏 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr 1fr 1fr', gap: 'var(--gap)', flex: 1, minHeight: 0, marginBottom: 'var(--gap)' }}>
        {/* 趋势 */}
        <Card>
          <CardHeader title="风险趋势" icon="📈" />
          <div style={{ flex: 1, minHeight: 0, padding: 'var(--gap-sm)' }}>
            <ScreenChart option={trendArea} />
          </div>
        </Card>

        {/* 风险分布 */}
        <Card>
          <CardHeader title="风险结构" icon="🎯" />
          <div style={{ flex: 1, display: 'flex', minHeight: 0, padding: 'var(--pad-sm) 0' }}>
            <div style={{ flex: 1 }}>{riskPie ? <ScreenChart option={riskPie} /> : <EmptyBox />}</div>
            <RiskLegend dist={data.risk_level_distribution || {}} labels={riskLabels} colors={T.riskColors} />
          </div>
        </Card>

        {/* 系统状态 */}
        <Card>
          <CardHeader title="运行态势" icon="⚙️" />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)', padding: 'var(--pad-sm) var(--pad)' }}>
            <StatusRow label="学校启用率" value={enabledRate} color={T.success} />
            <StatusRow label="测评完成率" value={completionRate} color={T.primary} />
            <StatusRow label="答卷有效率" value={effectiveRate} color={T.info} />
            <StatusRow label="风险处置率" value={riskDisposeRate} color={T.warning} />
            <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 'var(--gap-sm)', marginTop: 'auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap-sm)' }}>
                <MiniStat label="待处理" value={pendingRisks} color={T.danger} />
                <MiniStat label="已处置" value={Math.max(0, riskTotal - pendingRisks)} color={T.success} />
                <MiniStat label="AI调用" value={data.ai_call_total || 0} color="#9b59b6" />
                <MiniStat label="短信" value={data.sms_send_total || 0} color={T.info} />
              </div>
            </div>
          </div>
        </Card>

        {/* 质量分布 */}
        <Card>
          <CardHeader title="质量分布" icon="📋" />
          <div style={{ flex: 1, display: 'flex', minHeight: 0, padding: 'var(--pad-sm) 0' }}>
            <div style={{ flex: 1 }}>{qualityPie ? <ScreenChart option={qualityPie} /> : <EmptyBox />}</div>
            <RiskLegend dist={data.quality_distribution || {}} labels={{ normal: '正常', questionable: '存疑', mild_anomaly: '轻度', moderate_anomaly: '中度', severe_anomaly: '高度' }} colors={{ normal: T.success, questionable: T.warning, mild_anomaly: T.warning, moderate_anomaly: T.danger, severe_anomaly: '#ff4757' }} />
          </div>
        </Card>
      </div>

      {/* 底部4栏 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--gap)', height: 'calc(var(--kpi-h) * 3.5)', flexShrink: 0 }}>
        {/* 完成率排名 */}
        <Card>
          <CardHeader title="完成率排名" icon="🏆" extra={<span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>TOP {completionRankings.length}</span>} />
          <div style={{ flex: 1, minHeight: 0, padding: '0 var(--gap-sm)' }}>
            {makeBar(completionRankings, T.primary) ? <ScreenChart option={makeBar(completionRankings, T.primary)!} /> : <EmptyBox />}
          </div>
        </Card>

        {/* 风险排名 */}
        <Card>
          <CardHeader title="风险排名" icon="⚠️" extra={<span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>TOP {riskRankings.length}</span>} />
          <div style={{ flex: 1, minHeight: 0, padding: '0 var(--gap-sm)' }}>
            {makeBar(riskRankings, T.danger) ? <ScreenChart option={makeBar(riskRankings, T.danger)!} /> : <EmptyBox />}
          </div>
        </Card>

        {/* 最近预警 */}
        <Card>
          <CardHeader title="最近预警" icon="🔔" extra={<Tag color={T.danger}>{recentAlerts.length}</Tag>} />
          <div style={{ flex: 1, overflow: 'hidden', padding: 'var(--gap-sm) var(--pad)' }}>
            {recentAlerts.length > 0 ? recentAlerts.map((a: any, i: number) => (
              <ListItem key={i} index={i}>
                <Tag color={T.riskColors[a.risk_level as keyof typeof T.riskColors] || T.textMuted}>{riskLabels[a.risk_level] || a.risk_level}</Tag>
                <span style={{ fontSize: 'var(--fs-body)', color: T.text, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.school_name || '-'}</span>
                <span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted, fontFamily: T.fontMono }}>{a.created_at ? new Date(a.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}</span>
              </ListItem>
            )) : <EmptyBox text="暂无预警" />}
          </div>
        </Card>

        {/* 活跃学校 */}
        <Card>
          <CardHeader title="活跃学校" icon="🏫" extra={<span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>RECENT</span>} />
          <div style={{ flex: 1, overflow: 'hidden', padding: 'var(--gap-sm) var(--pad)' }}>
            {activeSchools.length > 0 ? activeSchools.map((s: any, i: number) => (
              <ListItem key={i} index={i}>
                <span style={{ fontSize: 'var(--fs-body)', color: T.text, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</span>
                <Tag color={s.status ? T.success : T.textMuted}>{s.status ? '启用' : '停用'}</Tag>
                <span style={{ fontSize: 'var(--fs-tiny)', color: T.textMuted }}>{s.student_count || 0}生</span>
              </ListItem>
            )) : <EmptyBox text="暂无活跃记录" />}
          </div>
        </Card>
      </div>
    </ScreenShell>
  );
}
