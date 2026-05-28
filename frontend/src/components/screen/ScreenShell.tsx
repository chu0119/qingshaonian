import { useState, useEffect } from 'react';
import { Button, Typography } from 'antd';
import { FullscreenOutlined, FullscreenExitOutlined, ArrowLeftOutlined } from '@ant-design/icons';
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
  title: string;
  subtitle?: string;
  updatedAt?: string;
  onBack?: () => void;
  children: React.ReactNode;
}

export default function ScreenShell({ title, subtitle, updatedAt, onBack, children }: Props) {
  const [time, setTime] = useState(new Date());
  const [fs, setFs] = useState(false);
  const isMobile = useIsMobile();

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const h = () => setFs(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', h);
    return () => document.removeEventListener('fullscreenchange', h);
  }, []);

  const toggleFs = async () => {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await document.documentElement.requestFullscreen();
    }
  };

  const dt = `${time.getFullYear()}-${String(time.getMonth()+1).padStart(2,'0')}-${String(time.getDate()).padStart(2,'0')}`;
  const tm = `${String(time.getHours()).padStart(2,'0')}:${String(time.getMinutes()).padStart(2,'0')}:${String(time.getSeconds()).padStart(2,'0')}`;

  return (
    <div style={{ minHeight: '100vh', background: `linear-gradient(180deg, ${theme.bg} 0%, #0a1a33 100%)`, color: theme.text, overflow: 'auto' }}>
      {/* frozen stars bg - deterministic */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
        <Stars />
      </div>

      <div style={{ position: 'relative', zIndex: 1, padding: isMobile ? '12px 8px' : '20px 28px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: isMobile ? 12 : 20 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Typography.Title level={isMobile ? 5 : 3} style={{ color: '#fff', margin: 0, letterSpacing: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {title}
            </Typography.Title>
            {subtitle && <div style={{ color: theme.textDim, fontSize: isMobile ? 12 : 14, marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis' }}>{subtitle}</div>}
            <div style={{ color: theme.textDim, fontSize: 12, marginTop: 4 }}>{dt} {tm}{updatedAt ? ` · 数据: ${updatedAt}` : ''}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <Button size="small" ghost icon={<FullscreenOutlined />} onClick={toggleFs} style={{ borderColor: theme.border, color: theme.textDim }}>
              {fs ? '退出' : '全屏'}
            </Button>
            {onBack && <Button size="small" ghost icon={<ArrowLeftOutlined />} onClick={onBack} style={{ borderColor: theme.border, color: theme.textDim }}>返回</Button>}
          </div>
        </div>

        {/* Content */}
        {children}
      </div>
    </div>
  );
}

/* Deterministic star field */
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
          position: 'absolute', left: `${x}%`, top: `${y}%`,
          width: 2, height: 2, borderRadius: '50%', background: '#fff',
          opacity: 0.1 + (i % 3) * 0.1,
          animation: `twinkle ${3 + (i % 4)}s ease-in-out ${(i % 3)}s infinite`,
        }} />
      ))}
      <style>{`@keyframes twinkle{0%,100%{opacity:0.1}50%{opacity:0.4}}`}</style>
    </>
  );
}
