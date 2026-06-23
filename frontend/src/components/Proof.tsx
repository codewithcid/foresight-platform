import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Calibration, Run, getCalibration, getRuns } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, MetricCard } from "../ui/dash";
import { stagger } from "../ui/motion";
import { AnimatedNumber } from "../ui/ui";
import { Activity, CheckDouble, Rupee, Target } from "./Icons";

const inr = (x: number) => "₹" + Math.round(x).toLocaleString("en-IN");

function PredVsActual({ pred, actual }: { pred: number; actual: number }) {
  const max = Math.max(pred, actual, 0.01) * 1.15;
  const bar = (v: number, cls: string) => (
    <div className="h-1.5 rounded-full bg-foreground/[0.06] overflow-hidden">
      <div className={`h-full rounded-full ${cls}`} style={{ width: `${Math.min(100, (v / max) * 100)}%` }} />
    </div>
  );
  return (
    <div className="grid gap-1 w-40">
      <div className="flex items-center gap-2"><span className="text-[10px] text-muted-foreground w-12">pred</span>{bar(pred, "bg-primary")}<span className="text-[10px] tabular-nums w-10 text-right">{(pred * 100).toFixed(1)}%</span></div>
      <div className="flex items-center gap-2"><span className="text-[10px] text-muted-foreground w-12">actual</span>{bar(actual, "bg-success")}<span className="text-[10px] tabular-nums w-10 text-right">{(actual * 100).toFixed(1)}%</span></div>
    </div>
  );
}

export default function Proof() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [cal, setCal] = useState<Calibration | null>(null);

  useEffect(() => {
    getRuns(50).then((d) => setRuns(d.runs));
    getCalibration().then(setCal);
    const t = setInterval(() => { getRuns(50).then((d) => setRuns(d.runs)); getCalibration().then(setCal); }, 8000);
    return () => clearInterval(t);
  }, []);

  const proven = runs.filter((r) => r.status === "proven" && r.summary?.actual_rel_lift != null);
  const meanErr = proven.length ? proven.reduce((a, r) => a + (r.summary.error_pp ?? 0), 0) / proven.length : null;
  const totalRev = proven.reduce((a, r) => a + (r.summary.pred_incr_revenue ?? 0), 0);

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground max-w-[75ch]">
        Every campaign Foresight runs is validated <b className="text-card-foreground/80">predicted vs. actual</b> on a
        held-out ground truth — success is quantified, not claimed. This is the proof spine behind Theme 2's
        "clear measures of success."
      </p>

      <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<CheckDouble size={16} />} label="Proven campaigns"
          value={<AnimatedNumber value={proven.length} format={(n) => String(Math.round(n))} />}
          badge={<Badge tone="success">validated</Badge>} sub="run end-to-end with proof" />
        <MetricCard icon={<Target size={16} />} label="Mean prediction error"
          value={meanErr != null ? <AnimatedNumber value={meanErr} format={(n) => `${n.toFixed(1)}pp`} /> : "—"}
          sub="predicted vs. actual lift" />
        <MetricCard icon={<Rupee size={16} />} label="Predicted incremental revenue"
          value={<AnimatedNumber value={totalRev} format={inr} />} sub="across proven runs" />
        <MetricCard icon={<Activity size={16} />} label="Live agent calibration"
          value={cal?.mae != null ? <AnimatedNumber value={cal.mae * 100} format={(n) => `${n.toFixed(1)}pp`} /> : "—"}
          sub={`${cal?.acted ?? 0} acted · ${cal?.held ?? 0} held`} />
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Campaign proof ledger</CardTitle>
          <CardDescription className="text-xs">Each proven workflow run, with predicted vs. actual lift and incremental revenue.</CardDescription>
        </CardHeader>
        <CardContent>
          {proven.length === 0 ? (
            <p className="text-sm text-muted-foreground">No proven runs yet — run a workflow and approve it to populate the proof ledger.</p>
          ) : (
            <div className="flex flex-col divide-y divide-border">
              <div className="hidden md:flex items-center gap-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                <span className="w-8">#</span><span className="flex-1">Campaign</span><span className="w-28">Channel · segment</span>
                <span className="w-40">Predicted vs. actual</span><span className="w-20 text-right">Error</span><span className="w-28 text-right">Incr. revenue</span>
              </div>
              {proven.map((r) => (
                <div key={r.id} className="flex flex-wrap md:flex-nowrap items-center gap-3 py-3 text-sm">
                  <span className="w-8 text-muted-foreground tabular-nums text-xs">#{r.id}</span>
                  <span className="flex-1 min-w-[10rem] font-medium truncate">{r.label}</span>
                  <span className="w-28 text-xs text-muted-foreground capitalize">{r.channel} · {r.target}</span>
                  <PredVsActual pred={r.summary.avg_rel_lift ?? 0} actual={r.summary.actual_rel_lift ?? 0} />
                  <span className="w-20 text-right text-xs"><Badge tone={(r.summary.error_pp ?? 99) < 15 ? "success" : "warning"}>{r.summary.error_pp}pp</Badge></span>
                  <span className="w-28 text-right text-sm tabular-nums text-success">{inr(r.summary.pred_incr_revenue ?? 0)}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
