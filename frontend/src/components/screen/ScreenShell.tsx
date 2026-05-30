import { useEffect, useRef, useState } from 'react';
import { Button, Typography } from 'antd';
import { FullscreenOutlined, FullscreenExitOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { theme } from './screenTheme';

export function useScreenMobile() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return isMobile;
}

interface Props {
  title: string;
  subtitle?: string;
  updatedAt?: string;
  onBack?: () => void;
  children: React.ReactNode;
}

export default function ScreenShell({ title, subtitle, updatedAt, onBack, children }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [time, setTime] = useState(new Date());
  const [fs, setFs] = useState(false);
  const isMobile = useScreenMobile();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const onFullscreenChange = () => setFs(document.fullscreenElement === rootRef.current);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
  }, []);

  const toggleFs = async () => {
    if (document.fullscreenElement === rootRef.current) {
      await document.exitFullscreen();
      return;
    }
    await rootRef.current?.requestFullscreen();
  };

  const dt = `${time.getFullYear()}-${String(time.getMonth() + 1).padStart(2, '0')}-${String(time.getDate()).padStart(2, '0')}`;
  const tm = `${String(time.getHours()).padStart(2, '0')}:${String(time.getMinutes()).padStart(2, '0')}:${String(time.getSeconds()).padStart(2, '0')}`;

  return (
    <div ref={rootRef} style={{
      minHeight: '100vh',
      background: `radial-gradient(ellipse at 50% 0%, rgba(0,184,240,0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 100%, rgba(77,159,255,0.06) 0%, transparent 40%), linear-gradient(180deg, ${theme.bg} 0%, #07162c 100%)`,
      color: theme.text,
      overflow: 'auto',
    }}>
      {/* Background effects */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
        <Stars />
        <GridLines />
      </div>

      <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', padding: isMobile ? '12px 10px 16px' : '14px 20px 18px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr auto 1fr', alignItems: 'center', gap: 10, marginBottom: isMobile ? 12 : 10, flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {onBack && <Button size="small" ghost icon={<ArrowLeftOutlined />} onClick={onBack} style={{ borderColor: theme.border, color: theme.textDim }}>返回</Button>}
          </div>
          <div style={{ minWidth: 0, textAlign: isMobile ? 'left' : 'center' }}>
            {/* Decorative line above title */}
            {!isMobile && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 6 }}>
                <span style={{ height: 1, width: 60, background: `linear-gradient(90deg, transparent, ${theme.cyan}66)`, display: 'block' }} />
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: theme.cyan, boxShadow: `0 0 10px ${theme.cyan}88` }} />
                <span style={{ height: 1, width: 60, background: `linear-gradient(90deg, ${theme.cyan}66, transparent)`, display: 'block' }} />
              </div>
            )}
            <Typography.Title level={isMobile ? 5 : 3} style={{
              color: '#fff',
              margin: 0,
              letterSpacing: isMobile ? 1 : 4,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              textShadow: `0 0 20px rgba(0,184,240,0.4), 0 0 40px rgba(0,184,240,0.15)`,
            }}>
              {title}
            </Typography.Title>
            {subtitle && <div style={{ color: theme.textDim, fontSize: isMobile ? 12 : 13, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: 1 }}>{subtitle}</div>}
          </div>
          <div style={{ display: 'flex', justifyContent: isMobile ? 'flex-start' : 'flex-end', alignItems: 'center', gap: 8, color: theme.textDim, fontSize: 12 }}>
            <span style={{ fontFamily: theme.numberFont, letterSpacing: 0.5 }}>{dt} {tm}{updatedAt ? ` · 数据: ${updatedAt}` : ''}</span>
            {!isMobile && (
              <Button size="small" ghost icon={fs ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFs} style={{ borderColor: theme.border, color: theme.textDim }}>
                {fs ? '退出' : '全屏'}
              </Button>
            )}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minHeight: 0 }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function Stars() {
  const positions = [
    [5,10],[15,3],[25,18],[35,5],[45,22],[55,8],[65,15],[75,4],[85,20],[95,10],
    [10,30],[20,25],[30,45],[40,35],[50,55],[60,40],[70,50],[80,30],[90,60],[3,70],
    [18,65],[28,75],[38,60],[48,80],[58,70],[68,55],[78,75],[88,65],[98,50],[8,90],
    [22,85],[32,95],[42,88],[52,92],[62,82],[72,95],[82,85],[92,90],[7,50],[13,55],
    [27,60],[37,52],[47,68],[57,48],[67,65],[77,45],[87,55],[97,42],[33,70],[55,30],
  ];
  return (
    <>
      {positions.map(([x, y], i) => (
        <div key={i} style={{
          position: 'absolute',
          left: `${x}%`,
          top: `${y}%`,
          width: i % 5 === 0 ? 3 : 2,
          height: i % 5 === 0 ? 3 : 2,
          borderRadius: '50%',
          background: '#dff8ff',
          opacity: 0.12 + (i % 3) * 0.08,
          boxShadow: '0 0 8px rgba(0,184,240,0.5)',
          animation: i % 4 === 0 ? `twinkle ${3 + (i % 3)}s ease-in-out infinite` : 'none',
          animationDelay: `${(i * 0.3) % 5}s`,
        }} />
      ))}
      <style>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.1; }
          50% { opacity: 0.35; }
        }
      `}</style>
    </>
  );
}

function GridLines() {
  return (
    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.03 }}>
      <defs>
        <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
          <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#00b8f0" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  );
}
