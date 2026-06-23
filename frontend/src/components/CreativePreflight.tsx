import { useEffect, useState } from "react";
import {
  CreativeCalibration, CreativeProofEntry, Meta, Preflight,
  getCreativeLedger, runPreflight, shipCreative,
} from "../api";

export default function CreativePreflight({ meta }: { meta: Meta | null }) {
  const [intervention, setIntervention] = useState("sms_discount");
  const [segment, setSegment] = useState("bargain_hunter");
  const [data, setData] = useState<Preflight | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [shipped, setShipped] = useState<CreativeProofEntry | null>(null);
  const [shipping, setShipping] = useState(false);
  const [calib, setCalib] = useState<CreativeCalibration | null>(null);

  useEffect(() => { getCreativeLedger(1).then((d) => setCalib(d.calibration)).catch(() => {}); }, []);

  async function run() {
    setLoading(true); setErr(null); setData(null); setShipped(null);
    try {
      setData(await runPreflight(intervention, segment));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function shipWinner() {
    if (!data) return;
    const win = data.variants.find((v) => v.id === data.pretest.winner_id);
    if (!win) return;
    setShipping(true);
    try {
      const res = await shipCreative({
        intervention: data.intervention, segment: data.segment, variant_id: win.id,
        angle: win.angle, copy: win.copy, image_url: win.image_url,
        predicted_resonance: data.pretest.winner_score,
      });
      setShipped(res.entry);
      setCalib(res.calibration);
    } finally {
      setShipping(false);
    }
  }

  const pt = data?.pretest;
  const scoreOf = (id: string) => pt?.scores.find((s) => s.variant_id === id);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2">
          Creative Pre-Flight
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-accent2/15 text-accent2 border border-accent2/30">
            self-testing
          </span>
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Generate ad variants → test them on a synthetic shopper panel → ship the winner.
          Every creative is scored <span className="text-slate-700 dark:text-slate-200">before a rupee is spent</span>.
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3 p-4 rounded-xl border border-slate-200 dark:border-line bg-slate-50 dark:bg-panel">
        <label className="text-xs text-slate-500 dark:text-slate-400">
          Intervention
          <select value={intervention} onChange={(e) => setIntervention(e.target.value)}
            className="mt-1 block w-52 bg-white dark:bg-ink border border-slate-300 dark:border-line rounded-md text-sm px-2 py-1.5 text-slate-700 dark:text-slate-200">
            {meta?.interventions.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-500 dark:text-slate-400">
          Target segment
          <select value={segment} onChange={(e) => setSegment(e.target.value)}
            className="mt-1 block w-48 bg-white dark:bg-ink border border-slate-300 dark:border-line rounded-md text-sm px-2 py-1.5 text-slate-700 dark:text-slate-200">
            {meta?.segments.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </label>
        <button onClick={run} disabled={loading}
          className="px-4 py-2 rounded-md bg-accent2 text-ink text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition">
          {loading ? "Generating & testing…" : "Run pre-flight"}
        </button>
        {data?.occasion_theme && (
          <span className="ml-auto text-xs px-3 py-1.5 rounded-full border border-accent/30 bg-accent/10 text-accent">
            Occasion: {data.occasion_theme}
          </span>
        )}
      </div>

      {err && <div className="text-sm text-rose-500">Could not run pre-flight: {err}</div>}
      {loading && (
        <div className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">
          Writing copy variants, rendering AI ad images, and polling the synthetic panel…
        </div>
      )}

      {data && pt && (
        <>
          {/* Winner banner */}
          <div className="p-4 rounded-xl border border-accent/40 bg-accent/[0.07] flex flex-wrap items-center gap-x-6 gap-y-2">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-500">Pre-test winner</div>
              <div className="text-lg font-bold text-accent">
                {pt.winner_angle} · {pt.winner_score}/100
              </div>
            </div>
            <div className="text-sm text-slate-600 dark:text-slate-300">
              Beat the field by <span className="font-semibold">{pt.spread} pts</span> across a 3-persona panel
              <span className="text-slate-400"> · scoring: {pt.method === "ai" ? "Groq persona panel" : "heuristic fallback"}</span>
            </div>
            {!shipped && (
              <button onClick={shipWinner} disabled={shipping}
                className="ml-auto px-4 py-2 rounded-md bg-accent text-ink text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition">
                {shipping ? "Measuring…" : "Ship winner & measure →"}
              </button>
            )}
          </div>

          {/* Creative proof: predicted resonance vs actual engagement */}
          {shipped && (
            <div className="p-5 rounded-xl border border-accent2/40 bg-accent2/[0.06]">
              <div className="text-[11px] uppercase tracking-wider text-accent2 font-semibold mb-3">
                ✓ Creative proof — predicted vs actual
              </div>
              <div className="grid grid-cols-3 items-center gap-3 max-w-xl">
                <div className="rounded-lg border border-slate-200 dark:border-line bg-white dark:bg-panel p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Panel predicted</div>
                  <div className="text-2xl font-bold text-accent2 font-mono">{shipped.predicted_resonance}</div>
                </div>
                <div className="text-center text-slate-400 text-sm">
                  vs<div className="text-[10px] mt-0.5">Δ {shipped.error}pp</div>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-line bg-white dark:bg-panel p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">Actual engagement</div>
                  <div className="text-2xl font-bold text-slate-800 dark:text-white font-mono">{shipped.actual_engagement}</div>
                </div>
              </div>
              {calib?.accuracy != null && (
                <div className="mt-3 text-sm text-slate-600 dark:text-slate-300">
                  Creative model accuracy <span className="font-semibold text-accent">{calib.accuracy}%</span>
                  <span className="text-slate-400"> · MAE {calib.mae}pp over {calib.n} shipped creative{calib.n === 1 ? "" : "s"}</span>
                </div>
              )}
              {shipped.relayed_to && (
                <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  → Winning creative shipped to <span className="font-semibold">{shipped.relayed_to}</span> on WhatsApp —
                  <span className="text-slate-400"> the creative we tested is the creative we send.</span>
                </div>
              )}
            </div>
          )}

          {/* Variant cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.variants.map((v) => {
              const sc = scoreOf(v.id);
              const isWin = v.id === pt.winner_id;
              return (
                <div key={v.id}
                  className={`rounded-xl border overflow-hidden bg-white dark:bg-panel ${
                    isWin ? "border-accent ring-1 ring-accent/40" : "border-slate-200 dark:border-line"}`}>
                  <div className="relative aspect-[3/2] bg-slate-100 dark:bg-ink">
                    <div className="absolute inset-0 grid place-items-center text-[11px] text-slate-400 animate-pulse">
                      rendering AI ad image…
                    </div>
                    <img src={v.image_url} alt={v.angle} loading="lazy"
                      className="relative w-full h-full object-cover" />
                    {isWin && (
                      <span className="absolute top-2 left-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-accent text-ink">
                        Winner
                      </span>
                    )}
                    <span className="absolute top-2 right-2 text-[10px] px-2 py-0.5 rounded-full bg-black/55 text-white">
                      {v.angle}
                    </span>
                  </div>
                  <div className="p-3 space-y-2">
                    <div className="font-semibold text-sm text-slate-800 dark:text-slate-100">{v.headline}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{v.body}</div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-ink overflow-hidden">
                        <div className={`h-full ${isWin ? "bg-accent" : "bg-accent2"}`}
                          style={{ width: `${sc?.mean_score ?? 0}%` }} />
                      </div>
                      <span className="text-xs font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        {sc?.mean_score ?? "–"}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      copy: {v.copy_source === "ai" ? "Groq" : "template"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Synthetic panel detail */}
          <div className="rounded-xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-4">
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">Synthetic shopper panel</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400">
                    <th className="py-1.5 pr-4">Persona</th>
                    {data.variants.map((v) => (
                      <th key={v.id} className="py-1.5 px-3 text-center">{v.angle}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pt.personas.map((p) => (
                    <tr key={p.name} className="border-t border-slate-100 dark:border-line/50">
                      <td className="py-2 pr-4">
                        <div className="font-medium text-slate-700 dark:text-slate-200">{p.name}</div>
                        <div className="text-[11px] text-slate-400 max-w-[220px]">{p.blurb}</div>
                      </td>
                      {data.variants.map((v) => {
                        const cell = scoreOf(v.id)?.per_persona.find((x) => x.name === p.name);
                        const win = v.id === pt.winner_id;
                        return (
                          <td key={v.id} className="py-2 px-3 text-center align-top">
                            <div className={`font-mono font-semibold ${win ? "text-accent" : "text-slate-600 dark:text-slate-300"}`}>
                              {cell?.score ?? "–"}
                            </div>
                            <div className="text-[10px] text-slate-400 max-w-[150px] mx-auto leading-snug">{cell?.reaction}</div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
