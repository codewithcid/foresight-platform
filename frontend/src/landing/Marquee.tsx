/** Infinite scrolling brand strip between sections. */
export default function Marquee() {
  const items = ["Anticipate", "Activate", "Prove"];
  const run = Array.from({ length: 6 }).flatMap(() => items);
  return (
    <div className="bg-black py-5 overflow-hidden border-y-4 border-[#FFB600]">
      <div className="marquee">
        {run.map((t, i) => (
          <span key={i} className="flex items-center shrink-0">
            <span className="font-display text-[#FFB600] text-2xl sm:text-3xl px-6 uppercase">{t}</span>
            <span className="text-white/40 text-2xl">◆</span>
          </span>
        ))}
      </div>
    </div>
  );
}
