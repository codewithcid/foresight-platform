import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Calibration, LedgerEntry, Meta, connectFeed, getCalibration, getDashboardBrief, getExplain, getLedger,
  simPause, simSpeed, simStart,
} from "../api";
import { AnimatedNumber } from "../ui/ui";
import { stagger } from "../ui/motion";
import {
  Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle, MetricCard,
} from "../ui/dash";
import DoughnutChart from "../charts/DoughnutChart";
import TrendLineChart from "../charts/TrendLineChart";
import { Bolt, Check, Mail, Megaphone, MessageSquare, Rupee, Smartphone, StopCircle, Target, TrendUp } from "./Icons";

function pct(x: number | null | undefined) {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(1)}%`;
}
function usd(x: number | null | undefined) {
  if (x === null || x === undefined) return "—";
  return `₹${x.toFixed(2)}`;
}

const CHANNEL_ICON: Record<string, JSX.Element> = {
  email: <Mail size={14} />, sms: <MessageSquare size={14} />, app_push: <Smartphone size={14} />, paid_social: <Megaphone size={14} />,
};

const STATUS: Record<string, { ring: string; tone: "default" | "outline" | "success"; label: string }> = {
  acted: { ring: "ring-primary/40", tone: "default", label: "Acted" },
  held: { ring: "ring-foreground/10", tone: "outline", label: "Held" },
  proven: { ring: "ring-success/40", tone: "success", label: "Proven" },
};

function EntryRow({ e }: { e: LedgerEntry }) {
  const isHold = e.status === "held";
  const error = e.error;
  const errOk = error !== null && error !== undefined && error < 0.08;
  const [explain, setExplain] = useState<{ factors: Record<string, any>; narrative: string; source: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const s = STATUS[e.status] ?? STATUS.held;

  async function toggleExplain() {
    if (explain) { setExplain(null); return; }
    setLoading(true);
    const res = await getExplain(e.id);
    setExplain(res);
    setLoading(false);
  }

  return (
    <div className={`rounded-lg ring-1 ${s.ring} bg-muted/30 p-3.5 transition-colors hover:bg-muted/50`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-medium text-foreground truncate">{e.first_name}</span>
          <span className="text-xs text-muted-foreground truncate">{e.segment}</span>
          <Badge tone={s.tone}>{s.label}</Badge>
          {e.occasion_key && <Badge tone="outline">{e.occasion_key}</Badge>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {e.channel && <span className="text-muted-foreground" title={e.channel}>{CHANNEL_ICON[e.channel]}</span>}
          <button onClick={toggleExplain} className="text-[10px] text-primary border border-primary/30 rounded-full px-2 py-0.5 hover:bg-primary/10 transition-colors">
            {loading ? "…" : explain ? "hide" : "explain"}
          </button>
        </div>
      </div>

      {isHold ? (
        <p className="text-sm text-muted-foreground mt-1.5">{e.reason}</p>
      ) : (
        <>
          <p className="text-sm text-card-foreground/90 mt-1.5">
            <span className="text-primary font-medium">{e.intervention_label}</span> · predicted{" "}
            <span className="font-semibold">{pct(e.predicted_rel_lift)}</span> lift · {usd(e.predicted_revenue)} rev ·
            cost {usd(e.cost)}
            {e.product_name && <span className="text-muted-foreground"> · re: {e.product_name}</span>}
          </p>
          {e.message && (
            <p className="text-xs text-muted-foreground mt-1 italic border-l-2 border-border pl-2">
              "{e.message}" <span className="text-muted-foreground/60">({e.message_source})</span>
            </p>
          )}
          <div className="mt-2">
            {e.actual_rel_lift === null ? (
              <span className="text-xs text-muted-foreground">resolving…</span>
            ) : (
              <div>
                <div className="flex items-center justify-between text-[11px] mb-1">
                  <span className="text-muted-foreground">predicted {pct(e.predicted_rel_lift)}</span>
                  <span className={errOk ? "text-success" : "text-amber-500 dark:text-amber-400"}>
                    actual {pct(e.actual_rel_lift)} · error {((error ?? 0) * 100).toFixed(1)}pp {errOk ? "(on target)" : "(correcting)"}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-foreground/[0.06] relative overflow-hidden">
                  <div
                    className="absolute top-0 h-full w-0.5 bg-muted-foreground"
                    style={{ left: `${Math.min(100, Math.max(0, (e.predicted_rel_lift ?? 0) * 150))}%` }}
                  />
                  <div
                    className={`h-full rounded-full ${errOk ? "bg-success" : "bg-amber-400"}`}
                    style={{ width: `${Math.min(100, Math.max(0, (e.actual_rel_lift ?? 0) * 150))}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {explain && (
        <div className="mt-2.5 pt-2.5 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2">{explain.narrative} <span className="text-muted-foreground/60">({explain.source})</span></p>
          <div className="grid grid-cols-2 gap-1 text-[11px]">
            {Object.entries(explain.factors).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2 border border-border rounded px-1.5 py-0.5">
                <span className="text-muted-foreground">{k.replace(/_/g, " ")}</span>
                <span className="text-card-foreground/80">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HBar({ label, value, max, suffix }: { label: string; value: number; max: number; suffix?: string }) {
  const pctW = Math.min(100, Math.max(0, (value / max) * 100));
  const neutral = Math.abs(value - 1) < 0.03;
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground truncate">{label}</span>
        <span className={`tabular-nums font-medium ${neutral ? "text-muted-foreground" : value > 1 ? "text-success" : "text-amber-500 dark:text-amber-400"}`}>
          {value.toFixed(2)}{suffix}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-foreground/[0.06] overflow-hidden">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pctW}%` }} />
      </div>
    </div>
  );
}

export default function MissionControl({ meta }: { meta: Meta | null }) {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [cal, setCal] = useState<Calibration | null>(null);
  const [running, setRunning] = useState(true);
  const [speed, setSpeedState] = useState(4);
  const [brief, setBrief] = useState<{ text: string; model: string } | null>(null);

  useEffect(() => {
    getDashboardBrief().then(setBrief).catch(() => {});
    getLedger(60).then((d) => {
      setEntries(d.entries);
      setCal(d.calibration);
    });
    const ws = connectFeed((payload) => {
      if (payload.type === "backlog") {
        setEntries(payload.entries);
        setCal((prev) => ({ ...(prev ?? {}), ...payload.calibration }));
        getCalibration().then(setCal);
      } else if (payload.type === "decision") {
        setEntries((prev) => [payload.entry, ...prev].slice(0, 80));
        getCalibration().then(setCal);
      } else if (payload.type === "resolution") {
        setEntries((prev) => prev.map((e) => (e.id === payload.entry.id ? payload.entry : e)));
        setCal((prev) => (prev ? { ...prev, ...payload.calibration } : payload.calibration));
      }
    });
    const poll = setInterval(() => getCalibration().then(setCal), 6000);
    return () => { ws.close(); clearInterval(poll); };
  }, []);

  const resolvedErrors = entries
    .filter((e) => e.error !== null && e.error !== undefined)
    .slice(0, 20)
    .reverse()
    .map((e) => (e.error as number) * 100);

  const acted = cal?.acted ?? 0;
  const held = cal?.held ?? 0;
  const total = acted + held;
  const actedShare = total ? Math.round((acted / total) * 100) : 0;
  const maeOk = cal?.mae != null && cal.mae < 0.08;

  const donutData = {
    labels: ["Acted", "Held"],
    datasets: [
      {
        data: [acted, held],
        backgroundColor: ["#ffb600", "#3b4252"],
        hoverBackgroundColor: ["#e0a200", "#4a5263"],
        borderWidth: 0,
      },
    ],
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Live situation brief */}
      {brief && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
          className="rounded-xl ring-1 ring-primary/30 bg-linear-to-r from-primary/[0.08] to-card p-4"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.14em] text-primary font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" /> Live situation brief
            </span>
            <span className="text-[10px] font-mono text-muted-foreground">{brief.model}</span>
          </div>
          <p className="text-sm text-card-foreground/90 leading-relaxed">{brief.text}</p>
        </motion.div>
      )}

      {/* Metric cards */}
      <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <MetricCard
          icon={<Bolt size={16} />} label="Decisions acted on"
          value={<AnimatedNumber value={acted} format={(n) => String(Math.round(n))} />}
          badge={total ? <Badge tone="default">{actedShare}%</Badge> : undefined}
          sub={total ? `of ${total} evaluated` : "awaiting events"}
        />
        <MetricCard
          icon={<StopCircle size={16} />} label="Held by guardrails"
          value={<AnimatedNumber value={held} format={(n) => String(Math.round(n))} />}
          sub="below threshold / capped"
        />
        <MetricCard
          icon={<Target size={16} />} label="Calibration error"
          value={cal?.mae != null ? <AnimatedNumber value={cal.mae * 100} format={(n) => `${n.toFixed(1)}pp`} /> : "—"}
          badge={cal?.mae != null ? <Badge tone={maeOk ? "success" : "warning"}>{maeOk ? "on target" : "correcting"}</Badge> : undefined}
          sub="predicted vs. actual, mean abs."
        />
        <MetricCard
          icon={<Rupee size={16} />} label="Spend so far"
          value={<AnimatedNumber value={cal?.total_spent ?? 0} format={usd} />}
          sub="live, against daily cap"
        />
        <MetricCard
          icon={<TrendUp size={16} />} label="Projected revenue"
          value={<AnimatedNumber value={cal?.total_projected_revenue ?? 0} format={usd} />}
          badge={<Badge tone="success">incremental</Badge>}
        />
      </motion.div>

      {/* Hero: calibration trend + acted/held donut */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
        <Card>
          <CardHeaderRow>
            <div className="grid gap-1">
              <CardTitle>Calibration — predicted vs. actual</CardTitle>
              <CardDescription>Prediction error on each resolved decision (percentage points). Lower is better.</CardDescription>
            </div>
            <Badge tone={maeOk ? "success" : "warning"}>{maeOk ? "On target" : "Self-correcting"}</Badge>
          </CardHeaderRow>
          <CardContent>
            {resolvedErrors.length > 1 ? (
              <TrendLineChart values={resolvedErrors} color="#ffb600" height={232} formatY={(n) => `${n.toFixed(1)}pp`} />
            ) : (
              <div className="h-[232px] grid place-items-center text-sm text-muted-foreground">Waiting for the first resolved outcomes…</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeaderRow>
            <div className="grid gap-1">
              <CardTitle>Acted vs. held</CardTitle>
              <CardDescription>{total} decisions evaluated</CardDescription>
            </div>
          </CardHeaderRow>
          <CardContent>
            <DoughnutChart data={donutData} height={180} />
            <div className="flex items-center justify-center gap-4 mt-2 text-xs">
              <span className="flex items-center gap-1.5 text-muted-foreground"><span className="h-2.5 w-2.5 rounded-sm bg-primary" /> Acted {acted}</span>
              <span className="flex items-center gap-1.5 text-muted-foreground"><span className="h-2.5 w-2.5 rounded-sm bg-[#3b4252]" /> Held {held}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live feed + side cards */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
        <Card>
          <CardHeaderRow>
            <div className="grid gap-1">
              <CardTitle>Live agent feed</CardTitle>
              <CardDescription>Each decision the agent makes, with its predicted-vs-actual proof.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={async () => { if (running) { await simPause(); setRunning(false); } else { await simStart(); setRunning(true); } }}
                className="text-xs px-3 py-1.5 rounded-md border border-border bg-muted/40 hover:bg-muted text-card-foreground transition-colors"
              >
                {running ? "Pause" : "Resume"}
              </button>
              {[2, 4, 8].map((sp) => (
                <button
                  key={sp}
                  onClick={async () => { await simSpeed(sp); setSpeedState(sp); }}
                  className={`text-xs px-2.5 py-1.5 rounded-md border transition-colors ${speed === sp ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground hover:bg-muted/50"}`}
                >
                  {sp}x
                </button>
              ))}
            </div>
          </CardHeaderRow>
          <CardContent>
            <div className="space-y-2.5 max-h-[70vh] overflow-y-auto pr-1 -mr-1">
              {entries.map((e) => (
                <EntryRow key={e.id} e={e} />
              ))}
              {entries.length === 0 && <p className="text-sm text-muted-foreground">Waiting for the first event…</p>}
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Self-correction</CardTitle>
              <CardDescription className="text-xs">
                Live multiplier on each intervention's predicted lift, nudged by every resolved outcome — 1.00× is neutral.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {cal?.correction_factors && Object.entries(cal.correction_factors).map(([k, v]) => (
                <HBar key={k} label={meta?.interventions.find((i) => i.key === k)?.label ?? k} value={v} max={2} suffix="×" />
              ))}
              {!cal?.correction_factors && <p className="text-xs text-muted-foreground">Waiting for the first resolved outcome…</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Guardrails active</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-xs text-card-foreground/80 space-y-2">
                <li className="flex items-center gap-1.5"><Check size={13} className="text-success" /> Max {meta?.guardrails.max_actions_per_day} actions / customer</li>
                <li className="flex items-center gap-1.5"><Check size={13} className="text-success" /> ₹{meta?.guardrails.daily_budget_usd} daily budget cap</li>
                <li className="flex items-center gap-1.5"><Check size={13} className="text-success" /> Hold below {((meta?.guardrails.min_rel_lift_to_act ?? 0) * 100).toFixed(0)}% predicted lift</li>
                <li className="flex items-center gap-1.5"><Check size={13} className="text-success" /> Brand-safety filter on drafted copy</li>
              </ul>
              <p className="text-[11px] text-muted-foreground mt-3 pt-2 border-t border-border">LLM mode: <span className="text-primary">{meta?.llm_mode}</span></p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
