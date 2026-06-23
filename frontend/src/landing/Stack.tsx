import { Section, Kicker, Heading } from "./bits";

const STACK = [
  {
    icon: "ri-function-line",
    title: "Causal core",
    chip: "the proof spine",
    body: "LightGBM S-learner estimates each customer's treatment effect (CATE). Every prediction is checked against the actual outcome — live calibration, not a one-off score.",
  },
  {
    icon: "ri-robot-2-line",
    title: "Agentic loop",
    chip: "self-correcting",
    body: "Strategist → Guardrail → Execution → Critic, with a Thompson-sampling contextual bandit and a policy that learns per segment.",
  },
  {
    icon: "ri-cpu-line",
    title: "AI integration",
    chip: "NVIDIA NIM + Groq",
    body: "A model pool — Qwen3-80B · Llama-3.3-70B · GPT-OSS / Nemotron-120B — with Groq fallback, keyless image generation, and a tool-calling supervisor exposed over MCP.",
  },
  {
    icon: "ri-stack-line",
    title: "Stack & scale",
    chip: "FastAPI · React",
    body: "FastAPI + React/Vite/TS over websockets. Projects to a 5-lakh addressable base — and the same engine runs on any dataset you upload.",
  },
];

export default function Stack() {
  return (
    <div id="stack" className="bg-[#0a0a0a] scroll-mt-20">
      <Section className="py-24 sm:py-32">
        <div data-reveal>
          <Kicker dark>Under the hood</Kicker>
        </div>
        <Heading dark className="mt-5">
          Real ML. Real agents. <span className="text-[#FFB600]">Real proof.</span>
        </Heading>

        <div className="mt-16 grid md:grid-cols-2 gap-5">
          {STACK.map((s) => (
            <div
              key={s.title}
              data-reveal
              className="flex gap-5 rounded-2xl border border-white/10 bg-white/[0.03] p-7 hover:border-[#FFB600]/40 transition-colors"
            >
              <div className="grid place-items-center w-12 h-12 shrink-0 rounded-xl bg-[#FFB600] text-black text-2xl">
                <i className={s.icon} />
              </div>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="font-grotesk font-extrabold text-white text-xl">{s.title}</h3>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#FFB600] border border-[#FFB600]/40 rounded-full px-2.5 py-0.5">
                    {s.chip}
                  </span>
                </div>
                <p className="text-white/60 leading-relaxed mt-2">{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
