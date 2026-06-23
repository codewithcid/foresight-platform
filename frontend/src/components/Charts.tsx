// Small hand-rolled SVG infographic primitives -- no charting library
// dependency, just enough to turn flat number rows into real visuals.

export function Sparkline({
  values, width = 120, height = 32, color = "#34e0a1", fill = true,
}: { values: number[]; width?: number; height?: number; color?: string; fill?: boolean }) {
  if (values.length < 2) {
    return <svg width={width} height={height} />;
  }
  const max = Math.max(...values, 0.0001);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = width / (values.length - 1);
  const points = values.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return [x, y];
  });
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const areaPath = `${path} L${width},${height} L0,${height} Z`;
  const gid = `spark-${color.replace("#", "")}`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {fill && (
        <>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.35" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gid})`} stroke="none" />
        </>
      )}
      <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r="2.2" fill={color} />
    </svg>
  );
}

export function Donut({
  segments, size = 110, strokeWidth = 16, centerLabel, centerSub,
}: {
  segments: { label: string; value: number; color: string }[];
  size?: number; strokeWidth?: number; centerLabel?: string; centerSub?: string;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" className="stroke-black/[0.06] dark:stroke-white/[0.06]" strokeWidth={strokeWidth} />
        {segments.map((seg, i) => {
          const frac = seg.value / total;
          const dash = frac * circumference;
          const dashoffset = offset;
          offset += dash;
          if (frac <= 0) return null;
          return (
            <circle
              key={i} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={seg.color} strokeWidth={strokeWidth}
              strokeDasharray={`${dash} ${circumference - dash}`} strokeDashoffset={-dashoffset}
              strokeLinecap="butt"
            />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold text-slate-800 dark:text-slate-100 leading-none">{centerLabel}</span>
        {centerSub && <span className="text-[10px] text-slate-500 dark:text-slate-500 mt-0.5">{centerSub}</span>}
      </div>
    </div>
  );
}

export function HBar({ label, value, max, color, suffix = "" }: { label: string; value: number; max: number; color: string; suffix?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-slate-600 dark:text-slate-300">{label}</span>
        <span className="font-medium" style={{ color }}>{value.toFixed(2)}{suffix}</span>
      </div>
      <div className="h-2 rounded-full bg-black/5 dark:bg-white/5 overflow-hidden relative">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }} />
      </div>
    </div>
  );
}
