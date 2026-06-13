import { useState, useEffect, useRef } from 'react';

/**
 * 数字跳动动画 hook
 * @param target 目标数值
 * @param duration 动画时长（毫秒）
 * @param decimals 小数位数
 */
export function useCountUp(
  target: number,
  duration: number = 1500,
  decimals: number = 0
): string {
  const [display, setDisplay] = useState('0');
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const startValueRef = useRef<number>(0);

  useEffect(() => {
    // 取消之前的动画
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
    }

    startTimeRef.current = performance.now();
    startValueRef.current = parseFloat(display) || 0;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);

      // easeOutQuart 缓动函数
      const eased = 1 - Math.pow(1 - progress, 4);
      const current = startValueRef.current + (target - startValueRef.current) * eased;

      setDisplay(current.toFixed(decimals));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [target, duration, decimals]);

  return display;
}

/**
 * 格式化数字（超过10000显示为X万）
 */
export function fmtNumber(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '0';
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  return num.toLocaleString('zh-CN');
}
