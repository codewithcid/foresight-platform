import { Section } from "./bits";

export default function CTA({ onLaunch }: { onLaunch: () => void }) {
  return (
    <div className="bg-[#0a0a0a]">
      <Section className="py-28 sm:py-36 text-center">
        <h2 data-reveal className="font-display text-white text-[clamp(2.5rem,8vw,7rem)] leading-[0.9]">
          Stop reacting.<br />
          <span className="text-[#FFB600]">Start anticipating.</span>
        </h2>
        <p data-reveal className="text-white/60 text-lg max-w-[44ch] mx-auto mt-7">
          See the live platform — one causal engine, real cross-channel delivery, one proof spine.
        </p>
        <div data-reveal className="mt-10">
          <button
            onClick={onLaunch}
            className="group inline-flex items-center gap-3 bg-[#FFB600] text-black font-grotesk font-bold uppercase tracking-wide text-base px-10 py-5 rounded-full hover:bg-white transition-colors"
          >
            Launch the platform
            <i className="ri-arrow-right-up-line text-xl group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>
      </Section>
    </div>
  );
}
