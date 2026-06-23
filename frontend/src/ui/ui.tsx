import { ReactNode, useEffect } from "react";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { EASE, fadeUp } from "./motion";

/** A number that smoothly counts up on mount and tweens on change. */
export function AnimatedNumber({ value, format, className }: {
  value: number; format: (n: number) => string; className?: string;
}) {
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => format(v));
  useEffect(() => {
    const controls = animate(mv, value, { duration: 0.9, ease: EASE });
    return () => controls.stop();
  }, [value]);
  return <motion.span className={className}>{text}</motion.span>;
}

/** Glass card with a fade-up entrance. Use inside a `stagger` parent for sequencing. */
export function Card({ children, className = "", interactive = false, ...rest }: {
  children: ReactNode; className?: string; interactive?: boolean;
} & React.ComponentProps<typeof motion.div>) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={interactive ? { y: -3 } : undefined}
      transition={{ duration: 0.25, ease: EASE }}
      className={`rounded-xl border border-slate-200/80 dark:border-line/80 bg-white/90 dark:bg-panel/80 backdrop-blur-sm shadow-sm dark:shadow-none ${interactive ? "hover:border-violet-500/50 dark:hover:border-violet-500/40" : ""} transition-colors ${className}`}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
        <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
        {children}
      </h2>
      {hint && <span className="text-[10px] text-slate-400 dark:text-slate-500">{hint}</span>}
    </div>
  );
}

export function Badge({ children, tone = "brand" }: { children: ReactNode; tone?: "brand" | "good" | "muted" }) {
  const tones = {
    brand: "bg-accent2/15 text-accent2 border-accent2/30",
    good: "bg-accent/15 text-accent border-accent/30",
    muted: "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-400/30",
  };
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${tones[tone]}`}>
      {children}
    </span>
  );
}
