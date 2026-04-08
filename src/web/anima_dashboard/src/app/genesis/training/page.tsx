"use client";

import React, { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Types
interface TrainingMetrics {
  step: number;
  loss: number;
  reward: number;
  coherence: number;
  gpu_util: number[];
  throughput: number;
  grad_norm: number;
}

interface DistributedStatus {
  rank: number;
  world_size: number;
  status: "healthy" | "warning" | "error";
  last_checkpoint: string;
  samples_processed: number;
}

// Hook for WebSocket connection to training backend
function useTrainingStream() {
  const [metrics, setMetrics] = useState<TrainingMetrics | null>(null);
  const [history, setHistory] = useState<TrainingMetrics[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Simulated WebSocket for demo - would connect to actual training backend
    const interval = setInterval(() => {
      const newMetric: TrainingMetrics = {
        step: (history.length > 0 ? history[history.length - 1].step : 0) + 1,
        loss: 2.0 * Math.exp(-history.length / 100) + Math.random() * 0.1,
        reward: -1.0 + 2.0 * (1 - Math.exp(-history.length / 200)) + Math.random() * 0.1,
        coherence: 0.4 + 0.1 * Math.sin(history.length / 50) + Math.random() * 0.05,
        gpu_util: Array.from({ length: 4 }, () => 70 + Math.random() * 25),
        throughput: 4500 + Math.random() * 500,
        grad_norm: 1.0 + Math.random() * 0.5,
      };
      
      setMetrics(newMetric);
      setHistory((prev) => [...prev.slice(-1000), newMetric]);
      setConnected(true);
    }, 100);

    return () => clearInterval(interval);
  }, [history.length]);

  return { metrics, history, connected };
}

// GPU Utilization Radar
function GPUUtilization({ utilizations }: { utilizations: number[] }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {utilizations.map((util, i) => (
        <div key={i} className="bg-gray-900 rounded p-2">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>GPU {i}</span>
            <span className={util > 90 ? "text-red-400" : "text-green-400"}>
              {util.toFixed(0)}%
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                util > 90
                  ? "bg-red-500"
                  : util > 70
                  ? "bg-yellow-500"
                  : "bg-green-500"
              }`}
              style={{ width: `${util}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// Training Timeline Chart
function TrainingChart({
  history,
  metric,
  color,
}: {
  history: TrainingMetrics[];
  metric: keyof TrainingMetrics;
  color: string;
}) {
  const data = {
    labels: history.map((m) => m.step.toString()),
    datasets: [
      {
        label: metric,
        data: history.map((m) => m[metric] as number),
        borderColor: color,
        backgroundColor: color + "20",
        fill: true,
        tension: 0.4,
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index" as const, intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#1a1a2e",
        borderColor: "#333",
        borderWidth: 1,
      },
    },
    scales: {
      x: { display: false },
      y: {
        grid: { color: "#333" },
        ticks: { color: "#666", font: { size: 10 } },
      },
    },
  };

  return (
    <div className="h-32">
      <Line data={data} options={options} />
    </div>
  );
}

// Causal Intervention Visualizer
function CausalGraph() {
  const [interventions, setInterventions] = useState<
    { layer: string; effect: number; active: boolean }[]
  >([
    { layer: "Knower (256→2048)", effect: 0.45, active: false },
    { layer: "Thinker (2048→512)", effect: 0.32, active: false },
    { layer: "Doer (512→12)", effect: 0.78, active: false },
  ]);

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h3 className="text-sm font-mono text-cyan-400 mb-3">Causal Interventions</h3>
      <div className="space-y-2">
        {interventions.map((inv, i) => (
          <div
            key={i}
            className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-all ${
              inv.active
                ? "border-cyan-500 bg-cyan-900/20"
                : "border-gray-700 hover:border-gray-600"
            }`}
            onClick={() =>
              setInterventions((prev) =>
                prev.map((p, j) => (j === i ? { ...p, active: !p.active } : p))
              )
            }
          >
            <div>
              <div className="text-xs text-gray-300">{inv.layer}</div>
              <div className="text-[10px] text-gray-500">
                Effect size: {inv.effect.toFixed(2)}
              </div>
            </div>
            <div
              className={`w-3 h-3 rounded-full ${
                inv.active ? "bg-cyan-400 animate-pulse" : "bg-gray-600"
              }`}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// Main Training Dashboard
export default function TrainingDashboard() {
  const { metrics, history, connected } = useTrainingStream();
  const [selectedTab, setSelectedTab] = useState<"overview" | "distributed" | "causal">("overview");

  return (
    <div className="min-h-screen bg-[#020208] text-gray-200 p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-mono text-green-400 font-bold">
              Training Dashboard
            </h1>
            <p className="text-sm text-gray-500">
              Live distributed training monitor
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div
              className={`px-3 py-1 rounded-full text-xs font-mono border ${
                connected
                  ? "border-green-500 text-green-400 bg-green-900/20"
                  : "border-red-500 text-red-400 bg-red-900/20"
              }`}
            >
              {connected ? "LIVE" : "DISCONNECTED"}
            </div>
            <button className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-mono text-sm transition">
              Export Report
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="flex gap-1 mb-6 border-b border-gray-800 pb-2">
        {[
          { key: "overview", label: "Overview", icon: "📊" },
          { key: "distributed", label: "Distributed", icon: "🌐" },
          { key: "causal", label: "Causal Analysis", icon: "🔬" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedTab(tab.key as any)}
            className={`px-4 py-2 font-mono text-sm rounded-t transition ${
              selectedTab === tab.key
                ? "text-green-400 border-b-2 border-green-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </nav>

      {/* Overview Tab */}
      {selectedTab === "overview" && (
        <div className="grid grid-cols-12 gap-4">
          {/* Key Metrics */}
          <div className="col-span-3 grid grid-cols-1 gap-3">
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">Steps</div>
              <div className="text-2xl font-mono text-white">
                {metrics?.step.toLocaleString() || "—"}
              </div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">Coherence</div>
              <div className="text-2xl font-mono text-cyan-400">
                {metrics?.coherence.toFixed(3) || "—"}
              </div>
              <div className="text-xs text-gray-600 mt-1">Target: 0.500</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">Throughput</div>
              <div className="text-2xl font-mono text-green-400">
                {Math.round(metrics?.throughput || 0).toLocaleString()}
              </div>
              <div className="text-xs text-gray-600 mt-1">steps/sec</div>
            </div>
          </div>

          {/* Charts */}
          <div className="col-span-6 space-y-4">
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs font-mono text-gray-400 mb-2">Loss</div>
              {history.length > 0 && (
                <TrainingChart history={history} metric="loss" color="#f87171" />
              )}
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs font-mono text-gray-400 mb-2">Reward</div>
              {history.length > 0 && (
                <TrainingChart history={history} metric="reward" color="#4ade80" />
              )}
            </div>
          </div>

          {/* GPU Status */}
          <div className="col-span-3">
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="text-xs font-mono text-gray-400 mb-3">
                GPU Utilization
              </div>
              {metrics && <GPUUtilization utilizations={metrics.gpu_util} />}
            </div>
          </div>
        </div>
      )}

      {/* Distributed Tab */}
      {selectedTab === "distributed" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-mono text-cyan-400 mb-4">World Topology</h3>
            <div className="grid grid-cols-4 gap-2">
              {Array.from({ length: 16 }, (_, i) => (
                <div
                  key={i}
                  className="aspect-square bg-gray-800 rounded flex items-center justify-center text-xs font-mono border border-gray-700 hover:border-cyan-500 transition"
                >
                  <div>
                    <div className="text-gray-500">R{i}</div>
                    <div className="text-green-400 text-[10px]">●</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 text-xs text-gray-500">
              World Size: 16 | Backend: NCCL | Gradient Accumulation: 4
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-mono text-cyan-400 mb-4">Communication Pattern</h3>
            <div className="h-64 flex items-center justify-center border border-gray-800 rounded">
              <div className="text-gray-600 text-sm">
                Ring-AllReduce visualization
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Causal Tab */}
      {selectedTab === "causal" && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-4">
            <CausalGraph />
          </div>
          <div className="col-span-8 bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-mono text-cyan-400 mb-3">
              Ablation Importance
            </h3>
            <div className="space-y-3">
              {[
                { layer: "encoder.0", importance: 0.95 },
                { layer: "encoder.1", importance: 0.87 },
                { layer: "knower.l1", importance: 0.72 },
                { layer: "thinker.l1", importance: 0.45 },
                { layer: "doer.l1", importance: 0.31 },
              ].map((item) => (
                <div key={item.layer} className="flex items-center gap-3">
                  <div className="w-32 text-xs text-gray-400 font-mono">
                    {item.layer}
                  </div>
                  <div className="flex-1 h-4 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full"
                      style={{ width: `${item.importance * 100}%` }}
                    />
                  </div>
                  <div className="w-12 text-xs text-right text-cyan-400">
                    {(item.importance * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
