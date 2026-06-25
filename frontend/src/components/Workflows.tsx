import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Run, RunStep, WorkflowMeta, approveRun, connectFeed, getRun, getRuns, getWorkflowMeta,
  rejectRun, runAutopilot, startWorkflow,
} from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle } from "../ui/dash";
import { useNav } from "../nav";

const AGENT: Record<string, string> = {
  trigger: "Sensor", predict: "Strategist", guardrail: "Guardrail", generate: "Execution",
  pretest: "Pre-test", approve: "Human", deliver: "Execution", prove: "Critic",
};

/** Types text out character-by-character for an "agent thinking" feel. */
function Typewriter({ text, speed = 14 }: { text: string; speed?: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0);
    if (!text) return;
    let i = 0;
    const id = setInterval(() => { i += 2; setN(i); if (i >= text.length) clearInterval(id); }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return <>{text.slice(0, n)}</>;
}

const STATUS_STYLE: Record<string, { ring: string; dot: string; text: string }> = {
  pending: { ring: "ring-foreground/10", dot: "bg-muted-foreground/40", text: "text-muted-foreground" },
  running: { ring: "ring-primary/50", dot: "bg-primary animate-pulse", text: "text-primary" },
  awaiting: { ring: "ring-primary/60", dot: "bg-primary animate-pulse", text: "text-primary" },
  done: { ring: "ring-success/40", dot: "bg-success", text: "text-success" },
  held: { ring: "ring-amber-500/40", dot: "bg-amber-400", text: "text-amber-500 dark:text-amber-400" },
  rejected: { ring: "ring-destructive/40", dot: "bg-destructive", text: "text-destructive" },
  failed: { ring: "ring-destructive/40", dot: "bg-destructive", text: "text-destructive" },
};

function fmtVal(k: string, v: any): string {
  if (typeof v === "number") {
    if (k.includes("revenue") || k.includes("cost")) return "₹" + Math.round(v).toLocaleString("en-IN");
    if (k.includes("pct") || k.includes("_pp")) return v + (k.includes("_pp") ? "pp" : "%");
    return v.toLocaleString("en-IN");
  }
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "boolean") return v ? "yes" : "no";
  return String(v);
}

function StepNode({ step, last }: { step: RunStep; last: boolean }) {
  const st = STATUS_STYLE[step.status] || STATUS_STYLE.pending;
  const out = step.output || {};
  const reasoning: string = out.reasoning || "";
  const entries = Object.entries(out).filter(([k]) => k !== "copy" && k !== "reasoning").slice(0, 3);
  const active = step.status === "running" || step.status === "awaiting";
  return (
    <div className="flex items-stretch">
      <div className={`rounded-xl ring-1 ${st.ring} bg-card p-3 w-[190px] shrink-0`}>
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground/70">{AGENT[step.name] || "Agent"}</span>
          <span className={`h-2 w-2 rounded-full ${st.dot}`} />
        </div>
        <div className="font-grotesk font-bold text-sm mt-0.5">{step.label}</div>
        <div className={`text-[10px] uppercase tracking-wider ${st.text}`}>{step.status}</div>
        {reasoning && (
          <p className="text-[10px] text-card-foreground/70 leading-snug mt-1.5 min-h-[2.4em]">
            {active ? "…" : <Typewriter text={reasoning} />}
          </p>
        )}
        {entries.length > 0 && (
          <div className="mt-1.5 space-y-0.5 border-t border-border/60 pt-1.5">
            {entries.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2 text-[10px]">
                <span className="text-muted-foreground truncate">{k.replace(/_/g, " ")}</span>
                <span className="text-card-foreground/80 tabular-nums shrink-0">{fmtVal(k, v)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {!last && <div className="self-center px-1 text-muted-foreground/50">→</div>}
    </div>
  );
}

export default function Workflows() {
  const [meta, setMeta] = useState<WorkflowMeta | null>(null);
  const [form, setForm] = useState({ workflow: "", segment: "", intervention: "", channel: "", test_recipient: "" });
  const [run, setRun] = useState<Run | null>(null);
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState(false);
  const [carried, setCarried] = useState<{ copy?: string; from?: string }>({});
  const [apLog, setApLog] = useState<{ phase: string; text: string; plan?: any[] }[]>([]);
  const [apBusy, setApBusy] = useState(false);
  const runIdRef = useRef<number | null>(null);
  const { handoff, clearHandoff } = useNav();

  // A surface handed us a prefilled campaign (e.g. Creative Pre-Flight's winner).
  useEffect(() => {
    if (!handoff) return;
    setForm((f) => ({
      ...f, workflow: "",
      segment: handoff.segment || f.segment,
      intervention: handoff.intervention || f.intervention,
      channel: handoff.channel || f.channel,
    }));
    if (handoff.copy) setCarried({ copy: handoff.copy, from: handoff.from });
    clearHandoff();
  }, [handoff]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    getWorkflowMeta().then((m) => {
      setMeta(m);
      const t = m.templates[0];
      if (t && !handoff) setForm({ workflow: t.id, segment: t.segment, intervention: t.intervention, channel: t.channel, test_recipient: "" });
    });
    refreshRuns();
    const ws = connectFeed((p) => {
      if (p.type === "workflow_step" && p.run_id === runIdRef.current) {
        setSteps((prev) => prev.map((s) => (s.name === p.step.name ? { ...s, status: p.step.status, output: p.step.output } : s)));
      } else if (p.type === "autopilot") {
        setApLog((l) => [...l, { phase: p.phase, text: p.text, plan: p.plan }]);
      }
    });
    return () => ws.close();
  }, []);

  async function autopilot() {
    setApBusy(true); setApLog([]);
    try { await runAutopilot("maximize incremental ROI within budget"); refreshRuns(); }
    finally { setApBusy(false); }
  }

  function refreshRuns() { getRuns(8).then((d) => setRuns(d.runs)); }

  function pickTemplate(id: string) {
    const t = meta?.templates.find((x) => x.id === id);
    if (t) { setForm({ workflow: t.id, segment: t.segment, intervention: t.intervention, channel: t.channel, test_recipient: form.test_recipient }); setCarried({}); }
  }

  async function launch() {
    if (!auto && (!form.segment || !form.intervention)) return;
    setBusy(true); setSteps([]); setRun(null);
    try {
      const r = await startWorkflow({ ...form, auto, copy: carried.copy, angle: carried.copy ? "approved" : undefined });
      runIdRef.current = r.id;
      setRun(r); setSteps(r.steps);
      refreshRuns();
    } finally { setBusy(false); }
  }

  async function approve() {
    if (!run) return;
    setBusy(true);
    try {
      const r = await approveRun(run.id, form.test_recipient || undefined);
      setRun(r); setSteps(r.steps); refreshRuns();
    } finally { setBusy(false); }
  }
  async function reject() {
    if (!run) return;
    const r = await rejectRun(run.id); setRun(r); setSteps(r.steps); refreshRuns();
  }

  const awaiting = run?.status === "awaiting_approval";
  const approveStep = steps.find((s) => s.name === "approve");
  const proveStep = steps.find((s) => s.name === "prove");
  const channelLive = meta?.channels.includes(form.channel);

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground max-w-[75ch]">
        One causal engine, orchestrated end to end: predict who a message will move, generate &amp; pre-test the
        creative, get human sign-off, deliver on a real channel, then prove the lift — predicted vs. actual.
      </p>

      {/* Builder */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">New run</CardTitle>
          <CardDescription className="text-xs">Start from a template, or configure the campaign.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            {meta?.templates.map((t) => (
              <button key={t.id} onClick={() => pickTemplate(t.id)}
                className={`text-left rounded-lg ring-1 px-3 py-2 transition-colors ${form.workflow === t.id ? "ring-primary bg-primary/10" : "ring-foreground/10 hover:bg-muted/50"}`}>
                <div className="font-grotesk font-bold text-sm">{t.label}</div>
                <div className="text-[11px] text-muted-foreground max-w-[26ch]">{t.description}</div>
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 text-sm cursor-pointer w-fit">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="accent-violet-500" />
            <span className="font-medium">Let the Strategist decide</span>
            <span className="text-[11px] text-muted-foreground">— the agent ranks every segment × action and picks the highest-ROI one itself</span>
          </label>

          <div className={`grid grid-cols-2 md:grid-cols-4 gap-3 ${auto ? "opacity-40 pointer-events-none" : ""}`}>
            <label className="text-xs text-muted-foreground">Segment
              <select value={form.segment} disabled={auto} onChange={(e) => setForm({ ...form, segment: e.target.value })} className="form-select w-full mt-1 text-sm">
                {meta?.segments.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
              </select>
            </label>
            <label className="text-xs text-muted-foreground">Action
              <select value={form.intervention} disabled={auto} onChange={(e) => setForm({ ...form, intervention: e.target.value })} className="form-select w-full mt-1 text-sm">
                {meta?.interventions.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
              </select>
            </label>
            <label className="text-xs text-muted-foreground">Channel
              <select value={form.channel} disabled={auto} onChange={(e) => setForm({ ...form, channel: e.target.value })} className="form-select w-full mt-1 text-sm">
                {["sms", "whatsapp", "email", "slack", "telegram"].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label className="text-xs text-muted-foreground">Test recipient (optional)
              <input value={form.test_recipient} disabled={auto} onChange={(e) => setForm({ ...form, test_recipient: e.target.value })} placeholder="+91XXXXXXXXXX" className="form-input w-full mt-1 text-sm" />
            </label>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button onClick={launch} disabled={busy}
              className="px-5 py-2.5 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
              {busy ? "Running…" : auto ? "Run — agent decides" : "Run workflow"}
            </button>
            <span className="text-[11px] text-muted-foreground">
              {auto ? "The Strategist will pick the segment, action & channel."
                    : <>Channel <b className="text-card-foreground/80">{form.channel}</b> {channelLive ? "· live" : "· not connected (proof still runs)"}</>}
              <span className="text-muted-foreground/60"> · first run can take ~30s (LLM warm-up)</span>
            </span>
          </div>
          {carried.copy && (
            <div className="rounded-lg ring-1 ring-success/40 bg-success/[0.08] p-3 text-xs">
              <div className="flex items-center gap-1.5 text-success font-semibold mb-1">
                <i className="ri-magic-line" /> Creative carried from {carried.from || "Pre-Flight"} — this run skips generation and ships it.
              </div>
              <span className="text-muted-foreground italic">"{carried.copy}"</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Autopilot */}
      <Card className="ring-primary/25">
        <CardHeaderRow>
          <div className="grid gap-1">
            <CardTitle className="text-sm flex items-center gap-2"><i className="ri-robot-2-line text-primary" /> Autopilot</CardTitle>
            <CardDescription className="text-xs">Give the agent a goal — it ranks every segment × action, then plans and runs the top campaigns autonomously, proving each on a holdout.</CardDescription>
          </div>
          <button onClick={autopilot} disabled={apBusy}
            className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
            <i className="ri-play-circle-line" /> {apBusy ? "Running…" : "Run Autopilot"}
          </button>
        </CardHeaderRow>
        {apLog.length > 0 && (
          <CardContent>
            <div className="rounded-lg bg-muted/30 ring-1 ring-foreground/10 p-3 font-mono text-xs space-y-1.5 max-h-72 overflow-y-auto">
              {apLog.map((e, i) => (
                <div key={i}>
                  <span className={
                    e.phase === "result" || e.phase === "done" ? "text-success"
                      : e.phase === "run" ? "text-primary" : "text-muted-foreground"
                  }>{e.phase === "done" ? "✓" : e.phase === "result" ? "✓" : "›"}</span>{" "}
                  <span className="text-card-foreground/90">{e.text}</span>
                  {e.plan && (
                    <ul className="mt-1 ml-4 space-y-0.5">
                      {e.plan.map((p: any, j: number) => (
                        <li key={j} className="text-muted-foreground">• {p.label} <span className="text-card-foreground/70">on {p.channel}</span> — ₹{Math.round(p.pred_incr_revenue).toLocaleString("en-IN")}, ROI {p.roi}×</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
              {apBusy && <div className="text-primary animate-pulse">▍ agent working…</div>}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Live graph */}
      {steps.length > 0 && (
        <Card>
          <CardHeaderRow>
            <div className="grid gap-1">
              <CardTitle className="text-sm">{run?.label} · run #{run?.id}</CardTitle>
              <CardDescription className="text-xs">Live execution trace</CardDescription>
            </div>
            <Badge tone={run?.status === "proven" ? "success" : run?.status === "rejected" || run?.status === "held" ? "warning" : "default"}>
              {run?.status}
            </Badge>
          </CardHeaderRow>
          <CardContent>
            <div className="flex flex-wrap gap-y-3 overflow-x-auto pb-1">
              {steps.map((s, i) => <StepNode key={s.name} step={s} last={i === steps.length - 1} />)}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval */}
      {awaiting && approveStep && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="ring-primary/40">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-primary animate-pulse" /> Approval needed</CardTitle>
              <CardDescription className="text-xs">The agent drafted, pre-tested, and is ready to send. Human sign-off required.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="rounded-lg bg-muted/40 ring-1 ring-foreground/10 p-3 text-sm italic">"{approveStep.output?.copy}"</div>
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span>Reach: <b className="text-card-foreground/80">{(approveStep.output?.reach ?? 0).toLocaleString("en-IN")}</b></span>
                <span>Predicted incremental revenue: <b className="text-success">₹{Math.round(approveStep.output?.predicted_incr_revenue ?? 0).toLocaleString("en-IN")}</b></span>
                {form.test_recipient && <span>Test send to: <b className="text-card-foreground/80">{form.test_recipient}</b></span>}
              </div>
              <div className="flex gap-2">
                <button onClick={approve} disabled={busy} className="px-4 py-2 rounded-md bg-success text-ink text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
                  {busy ? "Sending…" : "Approve & send"}
                </button>
                <button onClick={reject} disabled={busy} className="px-4 py-2 rounded-md ring-1 ring-foreground/15 text-sm font-medium hover:bg-muted/50 transition">Reject</button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Proof result */}
      {proveStep?.status === "done" && (
        <Card className="ring-success/30">
          <CardHeader><CardTitle className="text-sm">Proven — predicted vs. actual</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[["Predicted lift", proveStep.output.predicted_rel_lift_pct + "%"],
              ["Actual lift", proveStep.output.actual_rel_lift_pct + "%"],
              ["Error", proveStep.output.error_pp + "pp"],
              ["Actual incr. revenue", "₹" + Math.round(proveStep.output.actual_incr_revenue).toLocaleString("en-IN")]].map(([l, v]) => (
              <div key={l}>
                <div className="font-grotesk text-2xl font-bold tabular-nums">{v}</div>
                <div className="text-xs text-muted-foreground">{l}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* History */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Recent runs</CardTitle></CardHeader>
        <CardContent>
          {runs.length === 0 ? <p className="text-sm text-muted-foreground">No runs yet.</p> : (
            <div className="flex flex-col divide-y divide-border">
              {runs.map((r) => (
                <button key={r.id} onClick={() => getRun(r.id).then((full) => { runIdRef.current = full.id; setRun(full); setSteps(full.steps); })}
                  className="flex items-center gap-3 py-2.5 text-sm text-left hover:bg-muted/30 -mx-2 px-2 rounded transition-colors">
                  <span className="text-muted-foreground tabular-nums text-xs w-8">#{r.id}</span>
                  <span className="font-medium flex-1 truncate">{r.label}</span>
                  <span className="text-muted-foreground text-xs">{r.target}</span>
                  {r.summary?.error_pp != null && <span className="text-xs text-muted-foreground">err {r.summary.error_pp}pp</span>}
                  <Badge tone={r.status === "proven" ? "success" : r.status === "awaiting_approval" ? "default" : r.status === "rejected" || r.status === "held" ? "warning" : "outline"}>{r.status}</Badge>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
