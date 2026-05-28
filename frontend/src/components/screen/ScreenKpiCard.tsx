import { theme, fmtNumber } from './screenTheme';

interface Props {
  label: string;
  value: number;
  unit?: string;
  color?: string;
}

export default function ScreenKpiCard({ label, value, unit, color = theme.cyan }: Props) {
  return (
    <div style={{ height: '100%', minHeight: 70, textAlign: 'center', padding: '6px 4px', overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ fontFamily: theme.numberFont, fontSize: 'clamp(20px, 1.85vw, 36px)', fontWeight: 800, color: '#eef8ff', lineHeight: 1.05, letterSpacing: -0.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {fmtNumber(value)}{unit && <span style={{ fontSize: '0.42em', color, marginLeft: 3 }}>{unit}</span>}
      </div>
      <div style={{ color: theme.textDim, fontSize: 'clamp(11px, 0.68vw, 13px)', marginTop: 7, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
      <div style={{ height: 2, width: 28, background: color, margin: '7px auto 0', borderRadius: 1, opacity: 0.75, boxShadow: `0 0 10px ${color}` }} />
    </div>
  );
}
