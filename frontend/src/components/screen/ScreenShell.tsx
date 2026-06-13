/**
 * ScreenShell - 响应式大屏外壳
 * 带返回按钮、自适应缩放
 */
import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { screenTheme as T } from './theme';

interface ScreenShellProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  backTo?: string;
}

export default function ScreenShell({ title, subtitle, children, backTo }: ScreenShellProps) {
  const navigate = useNavigate();
  const [s, setS] = useState(1);

  useEffect(() => {
    const fit = () => setS(Math.min(window.innerWidth / 1920, window.innerHeight / 1080));
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);

  const cssVars: Record<string, string> = useMemo(() => ({
    '--s': String(s),
    '--header-h': `${Math.max(Math.round(64 * s), 40)}px`,
    '--gap': `${Math.max(Math.round(10 * s), 5)}px`,
    '--gap-sm': `${Math.max(Math.round(6 * s), 3)}px`,
    '--radius': `${Math.max(Math.round(10 * s), 5)}px`,
    '--pad': `${Math.max(Math.round(20 * s), 6)}px`,
    '--pad-sm': `${Math.max(Math.round(12 * s), 4)}px`,
    '--fs-title': `${Math.max(Math.round(24 * s), 13)}px`,
    '--fs-subtitle': `${Math.max(Math.round(12 * s), 8)}px`,
    '--fs-card-title': `${Math.max(Math.round(14 * s), 10)}px`,
    '--fs-kpi': `${Math.max(Math.round(26 * s), 14)}px`,
    '--fs-kpi-label': `${Math.max(Math.round(12 * s), 8)}px`,
    '--fs-body': `${Math.max(Math.round(13 * s), 9)}px`,
    '--fs-small': `${Math.max(Math.round(11 * s), 7)}px`,
    '--fs-tiny': `${Math.max(Math.round(10 * s), 7)}px`,
    '--fs-time': `${Math.max(Math.round(22 * s), 12)}px`,
    '--icon-lg': `${Math.max(Math.round(24 * s), 14)}px`,
    '--bar-h': `${Math.max(Math.round(7 * s), 3)}px`,
    '--kpi-h': `${Math.max(Math.round(62 * s), 36)}px`,
  }), [s]);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: T.bgGradient, fontFamily: T.fontFamily, color: T.text, ...cssVars }}>
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', background: 'radial-gradient(ellipse 800px 600px at 20% 30%, rgba(64,158,255,0.06) 0%, transparent 70%), radial-gradient(ellipse 600px 400px at 80% 70%, rgba(103,194,58,0.04) 0%, transparent 70%)' }} />
      <div style={{ position: 'relative', zIndex: 1, width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* 标题栏 */}
        <div style={{ height: 'var(--header-h)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: `0 var(--pad)`, flexShrink: 0, borderBottom: `1px solid ${T.border}`, background: 'rgba(10,14,39,0.6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
            {backTo && (
              <button onClick={() => navigate(backTo)} style={{ background: 'rgba(255,255,255,0.06)', border: `1px solid ${T.border}`, borderRadius: 'var(--radius)', color: T.textSecondary, cursor: 'pointer', padding: '6px 14px', fontSize: 'var(--fs-small)', display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(64,158,255,0.15)'; e.currentTarget.style.color = T.textHighlight; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = T.textSecondary; }}
              >
                <span style={{ fontSize: 'var(--fs-body)' }}>←</span> 返回
              </button>
            )}
            <div style={{ width: 'var(--bar-h)', height: 'calc(var(--header-h) * 0.5)', borderRadius: 'var(--bar-h)', background: `linear-gradient(180deg, ${T.primary}, ${T.primaryLight})` }} />
            <div>
              <div style={{ fontSize: 'var(--fs-title)', fontWeight: 800, letterSpacing: 3, color: T.textHighlight }}>{title}</div>
              {subtitle && <div style={{ fontSize: 'var(--fs-subtitle)', color: T.textMuted, marginTop: 1, letterSpacing: 1 }}>{subtitle}</div>}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap)' }}>
            <TimeDisplay />
            <div style={{ padding: 'var(--gap-sm) var(--gap)', borderRadius: 20, background: 'rgba(64,158,255,0.1)', border: `1px solid ${T.border}`, fontSize: 'var(--fs-tiny)', color: T.primary }}>自动刷新 30s</div>
          </div>
        </div>
        <div style={{ flex: 1, padding: 'var(--gap-sm) var(--pad)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function TimeDisplay() {
  const [t, setT] = useState(new Date());
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i); }, []);
  const f = (n: number) => n.toString().padStart(2, '0');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: T.fontMono }}>
      <span style={{ fontSize: 'var(--fs-time)', fontWeight: 700, color: T.textHighlight }}>{f(t.getHours())}:{f(t.getMinutes())}:{f(t.getSeconds())}</span>
      <span style={{ fontSize: 'var(--fs-small)', color: T.textMuted }}>{t.getFullYear()}-{f(t.getMonth() + 1)}-{f(t.getDate())}</span>
    </div>
  );
}
