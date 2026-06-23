import { createContext, useContext } from "react";
import type { Tab } from "./components/Sidebar";

/** A payload handed from one surface to another (e.g. Creative -> Workflows). */
export type Handoff = {
  segment?: string;
  intervention?: string;
  channel?: string;
  copy?: string;   // a specific creative to run, instead of generating one
  angle?: string;
  label?: string;
  from?: string;   // which surface sent it (for a "carried from …" chip)
} | null;

type NavApi = {
  go: (tab: Tab, handoff?: Handoff) => void;
  handoff: Handoff;
  clearHandoff: () => void;
  startTour: () => void;
};

export const NavContext = createContext<NavApi>({ go: () => {}, handoff: null, clearHandoff: () => {}, startTour: () => {} });
export const useNav = () => useContext(NavContext);

/** Map an intervention's channel label to a real delivery channel. */
export function deliveryChannel(c?: string): string {
  return { sms: "sms", email: "email", app_push: "whatsapp", paid_social: "telegram" }[c ?? ""] ?? "sms";
}
