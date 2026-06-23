import { Section, Kicker, Heading } from "./bits";

const PILLARS = [
  {
    step: "01",
    name: "Anticipate",
    icon: "ri-radar-line",
    tag: "See the lift first",
    body: "A LightGBM S-learner estimates each customer's individual treatment effect — so we predict who a message will actually move, before a rupee is spent.",
  },
  {
    step: "02",
    name: "Activate",
    icon: "ri-flashlight-line",
    tag: "Act across channels",
    body: "A guardrailed, multi-agent loop decides, drafts and ships autonomously — and remembers context across shop, WhatsApp and beyond.",
  },
  {
    step: "03",
    name: "Prove",
    icon: "ri-checkbox-circle-line",
    tag: "Predicted vs. actual",
    body: "Every prediction is validated against the real outcome — at the intervention, portfolio, creative and your-own-data level. That's the clear measure of success.",
  },
];

export default function Pillars() {
  return (
    <div className="bg-[#0a0a0a]">
      <Section className="py-24 sm:py-32">
        <div data-reveal>
          <Kicker dark>The approach</Kicker>
        </div>
        <Heading dark className="mt-5">
          Three words, <span className="text-[#FFB600]">measured</span> at every step.
        </Heading>

        <div className="mt-16 grid md:grid-cols-3 gap-5">
          {PILLARS.map((p) => (
            <div
              key={p.name}
              data-reveal
              className="relative rounded-2xl border border-white/10 bg-white/[0.03] p-8 overflow-hidden group hover:border-[#FFB600]/50 transition-colors"
            >
              <span className="absolute -top-4 -right-2 font-display text-white/[0.06] text-[7rem] leading-none select-none">
                {p.step}
              </span>
              <div className="grid place-items-center w-12 h-12 rounded-xl bg-[#FFB600] text-black text-2xl">
                <i className={p.icon} />
              </div>
              <div className="font-grotesk font-bold uppercase tracking-[0.18em] text-[#FFB600] text-xs mt-6">
                {p.name}
              </div>
              <h3 className="font-grotesk font-extrabold text-white text-2xl mt-1">{p.tag}</h3>
              <p className="text-white/60 leading-relaxed mt-3 relative z-10">{p.body}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
