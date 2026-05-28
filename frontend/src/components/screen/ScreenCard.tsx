import { theme } from './screenTheme';

interface Props {
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
}

export default function ScreenCard({ title, children, style, bodyStyle }: Props) {
  return (
    <div style={{
      background: theme.cardBg,
      border: `1px solid ${theme.border}`,
      boxShadow: 'inset 0 0 24px rgba(0,184,240,0.04), 0 12px 30px rgba(0,0,0,0.24)',
      borderRadius: theme.radius,
      padding: 'clamp(10px, 0.78vw, 16px)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
      ...style,
    }}>
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
        }}>
          {title}
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', ...bodyStyle }}>
        {children}
      </div>
    </div>
  );
}
