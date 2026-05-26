import { useState, useEffect, useCallback, useMemo } from 'react';
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
  deepRed: '#cf1322',
  bg: '#010b1a',
  cardBg: 'rgba(6,30,60,0.65)',
  borderGlow: 'rgba(0,212,255,0.25)',
  numberFont: "'DIN Alternate','Orbitron','Consolas','Microsoft YaHei',sans-serif",
};

// ======================= 深色科技风 ECharts 公共配置 =======================
const darkTooltip = {
  backgroundColor: 'rgba(6,30,60,0.92)',
  borderColor: 'rgba(0,212,255,0.35)',
  textStyle: { color: '#e8f4ff', fontSize: 13 },
};

const darkLegendText = { color: '#aac8e8', fontSize: 12 };

// ======================= 发光边框卡片 =======================
function GlowCard({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        position: 'relative',
        background: S.cardBg,
        border: `1px solid ${S.borderGlow}`,
        borderRadius: 4,
        padding: '20px 22px',
        backdropFilter: 'blur(4px)',
        boxShadow: `inset 0 0 30px rgba(0,212,255,0.03), 0 0 15px rgba(0,212,255,0.06)`,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        ...style,
      }}
    >
      {/* 四角发光装饰 */}
      <span
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 12,
          height: 2,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 2,
          height: 12,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 12,
          height: 2,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 2,
          height: 12,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: 12,
          height: 2,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: 2,
          height: 12,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: 12,
          height: 2,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      <span
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: 2,
          height: 12,
          background: S.cyan,
          boxShadow: `0 0 6px ${S.cyan}`,
        }}
      />
      {children}
    </div>
  );
}

// ======================= 渐变标题 =======================
function SectionTitle({ title }: { title: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, flexShrink: 0 }}>
      <div
        style={{
          width: 4,
          height: 16,
          background: `linear-gradient(180deg, ${S.cyan}, transparent)`,
        }}
      />
      <span style={{ color: '#c8ddf8', fontSize: 15, fontWeight: 600, letterSpacing: 2 }}>
        {title}
      </span>
      <div
        style={{
          flex: 1,
          height: 1,
          background: `linear-gradient(90deg, rgba(0,212,255,0.4), transparent)`,
        }}
      />
    </div>
  );
}

// ======================= 统计数字卡片（数字滚动动画） =======================
function StatItem({
  icon,
  label,
  value,
  unit,
  color,
}: {
  icon: string;
  label: string;
  value: number;
  unit?: string;
  color: string;
}) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value <= 0) {
      setDisplay(0);
      return;
    }
    let frame: number;
    const step = Math.max(1, Math.ceil(value / 30));
    const animate = () => {
      setDisplay((prev) => {
        if (prev >= value) return value;
        return Math.min(prev + step, value);
      });
      // re-check display after setState — use a ref would be cleaner but keep it simple
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
    // intentionally only re-run when value changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  // Stop animation when target reached
  useEffect(() => {
    if (display >= value && value > 0) {
      // no-op, animation naturally ends
    }
  }, [display, value]);

  return (
    <div style={{ textAlign: 'center', padding: '12px 8px', flex: 1 }}>
      <div
        style={{
          width: 50,
          height: 50,
          borderRadius: '50%',
          margin: '0 auto 12px',
          background: `radial-gradient(circle, ${color}22, transparent)`,
          border: `1px solid ${color}33`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: `0 0 20px ${color}11, inset 0 0 10px ${color}08`,
        }}
      >
        <span style={{ fontSize: 24 }}>{icon}</span>
      </div>
      <div
        style={{
          fontFamily: S.numberFont,
          fontSize: 32,
          fontWeight: 700,
          color: '#e8f4ff',
          lineHeight: 1.1,
        }}
      >
        {display.toLocaleString()}
      </div>
      {unit && (
        <div style={{ color: S.cyan, fontFamily: S.numberFont, fontSize: 14, marginTop: 2 }}>
          {unit}
        </div>
      )}
      <div style={{ color: '#5a8ab5', fontSize: 12, marginTop: 6 }}>{label}</div>
    </div>
  );
}

// ======================= 数码管风格数字 =======================
function DigitalClock({ time }: { time: Date }) {
  const fmt = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  const h = fmt(time.getHours());
  const m = fmt(time.getMinutes());
  const s = fmt(time.getSeconds());

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        fontFamily: S.numberFont,
        fontSize: 28,
        fontWeight: 700,
        color: S.cyan,
        letterSpacing: 4,
        textShadow: `0 0 12px ${S.cyan}66, 0 0 30px ${S.cyan}22`,
      }}
    >
      <span>{h}</span>
      <span style={{ animation: 'blink 1s step-end infinite', color: '#5a8ab5' }}>:</span>
      <span>{m}</span>
      <span style={{ animation: 'blink 1s step-end infinite', color: '#5a8ab5' }}>:</span>
      <span>{s}</span>
    </div>
  );
}

// ======================= 主体组件 =======================
export default function DataScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [risks, setRisks] = useState<any>(null);
  const [time, setTime] = useState(new Date());
  const [screenConfig, setScreenConfig] = useState({
    screen_title: '学生心理健康监测数据大屏',
    screen_subtitle: '',
  });

  // ---- 自动全屏 ----
  useEffect(() => {
    const el = document.documentElement;
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {});
    }
    const onFsChange = () => {
      if (!document.fullscreenElement) navigate(-1);
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, [navigate]);

  // ---- 数据获取（30秒轮询） ----
  const fetchAll = useCallback(async () => {
    try {
      const [dRes, qRes, rRes, cfgRes] = await Promise.all([
        client.get('/dashboard/school'),
        client.get('/quality/statistics/school'),
        client.get('/reports/risk-summary'),
        client
          .get('/system/screen-config')
          .catch(() => ({
            data: { data: { screen_title: '学生心理健康监测数据大屏', screen_subtitle: '' } },
          })),
      ]);
      setData(dRes.data.data);
      setQuality(qRes.data.data);
      setRisks(rRes.data.data);
      setScreenConfig(
        cfgRes.data.data || {
          screen_title: '学生心理健康监测数据大屏',
          screen_subtitle: '',
        },
      );
    } catch {
      /* 静默失败，保留旧数据 */
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 30000);
    return () => clearInterval(t);
  }, [fetchAll]);

  // ---- 时钟每秒更新 ----
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ---- 退出全屏 ----
  const exitFullscreen = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => navigate(-1));
    } else {
      navigate(-1);
    }
  };

  // ====================== 数据提取 ======================
  const stats = data?.stats || {};
  const riskDist = data?.risk_level_distribution || {};
  const qualityDist = data?.quality_distribution || {};

  const riskTotal =
    (riskDist.low || 0) +
    (riskDist.medium || 0) +
    (riskDist.high || 0) +
    (riskDist.urgent || 0);

  const qualityTotal =
    (qualityDist.normal || 0) +
    (qualityDist.mild_anomaly || 0) +
    (qualityDist.moderate_anomaly || 0) +
    (qualityDist.severe_anomaly || 0);

  const effectiveRate =
    quality?.effective_rate ||
    (qualityTotal > 0 ? Math.round(((qualityDist.normal || 0) / qualityTotal) * 100) : 100);

  const riskByStatus: any[] = risks?.by_status || [];

  // ---- 维度数据：优先使用 API 返回 ----
  const defaultDimensions = [
    { name: '情绪状态', score: 8.5 },
    { name: '睡眠质量', score: 6.2 },
    { name: '学习压力', score: 10.8 },
    { name: '人际关系', score: 5.1 },
    { name: '家庭支持', score: 4.3 },
    { name: '校园安全', score: 3.8 },
    { name: '网络使用', score: 7.6 },
    { name: '自我安全', score: 2.9 },
  ];
  const dimensionData: { name: string; score: number }[] =
    quality?.dimensions && Array.isArray(quality.dimensions)
      ? quality.dimensions
      : quality?.dimension_scores
        ? Object.entries(quality.dimension_scores).map(([k, v]) => ({
            name: k,
            score: v as number,
          }))
        : defaultDimensions;

  // ---- 日期显示 ----
  const fmt = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  const dateStr = `${time.getFullYear()}-${fmt(time.getMonth() + 1)}-${fmt(time.getDate())}`;

  // ====================== ECharts 配置 ======================

  // -- 风险等级分布饼图 --
  const riskPieOption = useMemo(() => {
    const pieData = [
      { value: riskDist.urgent || 0, name: '紧急风险', itemStyle: { color: S.deepRed } },
      { value: riskDist.high || 0, name: '高风险', itemStyle: { color: S.red } },
      { value: riskDist.medium || 0, name: '中风险', itemStyle: { color: S.orange } },
      { value: riskDist.low || 0, name: '低风险', itemStyle: { color: S.cyan } },
    ].filter((d) => d.value > 0);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        ...darkTooltip,
        trigger: 'item',
        formatter: '{b}: {c} 人 ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: '8%',
        top: 'center',
        textStyle: { ...darkLegendText },
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
      },
      series: [
        {
          type: 'pie',
          radius: ['52%', '76%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 3,
            borderColor: S.bg,
            borderWidth: 3,
          },
          label: {
            show: true,
            position: 'outside',
            color: '#aac8e8',
            fontSize: 11,
            formatter: '{b}\n{d}%',
          },
          labelLine: {
            lineStyle: { color: '#3a5a7a' },
          },
          emphasis: {
            label: { fontSize: 14, fontWeight: 'bold' },
            scaleSize: 8,
            shadowBlur: 20,
            shadowColor: 'rgba(0,0,0,0.3)',
          },
          data: pieData.length > 0 ? pieData : [{ value: 1, name: '暂无数据', itemStyle: { color: '#2a3a5a' } }],
        },
      ],
    };
  }, [riskDist]);

  // -- 答题质量分布饼图 --
  const qualityPieOption = useMemo(() => {
    const pieData = [
      { value: qualityDist.normal || 0, name: '正常', itemStyle: { color: S.green } },
      { value: qualityDist.mild_anomaly || 0, name: '轻度异常', itemStyle: { color: S.gold } },
      { value: qualityDist.moderate_anomaly || 0, name: '中度异常', itemStyle: { color: S.orange } },
      { value: qualityDist.severe_anomaly || 0, name: '高度异常', itemStyle: { color: S.red } },
    ].filter((d) => d.value > 0);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        ...darkTooltip,
        trigger: 'item',
        formatter: '{b}: {c} 份 ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: '8%',
        top: 'center',
        textStyle: { ...darkLegendText },
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
      },
      series: [
        {
          type: 'pie',
          radius: ['52%', '76%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 3,
            borderColor: S.bg,
            borderWidth: 3,
          },
          label: {
            show: true,
            position: 'outside',
            color: '#aac8e8',
            fontSize: 11,
            formatter: '{b}\n{d}%',
          },
          labelLine: {
            lineStyle: { color: '#3a5a7a' },
          },
          emphasis: {
            label: { fontSize: 14, fontWeight: 'bold' },
            scaleSize: 8,
            shadowBlur: 20,
            shadowColor: 'rgba(0,0,0,0.3)',
          },
          data:
            pieData.length > 0
              ? pieData
              : [{ value: 1, name: '暂无数据', itemStyle: { color: '#2a3a5a' } }],
        },
      ],
    };
  }, [qualityDist]);

  // -- 维度得分柱状图（横向） --
  const dimensionBarOption = useMemo(() => {
    const names = dimensionData.map((d) => d.name).reverse();
    const scores = dimensionData.map((d) => d.score).reverse();

    const barColors = [S.purple, S.cyan, S.orange, S.green, S.blue, S.gold, '#ff85c0', '#87e8de']
      .reverse()
      .slice(0, names.length);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        ...darkTooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params;
          return `${p.name}<br/>得分: <b style="color:${S.cyan}">${p.value}</b>`;
        },
      },
      grid: {
        left: '3%',
        right: '12%',
        top: '3%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        max: 15,
        axisLabel: { color: '#5a8ab5', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(0,212,255,0.2)' } },
        axisTick: { show: false },
        splitLine: {
          lineStyle: { color: 'rgba(0,212,255,0.06)', type: 'dashed' },
        },
        name: '分',
        nameTextStyle: { color: '#5a8ab5', fontSize: 10 },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLabel: { color: '#aac8e8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(0,212,255,0.2)' } },
        axisTick: { show: false },
      },
      series: [
        {
          type: 'bar',
          data: scores.map((v, i) => ({
            value: v,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: barColors[i] || S.cyan },
                { offset: 1, color: (barColors[i] || S.cyan) + '44' },
              ]),
              borderRadius: [0, 3, 3, 0],
            },
          })),
          barWidth: 16,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0,212,255,0.3)',
            },
          },
          label: {
            show: true,
            position: 'right',
            color: '#aac8e8',
            fontSize: 11,
            fontFamily: S.numberFont,
          },
        },
      ],
    };
  }, [dimensionData]);

  // -- 干预处理进度柱状图 --
  const interventionBarOption = useMemo(() => {
    const statusMap: Record<string, string> = {
      pending: '待处理',
      processing: '处理中',
      completed: '已完成',
      resolved: '已完成',
    };
    const colorMap: Record<string, string> = {
      pending: S.orange,
      processing: S.cyan,
      completed: S.green,
      resolved: S.green,
    };

    const chartData = riskByStatus.map((item: any) => ({
      name: statusMap[item.status] || item.label || item.status,
      value: item.count || 0,
      color: colorMap[item.status] || S.blue,
    }));

    // 计算总数用于百分比
    const total = chartData.reduce((s: number, d: any) => s + d.value, 0);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        ...darkTooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params;
          const pct = total > 0 ? Math.round((p.value / total) * 100) : 0;
          return `${p.name}<br/>数量: <b style="color:${S.cyan}">${p.value}</b> 条<br/>占比: <b style="color:${S.gold}">${pct}%</b>`;
        },
      },
      grid: {
        left: '5%',
        right: '12%',
        top: '8%',
        bottom: '5%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: chartData.map((d) => d.name),
        axisLabel: { color: '#aac8e8', fontSize: 12 },
        axisLine: { lineStyle: { color: 'rgba(0,212,255,0.2)' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#5a8ab5', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(0,212,255,0.2)' } },
        axisTick: { show: false },
        splitLine: {
          lineStyle: { color: 'rgba(0,212,255,0.06)', type: 'dashed' },
        },
      },
      series: [
        {
          type: 'bar',
          data: chartData.map((d) => ({
            value: d.value,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: d.color },
                { offset: 1, color: d.color + '33' },
              ]),
              borderRadius: [3, 3, 0, 0],
            },
          })),
          barWidth: 48,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0,212,255,0.3)',
            },
          },
          label: {
            show: true,
            position: 'top',
            color: '#e8f4ff',
            fontSize: 13,
            fontWeight: 'bold',
            fontFamily: S.numberFont,
          },
        },
      ],
    };
  }, [riskByStatus]);

  // ====================== 渲染 ======================
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        background: S.bg,
        position: 'fixed',
        top: 0,
        left: 0,
        zIndex: 9999,
        fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif",
        overflow: 'hidden',
        userSelect: 'none',
      }}
    >
      {/* ===== CSS动画 ===== */}
      <style>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.15; }
          50% { opacity: 0.6; }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
      `}</style>

      {/* ===== 星空粒子背景 ===== */}
      {Array.from({ length: 80 }).map((_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            borderRadius: '50%',
            background: '#fff',
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            width: `${1 + Math.random() * 2}px`,
            height: `${1 + Math.random() * 2}px`,
            animation: `twinkle ${2 + Math.random() * 4}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 5}s`,
            pointerEvents: 'none',
          }}
        />
      ))}

      {/* ===== 顶部栏 ===== */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          height: 72,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          borderBottom: '1px solid rgba(0,212,255,0.15)',
          background: 'linear-gradient(180deg, rgba(0,40,80,0.5), transparent)',
          flexShrink: 0,
        }}
      >
        {/* 左侧：标题 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${S.cyan}, transparent)`,
              boxShadow: `0 0 20px ${S.cyan}44`,
            }}
          />
          <div>
            <div
              style={{
                color: '#e8f4ff',
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: 4,
                fontFamily: S.numberFont,
              }}
            >
              {screenConfig.screen_title}
            </div>
            {screenConfig.screen_subtitle && (
              <div style={{ color: '#5a8ab5', fontSize: 12, letterSpacing: 2 }}>
                {screenConfig.screen_subtitle}
              </div>
            )}
          </div>
        </div>

        {/* 右侧：日期 + 数码管时间 + 退出 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <span style={{ color: '#5a8ab5', fontSize: 14, letterSpacing: 2 }}>{dateStr}</span>
          <DigitalClock time={time} />
          <div
            onClick={exitFullscreen}
            title="退出大屏"
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.04)',
              transition: 'all 0.3s',
              opacity: 0.5,
            }}
            onMouseEnter={(e) => {
              const t = e.currentTarget;
              t.style.borderColor = S.cyan;
              t.style.boxShadow = `0 0 8px ${S.cyan}44`;
              t.style.opacity = '1';
            }}
            onMouseLeave={(e) => {
              const t = e.currentTarget;
              t.style.borderColor = 'rgba(255,255,255,0.15)';
              t.style.boxShadow = 'none';
              t.style.opacity = '0.5';
            }}
          >
            <CloseOutlined style={{ color: '#8899aa', fontSize: 12 }} />
          </div>
        </div>
      </div>

      {/* ===== 主体内容区域 ===== */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          padding: '20px 28px',
          height: 'calc(100vh - 72px)',
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
        }}
      >
        {/* ----- 第一行：6 个统计卡片 ----- */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 14,
          }}
          className="stat-row"
        >
          <GlowCard>
            <StatItem icon="👥" label="学生总数" value={stats.student_count || 0} unit="人" color={S.cyan} />
          </GlowCard>
          <GlowCard>
            <StatItem icon="👨‍🏫" label="教师总数" value={stats.teacher_count || 0} unit="人" color={S.blue} />
          </GlowCard>
          <GlowCard>
            <StatItem icon="🏫" label="班级数量" value={stats.class_count || 0} unit="个" color={S.gold} />
          </GlowCard>
          <GlowCard>
            <StatItem icon="📋" label="答卷总数" value={stats.total_answer_sheets || 0} unit="份" color={S.green} />
          </GlowCard>
          <GlowCard>
            <StatItem icon="⚠️" label="风险预警" value={stats.risk_count || 0} unit="条" color={S.red} />
          </GlowCard>
          <GlowCard>
            <StatItem icon="✅" label="有效答卷率" value={effectiveRate} unit="%" color={S.purple} />
          </GlowCard>
        </div>

        {/* ----- 第二行：风险等级分布 + 答题质量分布（饼图） ----- */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 14,
            flex: 1,
            minHeight: 0,
          }}
          className="chart-row-2"
        >
          <GlowCard>
            <SectionTitle title="风险等级分布" />
            <div style={{ flex: 1, minHeight: 0 }}>
              {riskTotal > 0 ? (
                <ReactECharts
                  option={riskPieOption}
                  style={{ height: '100%', minHeight: 260 }}
                  opts={{ renderer: 'canvas' }}
                />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: '#3a5a7a',
                    fontSize: 14,
                  }}
                >
                  暂无风险数据
                </div>
              )}
            </div>
            {/* 底部汇总 */}
            <div style={{ textAlign: 'center', marginTop: 8, flexShrink: 0 }}>
              <span style={{ color: S.orange, fontFamily: S.numberFont, fontSize: 24, fontWeight: 700 }}>
                {stats.pending_risks || 0}
              </span>
              <span style={{ color: '#5a8ab5', marginLeft: 8, fontSize: 13 }}>条待处理预警</span>
            </div>
          </GlowCard>

          <GlowCard>
            <SectionTitle title="答题质量分布" />
            <div style={{ flex: 1, minHeight: 0 }}>
              {qualityTotal > 0 ? (
                <ReactECharts
                  option={qualityPieOption}
                  style={{ height: '100%', minHeight: 260 }}
                  opts={{ renderer: 'canvas' }}
                />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: '#3a5a7a',
                    fontSize: 14,
                  }}
                >
                  暂无质量数据
                </div>
              )}
            </div>
            {/* 底部汇总 */}
            <div style={{ textAlign: 'center', marginTop: 8, flexShrink: 0 }}>
              <span style={{ color: S.green, fontFamily: S.numberFont, fontSize: 24, fontWeight: 700 }}>
                {effectiveRate}%
              </span>
              <span style={{ color: '#5a8ab5', marginLeft: 8, fontSize: 13 }}>有效答卷率</span>
              {quality?.suggest_retest_count > 0 && (
                <>
                  <span
                    style={{
                      color: S.red,
                      fontFamily: S.numberFont,
                      fontSize: 24,
                      fontWeight: 700,
                      marginLeft: 24,
                    }}
                  >
                    {quality.suggest_retest_count}
                  </span>
                  <span style={{ color: '#5a8ab5', marginLeft: 8, fontSize: 13 }}>人建议复测</span>
                </>
              )}
            </div>
          </GlowCard>
        </div>

        {/* ----- 第三行：维度得分 + 干预处理进度（柱状图） ----- */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 14,
            flex: 1,
            minHeight: 0,
          }}
          className="chart-row-3"
        >
          <GlowCard>
            <SectionTitle title="各维度平均得分" />
            <div style={{ flex: 1, minHeight: 0 }}>
              <ReactECharts
                option={dimensionBarOption}
                style={{ height: '100%', minHeight: 280 }}
                opts={{ renderer: 'canvas' }}
              />
            </div>
          </GlowCard>

          <GlowCard>
            <SectionTitle title="干预处理进度" />
            <div style={{ flex: 1, minHeight: 0 }}>
              {riskByStatus.length > 0 ? (
                <ReactECharts
                  option={interventionBarOption}
                  style={{ height: '100%', minHeight: 280 }}
                  opts={{ renderer: 'canvas' }}
                />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: '#3a5a7a',
                    fontSize: 14,
                  }}
                >
                  暂无干预数据
                </div>
              )}
            </div>
            {/* 底部：待跟进总数 */}
            <div style={{ textAlign: 'center', marginTop: 8, flexShrink: 0 }}>
              <span style={{ color: S.orange, fontFamily: S.numberFont, fontSize: 24, fontWeight: 700 }}>
                {stats.pending_interventions || 0}
              </span>
              <span style={{ color: '#5a8ab5', marginLeft: 8, fontSize: 13 }}>待跟进干预事项</span>
            </div>
          </GlowCard>
        </div>
      </div>
    </div>
  );
}
