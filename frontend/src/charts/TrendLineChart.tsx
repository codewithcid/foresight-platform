import { useRef, useEffect, useState } from "react";
import {
  Chart, LineController, LineElement, Filler, PointElement, LinearScale, CategoryScale, Tooltip,
} from "chart.js";
import { chartAreaGradient, chartColors } from "./ChartjsConfig";
import { adjustColorOpacity } from "./utils";
import { useTheme } from "../ThemeContext";

Chart.register(LineController, LineElement, Filler, PointElement, LinearScale, CategoryScale, Tooltip);

export default function TrendLineChart({
  values,
  labels,
  color = "#ffb600",
  height = 128,
  formatY = (n: number) => String(Math.round(n)),
}: {
  values: number[];
  labels?: (string | number)[];
  color?: string;
  height?: number;
  formatY?: (n: number) => string;
}) {
  const [chart, setChart] = useState<Chart<"line"> | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();
  const darkMode = theme === "dark";
  const { tooltipBodyColor, tooltipBgColor, tooltipBorderColor } = chartColors;

  useEffect(() => {
    if (!canvas.current) return;
    const newChart = new Chart<"line", number[], unknown>(canvas.current, {
      type: "line",
      data: {
        labels: labels ?? values.map((_, i) => i + 1),
        datasets: [
          {
            data: values,
            borderColor: color,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            pointBackgroundColor: color,
            tension: 0.35,
            fill: true,
            backgroundColor: (ctx: any) => {
              const { chart } = ctx;
              const { ctx: c, chartArea } = chart;
              return chartAreaGradient(c, chartArea, [
                { stop: 0, color: adjustColorOpacity(color, 0) },
                { stop: 1, color: adjustColorOpacity(color, 0.25) },
              ]);
            },
            clip: 20,
          },
        ],
      },
      options: {
        layout: { padding: 8 },
        scales: {
          y: { display: false, beginAtZero: true },
          x: { display: false },
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: () => "",
              label: (context: any) => formatY(context.parsed.y),
            },
            bodyColor: darkMode ? tooltipBodyColor.dark : tooltipBodyColor.light,
            backgroundColor: darkMode ? tooltipBgColor.dark : tooltipBgColor.light,
            borderColor: darkMode ? tooltipBorderColor.dark : tooltipBorderColor.light,
          },
          legend: { display: false },
        },
        interaction: { intersect: false, mode: "nearest" },
        maintainAspectRatio: false,
        resizeDelay: 200,
      },
    });
    setChart(newChart);
    return () => newChart.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!chart) return;
    chart.data.labels = labels ?? values.map((_, i) => i + 1);
    chart.data.datasets[0].data = values;
    chart.update("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values]);

  useEffect(() => {
    if (!chart) return;
    const tt = chart.options.plugins!.tooltip!;
    tt.bodyColor = darkMode ? tooltipBodyColor.dark : tooltipBodyColor.light;
    tt.backgroundColor = darkMode ? tooltipBgColor.dark : tooltipBgColor.light;
    tt.borderColor = darkMode ? tooltipBorderColor.dark : tooltipBorderColor.light;
    chart.update("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  return (
    <div style={{ height }}>
      <canvas ref={canvas}></canvas>
    </div>
  );
}
