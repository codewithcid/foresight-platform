import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay } from "swiper/modules";
import "swiper/css";
import "swiper/css/pagination";
import { Section, Kicker, Heading } from "./bits";

const SURFACES = [
  {
    n: "01",
    icon: "ri-dashboard-3-line",
    name: "Foresight Dashboard",
    tag: "Working model",
    body: "Autonomous decisions live — every few seconds it evaluates a real customer, the guardrails pass, it acts, and shows predicted lift vs. the actual outcome. Drag the Time Machine to Diwali and the whole system's behaviour shifts.",
  },
  {
    n: "02",
    icon: "ri-pie-chart-2-line",
    name: "Spend Planner",
    tag: "Technical depth",
    body: "Give it a budget and it allocates across segments and channels to maximise incremental revenue — beating a naive even-split by 86%, validated on a held-out control.",
  },
  {
    n: "03",
    icon: "ri-upload-cloud-2-line",
    name: "Bring Your Own Data",
    tag: "Scalability",
    body: "Not just our synthetic demo — upload a real experiment CSV and it trains an uplift model on your segments, then proves it on a randomized holdout.",
  },
  {
    n: "04",
    icon: "ri-magic-line",
    name: "Creative Pre-Flight",
    tag: "AI integration",
    body: "Generate ad variants, pre-test them on a synthetic shopper panel, ship the winner — and prove its resonance against a hidden ground truth.",
  },
  {
    n: "05",
    icon: "ri-store-2-line",
    name: "Mēla — Shop",
    tag: "Communication",
    body: "The same agent acts inside a live storefront, personalising the journey and remembering context across the visit.",
  },
  {
    n: "06",
    icon: "ri-whatsapp-line",
    name: "WhatsApp",
    tag: "Cross-channel",
    body: "It carries the customer relationship into messaging — acting and remembering across channels, unprompted.",
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
            <span className="text-[#FFB600]">Six working surfaces.</span>
          </Heading>
        </div>
        <p data-reveal className="text-black/60 max-w-[36ch] leading-relaxed md:text-right">
          Not slides — a live product. Each surface runs on the same model, the same proof spine.
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
