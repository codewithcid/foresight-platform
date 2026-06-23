import { useEffect, useState } from "react";
import { BanditArm, getBanditStatus } from "../api";

export default function BanditPanel({ refreshKey }: { refreshKey: number }) {
  const [arms, setArms] = useState<BanditArm[]>([]);

  useEffect(() => {
    getBanditStatus().then((d) => setArms(d.arms));
    const t = setInterval(() => getBanditStatus().then((d) => setArms(d.arms)), 4000);
    return () => clearInterval(t);
  }, [refreshKey]);

  return (
    <div className="border border-slate-200 dark:border-line rounded-lg p-4 bg-white dark:bg-panel/60">
      <h3 className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1">Contextual bandit — learned reliability per arm</h3>
      <p className="text-[11px] text-slate-400 dark:text-slate-500 mb-3">
        Thompson-sampling Beta posterior per (segment, intervention). Replaces a single global correction
        factor — the agent learns differently per segment instead of applying one number everywhere.
        Mean reliability is the posterior's expected success rate; trials is how many times that arm has
        actually been tried and resolved.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {arms.map((a) => (
          <div key={`${a.segment}-${a.intervention}`} className="border border-slate-200/70 dark:border-line/70 rounded-md p-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600 dark:text-slate-300">{a.segment} × {a.intervention}</span>
              <span className="text-slate-400 dark:text-slate-500">{a.trials} trial{a.trials !== 1 ? "s" : ""}</span>
            </div>
            <div className="w-full h-1.5 bg-slate-200 dark:bg-line rounded-full mt-1.5 overflow-hidden">
              <div className="h-full bg-accent" style={{ width: `${a.mean_reliability * 100}%` }} />
            </div>
            <p className="text-[11px] text-accent mt-1">{(a.mean_reliability * 100).toFixed(0)}% reliable (α={a.alpha}, β={a.beta})</p>
          </div>
        ))}
        {arms.length === 0 && <p className="text-sm text-slate-500">No arms tried yet — let the agent run.</p>}
      </div>
    </div>
  );
}
