import { Empty, Tag } from 'antd';
import { theme, truncate } from './screenTheme';

interface Item {
  id: number | string;
  title: string;
  subtitle?: string;
  status?: string;
  statusColor?: string;
  time?: string;
  desc?: string;
}

interface Props {
  items: Item[];
  emptyText?: string;
  max?: number;
}

export default function LatestList({ items, emptyText = '暂无数据', max = 6 }: Props) {
  const list = items.slice(0, max);

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
        <div key={item.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '4px 0', borderBottom: i < list.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: theme.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{truncate(item.title, 20)}</div>
            {item.subtitle && <div style={{ color: theme.textDim, fontSize: 11, marginTop: 1 }}>{truncate(item.subtitle, 16)}</div>}
            {item.desc && <div style={{ color: theme.textDim, fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{truncate(item.desc, 30)}</div>}
          </div>
          {item.status && <Tag color={item.statusColor || 'default'} style={{ fontSize: 10, lineHeight: '18px', flexShrink: 0 }}>{item.status}</Tag>}
          {item.time && <span style={{ color: theme.textDim, fontSize: 11, flexShrink: 0 }}>{item.time}</span>}
        </div>
      ))}
    </div>
  );
}
