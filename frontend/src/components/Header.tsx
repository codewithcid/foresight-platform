import { useEffect, useRef, useState } from "react";
import { useTheme } from "../ThemeContext";
import { getSettings } from "../api";
import { Moon, Sun } from "./Icons";

export default function Header({
  title,
  subtitle,
  sidebarOpen,
  setSidebarOpen,
  onLogout,
  onSettings,
}: {
  title: string;
  subtitle?: string;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  onLogout?: () => void;
  onSettings?: () => void;
}) {
  const { theme, toggle } = useTheme();
  const [mode, setMode] = useState<string>("");
  const [menu, setMenu] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const workspace = localStorage.getItem("foresight-workspace") || "Foresight";
  const email = localStorage.getItem("foresight-email") || "demo@foresight.ai";

  useEffect(() => { getSettings().then((s) => setMode(s.mode)).catch(() => {}); }, [title]);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false); };
    document.addEventListener("click", h);
    return () => document.removeEventListener("click", h);
  }, []);

  return (
    <header className="sticky top-0 before:absolute before:inset-0 before:backdrop-blur-md max-lg:before:bg-white/90 dark:max-lg:before:bg-gray-800/90 before:-z-10 z-30 max-lg:shadow-xs lg:before:bg-gray-100/90 dark:lg:before:bg-gray-900/90">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:border-b border-gray-200 dark:border-gray-700/60">
          {/* Left: hamburger + title */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden"
              aria-controls="sidebar"
              aria-expanded={sidebarOpen}
              onClick={(e) => { e.stopPropagation(); setSidebarOpen(!sidebarOpen); }}
            >
              <span className="sr-only">Open sidebar</span>
              <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
                <rect x="4" y="5" width="16" height="2" />
                <rect x="4" y="11" width="16" height="2" />
                <rect x="4" y="17" width="16" height="2" />
              </svg>
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                  Foresight · Anticipate · Activate · Prove
                </span>
              </div>
              <h1 className="font-grotesk text-xl sm:text-2xl font-extrabold tracking-tight text-gray-800 dark:text-gray-100 truncate -mt-0.5">
                {title}
              </h1>
              {subtitle && (
                <p className="hidden md:block text-[11px] text-gray-500 dark:text-gray-400 truncate -mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>

          {/* Right: mode badge · theme · account */}
          <div className="flex items-center gap-2.5">
            {mode && (
              <button onClick={onSettings} title="Change in Settings"
                className={`hidden sm:inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full ring-1 ${
                  mode === "live" ? "text-success ring-success/40 bg-success/10" : "text-amber-500 dark:text-amber-400 ring-amber-400/40 bg-amber-400/10"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${mode === "live" ? "bg-success" : "bg-amber-400"} ${mode === "live" ? "" : "animate-pulse"}`} />
                {mode === "live" ? "Live" : "Sandbox"}
              </button>
            )}
            <button
              onClick={toggle}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              className="w-8 h-8 flex items-center justify-center rounded-full border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-violet-500 hover:border-violet-500/50 transition"
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            <div className="relative" ref={ref}>
              <button onClick={() => setMenu((v) => !v)}
                className="w-8 h-8 grid place-items-center rounded-full bg-violet-500/15 text-violet-500 font-bold text-sm hover:bg-violet-500/25 transition">
                {workspace.charAt(0).toUpperCase()}
              </button>
              {menu && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white dark:bg-gray-800 ring-1 ring-black/10 dark:ring-white/10 shadow-xl p-1.5 text-sm">
                  <div className="px-2.5 py-2">
                    <div className="font-semibold text-gray-800 dark:text-gray-100 truncate">{workspace}</div>
                    <div className="text-xs text-gray-400 truncate">{email}</div>
                  </div>
                  <div className="h-px bg-gray-100 dark:bg-gray-700/60 my-1" />
                  <button onClick={() => { setMenu(false); onSettings?.(); }}
                    className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2">
                    <i className="ri-settings-3-line" /> Settings
                  </button>
                  {onLogout && (
                    <button onClick={() => { setMenu(false); onLogout(); }}
                      className="w-full text-left px-2.5 py-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2">
                      <i className="ri-logout-box-r-line" /> Log out
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
