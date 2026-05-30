import { theme } from './screenTheme';

interface Props {
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  glow?: string;
}

export default function ScreenCard({ title, children, style, bodyStyle, glow }: Props) {
  const borderColor = glow || theme.cyan;
  return (
    <div style={{
      background: theme.cardBg,
      border: `1px solid ${theme.border}`,
      boxShadow: `inset 0 0 24px rgba(0,184,240,0.04), 0 8px 24px rgba(0,0,0,0.2)`,
      borderRadius: theme.radius,
      padding: 'clamp(10px, 0.78vw, 16px)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
      position: 'relative',
      ...style,
    }}>
      {/* Corner decorations */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: 20, height: 20, pointerEvents: 'none' }}>
        <path d="M0 12 L0 0 L12 0" fill="none" stroke={borderColor} strokeWidth="1.5" opacity="0.6" />
      </svg>
      <svg style={{ position: 'absolute', top: 0, right: 0, width: 20, height: 20, pointerEvents: 'none' }}>
        <path d="M8 0 L20 0 L20 12" fill="none" stroke={borderColor} strokeWidth="1.5" opacity="0.6" />
      </svg>
      <svg style={{ position: 'absolute', bottom: 0, left: 0, width: 20, height: 20, pointerEvents: 'none' }}>
        <path d="M0 8 L0 20 L12 20" fill="none" stroke={borderColor} strokeWidth="1.5" opacity="0.6" />
      </svg>
      <svg style={{ position: 'absolute', bottom: 0, right: 0, width: 20, height: 20, pointerEvents: 'none' }}>
        <path d="M8 20 L20 20 L20 8" fill="none" stroke={borderColor} strokeWidth="1.5" opacity="0.6" />
      </svg>

      {title && (
        <div style={{
          color: theme.cyan,
          fontSize: 'clamp(12px, 0.73vw, 14px)',
          fontWeight: 600,
          marginBottom: 8,
          letterSpacing: 0.5,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{
            width: 3,
            height: 14,
            borderRadius: 2,
            background: `linear-gradient(180deg, ${theme.cyan}, ${theme.blue})`,
            boxShadow: `0 0 8px ${theme.cyan}66`,
            flexShrink: 0,
          }} />
          {title}
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', ...bodyStyle }}>
        {children}
      </div>
    </div>
  );
}
