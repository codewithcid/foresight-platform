import { Section, Kicker, Heading } from "./bits";

const PAINS = [
  {
    icon: "ri-git-merge-line",
    title: "Siloed channels",
    body: "A customer is one person — but email, SMS, app and web each act blind to the others.",
  },
  {
    icon: "ri-money-dollar-circle-line",
    title: "Spend by gut",
    body: "Budgets chase last-click attribution, not who a message will actually move.",
  },
  {
    icon: "ri-eye-off-line",
    title: "Vanity metrics",
    body: "“Success” is measured in opens and clicks — not proven, incremental revenue.",
  },
];

export default function Problem() {
  return (
    <Section id="problem" className="py-24 sm:py-32">
      <div data-reveal>
        <Kicker>The problem</Kicker>
      </div>
      <Heading className="mt-5 max-w-[18ch]" >
        <span data-reveal className="inline-block">Marketing <span className="text-[#FFB600]">reacts.</span></span>{" "}
        <span data-reveal className="inline-block">It rarely anticipates — and almost never proves what worked.</span>
      </Heading>

      <div className="mt-16 grid md:grid-cols-3 gap-5">
        {PAINS.map((p) => (
          <div
            key={p.title}
            data-reveal
            className="group rounded-2xl border-2 border-black/10 p-7 hover:border-black transition-colors bg-white"
          >
            <div className="grid place-items-center w-12 h-12 rounded-xl bg-black text-[#FFB600] text-2xl">
              <i className={p.icon} />
            </div>
            <h3 className="font-grotesk font-extrabold text-xl mt-5">{p.title}</h3>
            <p className="text-black/60 leading-relaxed mt-2">{p.body}</p>
          </div>
        ))}
      </div>

      <p data-reveal className="mt-14 text-[clamp(1.1rem,2vw,1.6rem)] font-grotesk font-semibold leading-snug max-w-[44ch] border-l-4 border-[#FFB600] pl-6">
        Theme 2 asks for seamless cross-channel experiences <em>with clear measures of success.</em>{" "}
        Foresight is an agent that anticipates, acts across channels, and proves its impact — in rupees.
      </p>
    </Section>
  );
}
