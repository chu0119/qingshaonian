import { theme, fmtNumber } from './screenTheme';

interface Props {
  label: string;
  value: number;
  unit?: string;
  color?: string;
}

export default function ScreenKpiCard({ label, value, unit, color = theme.cyan }: Props) {
  const fs = Math.min(32, Math.max(18, 32 - String(value).length * 2));
  return (
    <div style={{
      textAlign: 'center', padding: '6px 4px',
      overflow: 'hidden',
    }}>
      <div style={{
        fontFamily: theme.numberFont, fontSize: fs, fontWeight: 700, color: '#e8f0fa',
        lineHeight: 1.2, letterSpacing: -0.5,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {fmtNumber(value)}
      </div>
      {unit && <span style={{ fontFamily: theme.numberFont, fontSize: Math.max(fs * 0.42, 10), color: theme.cyan, marginLeft: 2 }}>{unit}</span>}
      <div style={{
        color: theme.textDim, fontSize: 11, marginTop: 4,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>{label}</div>
      <div style={{ height: 2, width: 20, background: color, margin: '6px auto 0', borderRadius: 1, opacity: 0.6 }} />
    </div>
  );
}
