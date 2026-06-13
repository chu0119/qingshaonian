/**
 * ChartCard - 图表容器卡片
 * 玻璃拟态风格，带标题和边框装饰
 */
import { screenTheme as T } from './theme';

interface ChartCardProps {
  title: string;
  extra?: React.ReactNode;
  children: React.ReactNode;
  borderColor?: string;
}

export default function ChartCard({ title, extra, children, borderColor = T.primary }: ChartCardProps) {
  return (
    <div style={{
      background: T.bgCard,
      border: `1px solid ${T.border}`,
      borderRadius: 12,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      backdropFilter: 'blur(10px)',
    }}>
      {/* 标题栏 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 3, height: 14, borderRadius: 2,
            background: borderColor,
          }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: T.textHighlight }}>
            {title}
          </span>
        </div>
        {extra}
      </div>

      {/* 图表内容 */}
      <div style={{ flex: 1, padding: '8px 12px', minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}
