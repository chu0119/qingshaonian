/**
 * KpiCard - 数据指标卡片
 * 玻璃拟态风格，支持图标、数值、趋势
 */
import { useEffect, useRef, useState } from 'react';
import { screenTheme as T } from './theme';

interface KpiCardProps {
  label: string;
  value: number | string;
  suffix?: string;
  icon: React.ReactNode;
  color?: string;
  trend?: { value: number; isUp: boolean };
}

export default function KpiCard({ label, value, suffix, icon, color = T.primary, trend }: KpiCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const targetValue = typeof value === 'number' ? value : parseInt(value) || 0;
  const animRef = useRef<number>();

  useEffect(() => {
    if (typeof value !== 'number') {
      setDisplayValue(0);
      return;
    }
    const start = displayValue;
    const diff = targetValue - start;
    const duration = 1500;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(start + diff * eased));
      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [targetValue]);

  const displayText = typeof value === 'number' ? displayValue.toLocaleString() : value;

  return (
    <div style={{
      background: T.bgCard,
      border: `1px solid ${T.border}`,
      borderRadius: 12,
      padding: '16px 20px',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      backdropFilter: 'blur(10px)',
      transition: 'all 0.3s ease',
      cursor: 'default',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.borderColor = T.borderLight;
      e.currentTarget.style.background = T.bgCardHover;
    }}
    onMouseLeave={e => {
      e.currentTarget.style.borderColor = T.border;
      e.currentTarget.style.background = T.bgCard;
    }}
    >
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: `linear-gradient(135deg, ${color}20, ${color}10)`,
        border: `1px solid ${color}30`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color, fontSize: 22, flexShrink: 0,
      }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: T.textSecondary, marginBottom: 4 }}>{label}</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
          <span style={{
            fontSize: 28, fontWeight: 700, color: T.textHighlight,
            fontFamily: T.fontMono, lineHeight: 1,
          }}>
            {displayText}
          </span>
          {suffix && <span style={{ fontSize: 14, color: T.textSecondary }}>{suffix}</span>}
        </div>
        {trend && (
          <div style={{ fontSize: 11, color: trend.isUp ? T.success : T.danger, marginTop: 4 }}>
            {trend.isUp ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
    </div>
  );
}
