import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloseOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import client from '../../api/client';

// ======================= 科技风样式常量 =======================
const S = {
  cyan: '#00d4ff',
  blue: '#4096ff',
  gold: '#ffd666',
  green: '#00ff88',
  red: '#ff4d4f',
  orange: '#ff9c6e',
  purple: '#b37feb',
  bg: '#010b1a',
  cardBg: 'rgba(6,30,60,0.65)',
  borderGlow: 'rgba(0,212,255,0.25)',
  numberFont: "'DIN Alternate','Orbitron','Consolas','Microsoft YaHei',sans-serif",
};

// ======================= 发光卡片 =======================
function GlowCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  const corner = (position: React.CSSProperties) => (
    <span style={{ position: 'absolute', background: S.cyan, boxShadow: `0 0 6px ${S.cyan}`, ...position }} />
  );
  return (
    <div style={{ position: 'relative', background: S.cardBg, border: `1px solid ${S.borderGlow}`, borderRadius: 4, padding: '20px 22px', backdropFilter: 'blur(4px)', boxShadow: `inset 0 0 30px rgba(0,212,255,0.03), 0 0 15px rgba(0,212,255,0.06)`, overflow: 'hidden', display: 'flex', flexDirection: 'column', ...style }}>
      {corner({ top: 0, left: 0, width: 12, height: 2 })}
      {corner({ top: 0, left: 0, width: 2, height: 12 })}
      {corner({ top: 0, right: 0, width: 12, height: 2 })}
      {corner({ top: 0, right: 0, width: 2, height: 12 })}
      {corner({ bottom: 0, left: 0, width: 12, height: 2 })}
      {corner({ bottom: 0, left: 0, width: 2, height: 12 })}
      {corner({ bottom: 0, right: 0, width: 12, height: 2 })}
      {corner({ bottom: 0, right: 0, width: 2, height: 12 })}
      {children}
    </div>
  );
}

// ======================= 统计卡片 =======================
function StatItem({ icon, label, value, unit, color }: { icon: string; label: string; value: number; unit?: string; color: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '12px 8px', flex: 1 }}>
      <div style={{ width: 50, height: 50, borderRadius: '50%', margin: '0 auto 12px', background: `radial-gradient(circle, ${color}22, transparent)`, border: `1px solid ${color}33`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 20px ${color}11, inset 0 0 10px ${color}08` }}>
        <span style={{ fontSize: 24 }}>{icon}</span>
      </div>
      <div style={{ fontFamily: S.numberFont, fontSize: 32, fontWeight: 700, color: '#e8f4ff', lineHeight: 1.1 }}>{value.toLocaleString()}</div>
      {unit && <div style={{ color: S.cyan, fontFamily: S.numberFont, fontSize: 14, marginTop: 2 }}>{unit}</div>}
      <div style={{ color: '#5a8ab5', fontSize: 12, marginTop: 6 }}>{label}</div>
    </div>
  );
}

// ======================= 深色 ECharts 公共样式 =======================
const darkTooltip = { backgroundColor: 'rgba(6,30,60,0.92)', borderColor: 'rgba(0,212,255,0.35)', textStyle: { color: '#e8f4ff', fontSize: 13 } };
const darkTextColor = '#aac8e8';

function makeBarOption(data: any[], bars: { name: string; key: string; color: string }[], xKey = 'name') {
  return {
    tooltip: darkTooltip,
    legend: { textStyle: { color: darkTextColor, fontSize: 12 }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 45, containLabel: true },
    xAxis: { type: 'category', data: data.map((d: any) => d[xKey] || ''), axisLine: { lineStyle: { color: '#2a4a6a' } }, axisLabel: { color: darkTextColor, fontSize: 11, rotate: data.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(0,212,255,0.08)' } }, axisLabel: { color: darkTextColor } },
    series: bars.map(b => ({ name: b.name, type: 'bar', data: data.map((d: any) => d[b.key] || 0), itemStyle: { color: b.color, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 })),
  };
}

// ======================= 数码管时钟 =======================
function DigitalClock({ time }: { time: Date }) {
  const fmt = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: S.numberFont, fontSize: 28, fontWeight: 700, color: S.cyan, letterSpacing: 4, textShadow: `0 0 12px ${S.cyan}66, 0 0 30px ${S.cyan}22` }}>
      <span>{fmt(time.getHours())}</span>
      <span style={{ animation: 'blink 2s linear infinite' }}>:</span>
      <span>{fmt(time.getMinutes())}</span>
      <span style={{ animation: 'blink 2s linear infinite' }}>:</span>
      <span>{fmt(time.getSeconds())}</span>
    </div>
  );
}

// ======================= 主页面 =======================
export default function PlatformScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>({});
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const fetchData = () => client.get('/platform/dashboard').then(r => setData(r.data.data || {})).catch(() => {});
    fetchData();
    const t1 = setInterval(fetchData, 30000);
    const t2 = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);

  const today = `${time.getFullYear()}-${String(time.getMonth() + 1).padStart(2, '0')}-${String(time.getDate()).padStart(2, '0')}`;
  const weekDay = ['日', '一', '二', '三', '四', '五', '六'][time.getDay()];

  const stats = [
    { icon: '🏫', label: '学校总数', value: data.school_total || 0, unit: '所', color: S.cyan },
    { icon: '👥', label: '学生总数', value: data.student_total || 0, unit: '人', color: S.blue },
    { icon: '👨‍🏫', label: '教师总数', value: data.teacher_total || 0, unit: '人', color: S.gold },
    { icon: '📋', label: '问卷任务', value: data.task_total || 0, unit: '个', color: S.green },
    { icon: '📝', label: '答卷总数', value: data.answer_sheet_total || 0, unit: '份', color: S.purple },
    { icon: '⚠️', label: '风险提示', value: data.risk_alert_total || 0, unit: '条', color: S.orange },
    { icon: '🔔', label: '待处理', value: data.pending_risk_total || 0, unit: '条', color: S.red },
  ];

  const rankings = useMemo(() => data.completion_rankings || [], [data.completion_rankings]);
  const riskRankings = useMemo(() => data.risk_rankings || [], [data.risk_rankings]);

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: S.bg, color: '#e8f4ff', overflow: 'auto' }}>
      <style>{`
        @keyframes twinkle { 0%,100%{opacity:0.15} 50%{opacity:0.6} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
        @media (max-width: 768px) { .ps-stat-row { grid-template-columns: repeat(4, 1fr) !important; } .ps-chart-row { grid-template-columns: 1fr !important; } }
        @media (max-width: 480px) { .ps-stat-row { grid-template-columns: repeat(2, 1fr) !important; } }
      `}</style>

      {/* 星空粒子 */}
      {Array.from({ length: 60 }).map((_, i) => (
        <div key={i} style={{ position: 'absolute', borderRadius: '50%', background: '#fff', left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`, width: `${1 + Math.random() * 2}px`, height: `${1 + Math.random() * 2}px`, opacity: 0.1 + Math.random() * 0.3, animation: `twinkle ${3 + Math.random() * 6}s ease-in-out infinite`, animationDelay: `${Math.random() * 4}s` }} />
      ))}

      <div style={{ padding: '24px 32px' }}>
        {/* 顶部栏 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: 4 }}>青少年风险防范测评管理平台</div>
            <div style={{ color: '#5a8ab5', marginTop: 6, fontSize: 14 }}>
              {today} 星期{weekDay} &nbsp;|&nbsp; 全平台学校使用情况与风险监测概览
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <DigitalClock time={time} />
            <CloseOutlined onClick={() => navigate('/platform/dashboard')} style={{ fontSize: 20, cursor: 'pointer', color: '#5a8ab5' }} />
          </div>
        </div>

        {/* 统计卡片行 */}
        <div className="ps-stat-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 14, marginBottom: 20 }}>
          {stats.map((s, i) => (
            <GlowCard key={i}><StatItem {...s} /></GlowCard>
          ))}
        </div>

        {/* 图表行 */}
        <div className="ps-chart-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <GlowCard style={{ minHeight: 360 }}>
            <h3 style={{ color: S.cyan, fontSize: 15, marginBottom: 12, fontWeight: 600 }}>学校完成率排名</h3>
            {rankings.length > 0 ? (
              <ReactECharts style={{ flex: 1, minHeight: 300 }} option={makeBarOption(
                rankings,
                [{ name: '完成率(%)', key: 'completion_rate', color: S.cyan }],
              )} />
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#5a8ab5' }}>暂无数据</div>
            )}
          </GlowCard>

          <GlowCard style={{ minHeight: 360 }}>
            <h3 style={{ color: S.cyan, fontSize: 15, marginBottom: 12, fontWeight: 600 }}>学校风险提示排名</h3>
            {riskRankings.length > 0 ? (
              <ReactECharts style={{ flex: 1, minHeight: 300 }} option={makeBarOption(
                riskRankings,
                [
                  { name: '风险提示', key: 'risk_count', color: S.orange },
                  { name: '待处理', key: 'pending_risk_count', color: S.red },
                ],
              )} />
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#5a8ab5' }}>暂无数据</div>
            )}
          </GlowCard>
        </div>
      </div>
    </div>
  );
}
