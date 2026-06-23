import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./landing.css";

import LandingNav from "./LandingNav";
import Hero from "./Hero";
import Marquee from "./Marquee";
import Problem from "./Problem";
import Pillars from "./Pillars";
import Surfaces from "./Surfaces";
import Proof from "./Proof";
import Stack from "./Stack";
import Team from "./Team";
import CTA from "./CTA";
import Footer from "./Footer";

gsap.registerPlugin(ScrollTrigger);

export default function Landing({ onLaunch }: { onLaunch: () => void }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Reveal every [data-reveal] as it scrolls into view.
      ScrollTrigger.batch("[data-reveal]", {
        start: "top 88%",
        onEnter: (els) =>
          gsap.to(els, {
            opacity: 1,
            y: 0,
            duration: 0.7,
            ease: "power3.out",
            stagger: 0.08,
            overwrite: true,
          }),
      });
      // Pinned hero changes total scroll height — recompute once laid out.
      requestAnimationFrame(() => ScrollTrigger.refresh());
    }, root);

    // Safety net: never leave content stuck at opacity 0 (e.g. if a trigger
    // doesn't fire, on reduced-motion, or in fullPage screenshot capture).
    const fallback = window.setTimeout(() => {
      root.current?.querySelectorAll<HTMLElement>("[data-reveal]").forEach((el) => {
        if (getComputedStyle(el).opacity === "0") {
          el.style.opacity = "1";
          el.style.transform = "none";
        }
      });
    }, 2500);

    return () => {
      window.clearTimeout(fallback);
      ctx.revert();
    };
  }, []);

  return (
    <div id="top" ref={root} className="lp">
      <LandingNav onLaunch={onLaunch} />
      <Hero onLaunch={onLaunch} />
      <Marquee />
      <Problem />
      <Pillars />
      <Surfaces />
      <Proof />
      <Stack />
      <Team />
      <CTA onLaunch={onLaunch} />
      <Footer onLaunch={onLaunch} />
    </div>
  );
}
