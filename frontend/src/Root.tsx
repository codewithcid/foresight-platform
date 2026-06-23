import { useEffect, useState } from "react";
import App from "./App";
import Landing from "./landing/Landing";

type View = "landing" | "app";

/**
 * Top-level shell. Shows the marketing landing first; the "Launch Platform"
 * CTA flips to the live app. The choice persists for the tab session so a
 * refresh after launching stays in the app instead of bouncing to the hero.
 */
export default function Root() {
  const [view, setView] = useState<View>(
    () => (sessionStorage.getItem("foresight-view") as View) || "landing"
  );

  useEffect(() => {
    sessionStorage.setItem("foresight-view", view);
    // Landing is a light surface; let it scroll. The app owns its own layout.
    window.scrollTo(0, 0);
  }, [view]);

  if (view === "app") return <App onHome={() => setView("landing")} />;
  return <Landing onLaunch={() => setView("app")} />;
}
