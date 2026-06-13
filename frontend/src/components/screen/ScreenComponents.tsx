/**
 * ScreenComponents - 响应式大屏组件库
 */
import { screenTheme as T } from './theme';

export function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ background: T.bgCard, border: `1px solid ${T.border}`, borderRadius: 'var(--radius)', display: 'flex', flexDirection: 'column', overflow: 'hidden', ...style }}>{children}</div>;
}

export function CardHeader({ title, icon, extra }: { title: string; icon: string; extra?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--pad-sm) var(--pad)', borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
        <span style={{ fontSize: 'var(--fs-card-title)' }}>{icon}</span>
        <span style={{ fontSize: 'var(--fs-card-title)', fontWeight: 700, color: T.textHighlight }}>{title}</span>
      </div>
      {extra}
    </div>
  );
}

export function KpiBig({ label, value, suffix, icon, color }: { label: string; value: number | string; suffix?: string; icon: string; color: string }) {
  return (
    <div style={{ background: T.bgCard, border: `1px solid ${T.border}`, borderRadius: 'var(--radius)', padding: 'var(--pad-sm) var(--pad)', display: 'flex', alignItems: 'center', gap: 'var(--gap)', height: 'var(--kpi-h)' }}>
      <span style={{ fontSize: 'var(--icon-lg)' }}>{icon}</span>
      <div>
        <div style={{ fontSize: 'var(--fs-kpi-label)', color: T.textSecondary }}>{label}</div>
        <div style={{ fontSize: 'var(--fs-kpi)', fontWeight: 800, color: T.textHighlight, fontFamily: T.fontMono, lineHeight: 1.2 }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
          {suffix && <span style={{ fontSize: 'var(--fs-body)', color: T.textSecondary }}>{suffix}</span>}
        </div>
      </div>
    </div>
  );
}

export function StatusRow({ label, value, color }: { label: string; value: number; color: string }) {
  const displayValue = value < 0 ? '--' : `${value}%`;
  const barWidth = value < 0 ? 0 : Math.min(value, 100);
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--gap-sm)' }}>
        <span style={{ fontSize: 'var(--fs-body)', color: T.textSecondary }}>{label}</span>
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 700, color: T.textHighlight, fontFamily: T.fontMono }}>{displayValue}</span>
      </div>
      <div style={{ height: 'var(--bar-h)', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--bar-h)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${barWidth}%`, background: `linear-gradient(90deg, ${color}60, ${color})`, borderRadius: 'var(--bar-h)' }} />
      </div>
    </div>
  );
}

export function MiniStat({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.03)', border: `1px solid ${T.border}`, borderRadius: 'var(--radius)', padding: 'var(--gap-sm) var(--pad-sm)' }}>
      <div style={{ fontSize: 'var(--fs-small)', color: T.textMuted }}>{label}</div>
      <div style={{ fontSize: 'var(--fs-kpi)', fontWeight: 700, color, fontFamily: T.fontMono }}>{value}</div>
    </div>
  );
}

export function EmptyBox({ text = '暂无数据' }: { text?: string }) {
  return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: T.textMuted, fontSize: 'var(--fs-body)' }}>{text}</span></div>;
}

export function RiskLegend({ dist, labels, colors }: { dist: Record<string, number>; labels: Record<string, string>; colors: Record<string, string> }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 'var(--gap)', paddingRight: 'var(--pad)', minWidth: 'var(--pad) * 5' }}>
      {Object.entries(labels).map(([k, label]) => (
        <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
          <span style={{ width: 'var(--fs-small)', height: 'var(--fs-small)', borderRadius: '50%', background: colors[k] || T.textMuted, flexShrink: 0 }} />
          <span style={{ fontSize: 'var(--fs-body)', color: T.textSecondary, flex: 1 }}>{label}</span>
          <span style={{ fontSize: 'var(--fs-kpi-label)', fontWeight: 700, color: T.textHighlight, fontFamily: T.fontMono }}>{dist[k] || 0}</span>
        </div>
      ))}
    </div>
  );
}

/** 列表项组件 */
export function ListItem({ children, index }: { children: React.ReactNode; index: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)', padding: 'var(--gap-sm) 0', borderBottom: `1px solid ${T.border}` }}>
      <span style={{ width: 'var(--fs-body)', height: 'var(--fs-body)', borderRadius: '50%', background: index < 3 ? T.primary : 'rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 'var(--fs-tiny)', fontWeight: 700, color: index < 3 ? '#fff' : T.textMuted, flexShrink: 0 }}>
        {index + 1}
      </span>
      {children}
    </div>
  );
}

/** 标签组件 */
export function Tag({ color, children }: { color: string; children: React.ReactNode }) {
  return <span style={{ padding: '2px 8px', borderRadius: 'var(--gap-sm)', fontSize: 'var(--fs-tiny)', fontWeight: 600, background: `${color}20`, color, whiteSpace: 'nowrap' }}>{children}</span>;
}
