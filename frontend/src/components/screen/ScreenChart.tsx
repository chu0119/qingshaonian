import { useEffect, useState } from 'react';
import { Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
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

export const darkTooltip = {
  backgroundColor: 'rgba(6,18,36,0.95)',
  borderColor: theme.border,
  textStyle: { color: theme.text, fontSize: 12 },
};

interface Props {
  option: any;
  height?: number;
  empty?: boolean;
}

export default function ScreenChart({ option, height: h, empty }: Props) {
  const isMobile = useIsMobile();
  const [key, setKey] = useState(0);
  useEffect(() => {
    const onResize = () => setKey(k => k + 1);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  if (empty) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: h || 200, color: theme.textDim }}><Empty description="暂无数据" /></div>;
  }

  const baseH = h || (isMobile ? 200 : 260);
  return (
    <ReactECharts
      key={key}
      option={option}
      style={{ height: baseH, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
}
