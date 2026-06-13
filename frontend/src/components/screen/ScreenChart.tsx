/**
 * ScreenChart - ECharts 包装组件
 */
import ReactECharts from 'echarts-for-react';
import { screenTheme as T } from './theme';

interface ScreenChartProps {
  option: any;
  style?: React.CSSProperties;
  height?: number;
}

export default function ScreenChart({ option, style, height }: ScreenChartProps) {
  const defaultOption = {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: T.fontFamily },
  };

  return (
    <ReactECharts
      option={{ ...defaultOption, ...option }}
      style={{ width: '100%', height: height ? `${height}px` : '100%', ...style }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
}

/** 通用深色 tooltip */
export const darkTooltip = {
  backgroundColor: 'rgba(15, 23, 60, 0.95)',
  borderColor: T.border,
  borderWidth: 1,
  textStyle: { color: T.text, fontSize: 12 },
  extraCssText: 'backdrop-filter: blur(10px); border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);',
};
