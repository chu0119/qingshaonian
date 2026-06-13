import React, { useState, useEffect, useRef } from 'react';

interface ScrollListItem {
  id: number | string;
  [key: string]: any;
}

interface ScrollListProps {
  data: ScrollListItem[];
  columns: { key: string; title: string; width?: number; isRank?: boolean }[];
  maxRows?: number;
  scrollSpeed?: number;
  rowHeight?: number;
  style?: React.CSSProperties;
}

const rankColors = ['#ffd93d', '#c0c0c0', '#cd7f32'];

/**
 * 自动滚动列表 — 带排名徽章 + 深空风格
 */
export default function ScrollList({
  data,
  columns,
  maxRows = 6,
  scrollSpeed = 3500,
  rowHeight = 38,
  style,
}: ScrollListProps) {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    if (data.length <= maxRows) return;
    const timer = setInterval(() => {
      setOffset((prev) => {
        const next = prev + 1;
        return next >= data.length ? 0 : next;
      });
    }, scrollSpeed);
    return () => clearInterval(timer);
  }, [data.length, maxRows, scrollSpeed]);

  const visibleData = data.length <= maxRows
    ? data
    : [...data, ...data].slice(offset, offset + maxRows);

  return (
    <div style={{ overflow: 'hidden', height: rowHeight * maxRows, ...style }}>
      <div style={{ transition: 'transform 0.6s cubic-bezier(0.22, 1, 0.36, 1)', transform: `translateY(-${offset * rowHeight}px)` }}>
        {visibleData.map((item, index) => {
          const rank = (item as any).rank ?? (index < 3 ? index + 1 : undefined);
          return (
            <div
              key={`${item.id}-${index}`}
              className="scroll-list-item"
              style={{
                display: 'flex',
                height: rowHeight,
                alignItems: 'center',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                fontSize: 13,
                color: 'rgba(224,234,255,0.85)',
              }}
            >
              {columns.map((col) => {
                const val = item[col.key] ?? '-';
                // 排名列特殊样式
                if (col.isRank || (col.key === 'rank' && typeof val === 'number' && val <= 3)) {
                  const r = typeof val === 'number' ? val : parseInt(String(val));
                  return (
                    <div
                      key={col.key}
                      style={{
                        flex: col.width ? `0 0 ${col.width}px` : '0 0 32px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        paddingRight: 8,
                      }}
                    >
                      {r >= 1 && r <= 3 ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 20,
                            height: 20,
                            borderRadius: '50%',
                            background: `${rankColors[r - 1]}22`,
                            color: rankColors[r - 1],
                            fontSize: 11,
                            fontWeight: 700,
                          }}
                        >
                          {r}
                        </span>
                      ) : (
                        <span style={{ color: 'rgba(224,234,255,0.35)', fontSize: 12 }}>{val}</span>
                      )}
                    </div>
                  );
                }
                return (
                  <div
                    key={col.key}
                    style={{
                      flex: col.width ? `0 0 ${col.width}px` : 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      paddingRight: 8,
                    }}
                  >
                    {val}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
