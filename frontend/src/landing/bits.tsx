import { ReactNode } from "react";

/** Tiny uppercase section label with the yellow tick + dot motif. */
export function Kicker({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="h-2.5 w-2.5 rounded-full bg-[#FFB600]" />
      <span
        className={`font-grotesk font-bold uppercase tracking-[0.18em] text-xs ${
          dark ? "text-white/70" : "text-black/60"
        }`}
      >
        {children}
      </span>
    </div>
  );
}

/** Big agency-style display heading. */
export function Heading({
  children,
  dark = false,
  className = "",
}: {
  children: ReactNode;
  dark?: boolean;
  className?: string;
}) {
  return (
    <h2
      className={`font-display text-[clamp(2rem,5.5vw,4.5rem)] leading-[0.95] ${
        dark ? "text-white" : "text-black"
      } ${className}`}
    >
      {children}
    </h2>
  );
}

/** Section wrapper with consistent gutters + scroll anchor offset. */
export function Section({
  id,
  children,
  className = "",
}: {
  id?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={`scroll-mt-20 px-[5vw] sm:px-8 ${className}`}>
      <div className="mx-auto max-w-[1500px]">{children}</div>
    </section>
  );
}
