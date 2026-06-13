/**
 * 全屏扫描线动画 — 从上到下缓慢扫描的水平光线
 */
export default function ScanLine() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        zIndex: 2,
      }}
    >
      <div className="screen-scan-line" />
    </div>
  );
}
