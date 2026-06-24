import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay } from "swiper/modules";
import "swiper/css";
import "swiper/css/pagination";
import { Section, Kicker, Heading } from "./bits";

const SURFACES = [
  {
    n: "01",
    icon: "ri-database-2-line",
    name: "Audience & Uplift",
    tag: "Predict",
    body: "The causal core: a LightGBM S-learner scores each customer's incremental ROI (CATE). Upload your own experiment CSV and it validates the uplift on a randomized holdout.",
  },
  {
    n: "02",
    icon: "ri-pie-chart-2-line",
    name: "Spend Planner",
    tag: "Optimize",
    body: "Turns per-customer ROI predictions into the budget allocation with the highest total ROI — beating a naive even-split by ~86%, proven on a held-out control.",
  },
  {
    n: "03",
    icon: "ri-magic-line",
    name: "Creative Pre-Flight",
    tag: "Craft",
    body: "Predicts which message lifts ROI most — generates ad variants, pre-tests them on a synthetic shopper panel, and ships the winner straight into a campaign.",
  },
  {
    n: "04",
    icon: "ri-flow-chart",
    name: "Workflow Studio",
    tag: "Activate",
    body: "One orchestrated run: predict → guardrail → generate → pre-test → human approval → deliver on a real channel → prove. The agentic engine, with a person in the loop.",
  },
  {
    n: "05",
    icon: "ri-broadcast-line",
    name: "Real channels",
    tag: "Cross-channel",
    body: "Delivers through real providers — SMS, WhatsApp, Slack, Email and Telegram — not skins. The same agent and memory act consistently across every one.",
  },
  {
    n: "06",
    icon: "ri-plug-line",
    name: "Link-Up",
    tag: "Integrate",
    body: "Plug Foresight into your real app. It streams cart events; when one is abandoned the agent issues a budget-safe discount, WhatsApps a deep link back to the cart, and proves whether it recovered the sale — escalating the offer only if it pays.",
  },
  {
    n: "07",
    icon: "ri-checkbox-circle-line",
    name: "Proof",
    tag: "Prove & learn",
    body: "Every campaign validated predicted-vs-actual ROI and persisted to an audit trail — then proven outcomes recalibrate the model so the next prediction is sharper.",
  },
  {
    n: "08",
    icon: "ri-robot-2-line",
    name: "Agent Console",
    tag: "Operate",
    body: "Drive the whole loop in natural language — “launch a win-back SMS for bargain hunters” — over the same tool registry that's exposed externally via MCP.",
  },
];

export default function Surfaces() {
  return (
    <Section id="platform" className="py-24 sm:py-32">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
        <div>
          <div data-reveal>
            <Kicker>The platform</Kicker>
          </div>
          <Heading className="mt-5">
            One causal engine.<br />
            <span className="text-[#FFB600]">The whole ROI loop.</span>
          </Heading>
        </div>
        <p data-reveal className="text-black/60 max-w-[36ch] leading-relaxed md:text-right">
          Not slides — a live product. Predict → optimize → craft → activate → prove → learn, every
          stage on the same model and the same proof spine.
        </p>
      </div>

      <div data-reveal className="mt-14">
        <Swiper
          modules={[Navigation, Pagination, Autoplay]}
          spaceBetween={20}
          slidesPerView={1.1}
          pagination={{ clickable: true }}
          autoplay={{ delay: 4200, disableOnInteraction: true }}
          breakpoints={{ 640: { slidesPerView: 2.1 }, 1024: { slidesPerView: 3 } }}
        >
          {SURFACES.map((s) => (
            <SwiperSlide key={s.n}>
              <div className="h-full rounded-2xl border-2 border-black/10 bg-white p-7 flex flex-col min-h-[19rem] hover:border-black hover:-translate-y-1 transition-all">
                <div className="flex items-center justify-between">
                  <div className="grid place-items-center w-12 h-12 rounded-xl bg-[#FFB600] text-black text-2xl">
                    <i className={s.icon} />
                  </div>
                  <span className="font-display text-black/10 text-4xl leading-none">{s.n}</span>
                </div>
                <h3 className="font-grotesk font-extrabold text-xl mt-5">{s.name}</h3>
                <span className="self-start mt-2 text-[10px] font-bold uppercase tracking-wider text-black/50 border border-black/20 rounded-full px-2.5 py-0.5">
                  {s.tag}
                </span>
                <p className="text-black/60 leading-relaxed mt-4 text-sm">{s.body}</p>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>
    </Section>
  );
}
