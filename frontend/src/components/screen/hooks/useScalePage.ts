import { useEffect, useState, useCallback, useRef } from 'react';

/**
 * 专业大屏 scale 缩放适配 hook
 *
 * 以 1920×1080 为设计基准，自动计算缩放比例，
 * 保持画面居中且不变形。所有大屏内部元素用 px 定尺寸。
 */
export function useScalePage(designW = 1920, designH = 1080) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const calc = useCallback(() => {
    // 使用全屏元素的尺寸（如果在全屏模式下）
    const fullscreenEl = document.fullscreenElement;
    const vw = fullscreenEl ? fullscreenEl.clientWidth : window.innerWidth;
    const vh = fullscreenEl ? fullscreenEl.clientHeight : window.innerHeight;
    const s = Math.min(vw / designW, vh / designH);
    setScale(s);
    setOffset({
      x: (vw - designW * s) / 2,
      y: (vh - designH * s) / 2,
    });
  }, [designW, designH]);

  useEffect(() => {
    calc();
    window.addEventListener('resize', calc);
    document.addEventListener('fullscreenchange', calc);
    return () => {
      window.removeEventListener('resize', calc);
      document.removeEventListener('fullscreenchange', calc);
    };
  }, [calc]);

  /** 包裹容器的 style */
  const containerStyle: React.CSSProperties = {
    width: designW,
    height: designH,
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    position: 'absolute',
    left: offset.x,
    top: offset.y,
    overflow: 'hidden',
  };

  return { ref, scale, containerStyle };
}
