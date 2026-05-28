import { useState, useEffect } from 'react';
import { theme } from './screenTheme';

function useIsMobile() {
  const [m, setM] = useState(window.innerWidth < 768);
  useEffect(() => {
    const h = () => setM(window.innerWidth < 768);
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, []);
  return m;
}

interface Props {
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export default function ScreenCard({ title, children, style }: Props) {
  const isMobile = useIsMobile();
  return (
    <div style={{
      background: theme.cardBg,
      border: `1px solid ${theme.border}`,
      borderRadius: theme.radius,
      padding: isMobile ? '12px 10px' : '16px 18px',
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
      ...style,
    }}>
      {title && (
        <div style={{
          color: theme.cyan, fontSize: isMobile ? 13 : 14, fontWeight: 600,
          marginBottom: isMobile ? 8 : 12,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          flexShrink: 0,
        }}>
          {title}
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  );
}
