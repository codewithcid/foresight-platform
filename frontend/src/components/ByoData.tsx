import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ByoAnalysis, Plan, analyzeByoCsv, byoReplan, byoSampleUrl } from "../api";
import { AnimatedNumber } from "../ui/ui";
import { fadeUp, stagger } from "../ui/motion";
import DecileChart from "../charts/DecileChart";
import TrendLineChart from "../charts/TrendLineChart";
import { Check, Database, Upload } from "./Icons";

const CARD = "rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800 shadow-xs";
const inr = (x: number) => "₹" + Math.round(x).toLocaleString("en-IN");
const inrC = (x: number) =>
  x >= 1e7 ? "₹" + (x / 1e7).toFixed(2) + " Cr"
    : x >= 1e5 ? "₹" + (x / 1e5).toFixed(2) + " L"
      : x >= 1e3 ? "₹" + (x / 1e3).toFixed(1) + "k"
        : "₹" + Math.round(x);

function Curve({ curve, budget }: { curve: { budget: number; incr_revenue: number }[]; budget: number }) {
  if (curve.length < 2) return null;
  return <TrendLineChart values={curve.map((c) => c.incr_revenue)} color="#34e0a1" height={120} formatY={inrC} />;
}

export default function ByoData() {
  const [analysis, setAnalysis] = useState<ByoAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Interactive budget re-planning (server caches the dataset's cells).
  const [plan, setPlan] = useState<Plan | null>(null);
  const [budget, setBudget] = useState(0);
  const [maxBudget, setMaxBudget] = useState(1000);

  async function runAnalyze(file: File) {
    setLoading(true); setError(null); setFileName(file.name);
    try {
      const res = await analyzeByoCsv(file);
      setAnalysis(res);
      setPlan(res.plan);
      setBudget(Math.round(res.plan.budget));
      setMaxBudget(Math.max(Math.ceil(res.plan.max_useful_budget * 1.1), 100));
    } catch (e: any) {
      setError(e.message || "Could not analyze that file.");
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  async function useSample() {
    setLoading(true); setError(null);
    try {
      const res = await fetch(byoSampleUrl());
      const blob = await res.blob();
      await runAnalyze(new File([blob], "foresight_sample_experiment.csv", { type: "text/csv" }));
    } catch {
      setError("Could not load the sample dataset."); setLoading(false);
    }
  }

  // Debounced re-plan when the budget slider moves.
  useEffect(() => {
    if (!analysis || !budget) return;
    let on = true;
    const t = setTimeout(() => { byoReplan(budget).then((p) => { if (on) setPlan(p); }).catch(() => {}); }, 180);
    return () => { on = false; clearTimeout(t); };
  }, [budget]); // eslint-disable-line react-hooks/exhaustive-deps

  const inc = analysis?.validation.incrementality;
  const ds = analysis?.dataset;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
          Bring Your Own Data
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-500 border border-violet-500/30">
            real product
          </span>
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Upload your own marketing-experiment CSV. Foresight trains its causal uplift model on
          <span className="text-gray-700 dark:text-gray-200"> your</span> segments and treatments, proves it on a
          randomized holdout, and builds an optimized spend plan — no code, your data.
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={`${CARD} p-6 border-dashed transition-colors ${dragOver ? "border-violet-500 bg-violet-500/5" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) runAnalyze(f);
        }}
      >
        <div className="flex flex-col items-center text-center gap-3">
          <span className="grid place-items-center w-12 h-12 rounded-full bg-violet-500/15 text-violet-500"><Upload size={22} /></span>
          <div>
            <p className="text-sm font-medium text-gray-800 dark:text-gray-100">Drop a CSV here, or choose a file</p>
            <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">
              Needs columns for <b>segment</b>, <b>treatment</b> (incl. a control), and <b>converted</b> (0/1).
              Optional <b>cost</b>, <b>revenue</b>, and any extra feature columns are used automatically.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 mt-1">
            <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) runAnalyze(f); }} />
            <button onClick={() => fileRef.current?.click()} className="btn bg-violet-500 text-ink font-semibold hover:bg-violet-600 text-sm">
              <Upload size={15} /> <span className="ml-1.5">Choose CSV</span>
            </button>
            <button onClick={useSample} className="btn border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-violet-500/60 hover:text-violet-500 text-sm">
              <Database size={15} /> <span className="ml-1.5">Use sample data</span>
            </button>
            <a href={byoSampleUrl()} className="text-xs text-gray-400 hover:text-violet-500 underline underline-offset-2">download sample CSV</a>
          </div>
          {fileName && !error && <p className="text-[11px] text-gray-400">{loading ? "Analyzing" : "Loaded"}: {fileName}</p>}
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500 animate-pulse">Training the uplift model on your data…</p>}
      {error && (
        <div className={`${CARD} p-4 border-red-500/40`}>
          <p className="text-sm text-red-600 dark:text-red-400 font-medium">Couldn't analyze that file</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{error}</p>
        </div>
      )}

      {analysis && ds && (
        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-5">
          {/* Dataset summary */}
          <motion.div variants={fadeUp} className={`${CARD} p-4`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400">Dataset detected</span>
              <span className="text-[11px] text-gray-400">
                {ds.rows.toLocaleString("en-IN")} rows · {ds.customers.toLocaleString("en-IN")} customers · {(ds.conversion_rate * 100).toFixed(1)}% conversion
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-[10px] uppercase text-gray-400 mb-1.5">Segments</p>
                <div className="flex flex-wrap gap-1.5">
                  {ds.segments.map((s) => (
                    <span key={s.name} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300">
                      {s.name} <span className="text-gray-400">({s.n.toLocaleString("en-IN")})</span>
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-[10px] uppercase text-gray-400 mb-1.5">Treatments</p>
                <div className="flex flex-wrap gap-1.5">
                  {ds.treatments.map((t) => (
                    <span key={t.name} className={`text-xs px-2 py-0.5 rounded-full border ${t.is_control ? "border-gray-300 dark:border-gray-600 text-gray-500" : "bg-violet-500/10 text-violet-500 border-violet-500/30"}`}>
                      {t.name}{t.is_control ? " · control" : ""} <span className="opacity-60">({t.n.toLocaleString("en-IN")})</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-3 pt-2 border-t border-gray-100 dark:border-gray-700/60">
              Model features: {[...analysis.dataset.features_used.numeric, ...analysis.dataset.features_used.categorical].join(", ") || "segment only"}
              {" · "}{analysis.model.library} S-learner · {analysis.model.n_train.toLocaleString("en-IN")} train / {analysis.model.n_test.toLocaleString("en-IN")} holdout
            </p>
          </motion.div>

          {/* Validation proof */}
          {inc && (
            <motion.div variants={fadeUp} className={`${CARD} p-4 border-accent2/40`}>
              <div className="text-[11px] uppercase tracking-wider text-accent2 font-semibold mb-3">
                ✓ Holdout validation — predicted vs. actually observed
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <p className="text-2xl font-bold text-accent2 leading-none">
                    <AnimatedNumber value={inc.predicted_incr_conversions} format={(n) => `+${Math.round(n)}`} />
                  </p>
                  <p className="text-[11px] text-gray-500 mt-1.5">Predicted incremental conversions</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800 dark:text-gray-100 leading-none">
                    <AnimatedNumber value={inc.observed_incr_conversions} format={(n) => `+${Math.round(n)}`} />
                  </p>
                  <p className="text-[11px] text-gray-500 mt-1.5">Observed (treated − control)</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-accent leading-none">
                    {inc.accuracy_pct != null ? <AnimatedNumber value={inc.accuracy_pct} format={(n) => `${n.toFixed(0)}%`} /> : "—"}
                  </p>
                  <p className="text-[11px] text-gray-500 mt-1.5">Incrementality accuracy</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800 dark:text-gray-100 leading-none">
                    {analysis.validation.cell_mae_pp != null ? `${analysis.validation.cell_mae_pp.toFixed(1)}pp` : "—"}
                  </p>
                  <p className="text-[11px] text-gray-500 mt-1.5">Per-cell mean abs. error</p>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-3">
                Measured on a randomized {analysis.model.n_test.toLocaleString("en-IN")}-row holdout the model never trained on — real incrementality, the gold standard of marketing measurement.
              </p>
            </motion.div>
          )}

          {/* Uplift decile chart */}
          <motion.div variants={fadeUp} className={`${CARD} p-4`}>
            <div className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Does the model rank persuadability?</div>
            <p className="text-[11px] text-gray-400 dark:text-gray-500 mb-2">
              Holdout customers bucketed by predicted uplift (decile 1 = most persuadable). If the model is right, the
              <span className="text-accent"> predicted line</span> and the <span className="text-accent2">observed lift bars</span> both fall left-to-right.
            </p>
            <DecileChart
              predicted={analysis.validation.deciles.map((d) => d.avg_pred_uplift)}
              observed={analysis.validation.deciles.map((d) => d.obs_uplift)}
              height={240}
            />
          </motion.div>

          {/* Per-cell table */}
          <motion.div variants={fadeUp} className={`${CARD} p-4`}>
            <div className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">Per segment × treatment — predicted vs observed lift</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400">
                    <th className="py-1.5">Segment</th><th>Treatment</th>
                    <th className="text-right">Treated n</th>
                    <th className="text-right">Predicted lift</th><th className="text-right">Observed lift</th><th className="text-right">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.validation.cells.map((c, i) => (
                    <tr key={i} className="border-t border-gray-100 dark:border-gray-700/50">
                      <td className="py-2 text-gray-700 dark:text-gray-200">{c.segment}</td>
                      <td className="text-gray-500 dark:text-gray-400">{c.treatment}</td>
                      <td className="text-right font-mono text-gray-500">{c.n_treated.toLocaleString("en-IN")}</td>
                      <td className="text-right font-mono text-accent2">{c.pred_rel_lift != null ? `${(c.pred_rel_lift * 100).toFixed(0)}%` : "—"}</td>
                      <td className="text-right font-mono text-gray-700 dark:text-gray-200">{c.obs_rel_lift != null ? `${(c.obs_rel_lift * 100).toFixed(0)}%` : "n/a"}</td>
                      <td className={`text-right font-mono ${c.abs_error_pp != null && c.abs_error_pp < 4 ? "text-accent" : "text-amber-500"}`}>
                        {c.abs_error_pp != null ? `${c.abs_error_pp.toFixed(1)}pp` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          {/* Spend plan on your data */}
          {plan && (
            <motion.div variants={fadeUp} className="space-y-4">
              <div className={`${CARD} p-4`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400">Optimized spend plan on your data</span>
                  <span className="font-mono font-bold text-lg text-gray-800 dark:text-gray-100">{inr(budget)}</span>
                </div>
                <input
                  type="range" min={0} max={maxBudget} step={Math.max(1, Math.round(maxBudget / 100))}
                  value={budget} onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full accent-violet-500"
                />
                <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                  <span>₹0</span>
                  <span>saturation ≈ {inrC(plan.max_useful_budget)}</span>
                  <span>{inrC(maxBudget)}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "Allocated spend", value: plan.spend, c: "#ffb600", fmt: inr },
                  { label: "Predicted incremental revenue", value: plan.pred_incr_revenue, c: "#34e0a1", fmt: inr },
                  { label: "Blended ROI", value: plan.blended_roi, c: "#34e0a1", fmt: (n: number) => `${n.toFixed(1)}×` },
                  { label: "Incremental conversions", value: plan.pred_incr_conversions, c: "#ffb600", fmt: (n: number) => `+${Math.round(n).toLocaleString("en-IN")}` },
                ].map((m) => (
                  <div key={m.label} className={`${CARD} p-3.5`}>
                    <p className="text-2xl font-bold leading-none" style={{ color: m.c }}><AnimatedNumber value={m.value} format={m.fmt} /></p>
                    <p className="text-[11px] text-gray-500 mt-1.5">{m.label}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
                <div className={`${CARD} p-4`}>
                  <div className="text-[11px] uppercase tracking-wider text-gray-500 mb-3">Allocation by segment × treatment</div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-400">
                        <th className="py-1.5">Segment</th><th>Treatment</th>
                        <th className="text-right">Reach</th><th className="text-right">Cost</th><th className="text-right">Pred. revenue</th><th className="text-right">ROI</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.plan.map((p, i) => (
                        <tr key={i} className="border-t border-gray-100 dark:border-gray-700/50">
                          <td className="py-2 text-gray-700 dark:text-gray-200">{p.segment_label}</td>
                          <td className="text-gray-500 dark:text-gray-400">{p.intervention_label}</td>
                          <td className="text-right font-mono text-gray-500">{p.reach_funded.toLocaleString("en-IN")}</td>
                          <td className="text-right font-mono text-gray-500">{inr(p.cost)}</td>
                          <td className="text-right font-mono text-accent">{inr(p.pred_incr_revenue)}</td>
                          <td className="text-right font-mono text-gray-500">{p.roi}×</td>
                        </tr>
                      ))}
                      {plan.plan.length === 0 && <tr><td colSpan={6} className="py-3 text-gray-500 text-center">Increase the budget to fund a plan.</td></tr>}
                    </tbody>
                  </table>
                </div>

                <div className="space-y-4">
                  <div className={`${CARD} p-4`}>
                    <div className="text-[11px] uppercase tracking-wider text-gray-500 mb-1">Budget efficiency</div>
                    <p className="text-[11px] text-gray-400 mb-2">Predicted incremental revenue vs. budget — flattens at saturation.</p>
                    <Curve curve={plan.curve} budget={budget} />
                  </div>
                  {plan.baselines.uplift_vs_even_pct != null && (
                    <div className={`${CARD} p-4`}>
                      <div className="text-[11px] uppercase tracking-wider text-gray-500 mb-2">vs. naive allocation</div>
                      <p className="text-sm text-gray-700 dark:text-gray-200">
                        <span className="text-accent font-semibold text-lg">+{plan.baselines.uplift_vs_even_pct}%</span> more revenue than an even split, same budget.
                      </p>
                      <p className="text-[11px] text-gray-400 mt-1">+{inr(plan.baselines.uplift_vs_even_abs)} from ROI-ranked targeting.</p>
                    </div>
                  )}
                </div>
              </div>

              <p className="text-[11px] text-gray-400 dark:text-gray-500 flex items-center gap-1.5">
                <Check size={13} className="text-accent" />
                AOV {inr(analysis.aov)} ({analysis.aov_source}) · contact costs {analysis.cost_source} · plan projected onto your uploaded population.
              </p>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}
