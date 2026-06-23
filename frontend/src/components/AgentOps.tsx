import { useState } from "react";
import { AgentOpsResponse, askAgentOps } from "../api";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/dash";

const SAMPLE_QUESTIONS = [
  "Which channels are live, and summarize our proven campaigns.",
  "Launch a win-back SMS campaign for bargain hunters — don't approve it yet.",
  "What's the predicted uplift of a cart-recovery push for high-intent shoppers?",
  "List the recent workflow runs and their prediction error.",
  "How reliable has the SMS discount been for loyalists so far?",
];

export default function AgentOps() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentOpsResponse | null>(null);
  const [history, setHistory] = useState<{ q: string; r: AgentOpsResponse }[]>([]);

  async function ask(q?: string) {
    const text = q ?? question;
    if (!text.trim()) return;
    setLoading(true);
    setQuestion("");
    const res = await askAgentOps(text);
    setResult(res);
    setHistory((h) => [{ q: text, r: res }, ...h]);
    setLoading(false);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Ask the Supervisor</CardTitle>
            <CardDescription className="text-xs">
              An autonomous agent over Foresight's tool registry (NVIDIA NIM tool-calling, Groq fallback). It doesn't
              just answer — it can <b className="text-card-foreground/80">launch campaign workflows, approve runs, and
              send on real channels</b>, plus query the causal model, channels, runs and proof. Same tools are exposed
              externally over MCP.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && ask()}
                placeholder="Tell the agent what to do…"
                className="form-input flex-1 text-sm"
              />
              <button onClick={() => ask()} disabled={loading}
                className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition">
                {loading ? "Thinking…" : "Ask"}
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLE_QUESTIONS.map((q) => (
                <button key={q} onClick={() => ask(q)}
                  className="text-[11px] rounded-full px-2.5 py-1 ring-1 ring-foreground/10 text-muted-foreground hover:text-primary hover:ring-primary/40 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-card-foreground mb-3 whitespace-pre-wrap">{result.answer}</p>
              {result.trace.length > 0 && (
                <>
                  <h4 className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                    Reasoning trace · {result.trace.length} tool call{result.trace.length > 1 ? "s" : ""}
                  </h4>
                  <div className="space-y-2">
                    {result.trace.map((t, i) => (
                      <details key={i} className="rounded-md ring-1 ring-foreground/10 p-2 text-xs">
                        <summary className="cursor-pointer text-primary font-mono">
                          {t.step} · {t.tool}({JSON.stringify(t.args)})
                        </summary>
                        <pre className="text-[10px] text-muted-foreground mt-1.5 whitespace-pre-wrap break-all">
                          {JSON.stringify(t.result, null, 2)}
                        </pre>
                      </details>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="h-fit">
        <CardHeader><CardTitle className="text-sm">History</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {history.map((h, i) => (
              <div key={i} className="text-xs border-l-2 border-border pl-2">
                <p className="text-card-foreground/80">{h.q}</p>
                <p className="text-muted-foreground mt-0.5 flex items-center gap-1.5">
                  <Badge tone="outline">{h.r.trace.length} tool{h.r.trace.length !== 1 ? "s" : ""}</Badge>
                </p>
              </div>
            ))}
            {history.length === 0 && <p className="text-xs text-muted-foreground">Nothing asked yet.</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
