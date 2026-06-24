import { ReactNode, useEffect, useRef, useState } from "react";
import { Activity, CheckDouble, Database, Layers, Megaphone, Puzzle, Target, Wand } from "./Icons";

export type Tab = "dashboard" | "workflows" | "planner" | "byocsv" | "creative" | "channels" | "proof" | "agentops" | "settings";

const NAV: { group: string; items: { key: Tab; label: string; icon: ReactNode }[] }[] = [
  {
    group: "Foresight",
    items: [
      { key: "dashboard", label: "Command", icon: <Activity size={18} /> },
      { key: "workflows", label: "Workflows", icon: <Layers size={18} /> },
      { key: "planner", label: "Spend Planner", icon: <Target size={18} /> },
      { key: "byocsv", label: "Audience & Uplift", icon: <Database size={18} /> },
      { key: "creative", label: "Creative Pre-Flight", icon: <Wand size={18} /> },
      { key: "channels", label: "Channels", icon: <Megaphone size={18} /> },
      { key: "proof", label: "Proof", icon: <CheckDouble size={18} /> },
      { key: "agentops", label: "Agent Console", icon: <Puzzle size={18} /> },
      { key: "settings", label: "Settings", icon: <i className="ri-settings-3-line text-[18px]" /> },
    ],
  },
];

export default function Sidebar({
  tab,
  setTab,
  sidebarOpen,
  setSidebarOpen,
  onHome,
}: {
  tab: Tab;
  setTab: (t: Tab) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  onHome?: () => void;
}) {
  const trigger = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLDivElement>(null);

  const stored = localStorage.getItem("sidebar-expanded");
  const [sidebarExpanded, setSidebarExpanded] = useState(stored === null ? false : stored === "true");

  // Close on click outside (mobile drawer)
  useEffect(() => {
    const handler = ({ target }: MouseEvent) => {
      if (!sidebar.current || !trigger.current) return;
      if (!sidebarOpen || sidebar.current.contains(target as Node) || trigger.current.contains(target as Node)) return;
      setSidebarOpen(false);
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  });

  // Close on Esc
  useEffect(() => {
    const handler = ({ key }: KeyboardEvent) => {
      if (!sidebarOpen || key !== "Escape") return;
      setSidebarOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  });

  useEffect(() => {
    localStorage.setItem("sidebar-expanded", String(sidebarExpanded));
    document.body.classList.toggle("sidebar-expanded", sidebarExpanded);
  }, [sidebarExpanded]);

  return (
    <div className="min-w-fit">
      {/* Backdrop (mobile) */}
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        aria-hidden="true"
      />

      <div
        id="sidebar"
        ref={sidebar}
        className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:w-64! 2xl:w-64! shrink-0 bg-white dark:bg-ink2 p-4 transition-all duration-200 ease-in-out border-r border-gray-200 dark:border-white/10 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-64"
        }`}
      >
        {/* Header: close + logo */}
        <div className="flex justify-between mb-10 pr-3 sm:px-2">
          <button
            ref={trigger}
            className="lg:hidden text-gray-500 hover:text-gray-400"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-controls="sidebar"
            aria-expanded={sidebarOpen}
          >
            <span className="sr-only">Close sidebar</span>
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
              <path d="M10.7 18.7l1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" />
            </svg>
          </button>
          <button
            onClick={() => (onHome ? onHome() : setTab("dashboard"))}
            title={onHome ? "Back to home" : "Dashboard"}
            className="flex items-center gap-2.5 group"
          >
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-accent2/15 text-accent2 text-lg leading-none shrink-0 group-hover:bg-accent2/25 transition-colors">◎</span>
            <span className="font-extrabold tracking-tight text-gray-800 dark:text-gray-100 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">
              Foresight
            </span>
          </button>
        </div>

        {/* Links */}
        <div className="space-y-8">
          {NAV.map((section) => (
            <div key={section.group}>
              <h3 className="text-[10px] uppercase text-gray-400 dark:text-gray-500 font-bold tracking-[0.18em] pl-3">
                <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
                <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">{section.group}</span>
              </h3>
              <ul className="mt-3">
                {section.items.map(({ key, label, icon }) => {
                  const active = tab === key;
                  return (
                    <li
                      key={key}
                      className={`relative pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 transition-colors ${
                        active
                          ? "bg-violet-500/[0.14] dark:bg-violet-500/[0.16]"
                          : "hover:bg-gray-100 dark:hover:bg-white/5"
                      }`}
                    >
                      {active && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-full bg-violet-500" />
                      )}
                      <button
                        onClick={() => { setTab(key); setSidebarOpen(false); }}
                        className={`block w-full text-left truncate transition duration-150 ${
                          active ? "text-gray-900 dark:text-white" : "text-gray-800/90 dark:text-gray-100/80 hover:text-gray-900 dark:hover:text-white"
                        }`}
                      >
                        <div className="flex items-center">
                          <span className={`shrink-0 ${active ? "text-violet-500" : "text-gray-400 dark:text-gray-500"}`}>{icon}</span>
                          <span className={`text-sm ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200 ${active ? "font-bold" : "font-medium"}`}>
                            {label}
                          </span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Expand / collapse */}
        <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end mt-auto">
          <div className="w-12 pl-4 pr-3 py-2">
            <button
              className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400"
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
            >
              <span className="sr-only">Expand / collapse sidebar</span>
              <svg className="shrink-0 fill-current sidebar-expanded:rotate-180" width="16" height="16" viewBox="0 0 16 16">
                <path d="M15 16a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v14a1 1 0 0 1-1 1ZM8.586 7H1a1 1 0 1 0 0 2h7.586l-2.793 2.793a1 1 0 1 0 1.414 1.414l4.5-4.5A.997.997 0 0 0 12 8.01M11.924 7.617a.997.997 0 0 0-.217-.324l-4.5-4.5a1 1 0 0 0-1.414 1.414L8.586 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
