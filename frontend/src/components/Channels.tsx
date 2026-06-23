import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChannelStatus, ChannelLog, getChannels, getChannelLogs, testChannel } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardHeaderRow, CardTitle, IconChip } from "../ui/dash";
import { stagger, fadeUp } from "../ui/motion";

function timeAgo(ts: number) {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

function ModeBadge({ c }: { c: ChannelStatus }) {
  if (c.mode === "live") return <Badge tone="success">Live</Badge>;
  if (c.mode === "sandbox") return <Badge tone="warning">Sandbox</Badge>;
  return <Badge tone="outline">Needs key</Badge>;
}

function ChannelCard({ c, onSent }: { c: ChannelStatus; onSent: () => void }) {
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const enabled = c.configured;

  async function send() {
    if (!to.trim()) return;
    setBusy(true); setResult(null);
    try {
      const r = await testChannel(c.id, to.trim());
      setResult({ ok: r.ok, msg: r.ok ? `Sent${r.sandbox ? " (sandbox)" : ""} · ${r.provider_id || "ok"}` : r.error || "Failed" });
      if (r.ok) onSent();
    } catch (e: any) {
      setResult({ ok: false, msg: e.message || "Request failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div variants={fadeUp}>
      <Card className="h-full">
        <CardHeaderRow>
          <div className="flex items-center gap-3">
            <IconChip className={enabled ? "text-primary border-primary/40 bg-primary/10" : ""}>
              <i className={`${c.icon} text-lg`} />
            </IconChip>
            <div>
              <CardTitle>{c.label}</CardTitle>
              <CardDescription className="capitalize">{c.kind}</CardDescription>
            </div>
          </div>
          <ModeBadge c={c} />
        </CardHeaderRow>
        <CardContent className="flex flex-col gap-3">
          {enabled ? (
            <>
              <div className="flex gap-2">
                <input
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                  placeholder={c.kind === "email" ? "you@example.com" : "+91XXXXXXXXXX"}
                  className="form-input flex-1 text-sm"
                />
                <button
                  onClick={send}
                  disabled={busy || !to.trim()}
                  className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition"
                >
                  {busy ? "Sending…" : "Test"}
                </button>
              </div>
              {c.sandbox && (
                <p className="text-[11px] text-muted-foreground">
                  Twilio WhatsApp sandbox — the recipient must first join by texting the sandbox code.
                </p>
              )}
              {result && (
                <p className={`text-xs ${result.ok ? "text-success" : "text-destructive"}`}>
                  {result.ok ? "✓ " : "✗ "}{result.msg}
                </p>
              )}
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">{c.hint || "Add the required key to enable this channel."}</p>
              <div className="flex flex-wrap gap-1.5">
                {c.needs.map((n) => (
                  <code key={n} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">{n}</code>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function Channels() {
  const [channels, setChannels] = useState<ChannelStatus[]>([]);
  const [logs, setLogs] = useState<ChannelLog[]>([]);

  function refreshLogs() { getChannelLogs(20).then((d) => setLogs(d.logs)); }
  useEffect(() => { getChannels().then((d) => setChannels(d.channels)); refreshLogs(); }, []);

  const liveCount = channels.filter((c) => c.configured).length;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-sm text-muted-foreground max-w-[70ch]">
          One agent, every channel. Foresight delivers through real providers — not skins — so a
          decision made by the causal engine can actually reach the customer. {liveCount} of {channels.length} connected.
        </p>
      </div>

      <motion.div variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {channels.map((c) => (
          <ChannelCard key={c.id} c={c} onSent={refreshLogs} />
        ))}
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Delivery log</CardTitle>
          <CardDescription className="text-xs">Every real send, persisted to the audit trail.</CardDescription>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sends yet. Connect a channel and send a test.</p>
          ) : (
            <div className="flex flex-col divide-y divide-border">
              {logs.map((l) => (
                <div key={l.id} className="flex items-center gap-3 py-2.5 text-sm">
                  <Badge tone={l.status === "sent" ? "success" : "destructive"}>{l.status}</Badge>
                  <span className="font-medium capitalize w-20 shrink-0">{l.channel}</span>
                  <span className="text-muted-foreground font-mono text-xs shrink-0">{l.to_addr}</span>
                  <span className="text-muted-foreground truncate flex-1">{l.error || l.body}</span>
                  <span className="text-muted-foreground/70 text-xs shrink-0">{timeAgo(l.ts)}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
