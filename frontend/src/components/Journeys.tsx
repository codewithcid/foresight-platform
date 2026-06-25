import { useEffect, useRef, useState } from "react";
import { C360Event, Customer360, Journey, JourneyState, connectFeed, getCustomer360, getJourneys, respondJourney, startJourney } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle, MetricCard } from "../ui/dash";
import { Activity, Bolt, CheckDouble } from "./Icons";

const CH_ICON: Record<string, string> = {
  sms: "ri-message-2-line", whatsapp: "ri-whatsapp-line", email: "ri-mail-line",
  telegram: "ri-telegram-line", slack: "ri-slack-line",
};
const STATUS_TONE: Record<string, "default" | "success" | "warning" | "outline"> = {
  active: "default", converted: "success", exhausted: "warning",
};
const rel = (ts?: number) => {
  if (!ts) return "";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago` : `${Math.floor(s / 3600)}h ago`;
};

function Sequence({ j }: { j: Journey }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {j.steps.map((s, i) => {
        const sent = i <= j.step_idx;
        const current = i === j.step_idx && j.status === "active";
        const won = i === j.step_idx && j.status === "converted";
        const cls = won ? "bg-success/20 text-success ring-success/40"
          : current ? "bg-primary/15 text-primary ring-primary/50"
          : sent ? "bg-muted/60 text-muted-foreground ring-foreground/15"
          : "text-muted-foreground/50 ring-foreground/10";
        return (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <i className={`ri-arrow-right-line text-[11px] ${sent ? "text-primary/60" : "text-muted-foreground/30"}`} />}
            <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ring-1 ${cls}`}>
              <i className={CH_ICON[s.channel] || "ri-send-plane-line"} /> {s.channel}{won && " ✓"}
            </span>
          </span>
        );
      })}
    </div>
  );
}

export default function Journeys() {
  const [st, setSt] = useState<JourneyState | null>(null);
  const [form, setForm] = useState({ template: "winback", name: "", phone: "", email: "" });
  const [busy, setBusy] = useState(false);
  const [c360, setC360] = useState<Customer360 | null>(null);
  const [lookup, setLookup] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  function refresh() { getJourneys().then(setSt); }
  useEffect(() => {
    refresh();
    const ws = connectFeed((p) => { if (p?.type === "journey") refresh(); });
    wsRef.current = ws;
    const id = setInterval(refresh, 5000);
    return () => { ws.close(); clearInterval(id); };
  }, []);

  async function start() {
    if (!form.phone.trim() && !form.email.trim()) return;
    setBusy(true);
    try { await startJourney(form); refresh(); } finally { setBusy(false); }
  }
  async function respond(id: number) { await respondJourney(id); refresh(); }
  async function look() { if (lookup.trim()) setC360(await getCustomer360(lookup.trim())); }

  if (!st) return <p className="text-sm text-muted-foreground">Loading journeys…</p>;
  const m = st.metrics;
  const tmpl = st.templates.find((t) => t.id === form.template);

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground max-w-[78ch]">
        A journey is an ordered, multi-channel cadence with <b className="text-card-foreground/80">branch-on-response</b>:
        Foresight sends on one channel, and if the customer engages it stops — goal met. If not, after a wait it
        escalates to the next channel, following them wherever they are. Every touch feeds the Customer-360 timeline.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={<Activity size={16} />} label="Active journeys" value={m.active} sub={`escalate every ${st.wait_sec}s`} />
        <MetricCard icon={<CheckDouble size={16} />} label="Converted" value={m.converted} sub="engaged → stopped" />
        <MetricCard icon={<Bolt size={16} />} label="Exhausted" value={m.exhausted} sub="no engagement" />
        <MetricCard icon={<Activity size={16} />} label="Total" value={st.journeys.length} sub="all journeys" />
      </div>

      {/* Start a journey */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Start a cross-channel journey</CardTitle>
          <CardDescription className="text-xs">Pick a cadence and a recipient; the agent runs it across channels and branches on response.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label className="text-[11px] text-muted-foreground">Cadence
              <select value={form.template} onChange={(e) => setForm({ ...form, template: e.target.value })} className="form-select w-full mt-1 text-sm">
                {st.templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label className="text-[11px] text-muted-foreground">Name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Asha" className="form-input w-full mt-1 text-sm" />
            </label>
            <label className="text-[11px] text-muted-foreground">Phone
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+9162…" className="form-input w-full mt-1 text-sm" />
            </label>
            <label className="text-[11px] text-muted-foreground">Email (for email steps)
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="asha@…" className="form-input w-full mt-1 text-sm" />
            </label>
          </div>
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <button onClick={start} disabled={busy || (!form.phone.trim() && !form.email.trim())}
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
              {busy ? "Starting…" : "Start journey"}
            </button>
            {tmpl && <span className="text-xs text-muted-foreground">Path: {tmpl.channels.join(" → ")}</span>}
          </div>
        </CardContent>
      </Card>

      {/* Live journeys */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" /> Journeys</CardTitle>
          <CardDescription className="text-xs">Live — each advances across channels until the customer responds.</CardDescription>
        </CardHeader>
        <CardContent>
          {st.journeys.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">No journeys yet — start one above.</p>
          ) : (
            <div className="flex flex-col divide-y divide-foreground/5">
              {st.journeys.map((j) => (
                <div key={j.id} className="py-3 flex items-center justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-semibold">{j.name || j.phone || j.email}</span>
                      <Badge tone={STATUS_TONE[j.status] || "outline"}>{j.status}</Badge>
                      <span className="text-[11px] text-muted-foreground">{rel(j.touches[j.touches.length - 1]?.ts)}</span>
                    </div>
                    <div className="mt-1.5"><Sequence j={j} /></div>
                  </div>
                  {j.status === "active" && (
                    <button onClick={() => respond(j.id)} className="text-xs font-semibold text-success hover:underline shrink-0">Simulate response →</button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Customer 360 */}
      <Card>
        <CardHeaderRow>
          <div>
            <CardTitle className="text-sm">Customer 360</CardTitle>
            <CardDescription className="text-xs">Every touch for one customer, stitched across all channels — one identity, one journey.</CardDescription>
          </div>
        </CardHeaderRow>
        <CardContent>
          <div className="flex gap-2">
            <input value={lookup} onChange={(e) => setLookup(e.target.value)} onKeyDown={(e) => e.key === "Enter" && look()}
              placeholder="phone or email (e.g. +9162…)" className="form-input flex-1 text-sm" />
            <button onClick={look} className="px-4 rounded-md bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90">Look up</button>
          </div>
          {c360 && (
            <div className="mt-3">
              <div className="text-xs text-muted-foreground mb-2">
                <b className="text-card-foreground/80">{c360.contact}</b> · {c360.counts.messages} messages · {c360.counts.engagements} engagements · {c360.journeys.length} journeys
              </div>
              {c360.events.length === 0 ? <p className="text-sm text-muted-foreground">No touches found for this contact.</p> : (
                <div className="relative pl-4 border-l-2 border-foreground/10 space-y-2.5 max-h-80 overflow-y-auto">
                  {c360.events.map((e: C360Event, i) => (
                    <div key={i} className="relative">
                      <span className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full ${e.type === "engagement" ? "bg-success" : e.type === "in" ? "bg-primary" : "bg-muted-foreground/50"}`} />
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        <i className={CH_ICON[e.channel] || "ri-circle-line"} />
                        <span className="uppercase tracking-wide">{e.type === "in" ? "inbound" : e.type === "out" ? "sent" : e.type}</span>
                        <span>· {e.channel}</span><span>· {rel(e.ts)}</span>
                      </div>
                      <div className="text-sm text-card-foreground/90">{e.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
