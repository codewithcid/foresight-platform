import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * Split-screen hero. The yellow panel starts clipped to the left half with the
 * giant FORESIGHT wordmark straddling the seam (the iconic reference look). As
 * you scroll through the first viewport the panel fills, the wordmark recedes to
 * a faint watermark, and the tagline + CTAs take over — all scrubbed & pinned.
 */
export default function Hero({ onLaunch }: { onLaunch: () => void }) {
  const root = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const word = useRef<HTMLDivElement>(null);
  const tagline = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "+=90%",
          scrub: 0.6,
          pin: true,
          anticipatePin: 1,
        },
      });
      tl.to(panel.current, { clipPath: "inset(0 0% 0 0)", ease: "none" }, 0)
        .to(word.current, { opacity: 0.1, scale: 1.04, ease: "none" }, 0)
        .fromTo(
          tagline.current,
          { opacity: 0, x: -28 },
          { opacity: 1, x: 0, ease: "none", duration: 0.6 },
          0.25
        );
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <section ref={root} className="relative h-[100svh] w-full overflow-hidden bg-white">
      {/* Yellow panel (clipped → expands on scroll) */}
      <div ref={panel} className="hero-panel absolute inset-0 bg-[#FFB600]" />

      {/* Giant wordmark */}
      <div
        ref={word}
        className="absolute z-10 inset-0 flex flex-col items-center justify-center select-none"
      >
        <h1 className="font-display hero-word text-black">Fore</h1>
        <div className="flex items-end gap-[0.12em]">
          <h1 className="font-display hero-word text-black">Sight</h1>
          <span className="rounded-full bg-black w-[0.16em] h-[0.16em] mb-[0.12em] text-[clamp(4.5rem,19vw,18rem)]" />
        </div>
      </div>

      {/* Tagline column (hidden until scroll reveal). Full-height flex wrapper
          centers it vertically so GSAP can own the transform (x) without
          clobbering a translate-based centering. */}
      <div ref={tagline} className="absolute z-20 inset-0 flex items-center opacity-0">
       <div className="ml-[7vw] max-w-[36rem]">
        <div className="flex items-center gap-2 text-black/80">
          <i className="ri-pulse-line text-2xl" />
          <span className="font-grotesk font-bold tracking-[0.18em] text-sm uppercase">
            Epsilon TeXpedition · 2026
          </span>
        </div>
        <h2 className="font-grotesk font-extrabold text-black text-[clamp(2rem,4.4vw,3.4rem)] leading-[1.04] mt-3">
          The marketing AI that <span className="underline decoration-black/40 decoration-4 underline-offset-4">proves</span> it worked.
        </h2>
        <p className="text-black/70 text-[clamp(1rem,1.4vw,1.2rem)] leading-relaxed mt-4 max-w-[30rem]">
          One causal engine that anticipates lift per customer, acts across every channel,
          and proves the impact in rupees — not opens and clicks.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-7">
          <button
            onClick={onLaunch}
            className="group inline-flex items-center gap-2 bg-black text-white font-grotesk font-bold uppercase tracking-wide text-sm px-7 py-4 rounded-full hover:bg-neutral-800 transition-colors"
          >
            Launch the platform
            <i className="ri-arrow-right-up-line text-lg group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
          <a
            href="#proof"
            className="inline-flex items-center gap-2 border-2 border-black text-black font-grotesk font-bold uppercase tracking-wide text-sm px-7 py-4 rounded-full hover:bg-black hover:text-white transition-colors"
          >
            See the proof
          </a>
        </div>
       </div>
      </div>

      {/* Bouncing arrow */}
      <div className="absolute z-20 bottom-6 right-7 text-black/70 flex flex-col items-center gap-1">
        <span className="font-grotesk text-[10px] uppercase tracking-[0.2em]">Scroll</span>
        <i className="ri-arrow-down-line text-2xl arrow-bounce" />
      </div>
    </section>
  );
}
