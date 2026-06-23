// A small, consistent line-icon set (stroke-based, inherits text color via
// currentColor) replacing every emoji used in UI chrome across the app.
// Product "photos" in the Shop tab keep their illustrated emoji fallback --
// that's deliberate product art, a different concern from interface icons.
import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base(size: number) {
  return { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
}

export const Upload = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M5 16v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3" /></svg>
);
export const Database = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></svg>
);
export const Search = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>
);
export const Cart = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="9" cy="20" r="1.4" /><circle cx="18" cy="20" r="1.4" /><path d="M2 3h2l2.4 12.2a2 2 0 0 0 2 1.6h8.6a2 2 0 0 0 2-1.6L21 7H6" /></svg>
);
export const Heart = ({ size = 18, filled = false, ...p }: IconProps & { filled?: boolean }) => (
  <svg {...base(size)} fill={filled ? "currentColor" : "none"} {...p}><path d="M12 20.5s-7.5-4.6-9.7-9.1C.7 7.8 2.4 4.5 5.7 4c2-.3 3.8.7 5 2.3a.5.5 0 0 0 .8 0c1.2-1.6 3-2.6 5-2.3 3.3.5 5 3.8 3.4 7.4-2.2 4.5-9.7 9.1-9.7 9.1z" /></svg>
);
export const Star = ({ size = 18, filled = true, ...p }: IconProps & { filled?: boolean }) => (
  <svg {...base(size)} fill={filled ? "currentColor" : "none"} {...p}><path d="M12 2.8l2.9 6 6.5.7-4.8 4.5 1.3 6.4L12 17l-5.9 3.4 1.3-6.4-4.8-4.5 6.5-.7z" /></svg>
);
export const Sparkle = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6z" /><path d="M19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7z" /></svg>
);
export const ArrowLeft = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M19 12H5M11 18l-6-6 6-6" /></svg>
);
export const Check = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M20 6L9 17l-5-5" /></svg>
);
export const CheckDouble = ({ size = 14, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M2 12l4 4 8-8" /><path d="M9 16l3.5 3.5L21 9" /></svg>
);
export const Close = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M18 6L6 18M6 6l12 12" /></svg>
);
export const Video = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="2" y="6" width="14" height="12" rx="2" /><path d="M16 10.5l5-3v9l-5-3z" /></svg>
);
export const Phone = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M5 4h3l1.5 4.5L7.5 10a11 11 0 0 0 6.5 6.5l1.5-2L20 16v3a1.5 1.5 0 0 1-1.6 1.5A16 16 0 0 1 3.5 5.6 1.5 1.5 0 0 1 5 4z" /></svg>
);
export const Brain = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8 3 3 0 0 0 2 5.2h2zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 1 5.8 3 3 0 0 1-2 5.2h-2z" /><path d="M9 4v14M15 4v14" /></svg>
);
export const Paperclip = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M21 11.5l-8.5 8.5a4.5 4.5 0 0 1-6.4-6.4l9-9a3 3 0 0 1 4.3 4.3l-8.5 8.5a1.5 1.5 0 0 1-2.1-2.1l7.1-7.1" /></svg>
);
export const Send = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M22 2L11 13M22 2l-7 20-4-9-9-4z" /></svg>
);
export const Bolt = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M13 2L4 14h6l-1 8 9-12h-6z" /></svg>
);
export const StopCircle = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="9" /><rect x="9" y="9" width="6" height="6" /></svg>
);
export const MessageSquare = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M21 11.5a8.4 8.4 0 0 1-1.3 4.5L21 20l-4.1-1.1A8.5 8.5 0 1 1 21 11.5z" /></svg>
);
export const Smartphone = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="6" y="2" width="12" height="20" rx="2" /><path d="M11 18h2" /></svg>
);
export const Megaphone = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M3 11v2a2 2 0 0 0 2 2h1l3 5h2l-1-5h2l9 4V6l-9 4H6a2 2 0 0 0-2 2z" /></svg>
);
export const Mail = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M3 6l9 7 9-7" /></svg>
);
export const TrendUp = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></svg>
);
export const TrendDown = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M3 7l6 6 4-4 8 8" /><path d="M21 11V5h-6" /></svg>
);
export const TrendFlat = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M3 12h18" /><path d="M17 8l4 4-4 4" /></svg>
);
export const Rupee = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M6 4h11M6 9h11M6 4a5 5 0 0 1 0 10h-1l7 7" /></svg>
);
export const Target = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.2" fill="currentColor" /></svg>
);
export const Wand = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M4 20L18 6" /><path d="M16 2l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" /><path d="M5 14l.7 1.4L7 16l-1.3.6L5 18l-.7-1.4L3 16l1.3-.6z" /></svg>
);
export const Radar = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 12L12 4" /><path d="M12 12l6 3" /><circle cx="12" cy="12" r="1.4" fill="currentColor" /></svg>
);
export const Dice = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1" fill="currentColor" /><circle cx="16" cy="8" r="1" fill="currentColor" /><circle cx="12" cy="12" r="1" fill="currentColor" /><circle cx="8" cy="16" r="1" fill="currentColor" /><circle cx="16" cy="16" r="1" fill="currentColor" /></svg>
);
export const Puzzle = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M9 4h3v2.2a1.6 1.6 0 1 1 0 3.1V12h3a1.6 1.6 0 1 0 3.1 0H21v6h-3.2a1.6 1.6 0 1 0-3.1 0H12v-3a1.6 1.6 0 1 1-3 0v3H6a1.6 1.6 0 1 0-3.1 0H3v-6h2.2a1.6 1.6 0 1 0 0-3.1V4z" /></svg>
);
export const Bag = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M6 8h12l1 12H5z" /><path d="M9 8a3 3 0 1 1 6 0" /></svg>
);
export const Layers = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></svg>
);
export const Calendar = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></svg>
);
export const Flag = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M5 21V4" /><path d="M5 5h13l-3 4 3 4H5" /></svg>
);
export const Activity = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M3 12h4l2 8 4-16 2 8h6" /></svg>
);
export const Leaf = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M5 20C3 10 11 4 20 4c0 9-6 17-16 16z" /><path d="M5 20c2-6 6-9 11-11" /></svg>
);
export const Gift = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="3" y="9" width="18" height="12" rx="1" /><path d="M3 9h18v4H3z" /><path d="M12 9v12M12 9c-2 0-4-1-4-3.5S9.5 2 12 5c0-3 4-3.5 4-1S14 9 12 9z" /></svg>
);
export const PartyStar = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M4 20l5-14 5 14" /><path d="M14 20l3-9 3 9" /><circle cx="18" cy="5" r="1.4" fill="currentColor" /></svg>
);
export const Sun = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="4.5" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></svg>
);
export const Moon = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 7 7 0 0 0 20 14.5z" /></svg>
);
export const Pulse = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><circle cx="12" cy="12" r="2" fill="currentColor" /></svg>
);
export const Shield = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6z" /></svg>
);
export const Reply = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M9 14L3 9l6-5" /><path d="M3 9h11a6 6 0 0 1 6 6v3" /></svg>
);
export const Pencil = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><path d="M12 20h9" /><path d="M16.5 3.5a2 2 0 0 1 3 3L7 19l-4 1 1-4z" /></svg>
);
export const ClipboardList = ({ size = 18, ...p }: IconProps) => (
  <svg {...base(size)} {...p}><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 3h6v3H9zM8 11h8M8 15h8" /></svg>
);
