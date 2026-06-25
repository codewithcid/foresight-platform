import { Section, Kicker, Heading } from "./bits";

const TEAM = [
  {
    photo: "/team/sidhardh.png",
    initials: "SS",
    name: "Sidhardh S",
    role: "Team Lead · AI / ML & Full-Stack",
    sub: "github.com/codewithcid",
  },
  {
    photo: "/team/rochit.png",
    initials: "RL",
    name: "Rochit L",
    role: "Co-builder · Backend & Systems",
    sub: "Foresight · finals build",
  },
];

export default function Team() {
  return (
    <Section id="team" className="py-24 sm:py-32">
      <div data-reveal>
        <Kicker>The team</Kicker>
      </div>
      <Heading className="mt-5">
        Built by <span className="text-[#FFB600]">two</span>.
      </Heading>

      <div className="mt-14 grid sm:grid-cols-2 gap-5 max-w-[52rem]">
        {TEAM.map((m) => (
          <div
            key={m.name}
            data-reveal
            className="flex items-center gap-5 rounded-2xl border-2 border-black/10 p-6 bg-white hover:border-black transition-colors"
          >
            <div className="relative w-24 h-24 shrink-0">
              <span className="absolute inset-0 grid place-items-center rounded-2xl bg-[#FFB600] text-black font-display text-3xl">
                {m.initials}
              </span>
              <img
                src={m.photo}
                alt={m.name}
                className="relative w-24 h-24 rounded-2xl object-cover border-2 border-black"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = "none";
                }}
              />
            </div>
            <div>
              <h3 className="font-grotesk font-extrabold text-xl">{m.name}</h3>
              <div className="text-black/70 font-medium text-sm mt-1">{m.role}</div>
              <div className="text-black/45 text-xs font-mono mt-1.5">{m.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
