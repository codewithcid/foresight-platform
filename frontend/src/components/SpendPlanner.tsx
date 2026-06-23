import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plan, getPlannerAnalyst, getPlannerDefaults, optimizePlan } from "../api";
import { AnimatedNumber } from "../ui/ui";
import { fadeUp, stagger } from "../ui/motion";
import { exportPlanPdf } from "../report";
import { deliveryChannel, useNav } from "../nav";

const inr = (x: number) => "₹" + Math.round(x).toLocaleString("en-IN");
const inrC = (x: number) =>
  x >= 1e7 ? "₹" + (x / 1e7).toFixed(2) + " Cr"
    : x >= 1e5 ? "₹" + (x / 1e5).toFixed(2) + " L"
      : x >= 1e3 ? "₹" + (x / 1e3).toFixed(1) + "k"
        : "₹" + Math.round(x);

function Curve({ curve, budget }: { curve: { budget: number; incr_revenue: number }[]; budget: number }) {
  if (curve.length < 2) return null;
  const w = 600, h = 150, pad = 10;
  const xmax = Math.max(...curve.map((c) => c.budget), 1);
  const ymax = Math.max(...curve.map((c) => c.incr_revenue), 1);
  const X = (b: number) => pad + (b / xmax) * (w - 2 * pad);
  const Y = (r: number) => h - pad - (r / ymax) * (h - 2 * pad);
  const line = curve.map((c, i) => `${i ? "L" : "M"} ${X(c.budget).toFixed(1)} ${Y(c.incr_revenue).toFixed(1)}`).join(" ");
  const area = `${line} L ${X(xmax).toFixed(1)} ${(h - pad).toFixed(1)} L ${X(0).toFixed(1)} ${(h - pad).toFixed(1)} Z`;
  const bx = X(Math.min(budget, xmax));
  const by = Y((curve.find((c) => c.budget >= budget) ?? curve[curve.length - 1]).incr_revenue);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <defs>
        <linearGradient id="curvefill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#34e0a1" stopOpacity="0.30" />
          <stop offset="100%" stopColor="#34e0a1" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#curvefill)" />
      <path d={line} fill="none" stroke="#34e0a1" strokeWidth="2" />
      <line x1={bx} y1={pad} x2={bx} y2={h - pad} stroke="#ffb600" strokeWidth="1.5" strokeDasharray="4 3" />
      <circle cx={bx} cy={by} r="4" fill="#ffb600" />
    </svg>
  );
}

export default function SpendPlanner() {
  const { go } = useNav();
  const [maxBudget, setMaxBudget] = useState(2000);
  const [budget, setBudget] = useState(0);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyst, setAnalyst] = useState<{ text: string; model: string } | null>(null);

  useEffect(() => {
    getPlannerDefaults().then((d) => {
      setMaxBudget(Math.max(Math.ceil(d.max_useful_budget * 1.1), 100));
      setBudget(Math.round(d.suggested_budget));
    });
  }, []);

  useEffect(() => {
    if (!budget) return;
    let on = true;
    setLoading(true);
    const t = setTimeout(() => {
      optimizePlan(budget).then((p) => { if (on) { setPlan(p); setLoading(false); } });
    }, 160);
    return () => { on = false; clearTimeout(t); };
  }, [budget]);

  // AI Analyst (NVIDIA 120B pool) -- longer debounce so it only fires once the
  // budget settles, not on every slider tick.
  useEffect(() => {
    if (!budget) return;
    let on = true;
    const t = setTimeout(() => {
      getPlannerAnalyst(budget).then((a) => { if (on) setAnalyst(a); }).catch(() => {});
    }, 1100);
    return () => { on = false; clearTimeout(t); };
  }, [budget]);

  const saturated = plan ? budget >= plan.max_useful_budget * 0.98 : false;
  const inc = plan?.incrementality;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            Spend Planner
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/30">
              optimize · prove
            </span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Set a budget. Foresight allocates it across segment × channel to maximize
            <span className="text-slate-700 dark:text-slate-200"> predicted incremental revenue</span>, then proves the plan
            against a held-out control.
          </p>
        </div>
        <motion.button
          whileTap={{ scale: 0.96 }}
          onClick={() => plan && exportPlanPdf(plan, analyst?.text ?? null)}
          disabled={!plan}
          className="shrink-0 text-xs px-3.5 py-2 rounded-lg border border-slate-300 dark:border-line text-slate-600 dark:text-slate-300 hover:border-accent2/60 hover:text-accent2 disabled:opacity-40 transition"
        >
          ↓ Download PDF
        </motion.button>
      </div>

      {/* Budget control */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-line bg-slate-50 dark:bg-panel">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-slate-500 dark:text-slate-400">Marketing budget</label>
          <span className="font-mono font-bold text-lg text-slate-800 dark:text-slate-100">{inr(budget)}</span>
        </div>
        <input
          type="range" min={0} max={maxBudget} step={Math.max(1, Math.round(maxBudget / 100))}
          value={budget} onChange={(e) => setBudget(Number(e.target.value))}
          className="w-full accent-accent"
        />
        <div className="flex justify-between text-[10px] text-slate-400 mt-1">
          <span>₹0</span>
          {plan && <span className={saturated ? "text-amber-500" : ""}>saturation ≈ {inrC(plan.max_useful_budget)}</span>}
          <span>{inrC(maxBudget)}</span>
        </div>
        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-2">
          Projected onto a 5,00,000-customer addressable base · per-segment lift learned from live data.
        </p>
      </div>

      {plan && (
        <>
          {/* Headline metrics */}
          <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {([
              { label: "Allocated spend", value: plan.spend, fmt: inr, c: "#ffb600", sub: "" },
              { label: "Predicted incremental revenue", value: plan.pred_incr_revenue, fmt: inr, c: "#34e0a1",
                sub: `90% CI ${inr(plan.pred_incr_revenue_ci[0])} – ${inr(plan.pred_incr_revenue_ci[1])}` },
              { label: "Blended ROI", value: plan.blended_roi, fmt: (n: number) => `${n.toFixed(1)}×`, c: "#34e0a1", sub: "" },
              { label: "Incremental conversions", value: plan.pred_incr_conversions, fmt: (n: number) => `+${Math.round(n).toLocaleString("en-IN")}`, c: "#ffb600", sub: "" },
            ]).map((m) => (
              <motion.div key={m.label} variants={fadeUp}
                className="rounded-2xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-3.5">
                <p className="text-2xl font-bold leading-none" style={{ color: m.c }}>
                  <AnimatedNumber value={m.value} format={m.fmt} />
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-500 mt-1.5">{m.label}</p>
                {m.sub && <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 font-mono">{m.sub}</p>}
              </motion.div>
            ))}
          </motion.div>

          {/* AI Analyst -- executive brief written live by the NVIDIA 120B pool */}
          <motion.div variants={fadeUp} initial="hidden" animate="show"
            className="rounded-2xl border border-accent2/30 bg-linear-to-br from-accent2/[0.08] to-transparent p-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] uppercase tracking-wider text-accent2 font-semibold">✦ AI Analyst — executive brief</span>
              {analyst && <span className="text-[10px] font-mono text-slate-400">{analyst.model}</span>}
            </div>
            {analyst
              ? <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">{analyst.text}</p>
              : <p className="text-sm text-slate-400 animate-pulse">Generating strategic brief…</p>}
          </motion.div>

          {/* Benchmark vs naive allocation -- proves the optimization is worth something */}
          {(() => {
            const bl = plan.baselines;
            const bars = [
              { label: "Foresight (optimized)", value: bl.foresight, c: "#34e0a1", strong: true },
              { label: "Even split", value: bl.even_split, c: "#ffb600", strong: false },
              { label: "Biggest segment first", value: bl.biggest_segment, c: "#64748b", strong: false },
            ];
            const max = Math.max(...bars.map((b) => b.value), 1);
            return (
              <motion.div variants={fadeUp} initial="hidden" animate="show"
                className="rounded-2xl border border-accent/30 bg-accent/[0.05] p-4">
                <div className="flex items-baseline justify-between mb-3">
                  <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Foresight vs naive allocation <span className="text-slate-400">· same budget</span>
                  </span>
                  {bl.uplift_vs_even_pct != null && (
                    <span className="text-sm font-semibold text-accent">
                      +{bl.uplift_vs_even_pct}% vs even split · +{inr(bl.uplift_vs_even_abs)}
                    </span>
                  )}
                </div>
                <div className="space-y-2.5">
                  {bars.map((b) => (
                    <div key={b.label} className="flex items-center gap-3">
                      <div className="w-44 shrink-0 text-xs text-slate-600 dark:text-slate-300">{b.label}</div>
                      <div className="flex-1 h-6 rounded-md bg-slate-100 dark:bg-ink/60 overflow-hidden">
                        <motion.div className="h-full rounded-md flex items-center justify-end pr-2"
                          style={{ background: b.c }}
                          initial={{ width: 0 }} animate={{ width: `${(b.value / max) * 100}%` }}
                          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}>
                          <span className={`text-[11px] font-mono font-semibold ${b.strong ? "text-ink" : "text-white/90"}`}>{inr(b.value)}</span>
                        </motion.div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-3">
                  Naive plans spend the same budget without ROI-ranking — wasting it on weak channels. The gap is the value of the optimization.
                </p>
              </motion.div>
            );
          })()}

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
            {/* Allocation */}
            <div className="rounded-xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-4">
              <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Optimized allocation</div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400">
                    <th className="py-1.5">Segment</th><th>Channel</th>
                    <th className="text-right">Reach</th><th className="text-right">Cost</th>
                    <th className="text-right">Pred. revenue</th><th className="text-right">ROI</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {plan.plan.map((p, i) => (
                    <tr key={i} className="border-t border-slate-100 dark:border-line/50 group">
                      <td className="py-2 text-slate-700 dark:text-slate-200">{p.segment_label}</td>
                      <td className="text-slate-500 dark:text-slate-400">{p.intervention_label}</td>
                      <td className="text-right font-mono text-slate-600 dark:text-slate-300">{p.reach_funded.toLocaleString("en-IN")}</td>
                      <td className="text-right font-mono text-slate-600 dark:text-slate-300">{inr(p.cost)}</td>
                      <td className="text-right font-mono text-accent">{inr(p.pred_incr_revenue)}</td>
                      <td className="text-right font-mono text-slate-500">{p.roi}×</td>
                      <td className="text-right">
                        <button
                          onClick={() => go("workflows", { segment: p.segment, intervention: p.intervention, channel: deliveryChannel(p.channel), from: "Spend Planner" })}
                          className="text-[11px] text-accent2 opacity-60 group-hover:opacity-100 hover:underline whitespace-nowrap"
                          title="Launch this allocation as a workflow">
                          Launch →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {plan.plan.length === 0 && (
                    <tr><td colSpan={7} className="py-3 text-slate-500 text-center">Increase the budget to fund a plan.</td></tr>
                  )}
                </tbody>
              </table>
              <p className="text-[11px] text-slate-400 mt-3">
                Channels are capped by realistic reach, so segments are covered by a mix — and unprofitable
                channels (negative ROI) are left out automatically.
              </p>
            </div>

            {/* Curve + proof */}
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-4">
                <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Budget efficiency</div>
                <p className="text-[11px] text-slate-400 mb-2">
                  {saturated
                    ? "You're past the saturation point — extra spend barely adds revenue."
                    : "Predicted incremental revenue vs. budget. The curve flattens at saturation."}
                </p>
                <Curve curve={plan.curve} budget={budget} />
              </div>

              {inc && (
                <div className="rounded-xl border border-accent2/40 bg-accent2/[0.06] p-4">
                  <div className="text-[11px] uppercase tracking-wider text-accent2 font-semibold mb-2">
                    ✓ Incrementality proof (held-out)
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div>
                      <div className="text-[10px] uppercase text-slate-500">Predicted</div>
                      <div className="font-mono font-bold text-accent2">{inr(inc.predicted_incr_revenue)}</div>
                    </div>
                    <span className="text-slate-400 text-xs">vs</span>
                    <div className="text-right">
                      <div className="text-[10px] uppercase text-slate-500">Actual (control)</div>
                      <div className="font-mono font-bold text-slate-800 dark:text-white">{inr(inc.actual_incr_revenue)}</div>
                    </div>
                  </div>
                  {inc.accuracy != null && (
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">
                      Plan accuracy <span className="font-semibold text-accent">{inc.accuracy}%</span>
                      <span className="text-slate-400"> · true incremental lift measured against a randomized holdout</span>
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
      {loading && !plan && <p className="text-sm text-slate-500 animate-pulse">Optimizing…</p>}
    </div>
  );
}
