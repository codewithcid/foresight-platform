import { Persona } from "../api";
import { useTheme } from "../ThemeContext";
import { Moon, Sun } from "./Icons";

export default function Header({
  title,
  subtitle,
  sidebarOpen,
  setSidebarOpen,
  personas,
  personaId,
  setPersonaId,
}: {
  title: string;
  subtitle?: string;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  personas: Persona[];
  personaId: string;
  setPersonaId: (id: string) => void;
}) {
  const { theme, toggle } = useTheme();

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

          {/* Right: persona + theme */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-[11px] text-gray-500 dark:text-gray-400">Viewing as</span>
              <select
                value={personaId}
                onChange={(e) => setPersonaId(e.target.value)}
                className="form-select text-xs py-1.5"
              >
                {personas.map((p) => (
                  <option key={p.customer_id} value={p.customer_id}>{p.first_name} · {p.segment_label}</option>
                ))}
              </select>
            </div>
            <button
              onClick={toggle}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              className="w-8 h-8 flex items-center justify-center rounded-full border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-violet-500 hover:border-violet-500/50 transition"
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
