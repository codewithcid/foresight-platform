import { useEffect, useState } from "react";
import App from "./App";
import Landing from "./landing/Landing";
import Login from "./components/Login";

type View = "landing" | "app";

/**
 * Top-level shell. Marketing landing first; "Launch Platform" flips to the app,
 * which is gated behind a sign-in. Session persists for the tab.
 */
export default function Root() {
  const [view, setView] = useState<View>(
    () => (sessionStorage.getItem("foresight-view") as View) || "landing"
  );
  const [authed, setAuthed] = useState<boolean>(() => !!localStorage.getItem("foresight-auth"));

  useEffect(() => {
    sessionStorage.setItem("foresight-view", view);
    window.scrollTo(0, 0);
  }, [view]);

  function logout() {
    localStorage.removeItem("foresight-auth");
    setAuthed(false);
    setView("landing");
  }

  if (view === "app") {
    if (!authed) return <Login onAuthed={() => setAuthed(true)} onBack={() => setView("landing")} />;
    return <App onHome={() => setView("landing")} onLogout={logout} />;
  }
  return <Landing onLaunch={() => setView("app")} />;
}
