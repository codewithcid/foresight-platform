import { useRef, useEffect, useState } from "react";
import {
  Chart, BarController, BarElement, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, Tooltip,
} from "chart.js";
import { chartColors } from "./ChartjsConfig";
import { adjustColorOpacity } from "./utils";
import { useTheme } from "../ThemeContext";

Chart.register(BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip);

const pct = (v: number) => `${(v * 100).toFixed(1)}pp`;

export default function DecileChart({
  predicted,
  observed,
  height = 240,
}: {
  predicted: number[];
  observed: (number | null)[];
  height?: number;
}) {
  const [chart, setChart] = useState<Chart | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();
  const darkMode = theme === "dark";
  const { tooltipBodyColor, tooltipBgColor, tooltipBorderColor, gridColor, textColor } = chartColors;

  const grid = darkMode ? gridColor.dark : gridColor.light;
  const text = darkMode ? textColor.dark : textColor.light;

  useEffect(() => {
    if (!canvas.current) return;
    const newChart = new Chart(canvas.current, {
      type: "bar",
      data: {
        labels: predicted.map((_, i) => `${i + 1}`),
        datasets: [
          {
            type: "bar",
            label: "Observed lift",
            data: observed.map((o) => (o == null ? 0 : o)),
            backgroundColor: adjustColorOpacity("#ffb600", 0.5),
            hoverBackgroundColor: adjustColorOpacity("#ffb600", 0.75),
            borderRadius: 4,
            order: 2,
          },
          {
            type: "line",
            label: "Predicted uplift",
            data: predicted,
            borderColor: "#34e0a1",
            borderWidth: 2.5,
            pointRadius: 2,
            pointBackgroundColor: "#34e0a1",
            tension: 0.35,
            order: 1,
          } as any,
        ],
      },
      options: {
        layout: { padding: 8 },
        scales: {
          y: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: grid },
            ticks: { color: text, callback: (v) => `${(Number(v) * 100).toFixed(0)}%` },
          },
          x: {
            border: { display: false },
            grid: { display: false },
            ticks: { color: text },
            title: { display: true, text: "uplift decile (1 = most persuadable, ranked by model)", color: text, font: { size: 10 } },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (c) => `${c.dataset.label}: ${pct(Number(c.parsed.y))}` },
            bodyColor: darkMode ? tooltipBodyColor.dark : tooltipBodyColor.light,
            backgroundColor: darkMode ? tooltipBgColor.dark : tooltipBgColor.light,
            borderColor: darkMode ? tooltipBorderColor.dark : tooltipBorderColor.light,
          },
        },
        interaction: { intersect: false, mode: "index" },
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
    chart.data.labels = predicted.map((_, i) => `${i + 1}`);
    chart.data.datasets[0].data = observed.map((o) => (o == null ? 0 : o));
    chart.data.datasets[1].data = predicted;
    chart.update("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predicted, observed]);

  useEffect(() => {
    if (!chart) return;
    const sc: any = chart.options.scales;
    if (sc?.y) { sc.y.grid.color = grid; sc.y.ticks.color = text; }
    if (sc?.x) { sc.x.ticks.color = text; sc.x.title.color = text; }
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
