import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AgentOpsResponse, askAgentOps } from "../api";
import { Brain, Close, Send } from "./Icons";

type Msg = { role: "user" | "ai"; text: string; trace?: AgentOpsResponse["trace"] };

const EXAMPLES = [
  "What should our Diwali strategy be for bargain hunters?",
  "Which segment has the best ROI right now?",
  "Summarise the agent's activity today.",
];

function TraceView({ trace }: { trace: AgentOpsResponse["trace"] }) {
  const [open, setOpen] = useState(false);
  if (!trace?.length) return null;
  return (
    <div className="mt-2">
      <button onClick={() => setOpen((o) => !o)}
        className="text-[10px] uppercase tracking-wider text-accent2/80 hover:text-accent2">
        {open ? "hide" : "show"} reasoning · {trace.length} tool {trace.length === 1 ? "call" : "calls"}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-1 space-y-1">
            {trace.map((t) => (
              <div key={t.step} className="text-[11px] rounded-md border border-slate-200 dark:border-line bg-slate-50 dark:bg-ink/50 px-2 py-1">
                <span className="font-mono text-accent2">{t.tool}</span>
                <span className="text-slate-400"> ({Object.values(t.args || {}).join(", ")})</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Copilot() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: 1e9, behavior: "smooth" }); }, [msgs, loading]);

  async function ask(text: string) {
    if (!text.trim() || loading) return;
    setMsgs((m) => [...m, { role: "user", text }]); setQ(""); setLoading(true);
    try {
      const res = await askAgentOps(text);
      setMsgs((m) => [...m, { role: "ai", text: res.answer, trace: res.trace }]);
    } catch {
      setMsgs((m) => [...m, { role: "ai", text: "Sorry — I couldn't reach the reasoning engine just now." }]);
    } finally { setLoading(false); }
  }

  return (
    <>
      <motion.button
        onClick={() => setOpen(true)}
        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 pl-4 pr-5 py-3 rounded-full bg-linear-to-r from-accent2 to-accent text-ink font-semibold shadow-xl shadow-accent2/30"
      >
        <Brain size={18} /> Ask Foresight
      </motion.button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setOpen(false)} className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
            <motion.div
              initial={{ x: 440 }} animate={{ x: 0 }} exit={{ x: 440 }}
              transition={{ type: "spring", damping: 28, stiffness: 260 }}
              className="fixed top-0 right-0 z-50 h-full w-[420px] max-w-[94vw] bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700/60 flex flex-col shadow-2xl"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-line">
                <div className="flex items-center gap-2">
                  <span className="grid place-items-center w-7 h-7 rounded-lg bg-accent2/15 text-accent2"><Brain size={16} /></span>
                  <div>
                    <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">Ask Foresight</div>
                    <div className="text-[10px] text-slate-400">grounded in live data · tool-calling agent</div>
                  </div>
                </div>
                <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><Close size={18} /></button>
              </div>

              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                {msgs.length === 0 && (
                  <div className="space-y-2">
                    <p className="text-sm text-slate-500 dark:text-slate-400">Ask anything about your customers, segments, spend, or the agent's decisions.</p>
                    {EXAMPLES.map((ex) => (
                      <button key={ex} onClick={() => ask(ex)}
                        className="block w-full text-left text-xs rounded-lg border border-slate-200 dark:border-line bg-slate-50 dark:bg-ink/40 px-3 py-2 text-slate-600 dark:text-slate-300 hover:border-accent2/50 transition">
                        {ex}
                      </button>
                    ))}
                  </div>
                )}
                {msgs.map((m, i) => (
                  <div key={i} className={m.role === "user" ? "text-right" : ""}>
                    <div className={`inline-block max-w-[88%] text-sm rounded-2xl px-3 py-2 ${
                      m.role === "user"
                        ? "bg-accent2 text-ink rounded-br-sm"
                        : "bg-slate-100 dark:bg-panel text-slate-700 dark:text-slate-200 rounded-bl-sm text-left"}`}>
                      <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>
                      {m.role === "ai" && m.trace && <TraceView trace={m.trace} />}
                    </div>
                  </div>
                ))}
                {loading && <div className="text-sm text-slate-400 animate-pulse">Foresight is reasoning…</div>}
              </div>

              <div className="p-3 border-t border-slate-200 dark:border-line flex items-center gap-2">
                <input
                  value={q} onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") ask(q); }}
                  placeholder="Ask Foresight…"
                  className="flex-1 bg-slate-100 dark:bg-ink/60 border border-slate-200 dark:border-line rounded-full px-4 py-2 text-sm text-slate-800 dark:text-slate-100 outline-none focus:border-accent2"
                />
                <button onClick={() => ask(q)} disabled={loading || !q.trim()}
                  className="grid place-items-center w-9 h-9 rounded-full bg-accent2 text-ink disabled:opacity-40">
                  <Send size={16} />
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
