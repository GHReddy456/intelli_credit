import React from "react";
import {
  Chart as ChartJS, RadialLinearScale, PointElement, LineElement,
  Filler, Tooltip, Legend,
} from "chart.js";
import { Radar } from "react-chartjs-2";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

export default function RiskRadar({ analysis }) {
  const five = analysis?.decision?.five_cs_scores || {};
  const labels = ["Character", "Capacity", "Capital", "Collateral", "Conditions"];
  const values = [
    five.character  || 0,
    five.capacity   || 0,
    five.capital    || 0,
    five.collateral || 0,
    five.conditions || 0,
  ];

  const data = {
    labels,
    datasets: [{
      label: "Five Cs Score (0–100)",
      data: values,
      backgroundColor: "rgba(99, 102, 241, 0.25)",
      borderColor:     "rgba(99, 102, 241, 0.9)",
      pointBackgroundColor: values.map(v => v >= 70 ? "#10B981" : v >= 50 ? "#F59E0B" : "#EF4444"),
      pointRadius: 5,
      borderWidth: 2,
    }],
  };

  const options = {
    responsive: true,
    scales: {
      r: {
        min: 0, max: 100,
        ticks: { color: "#64748B", stepSize: 20, backdropColor: "transparent" },
        grid:        { color: "#d0f5fb" },
        angleLines:  { color: "#d0f5fb" },
        pointLabels: { color: "#334155", font: { size: 12 } },
      },
    },
    plugins: {
      legend: { labels: { color: "#475569" } },
    },
  };

  return (
    <div className="glass" style={{ padding: "24px", borderRadius: 16, maxWidth: 500, margin: "0 auto" }}>
      <h2 style={{ color: "#334155", fontWeight: 700, fontSize: 13, marginBottom: 16, textAlign: "center", textTransform: "uppercase", letterSpacing: "1px" }}>Five Cs Risk Radar</h2>
      <Radar data={data} options={options} />
      <div className="mt-4 grid grid-cols-5 gap-2 text-center">
        {labels.map((l, i) => {
          const v = values[i];
          const col = v >= 70 ? "#10B981" : v >= 50 ? "#F59E0B" : "#EF4444";
          return (
            <div key={l}>
              <p className="text-xs text-slate-500">{l}</p>
              <p className="font-bold text-sm" style={{ color: col }}>{v.toFixed(0)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
