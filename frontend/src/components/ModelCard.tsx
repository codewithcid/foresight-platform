import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Meta, ModelCardData, Qini, getModelCard, getQini } from "../api";
import { fadeUp, stagger } from "../ui/motion";

function QiniChart({ q }: { q: Qini }) {
  const w = 560, h = 210, pad = 28;
  const X = (f: number) => pad + f * (w - 2 * pad);
  const Y = (v: number) => h - pad - v * (h - 2 * pad);
  const fwd = q.curve.map((c) => `${X(c.frac).toFixed(1)},${Y(c.model).toFixed(1)}`);
  const back = q.curve.slice().reverse().map((c) => `${X(c.frac).toFixed(1)},${Y(c.random).toFixed(1)}`);
  const area = `M ${fwd.join(" L ")} L ${back.join(" L ")} Z`;
  const line = `M ${fwd.join(" L ")}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      <defs>
        <linearGradient id="qfill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#34e0a1" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#34e0a1" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* frame */}
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="#334155" strokeWidth="1" />
      <line x1={pad} y1={pad} x2={pad} y2={h - pad} stroke="#334155" strokeWidth="1" />
      {/* random diagonal */}
      <line x1={X(0)} y1={Y(0)} x2={X(1)} y2={Y(1)} stroke="#64748b" strokeWidth="1.5" strokeDasharray="5 4" />
      {/* model lift area + line */}
      <path d={area} fill="url(#qfill)" />
      <motion.path d={line} fill="none" stroke="#34e0a1" strokeWidth="2.5"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.9 }} />
      <text x={X(0.5)} y={h - 8} textAnchor="middle" className="fill-slate-400" fontSize="10">% of customers targeted (ranked by predicted uplift)</text>
      <text x={X(0.62)} y={Y(0.78)} className="fill-accent" fontSize="10">Foresight ranking</text>
      <text x={X(0.7)} y={Y(0.58)} className="fill-slate-500" fontSize="10">random</text>
    </svg>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <motion.div variants={fadeUp} className="rounded-2xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">{title}</div>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="text-[13px] text-slate-600 dark:text-slate-300 leading-snug pl-3 relative">
            <span className="absolute left-0 text-accent2">·</span>{it}
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

export default function ModelCard({ meta }: { meta: Meta | null }) {
  const [card, setCard] = useState<ModelCardData | null>(null);
  const [qini, setQini] = useState<Qini | null>(null);
  const [intervention, setIntervention] = useState("cart_recovery_push");

  useEffect(() => { getModelCard().then(setCard).catch(() => {}); }, []);
  useEffect(() => { getQini(intervention).then(setQini).catch(() => {}); }, [intervention]);

  if (!card) return <p className="text-sm text-slate-500 animate-pulse">Loading model card…</p>;

  return (
    <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-4">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2">
          {card.name}
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/30">model card · v{card.version}</span>
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{card.objective}</p>
      </div>

      {/* Metrics strip */}
      <motion.div variants={stagger} className="grid grid-cols-3 gap-3">
        {[
          ["Validation MAE", `${card.metrics.cell_mae_pp}pp`, "predicted vs actual lift"],
          ["Mean Qini (AUUC)", card.metrics.mean_qini.toFixed(3), "uplift ranking quality"],
          ["Held-out cells", String(card.metrics.n_validation_cells), "segment × intervention"],
        ].map(([l, v, s]) => (
          <motion.div key={l} variants={fadeUp} className="rounded-2xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-3.5">
            <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 leading-none">{v}</p>
            <p className="text-[11px] text-slate-500 mt-1.5">{l}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{s}</p>
          </motion.div>
        ))}
      </motion.div>

      {/* Qini curve */}
      <motion.div variants={fadeUp} className="rounded-2xl border border-slate-200 dark:border-line bg-white dark:bg-panel p-4">
        <div className="flex items-center justify-between mb-1">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Qini / uplift curve</div>
          <select value={intervention} onChange={(e) => setIntervention(e.target.value)}
            className="bg-white dark:bg-ink border border-slate-300 dark:border-line rounded-md text-xs px-2 py-1 text-slate-700 dark:text-slate-200">
            {meta?.interventions.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
          </select>
        </div>
        <p className="text-[11px] text-slate-400 mb-2">
          {qini ? <>Targeting by predicted uplift captures incremental conversions far faster than random — Qini coefficient <span className="text-accent font-semibold">{qini.qini.toFixed(3)}</span> (higher = better ranking).</> : "…"}
        </p>
        {qini && <QiniChart q={qini} />}
      </motion.div>

      {/* Card sections */}
      <motion.div variants={stagger} className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <ListCard title="How it works" items={[card.model_type, `Library: ${card.library}`, `Features: ${card.features.join(", ")}`, card.training_data]} />
        <ListCard title="Validation" items={card.validation} />
        <ListCard title="Assumptions" items={card.assumptions} />
        <ListCard title="Limitations" items={card.limitations} />
        <ListCard title="Responsible AI" items={card.responsible_ai} />
      </motion.div>
    </motion.div>
  );
}
