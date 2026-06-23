import { createContext, useContext } from "react";
import type { Tab } from "./components/Sidebar";

/** Lets any surface hand off to another (the ROI-loop nodes + cross-surface CTAs). */
export const NavContext = createContext<(t: Tab) => void>(() => {});
export const useNav = () => useContext(NavContext);
