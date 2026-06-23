import { useRef, useEffect, useState } from "react";
import {
  Chart, DoughnutController, ArcElement, Tooltip, type ChartData,
} from "chart.js";
import { chartColors } from "./ChartjsConfig";
import { useTheme } from "../ThemeContext";

Chart.register(DoughnutController, ArcElement, Tooltip);

export default function DoughnutChart({
  data,
  height = 180,
  legend = true,
}: {
  data: ChartData<"doughnut">;
  height?: number;
  legend?: boolean;
}) {
  const [chart, setChart] = useState<Chart<"doughnut"> | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();
  const darkMode = theme === "dark";
  const { tooltipTitleColor, tooltipBodyColor, tooltipBgColor, tooltipBorderColor } = chartColors;

  useEffect(() => {
    if (!canvas.current) return;
    const newChart = new Chart<"doughnut", number[], unknown>(canvas.current, {
      type: "doughnut",
      data,
      options: {
        cutout: "80%",
        layout: { padding: 16 },
        plugins: {
          legend: { display: false },
          tooltip: {
            titleColor: darkMode ? tooltipTitleColor.dark : tooltipTitleColor.light,
            bodyColor: darkMode ? tooltipBodyColor.dark : tooltipBodyColor.light,
            backgroundColor: darkMode ? tooltipBgColor.dark : tooltipBgColor.light,
            borderColor: darkMode ? tooltipBorderColor.dark : tooltipBorderColor.light,
          },
        },
        interaction: { intersect: false, mode: "nearest" },
        animation: { duration: 500 },
        maintainAspectRatio: false,
        resizeDelay: 200,
      },
    });
    setChart(newChart);
    return () => newChart.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep chart data in sync as live values change.
  useEffect(() => {
    if (!chart) return;
    chart.data = data;
    chart.update("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  useEffect(() => {
    if (!chart || !chart.options.plugins?.tooltip) return;
    const tt = chart.options.plugins.tooltip;
    tt.titleColor = darkMode ? tooltipTitleColor.dark : tooltipTitleColor.light;
    tt.bodyColor = darkMode ? tooltipBodyColor.dark : tooltipBodyColor.light;
    tt.backgroundColor = darkMode ? tooltipBgColor.dark : tooltipBgColor.light;
    tt.borderColor = darkMode ? tooltipBorderColor.dark : tooltipBorderColor.light;
    chart.update("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  const labels = (data.labels ?? []) as string[];
  const colors = (data.datasets[0]?.backgroundColor ?? []) as string[];
  const values = (data.datasets[0]?.data ?? []) as number[];

  return (
    <div className="grow flex flex-col justify-center">
      <div style={{ height }}>
        <canvas ref={canvas}></canvas>
      </div>
      {legend && (
        <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-1">
          {labels.map((l, i) => (
            <li key={l} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: colors[i] }} />
              {l} <span className="text-gray-400 dark:text-gray-500">({values[i] ?? 0})</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
