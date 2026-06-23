const COLUMNS = [
  { head: "Platform", items: ["Dashboard", "Spend Planner", "Bring Your Own Data", "Creative Pre-Flight"] },
  { head: "Proof", items: ["Predicted vs. actual", "Incrementality holdout", "Synthetic pre-test", "Live calibration"] },
  { head: "Tech", items: ["LightGBM S-learner", "Multi-agent loop", "NVIDIA NIM + Groq", "MCP server"] },
];

const SOCIAL = [
  { icon: "ri-github-fill", href: "https://github.com/codewithcid/foresight" },
  { icon: "ri-mail-fill", href: "mailto:sidhardh512@gmail.com" },
  { icon: "ri-global-line", href: "#top" },
];

export default function Footer({ onLaunch }: { onLaunch: () => void }) {
  return (
    <footer className="bg-black text-white">
      <div className="mx-auto max-w-[1500px] px-[5vw] sm:px-8 py-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="grid place-items-center w-9 h-9 rounded-lg bg-[#FFB600] text-black text-xl leading-none">◎</span>
              <span className="font-grotesk font-extrabold text-2xl">Foresight</span>
            </div>
            <p className="font-grotesk font-bold uppercase tracking-[0.18em] text-[#FFB600] text-xs mt-4">
              Anticipate · Activate · Prove
            </p>
            <p className="text-white/50 text-sm mt-4 max-w-[34ch] leading-relaxed">
              The marketing AI that anticipates lift, acts across channels, and proves its impact.
            </p>
            <div className="flex gap-3 mt-6">
              {SOCIAL.map((s) => (
                <a
                  key={s.icon}
                  href={s.href}
                  target={s.href.startsWith("http") ? "_blank" : undefined}
                  rel="noreferrer"
                  className="grid place-items-center w-10 h-10 rounded-full border border-white/20 text-lg hover:bg-[#FFB600] hover:text-black hover:border-[#FFB600] transition-colors"
                >
                  <i className={s.icon} />
                </a>
              ))}
            </div>
          </div>

          {COLUMNS.map((c) => (
            <div key={c.head}>
              <h4 className="font-grotesk font-bold uppercase tracking-wider text-sm text-white/90">{c.head}</h4>
              <ul className="mt-4 space-y-2.5">
                {c.items.map((i) => (
                  <li key={i} className="text-white/50 text-sm hover:text-[#FFB600] transition-colors cursor-default">
                    {i}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-white/40 text-xs">© 2026 Team Foresight · Epsilon TeXpedition · Theme 2</p>
          <button
            onClick={onLaunch}
            className="font-grotesk font-bold uppercase tracking-wide text-xs text-black bg-[#FFB600] px-5 py-2.5 rounded-full hover:bg-white transition-colors"
          >
            Launch Platform →
          </button>
        </div>
      </div>
    </footer>
  );
}
