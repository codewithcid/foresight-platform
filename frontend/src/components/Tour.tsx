import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Tab } from "./Sidebar";
import { useNav } from "../nav";

type Step = { tab: Tab; phase: string; title: string; say: string; tip?: string };

// The guided walk through the ROI loop — one stop per stage.
export const TOUR: Step[] = [
  { tab: "dashboard", phase: "Overview", title: "One ROI loop",
    say: "Foresight predicts the ROI of every action before spend, acts on the profitable ones across real channels, proves the result, and learns. Every surface is one stage of this loop.",
    tip: "The diagram at the top maps it — each stage is clickable." },
  { tab: "byocsv", phase: "Predict", title: "Audience & Uplift",
    say: "It starts with causal prediction: a LightGBM S-learner scores each customer's incremental ROI (CATE). Upload an experiment CSV, or use the sample.",
    tip: "Try ‘Use sample data’ to see uplift validated on a holdout." },
  { tab: "planner", phase: "Optimize", title: "Spend Planner",
    say: "Those per-customer predictions become a budget plan that maximizes total ROI — beating a naive even-split by ~86%, proven on a held-out control.",
    tip: "Hit ‘Launch →’ on any allocation row to turn it into a campaign." },
  { tab: "creative", phase: "Craft", title: "Creative Pre-Flight",
    say: "Before spending, it predicts which message lifts ROI most — generating variants and pre-testing them on a synthetic shopper panel.",
    tip: "‘Launch as campaign →’ carries the winning creative straight into a workflow." },
  { tab: "workflows", phase: "Activate", title: "Workflows",
    say: "The agent runs it end to end: predict → guardrail → generate → pre-test → human approval → deliver on a real channel → prove. Guardrails block negative-ROI sends.",
    tip: "Pick a template, Run, then Approve & send." },
  { tab: "channels", phase: "Activate", title: "Channels",
    say: "Predicted ROI only becomes real ROI if the message lands. Foresight delivers through real providers — SMS, WhatsApp, Slack, Email, Telegram.",
    tip: "Send a test on any live channel." },
  { tab: "store", phase: "Activate", title: "Link-Up",
    say: "Plug Foresight into a real app. Your store streams cart events; when one is abandoned the agent issues a budget-safe discount, WhatsApps a deep link back to the cart, and proves whether it recovered the sale — escalating the offer only if it pays off.",
    tip: "Hit ‘Simulate abandoned cart’ to watch the recover → prove loop live." },
  { tab: "proof", phase: "Prove", title: "Proof",
    say: "Every campaign is validated predicted-vs-actual ROI — and the model-recalibration card shows proven outcomes sharpening the next prediction. The loop closes.",
    tip: "This is the ‘clear measures of success’." },
  { tab: "agentops", phase: "Operate", title: "Agent Console",
    say: "Or skip the clicks: tell the agent in plain English — ‘launch a win-back SMS for bargain hunters’ — and it drives the whole loop itself.",
    tip: "It uses the same tools exposed over MCP." },
];

export default function Tour({ step, setStep }: { step: number | null; setStep: (s: number | null) => void }) {
  const { go } = useNav();
  const active = step !== null;
  const cur = active ? TOUR[step!] : null;

  // Navigate to the current step's surface whenever the step changes.
  useEffect(() => {
    if (step !== null) go(TOUR[step].tab);
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AnimatePresence>
      {active && cur && (
        <motion.div
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.25 }}
          className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 w-[min(92vw,640px)]"
        >
          <div className="rounded-2xl bg-card ring-1 ring-primary/40 shadow-2xl shadow-black/40 p-4">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-primary-foreground bg-primary rounded px-1.5 py-0.5">{cur.phase}</span>
                <span className="font-grotesk font-bold text-sm">{cur.title}</span>
              </div>
              <span className="text-[11px] text-muted-foreground tabular-nums">{step! + 1} / {TOUR.length}</span>
            </div>
            <p className="text-sm text-card-foreground/90 leading-relaxed">{cur.say}</p>
            {cur.tip && <p className="text-xs text-primary/90 mt-1.5">→ {cur.tip}</p>}

            {/* progress dots */}
            <div className="flex gap-1 mt-3">
              {TOUR.map((_, i) => (
                <button key={i} onClick={() => setStep(i)}
                  className={`h-1 flex-1 rounded-full transition-colors ${i <= step! ? "bg-primary" : "bg-foreground/15"}`} />
              ))}
            </div>

            <div className="flex items-center justify-between mt-3">
              <button onClick={() => setStep(null)} className="text-xs text-muted-foreground hover:text-card-foreground">Exit tour</button>
              <div className="flex items-center gap-2">
                <button onClick={() => setStep(Math.max(0, step! - 1))} disabled={step === 0}
                  className="text-xs px-3 py-1.5 rounded-md ring-1 ring-foreground/15 hover:bg-muted/50 disabled:opacity-40 transition">Back</button>
                {step! < TOUR.length - 1 ? (
                  <button onClick={() => setStep(step! + 1)}
                    className="text-xs px-4 py-1.5 rounded-md bg-primary text-primary-foreground font-semibold hover:opacity-90 transition">Next →</button>
                ) : (
                  <button onClick={() => setStep(null)}
                    className="text-xs px-4 py-1.5 rounded-md bg-success text-ink font-semibold hover:opacity-90 transition">Finish ✓</button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
