import { useEffect, useState } from "react";
import { getChannels, getRuns } from "../api";
import { useNav } from "../nav";
import type { Tab } from "./Sidebar";

/** First-run checklist — connect a channel, run a campaign, see the proof. Dismissible. */
export default function Onboarding() {
  const { go } = useNav();
  const [dismissed, setDismissed] = useState(() => !!localStorage.getItem("foresight-onboarded"));
  const [s, setS] = useState({ connected: false, ran: false, proven: false });

  useEffect(() => {
    getChannels().then((d) => setS((p) => ({ ...p, connected: d.channels.some((c) => c.configured) }))).catch(() => {});
    getRuns(50).then((d) => setS((p) => ({ ...p, ran: d.runs.length > 0, proven: d.runs.some((r) => r.status === "proven") }))).catch(() => {});
  }, []);

  if (dismissed) return null;
  const items: { done: boolean; label: string; tab: Tab; cta: string }[] = [
    { done: s.connected, label: "Connect a channel", tab: "settings", cta: "Connect" },
    { done: s.ran, label: "Run your first campaign", tab: "workflows", cta: "Run" },
    { done: s.proven, label: "See the proof", tab: "proof", cta: "View" },
  ];
  const allDone = items.every((i) => i.done);

  function dismiss() { localStorage.setItem("foresight-onboarded", "1"); setDismissed(true); }

  return (
    <div className="rounded-xl ring-1 ring-foreground/10 bg-linear-to-r from-primary/[0.06] to-card p-4 mb-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" /> {allDone ? "You're all set" : "Get started"}
        </h2>
        <button onClick={dismiss} className="text-xs text-muted-foreground hover:text-card-foreground">Dismiss ✕</button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((it, i) => (
          <div key={it.label} className="flex items-center gap-3 rounded-lg ring-1 ring-foreground/10 bg-muted/25 p-3">
            <span className={`grid place-items-center w-6 h-6 rounded-full shrink-0 text-xs ${it.done ? "bg-success/20 text-success" : "ring-1 ring-foreground/20 text-muted-foreground"}`}>
              {it.done ? "✓" : i + 1}
            </span>
            <span className={`flex-1 text-sm ${it.done ? "text-muted-foreground line-through" : "text-card-foreground"}`}>{it.label}</span>
            {!it.done && (
              <button onClick={() => go(it.tab)} className="text-xs font-semibold text-primary hover:underline shrink-0">{it.cta} →</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
