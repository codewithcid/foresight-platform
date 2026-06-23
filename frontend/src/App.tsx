import { useEffect, useState } from "react";
import { Meta, getMeta } from "./api";
import Sidebar, { Tab } from "./components/Sidebar";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import AgentOps from "./components/AgentOps";
import CreativePreflight from "./components/CreativePreflight";
import SpendPlanner from "./components/SpendPlanner";
import ByoData from "./components/ByoData";
import Channels from "./components/Channels";
import Workflows from "./components/Workflows";
import Proof from "./components/Proof";
import Copilot from "./components/Copilot";
import Tour from "./components/Tour";
import { Handoff, NavContext } from "./nav";
import { AnimatePresence, motion } from "framer-motion";
import { pageTransition } from "./ui/motion";

const TITLES: Record<Tab, string> = {
  dashboard: "Command",
  workflows: "Workflows",
  planner: "Spend Planner",
  byocsv: "Audience & Uplift",
  creative: "Creative Pre-Flight",
  channels: "Channels",
  proof: "Proof",
  agentops: "Agent Console",
};

// One line per surface: its role in the core loop of predicting (and proving) ROI.
const SUBTITLES: Record<Tab, string> = {
  dashboard: "Live cockpit — watch predicted ROI being acted on, and the loop learn.",
  workflows: "Activate — orchestrate the ROI-maximizing action, end to end.",
  planner: "Anticipate — allocate budget to the highest-predicted-ROI segments.",
  byocsv: "Anticipate — the causal model that predicts each customer's ROI.",
  creative: "Activate — predict which creative lifts ROI, before you spend.",
  channels: "Activate — the real rails that turn predicted ROI into realized ROI.",
  proof: "Prove — actual vs. predicted ROI on every campaign.",
  agentops: "Operate — drive the whole ROI loop in natural language.",
};

export default function App({ onHome }: { onHome?: () => void }) {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [handoff, setHandoff] = useState<Handoff>(null);
  const [tourStep, setTourStep] = useState<number | null>(null);

  const go = (t: Tab, h: Handoff = null) => { setHandoff(h); setTab(t); };

  useEffect(() => {
    getMeta().then(setMeta);
    // First-ever visit: auto-open the guided tour once.
    if (!localStorage.getItem("foresight-tour-seen")) {
      localStorage.setItem("foresight-tour-seen", "1");
      const t = setTimeout(() => setTourStep(0), 900);
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <NavContext.Provider value={{ go, handoff, clearHandoff: () => setHandoff(null), startTour: () => setTourStep(0) }}>
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar tab={tab} setTab={(t) => go(t)} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} onHome={onHome} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-100">
        <Header
          title={TITLES[tab]}
          subtitle={SUBTITLES[tab]}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
        />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={tab}
                initial={pageTransition.initial}
                animate={pageTransition.animate}
                exit={pageTransition.exit}
                transition={pageTransition.transition}
              >
                {tab === "dashboard" && <Dashboard meta={meta} />}
                {tab === "workflows" && <Workflows />}
                {tab === "planner" && <SpendPlanner />}
                {tab === "byocsv" && <ByoData />}
                {tab === "channels" && <Channels />}
                {tab === "proof" && <Proof />}
                {tab === "creative" && <CreativePreflight meta={meta} />}
                {tab === "agentops" && <AgentOps />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>

      <Copilot />
      <Tour step={tourStep} setStep={setTourStep} />
    </div>
    </NavContext.Provider>
  );
}
