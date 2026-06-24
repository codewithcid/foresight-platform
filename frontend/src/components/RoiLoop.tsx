import type { Tab } from "./Sidebar";
import { useNav } from "../nav";

type Stage = {
  step: number;
  phase: "Anticipate" | "Activate" | "Prove" | "Learn";
  title: string;
  tab: Tab;
  role: string;
  icon: string;
};

const PHASE: Record<Stage["phase"], string> = {
  Anticipate: "text-violet-500 bg-violet-500/10",
  Activate: "text-amber-500 dark:text-amber-400 bg-amber-400/10",
  Prove: "text-success bg-success/10",
  Learn: "text-sky-400 bg-sky-400/10",
};

// The closed loop: every surface is one stage of "predict ROI → act → prove → learn".
const STAGES: Stage[] = [
  { step: 1, phase: "Anticipate", title: "Audience & Uplift", tab: "byocsv", icon: "ri-database-2-line",
    role: "Scores each customer's incremental ROI (CATE)." },
  { step: 2, phase: "Anticipate", title: "Spend Planner", tab: "planner", icon: "ri-pie-chart-2-line",
    role: "Allocates budget to the highest-ROI segments." },
  { step: 3, phase: "Activate", title: "Creative Pre-Flight", tab: "creative", icon: "ri-magic-line",
    role: "Pre-tests which message lifts ROI most." },
  { step: 4, phase: "Activate", title: "Workflows + Channels", tab: "workflows", icon: "ri-flow-chart",
    role: "Delivers the ROI-maximizing action, live." },
  { step: 5, phase: "Activate", title: "Link-Up", tab: "store", icon: "ri-plug-line",
    role: "Recovers abandoned carts on your live app." },
  { step: 6, phase: "Prove", title: "Proof", tab: "proof", icon: "ri-checkbox-circle-line",
    role: "Measures actual vs. predicted ROI." },
  { step: 7, phase: "Learn", title: "Command", tab: "dashboard", icon: "ri-pulse-line",
    role: "Recalibrates predictions from results." },
];

export default function RoiLoop() {
  const { go, startTour } = useNav();
  return (
    <div className="rounded-xl ring-1 ring-foreground/10 bg-card p-5 mb-6">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" /> The ROI loop
          </h2>
          <p className="text-xs text-muted-foreground/80 mt-1 hidden sm:block">
            Predict <span className="text-muted-foreground/40">→</span> Optimize
            <span className="text-muted-foreground/40"> → </span>Craft
            <span className="text-muted-foreground/40"> → </span>Activate
            <span className="text-muted-foreground/40"> → </span>Prove
            <span className="text-muted-foreground/40"> → </span>Learn
            <span className="text-primary"> ↺</span>
          </p>
        </div>
        <button
          onClick={startTour}
          className="shrink-0 inline-flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition"
        >
          <i className="ri-play-circle-line text-sm" /> Guided tour
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        {STAGES.map((s) => (
          <button
            key={s.title}
            onClick={() => go(s.tab)}
            className="group flex flex-col h-full text-left rounded-lg ring-1 ring-foreground/10 bg-muted/25 hover:bg-muted/50 hover:ring-primary/40 transition-colors p-3"
          >
            <div className="flex items-center justify-between">
              <span className={`text-[9px] font-bold uppercase tracking-wider rounded px-1.5 py-0.5 ${PHASE[s.phase]}`}>{s.phase}</span>
              <span className="text-[10px] font-mono text-muted-foreground/40">{s.step}/{STAGES.length}</span>
            </div>
            <div className="flex items-center gap-2 mt-2.5">
              <i className={`${s.icon} text-base text-muted-foreground group-hover:text-primary transition-colors`} />
              <span className="font-grotesk font-bold text-[13px] leading-tight">{s.title}</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-snug mt-1.5">{s.role}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
