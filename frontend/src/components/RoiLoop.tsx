import type { Tab } from "./Sidebar";
import { useNav } from "../nav";

type Stage = {
  phase: "Anticipate" | "Activate" | "Prove" | "Learn";
  title: string;
  tab: Tab;
  role: string;
  icon: string;
};

const PHASE_COLOR: Record<Stage["phase"], string> = {
  Anticipate: "text-violet-500",
  Activate: "text-amber-500 dark:text-amber-400",
  Prove: "text-success",
  Learn: "text-sky-400",
};

// The closed loop: every surface is one stage of "predict ROI → act → prove → learn".
const STAGES: Stage[] = [
  { phase: "Anticipate", title: "Audience & Uplift", tab: "byocsv", icon: "ri-database-2-line",
    role: "Causal model scores each customer's incremental ROI (CATE)." },
  { phase: "Anticipate", title: "Spend Planner", tab: "planner", icon: "ri-pie-chart-2-line",
    role: "Allocates budget to the highest-predicted-ROI segments." },
  { phase: "Activate", title: "Creative Pre-Flight", tab: "creative", icon: "ri-magic-line",
    role: "Pre-tests which message lifts ROI most, before spend." },
  { phase: "Activate", title: "Workflows + Channels", tab: "workflows", icon: "ri-flow-chart",
    role: "Delivers the ROI-maximizing action on real channels." },
  { phase: "Prove", title: "Proof", tab: "proof", icon: "ri-checkbox-circle-line",
    role: "Measures actual vs. predicted ROI on every campaign." },
  { phase: "Learn", title: "Command", tab: "dashboard", icon: "ri-pulse-line",
    role: "Self-correction feeds the gap back to recalibrate predictions." },
];

export default function RoiLoop() {
  const go = useNav();
  return (
    <div className="rounded-xl ring-1 ring-foreground/10 bg-card p-4 mb-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" /> The ROI loop — how every surface connects
        </h2>
        <span className="text-[10px] text-muted-foreground/70 hidden sm:block">predict → act → prove → learn → repeat</span>
      </div>
      <div className="flex items-stretch gap-1 overflow-x-auto pb-1">
        {STAGES.map((s, i) => (
          <div key={s.title} className="flex items-stretch shrink-0">
            <button
              onClick={() => go(s.tab)}
              className="group w-[168px] text-left rounded-lg ring-1 ring-foreground/10 bg-muted/30 hover:bg-muted/60 hover:ring-primary/40 transition-colors p-3"
            >
              <div className="flex items-center justify-between">
                <span className={`text-[9px] font-bold uppercase tracking-wider ${PHASE_COLOR[s.phase]}`}>{s.phase}</span>
                <i className={`${s.icon} text-muted-foreground group-hover:text-primary transition-colors`} />
              </div>
              <div className="font-grotesk font-bold text-sm mt-1 leading-tight">{s.title}</div>
              <p className="text-[10px] text-muted-foreground leading-snug mt-1">{s.role}</p>
            </button>
            <div className="self-center px-1 text-muted-foreground/40">
              <i className={i === STAGES.length - 1 ? "ri-loop-left-line text-sky-400" : "ri-arrow-right-line"} />
            </div>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-muted-foreground/70 mt-2">
        Each stage feeds the next; the loop closes when proven outcomes recalibrate the model — so the ROI
        prediction gets sharper every cycle. The <span className="text-card-foreground/80">Agent Console</span> can drive any stage.
      </p>
    </div>
  );
}
