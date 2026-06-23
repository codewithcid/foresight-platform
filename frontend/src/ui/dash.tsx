import { ReactNode } from "react";
import { motion } from "framer-motion";
import { fadeUp } from "./motion";

/* ============================================================
   shadcn-style dashboard primitives (adapted to our stack).
   Flat `bg-card` surfaces with a subtle `ring`, muted-foreground
   labels, tabular numerals — the clean admin-dashboard look.
   ============================================================ */

export function Card({ className = "", children, ...rest }: { className?: string; children: ReactNode } & React.ComponentProps<"div">) {
  return (
    <div
      className={`flex flex-col gap-4 overflow-hidden rounded-xl bg-card py-4 text-card-foreground ring-1 ring-foreground/10 ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Card with a fade-up entrance — use inside a `stagger` parent. */
export function MotionCard({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <motion.div
      variants={fadeUp}
      className={`flex flex-col gap-4 overflow-hidden rounded-xl bg-card py-4 text-card-foreground ring-1 ring-foreground/10 ${className}`}
    >
      {children}
    </motion.div>
  );
}

export function CardHeader({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`grid auto-rows-min items-start gap-1 px-4 ${className}`}>{children}</div>;
}

export function CardHeaderRow({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`flex items-start justify-between gap-3 px-4 ${className}`}>{children}</div>;
}

export function CardTitle({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`font-grotesk text-base leading-snug font-semibold ${className}`}>{children}</div>;
}

export function CardDescription({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`text-sm text-muted-foreground ${className}`}>{children}</div>;
}

export function CardContent({ className = "", children }: { className?: string; children: ReactNode }) {
  return <div className={`px-4 ${className}`}>{children}</div>;
}

/** Small rounded icon container (the shadcn metric-card glyph chip). */
export function IconChip({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`flex size-8 items-center justify-center rounded-lg border border-border bg-muted text-muted-foreground ${className}`}>
      {children}
    </div>
  );
}

type BadgeTone = "default" | "outline" | "success" | "destructive" | "warning";

const BADGE_TONES: Record<BadgeTone, string> = {
  default: "bg-primary text-primary-foreground",
  outline: "border border-border text-muted-foreground",
  success: "bg-success/15 text-success",
  destructive: "bg-destructive/15 text-destructive",
  warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
};

export function Badge({ tone = "default", className = "", children }: { tone?: BadgeTone; className?: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap [&>svg]:size-3 ${BADGE_TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/** A shadcn-style KPI card: icon chip, label, big tabular value, optional badge + subtext. */
export function MetricCard({
  icon,
  label,
  value,
  badge,
  sub,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  badge?: ReactNode;
  sub?: string;
}) {
  return (
    <motion.div
      variants={fadeUp}
      className="flex flex-col gap-3 overflow-hidden rounded-xl bg-linear-to-t from-primary/[0.06] to-card py-4 text-card-foreground ring-1 ring-foreground/10"
    >
      <div className="flex items-start justify-between px-4">
        <IconChip>{icon}</IconChip>
        {badge}
      </div>
      <div className="flex flex-col gap-1 px-4">
        <div className="font-medium text-3xl tabular-nums leading-none tracking-tight text-foreground">{value}</div>
        <p className="text-muted-foreground text-sm leading-snug">{label}</p>
        {sub && <p className="text-muted-foreground/70 text-xs">{sub}</p>}
      </div>
    </motion.div>
  );
}
