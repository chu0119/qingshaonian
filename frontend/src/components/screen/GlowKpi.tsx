import React from 'react';
import { useCountUp, fmtNumber } from './hooks/useCountUp';

interface GlowKpiProps {
  label: string;
  value: number;
  suffix?: string;
  color?: string;
  pulse?: boolean;
  icon?: string;
  style?: React.CSSProperties;
}

/**
 * 科幻 KPI 数字卡片 — 深空背景 + 流光边框 + 数字跳动 + 底部光条
 */
export default function GlowKpi({
  label,
  value,
  suffix = '',
  color = '#00d4ff',
  pulse = false,
  icon,
  style,
}: GlowKpiProps) {
  const displayValue = useCountUp(value, 1800, value % 1 !== 0 ? 1 : 0);

  return (
    <div
      style={{
        position: 'relative',
        background: 'linear-gradient(160deg, rgba(6,16,42,0.95) 0%, rgba(8,20,50,0.88) 100%)',
        border: `1px solid ${color}20`,
        borderRadius: 8,
        padding: '14px 16px 12px',
        overflow: 'hidden',
        animation: pulse ? 'alert-border 2s ease-in-out infinite' : undefined,
        ...style,
      }}
    >
      {/* 顶部渐变光晕 */}
      <div style={{
        position: 'absolute', top: 0, left: '10%', right: '10%', height: 1,
        background: `linear-gradient(90deg, transparent, ${color}60, transparent)`,
      }} />

      {/* 左上角指示灯 */}
      <div style={{
        position: 'absolute', top: 10, right: 10,
        width: 7, height: 7, borderRadius: '50%',
        background: `radial-gradient(circle, ${color} 30%, transparent 70%)`,
        boxShadow: `0 0 10px ${color}88, 0 0 20px ${color}44`,
        animation: pulse ? 'kpi-pulse 1.5s ease-in-out infinite' : 'none',
      }} />

      {/* 标签 */}
      <div style={{
        fontSize: 12, color: 'rgba(224,234,255,0.45)',
        marginBottom: 8, letterSpacing: 2, fontWeight: 500,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        {icon && <span style={{ fontSize: 14 }}>{icon}</span>}
        {label}
      </div>

      {/* 数字 */}
      <div style={{
        fontSize: 32, fontWeight: 800,
        fontFamily: "'Orbitron', 'DIN Alternate', monospace",
        color,
        textShadow: `0 0 28px ${color}55, 0 0 56px ${color}22`,
        lineHeight: 1.1,
        animation: 'num-flicker 6s ease-in-out infinite',
      }}>
        {fmtNumber(displayValue)}
        {suffix && (
          <span style={{ fontSize: 14, marginLeft: 4, opacity: 0.6, fontWeight: 500, fontFamily: 'sans-serif' }}>
            {suffix}
          </span>
        )}
      </div>

      {/* 底部光条 */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        opacity: 0.6,
        animation: 'kpi-bar-glow 3s ease-in-out infinite',
      }} />

      {/* 角装饰 */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: 16, height: 16, pointerEvents: 'none' }}>
        <path d="M0 0 L16 0 L16 2 L2 2 L2 16 L0 16 Z" fill={color} opacity={0.4} />
      </svg>
      <svg style={{ position: 'absolute', bottom: 0, right: 0, width: 16, height: 16, pointerEvents: 'none' }}>
        <path d="M14 0 L16 0 L16 16 L0 16 L0 14 L14 14 Z" fill={color} opacity={0.4} />
      </svg>
    </div>
  );
}
