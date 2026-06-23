import { useEffect, useState } from "react";
import { Meta, Persona, getDemoPersonas, getMeta } from "./api";
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

export default function App({ onHome }: { onHome?: () => void }) {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaId, setPersonaId] = useState<string>("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    getMeta().then(setMeta);
    getDemoPersonas().then((d) => {
      setPersonas(d.personas);
      if (d.personas.length) setPersonaId(d.personas[0].customer_id);
    });
  }, []);

  const persona = personas.find((p) => p.customer_id === personaId);
  const personaLabel = persona ? `${persona.first_name} (${persona.segment_label})` : "…";

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar tab={tab} setTab={setTab} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} onHome={onHome} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-100">
        <Header
          title={TITLES[tab]}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          personas={personas}
          personaId={personaId}
          setPersonaId={setPersonaId}
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
    </div>
  );
}
