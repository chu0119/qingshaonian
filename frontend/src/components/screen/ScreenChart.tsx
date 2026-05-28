import { Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import { theme } from './screenTheme';

export const darkTooltip = {
  backgroundColor: 'rgba(6,18,36,0.96)',
  borderColor: theme.border,
  textStyle: { color: theme.text, fontSize: 12 },
};

interface Props {
  option: any;
  height?: number | string;
  empty?: boolean;
}

export default function ScreenChart({ option, height = '100%', empty }: Props) {
  const styleHeight = typeof height === 'number' ? `${height}px` : height;

  if (empty) {
    return <div style={{ height: styleHeight, minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.textDim }}><Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /></div>;
  }

  return (
    <ReactECharts
      option={option}
      style={{ height: styleHeight, minHeight: 120, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
}
