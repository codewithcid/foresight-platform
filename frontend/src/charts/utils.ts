// Chart helpers adapted from the Mosaic template (Cruip), typed for our app.

export const formatThousands = (value: number) =>
  Intl.NumberFormat("en-IN", { maximumSignificantDigits: 3, notation: "compact" }).format(value);

/** Indian-rupee compact formatter (₹1.2L / ₹3.4Cr style via en-IN grouping). */
export const formatINRCompact = (value: number) =>
  value >= 1e7 ? "₹" + (value / 1e7).toFixed(2) + "Cr"
    : value >= 1e5 ? "₹" + (value / 1e5).toFixed(2) + "L"
      : value >= 1e3 ? "₹" + (value / 1e3).toFixed(1) + "k"
        : "₹" + Math.round(value);

export const getCssVariable = (variable: string): string =>
  getComputedStyle(document.documentElement).getPropertyValue(variable).trim();

const adjustHexOpacity = (hexColor: string, opacity: number): string => {
  hexColor = hexColor.replace("#", "");
  const r = parseInt(hexColor.substring(0, 2), 16);
  const g = parseInt(hexColor.substring(2, 4), 16);
  const b = parseInt(hexColor.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
};

const adjustHSLOpacity = (hslColor: string, opacity: number): string =>
  hslColor.replace("hsl(", "hsla(").replace(")", `, ${opacity})`);

const adjustOKLCHOpacity = (oklchColor: string, opacity: number): string =>
  oklchColor.replace(/oklch\((.*?)\)/, (_m, p1) => `oklch(${p1} / ${opacity})`);

export const adjustColorOpacity = (color: string, opacity: number): string => {
  if (color.startsWith("#")) return adjustHexOpacity(color, opacity);
  if (color.startsWith("hsl")) return adjustHSLOpacity(color, opacity);
  if (color.startsWith("oklch")) return adjustOKLCHOpacity(color, opacity);
  // Already rgb/rgba or a named color — return as-is rather than throwing.
  return color;
};
