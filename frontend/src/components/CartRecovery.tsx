import { useEffect, useRef, useState } from "react";
import { StoreCart, StoreConfig, StoreState, connectFeed, getStoreConfig, getStoreState, setStoreConfig, simulateCart } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle, MetricCard } from "../ui/dash";
import { Bag, Bolt, CheckDouble, Rupee, Target } from "./Icons";

const inr = (x: number) => "₹" + Math.round(x || 0).toLocaleString("en-IN");

const STATUS_TONE: Record<string, "default" | "outline" | "success" | "destructive" | "warning"> = {
  active: "warning", pushed: "default", recovered: "success", lost: "destructive",
};

type LogLine = { t: number; text: string; tone: string };

function describe(p: any): LogLine | null {
  const c: StoreCart = p.cart || {};
  const who = c.name || c.cart_id || "a shopper";
  if (p.event === "cart_updated") return { t: Date.now(), tone: "muted", text: `🛒 ${who} updated a cart — ${inr(c.value)}` };
  if (p.event === "push")
    return { t: Date.now(), tone: "primary", text: `${p.escalated ? "↑ Escalated to" : "→ Pushed"} ${p.percent}% to ${who} (${p.code})${p.delivered ? " · WhatsApp sent" : ""}` };
  if (p.event === "purchase")
    return { t: Date.now(), tone: p.attributed ? "success" : "muted", text: p.attributed ? `✓ ${who} bought — recovered ${inr(p.value)}` : `${who} bought (organic) ${inr(p.value)}` };
  if (p.event === "lost") return { t: Date.now(), tone: "destructive", text: `✗ ${who} lost — ${p.reason}` };
  return null;
}

export default function CartRecovery() {
  const [state, setState] = useState<StoreState | null>(null);
  const [cfg, setCfg] = useState<StoreConfig | null>(null);
  const [log, setLog] = useState<LogLine[]>([]);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const [urlDraft, setUrlDraft] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  function refresh() { getStoreState().then(setState); }
  useEffect(() => {
    refresh();
    getStoreConfig().then((c) => { setCfg(c); setUrlDraft(c.store_url); });
    const ws = connectFeed((p) => {
      if (p?.type !== "store") return;
      const line = describe(p);
      if (line) setLog((l) => [line, ...l].slice(0, 40));
      refresh();
    });
    wsRef.current = ws;
    const id = setInterval(refresh, 6000);
    return () => { ws.close(); clearInterval(id); };
  }, []);

  async function simulate() { setBusy(true); try { await simulateCart(); refresh(); } finally { setBusy(false); } }
  function copy(text: string, what: string) { navigator.clipboard?.writeText(text); setCopied(what); setTimeout(() => setCopied(""), 1500); }
  async function saveUrl() { if (cfg && urlDraft && urlDraft !== cfg.store_url) setCfg(await setStoreConfig({ store_url: urlDraft })); }
  async function regen() { setCfg(await setStoreConfig({ regenerate_key: true })); }

  if (!state) return <p className="text-sm text-muted-foreground">Loading cart recovery…</p>;
  const m = state.metrics;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <p className="text-sm text-muted-foreground max-w-[70ch]">
          Your store streams cart events to Foresight. When a cart is abandoned, the agent issues a
          budget-safe discount, sends a WhatsApp deep-link back to the cart, then proves whether the
          push actually recovered the sale — escalating the offer only if it pays off.
        </p>
        <button onClick={simulate} disabled={busy}
          className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
          <Bolt size={15} /> {busy ? "Simulating…" : "Simulate abandoned cart"}
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <MetricCard icon={<Bag size={16} />} label="Carts acted on" value={m.pushed} sub={`${m.awaiting} awaiting outcome`} />
        <MetricCard icon={<CheckDouble size={16} />} label="Recovered" value={m.recovered}
          badge={m.recovery_rate != null ? <Badge tone="success">{m.recovery_rate}%</Badge> : undefined} sub={`${m.lost} lost`} />
        <MetricCard icon={<Rupee size={16} />} label="Recovered revenue" value={inr(m.recovered_value)} sub="attributed to pushes" />
        <MetricCard icon={<Target size={16} />} label="Discount spend" value={inr(m.budget_spent)} sub={`of ${inr(m.budget_cap)} cap`} />
        <MetricCard icon={<Bolt size={16} />} label="Active carts" value={m.active} sub={`abandon after ${state.abandon_window}s`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recovery queue */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm">Recovery queue</CardTitle>
            <CardDescription className="text-xs">Every cart the store has reported, and what the agent did.</CardDescription>
          </CardHeader>
          <CardContent>
            {state.carts.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">No carts yet — connect your store, or hit “Simulate abandoned cart”.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    <tr className="text-left border-b border-foreground/10">
                      <th className="py-2 pr-3 font-semibold">Customer</th>
                      <th className="py-2 pr-3 font-semibold">Cart</th>
                      <th className="py-2 pr-3 font-semibold">Offer</th>
                      <th className="py-2 pr-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.carts.map((c) => (
                      <tr key={c.cart_id} className="border-b border-foreground/5 last:border-0">
                        <td className="py-2 pr-3">{c.name || <span className="text-muted-foreground">{c.cart_id}</span>}</td>
                        <td className="py-2 pr-3 text-muted-foreground">{(c.items?.[0]?.name) || "—"}<span className="text-card-foreground/70"> · {inr(c.value)}</span></td>
                        <td className="py-2 pr-3 font-mono text-xs">{c.discount_code ? `${c.discount_code}` : "—"}</td>
                        <td className="py-2 pr-3"><Badge tone={STATUS_TONE[c.status] || "outline"}>{c.status}{c.status === "recovered" && c.recovered_value ? ` ${inr(c.recovered_value)}` : ""}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Live feed */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" /> Live activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5 max-h-80 overflow-y-auto text-xs">
              {log.length === 0 ? <p className="text-muted-foreground">Waiting for store events…</p> :
                log.map((l, i) => (
                  <div key={i} className={
                    l.tone === "success" ? "text-success" : l.tone === "destructive" ? "text-destructive"
                      : l.tone === "primary" ? "text-card-foreground" : "text-muted-foreground"}>
                    {l.text}
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Developer / connect panel */}
      <Card>
        <CardHeaderRow>
          <div>
            <CardTitle className="text-sm">Connect your store</CardTitle>
            <CardDescription className="text-xs">Hand these to your developer. Events authenticate with the ingest key.</CardDescription>
          </div>
          <Badge tone={state.ingest_key_set ? "success" : "warning"}>{state.ingest_key_set ? "Key active" : "Default key"}</Badge>
        </CardHeaderRow>
        <CardContent className="flex flex-col gap-3">
          {cfg && (
            <>
              <Field label="Ingest key (X-Foresight-Key)" value={cfg.ingest_key} onCopy={() => copy(cfg.ingest_key, "key")} copied={copied === "key"} mono action={<button onClick={regen} className="text-xs text-primary hover:underline">Regenerate</button>} />
              <Field label="Events endpoint" value={`${cfg.base_url}/api/store/event`} onCopy={() => copy(`${cfg.base_url}/api/store/event`, "ep")} copied={copied === "ep"} mono />
              <label className="text-[11px] text-muted-foreground">Store cart URL template <span className="text-muted-foreground/60">— {`{cart_id}`} is substituted</span>
                <div className="flex gap-2 mt-1">
                  <input value={urlDraft} onChange={(e) => setUrlDraft(e.target.value)} placeholder="https://your-store.com/cart/{cart_id}" className="form-input flex-1 text-sm font-mono" />
                  <button onClick={saveUrl} className="px-3 rounded-md bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90">Save</button>
                </div>
              </label>
              <p className="text-[11px] text-muted-foreground">Discount ladder: {state.ladder.map((p) => `${p}%`).join(" → ")} · escalates only within budget &amp; margin.</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, value, onCopy, copied, mono, action }: { label: string; value: string; onCopy: () => void; copied: boolean; mono?: boolean; action?: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
        <span>{label}</span>{action}
      </div>
      <div className="flex gap-2">
        <code className={`flex-1 truncate rounded-md bg-muted/40 ring-1 ring-foreground/10 px-3 py-1.5 text-xs ${mono ? "font-mono" : ""}`}>{value}</code>
        <button onClick={onCopy} className="px-3 rounded-md ring-1 ring-foreground/15 text-xs hover:bg-muted/50">{copied ? "Copied" : "Copy"}</button>
      </div>
    </div>
  );
}
