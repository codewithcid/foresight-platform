import { useEffect, useState } from "react";
import { AdminBot, Connection, SettingsData, getSettings, saveSettings, setMode } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle, IconChip } from "../ui/dash";

const inr = (x: number) => "₹" + Math.round(x).toLocaleString("en-IN");

function AdminBotCard({ bot, onSaved }: { bot: AdminBot; onSaved: () => void }) {
  const [base, setBase] = useState(bot.wati_base || "");
  const [token, setToken] = useState("");
  const [admins, setAdmins] = useState(bot.admins || "");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const connected = !!bot.wati_token_set && !!bot.wati_base;

  async function save() {
    const updates: Record<string, string> = {};
    if (base.trim()) updates.WATI_BASE_URL = base.trim();
    if (token.trim() && !token.includes("•")) updates.WATI_ACCESS_TOKEN = token.trim();
    updates.ADMIN_WHATSAPP_NUMBERS = admins.trim();
    setBusy(true);
    try { await saveSettings(updates); setToken(""); onSaved(); } finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeaderRow>
        <div>
          <CardTitle className="text-sm flex items-center gap-2"><i className="ri-whatsapp-line text-success" /> Admin WhatsApp bot (Wati)</CardTitle>
          <CardDescription className="text-xs">Chat with Foresight over WhatsApp — admins only. Reads live data and acts with confirmation.</CardDescription>
        </div>
        <Badge tone={connected ? "success" : "warning"}>{connected ? "Connected" : "Needs setup"}</Badge>
      </CardHeaderRow>
      <CardContent className="flex flex-col gap-3">
        <label className="text-[11px] text-muted-foreground">Wati API endpoint (from Wati → API Docs)
          <input value={base} onChange={(e) => setBase(e.target.value)} placeholder="https://live-mt-server.wati.io/123456" className="form-input w-full mt-1 text-sm font-mono" />
        </label>
        <label className="text-[11px] text-muted-foreground">Wati access token
          <input value={token} onChange={(e) => setToken(e.target.value)} type="password"
            placeholder={bot.wati_token_set ? bot.wati_token_masked : "paste your Wati token"} className="form-input w-full mt-1 text-sm font-mono" />
        </label>
        <label className="text-[11px] text-muted-foreground">Admin WhatsApp numbers <span className="text-muted-foreground/60">— comma-separated, E.164</span>
          <input value={admins} onChange={(e) => setAdmins(e.target.value)} placeholder="+9162…, +9198…" className="form-input w-full mt-1 text-sm" />
        </label>
        <div>
          <div className="text-[11px] text-muted-foreground mb-1">Webhook URL — paste this in Wati → Webhooks (event: message received)</div>
          <div className="flex gap-2">
            <code className="flex-1 truncate rounded-md bg-muted/40 ring-1 ring-foreground/10 px-3 py-1.5 text-xs font-mono">{bot.webhook_url}</code>
            <button onClick={() => { navigator.clipboard?.writeText(bot.webhook_url); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
              className="px-3 rounded-md ring-1 ring-foreground/15 text-xs hover:bg-muted/50">{copied ? "Copied" : "Copy"}</button>
          </div>
        </div>
        <button onClick={save} disabled={busy}
          className="w-fit px-4 py-2 rounded-md bg-primary text-primary-foreground text-xs font-semibold disabled:opacity-40 hover:opacity-90 transition">
          {busy ? "Saving…" : "Save"}
        </button>
      </CardContent>
    </Card>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  return mode === "live"
    ? <Badge tone="success">Live</Badge>
    : mode === "sandbox" ? <Badge tone="warning">Sandbox</Badge> : <Badge tone="outline">Needs key</Badge>;
}

function ConnectionCard({ c, onSaved }: { c: Connection; onSaved: () => void }) {
  const [vals, setVals] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(!c.configured);

  async function save() {
    const updates = Object.fromEntries(Object.entries(vals).filter(([, v]) => v.trim()));
    if (!Object.keys(updates).length) { setOpen(false); return; }
    setBusy(true);
    try { await saveSettings(updates); setVals({}); onSaved(); setOpen(false); } finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeaderRow>
        <div className="flex items-center gap-3">
          <IconChip className={c.configured ? "text-primary border-primary/40 bg-primary/10" : ""}><i className={`${c.icon} text-lg`} /></IconChip>
          <div>
            <CardTitle>{c.label}</CardTitle>
            <CardDescription className="capitalize">{c.kind}</CardDescription>
          </div>
        </div>
        <ModeBadge mode={c.mode} />
      </CardHeaderRow>
      <CardContent className="flex flex-col gap-2.5">
        {open ? (
          <>
            {c.fields.map((f) => (
              <label key={f.key} className="text-[11px] text-muted-foreground">
                <span className="font-mono">{f.key}</span>
                <input
                  value={vals[f.key] ?? ""}
                  onChange={(e) => setVals({ ...vals, [f.key]: e.target.value })}
                  placeholder={f.set ? f.masked : "not set — paste to connect"}
                  className="form-input w-full mt-1 text-sm font-mono"
                />
              </label>
            ))}
            <div className="flex gap-2 mt-1">
              <button onClick={save} disabled={busy}
                className="px-3.5 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-semibold disabled:opacity-40 hover:opacity-90 transition">
                {busy ? "Saving…" : "Save & connect"}
              </button>
              {c.configured && <button onClick={() => { setVals({}); setOpen(false); }} className="px-3 py-1.5 rounded-md ring-1 ring-foreground/15 text-xs hover:bg-muted/50">Cancel</button>}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{c.fields.every((f) => f.set) ? "All keys set." : "Some keys missing."}</span>
            <button onClick={() => setOpen(true)} className="text-xs text-primary hover:underline">Reconfigure</button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Settings() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [savingMode, setSavingMode] = useState(false);
  function refresh() { getSettings().then(setData); }
  useEffect(() => { refresh(); }, []);

  async function toggleMode(mode: "sandbox" | "live") {
    setSavingMode(true);
    try { await setMode(mode); refresh(); } finally { setSavingMode(false); }
  }

  if (!data) return <p className="text-sm text-muted-foreground">Loading settings…</p>;
  const liveCount = data.connections.filter((c) => c.configured).length;

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground max-w-[75ch]">
        Connect your providers, choose how Foresight operates, and review its guardrails — all in-app.
      </p>

      {/* Workspace + mode */}
      <Card>
        <CardHeaderRow>
          <div>
            <CardTitle className="text-sm">{data.workspace}</CardTitle>
            <CardDescription className="text-xs">{liveCount} of {data.connections.length} channels connected</CardDescription>
          </div>
          <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/40 ring-1 ring-foreground/10">
            {(["sandbox", "live"] as const).map((m) => (
              <button key={m} onClick={() => toggleMode(m)} disabled={savingMode}
                className={`text-xs font-semibold px-3 py-1.5 rounded-md capitalize transition-colors ${data.mode === m ? (m === "live" ? "bg-success text-ink" : "bg-primary text-primary-foreground") : "text-muted-foreground hover:text-card-foreground"}`}>
                {m}
              </button>
            ))}
          </div>
        </CardHeaderRow>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            {data.mode === "sandbox"
              ? "Sandbox: synthetic traffic streams to Command so you can explore safely. Switch to Live to operate on your real channels only."
              : "Live: synthetic traffic is paused. The agent acts only on your real connected channels."}
          </p>
        </CardContent>
      </Card>

      {/* Connections */}
      <div>
        <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground mb-3">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" /> Connections
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.connections.map((c) => <ConnectionCard key={c.id} c={c} onSaved={refresh} />)}
        </div>
      </div>

      {/* Admin WhatsApp bot */}
      {data.admin_bot && <AdminBotCard bot={data.admin_bot} onSaved={refresh} />}

      {/* Operating limits */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Operating limits (guardrails)</CardTitle>
          <CardDescription className="text-xs">The responsible-AI bounds the agent enforces on every send.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-4">
          {[["Max actions / customer / day", data.limits.max_actions_per_day],
            ["Daily budget cap", inr(data.limits.daily_budget)],
            ["Min predicted lift to act", data.limits.min_lift_pct + "%"]].map(([l, v]) => (
            <div key={l as string}>
              <div className="font-grotesk text-xl font-bold tabular-nums">{v}</div>
              <div className="text-xs text-muted-foreground">{l}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
