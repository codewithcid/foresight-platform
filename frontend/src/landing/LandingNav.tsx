import { useEffect, useState } from "react";

const LINKS = [
  { href: "#problem", label: "Problem" },
  { href: "#platform", label: "Platform" },
  { href: "#proof", label: "Proof" },
  { href: "#stack", label: "Tech" },
  { href: "#team", label: "Team" },
];

export default function LandingNav({ onLaunch }: { onLaunch: () => void }) {
  const [solid, setSolid] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 64);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        solid ? "bg-white/90 backdrop-blur-md border-b border-black/10 shadow-sm" : "bg-transparent"
      }`}
    >
      <nav className="mx-auto max-w-[1500px] px-[5vw] sm:px-8 h-16 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2.5 shrink-0">
          <span className="grid place-items-center w-8 h-8 rounded-lg bg-black text-[#FFB600] text-lg leading-none">◎</span>
          <span className="font-grotesk font-extrabold tracking-tight text-lg text-black">Foresight</span>
        </a>

        <ul className="hidden md:flex items-center gap-8">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="link-grow font-grotesk font-semibold text-sm text-black/80 hover:text-black transition-colors"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-3">
          <button
            onClick={onLaunch}
            className="group inline-flex items-center gap-2 bg-[#FFB600] text-black font-grotesk font-bold uppercase tracking-wide text-xs sm:text-sm px-5 py-2.5 rounded-full border-2 border-black hover:bg-black hover:text-[#FFB600] transition-colors"
          >
            Launch Platform
            <i className="ri-arrow-right-up-line text-base group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
          <button
            className="md:hidden text-2xl text-black"
            aria-label="Menu"
            onClick={() => setOpen((v) => !v)}
          >
            <i className={open ? "ri-close-line" : "ri-menu-line"} />
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-white border-t border-black/10 px-[5vw] py-4">
          <ul className="flex flex-col gap-3">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="font-grotesk font-semibold text-black/80"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
}
