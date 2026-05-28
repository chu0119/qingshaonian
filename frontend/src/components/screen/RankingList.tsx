import { Empty } from 'antd';
import { theme, truncate } from './screenTheme';

interface Item {
  name: string;
  value: number;
  pct?: number;
  suffix?: string;
}

interface Props {
  title: string;
  items: Item[];
  valueLabel?: string;
  emptyText?: string;
  max?: number;
}

export default function RankingList({ title, items, valueLabel = '值', emptyText = '暂无数据', max = 10 }: Props) {
  const list = items.slice(0, max);
  const colors = ['#e8b339', '#a0a8b8', '#c08060', theme.textDim, theme.textDim];

  if (!list.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 120, color: theme.textDim, fontSize: 13 }}>
        <Empty description={emptyText} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div style={{ fontSize: 12 }}>
      {list.map((item, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: i < list.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
          <span style={{ width: 20, textAlign: 'center', fontWeight: i < 3 ? 700 : 400, color: colors[i] || theme.textDim, flexShrink: 0, fontSize: i < 3 ? 14 : 12 }}>
            {i < 3 ? ['🥇','🥈','🥉'][i] : i + 1}
          </span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: theme.text }}>{truncate(item.name, 12)}</span>
          <span style={{ flexShrink: 0, color: theme.cyan, fontWeight: 600 }}>{item.value}{item.suffix || ''}</span>
          {item.pct !== undefined && (
            <span style={{ flexShrink: 0, color: theme.textDim, width: 40, textAlign: 'right' }}>{item.pct}%</span>
          )}
        </div>
      ))}
    </div>
  );
}
