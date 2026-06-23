import { useEffect, useRef, useState } from "react";
import { Section, Kicker, Heading } from "./bits";

/** Counts up from 0 → value the first time it scrolls into view. */
function CountUp({ value, suffix = "", prefix = "", decimals = 0 }: {
  value: number; suffix?: string; prefix?: string; decimals?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [n, setN] = useState(0);
  const done = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting || done.current) return;
        done.current = true;
        const start = performance.now();
        const dur = 1100;
        const tick = (t: number) => {
          const p = Math.min(1, (t - start) / dur);
          const eased = 1 - Math.pow(1 - p, 3);
          setN(value * eased);
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.4 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [value]);

  return (
    <span ref={ref}>
      {prefix}
      {n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}

const STATS = [
  { node: <CountUp prefix="+" value={86} suffix="%" />, label: "Spend Planner beats a naive even-split, validated on a held-out control." },
  { node: <CountUp value={96} suffix="%" />, label: "Incrementality-holdout accuracy on the synthetic portfolio proof." },
  { node: <CountUp value={4} />, label: "Levels of predicted-vs-actual proof: intervention, portfolio, creative, your data." },
];

export default function Proof() {
  return (
    <div id="proof" className="bg-[#FFB600] scroll-mt-20">
      <Section className="py-24 sm:py-32">
        <div data-reveal>
          <Kicker>The proof spine</Kicker>
        </div>
        <Heading className="mt-5 max-w-[20ch]">
          We don't just personalize — we prove it worked.
        </Heading>
        <p data-reveal className="mt-6 text-black/70 text-lg max-w-[52ch] leading-relaxed">
          Real causal ML, not an LLM wrapper. Every prediction is checked against the actual
          outcome — live calibration, end to end.
        </p>

        <div className="mt-16 grid sm:grid-cols-3 gap-px bg-black/15 rounded-2xl overflow-hidden border border-black/15">
          {STATS.map((s, i) => (
            <div key={i} data-reveal className="bg-[#FFB600] p-8">
              <div className="stat-num text-black text-[clamp(3rem,7vw,5.5rem)]">{s.node}</div>
              <p className="text-black/70 font-medium leading-snug mt-2">{s.label}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
