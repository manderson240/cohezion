"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface AgentNode {
  id: string;
  regime: "exploit" | "explore" | "pivot" | "unknown";
  n_clusters: number;
  n_loops: number;
  persistence_entropy_h0: number;
  total_persistence: number;
}

const REGIME_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  exploit: { bg: "bg-green-900/30", border: "border-green-500", text: "text-green-400", label: "Exploit" },
  explore: { bg: "bg-cyan-900/30", border: "border-cyan-500", text: "text-cyan-400", label: "Explore" },
  pivot: { bg: "bg-red-900/30", border: "border-red-500", text: "text-red-400", label: "Pivot" },
  unknown: { bg: "bg-gray-900/30", border: "border-gray-600", text: "text-gray-400", label: "Unknown" },
};

const MODEL_COLORS: Record<string, string> = {
  "phi3": "#22d3ee",
  "qwen": "#fbbf24",
  "deepseek": "#a855f7",
  "default": "#6b7280",
};

interface SwarmTopologyVizProps {
  className?: string;
}

export default function SwarmTopologyViz({ className = "" }: SwarmTopologyVizProps) {
  const [agents, setAgents] = useState<AgentNode[]>([]);
  const [routingSummary, setRoutingSummary] = useState<Record<string, number>>({});

  const fetchTopology = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/swarm/metrics`);
      if (resp.ok) {
        const data = await resp.json();
        // Map swarm metrics to agent nodes
        if (data.agents) {
          setAgents(Object.values(data.agents));
        }
      }
    } catch {
      // Fallback demo data
      setAgents([
        { id: "architect", regime: "exploit", n_clusters: 2, n_loops: 0, persistence_entropy_h0: 0.3, total_persistence: 1.2 },
        { id: "engineer", regime: "explore", n_clusters: 4, n_loops: 1, persistence_entropy_h0: 0.8, total_persistence: 2.1 },
        { id: "biologist", regime: "exploit", n_clusters: 1, n_loops: 0, persistence_entropy_h0: 0.1, total_persistence: 0.8 },
        { id: "quantum_hw", regime: "unknown", n_clusters: 0, n_loops: 0, persistence_entropy_h0: 0.0, total_persistence: 0.0 },
        { id: "quantum_algo", regime: "pivot", n_clusters: 3, n_loops: 2, persistence_entropy_h0: 1.1, total_persistence: 3.5 },
      ]);
      setRoutingSummary({ exploit: 2, explore: 1, pivot: 1, unknown: 1 });
    }
  }, []);

  useEffect(() => {
    fetchTopology();
    const interval = setInterval(fetchTopology, 15000);
    return () => clearInterval(interval);
  }, [fetchTopology]);

  // Compute regime distribution
  const regimeCounts = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.regime] = (acc[a.regime] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <h3 className="text-sm text-green-400 font-bold mb-3">Swarm Topology (TDA-Driven)</h3>

      {/* Agent grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
        {agents.map((agent) => {
          const style = REGIME_COLORS[agent.regime] || REGIME_COLORS.unknown;
          return (
            <div
              key={agent.id}
              className={`${style.bg} border ${style.border} rounded-lg p-3 transition-all hover:scale-[1.02]`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-[11px] font-bold ${style.text}`}>
                  {agent.id}
                </span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded ${style.bg} ${style.text} border ${style.border}`}>
                  {style.label}
                </span>
              </div>
              <div className="text-[9px] text-gray-500 space-y-0.5">
                <div>H0 clusters: {agent.n_clusters} | H1 loops: {agent.n_loops}</div>
                <div>Entropy: {agent.persistence_entropy_h0.toFixed(2)} | Persistence: {agent.total_persistence.toFixed(2)}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Regime distribution */}
      <div className="border-t border-gray-800 pt-3">
        <div className="text-[10px] text-gray-500 mb-2">Regime Distribution</div>
        <div className="flex gap-2 mb-3">
          {Object.entries(REGIME_COLORS).map(([regime, style]) => {
            const count = regimeCounts[regime] || 0;
            if (count === 0) return null;
            return (
              <div key={regime} className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${style.border} border`} />
                <span className={`text-[10px] ${style.text}`}>
                  {style.label}: {count}
                </span>
              </div>
            );
          })}
        </div>

        {/* Horizontal bar chart — static mock data */}
        <div className="space-y-2">
          {[
            { label: "Exploit", pct: 60, count: 24, color: "#10b981" },
            { label: "Explore", pct: 30, count: 12, color: "#3b82f6" },
            { label: "Pivot", pct: 10, count: 4, color: "#f59e0b" },
          ].map((bar) => (
            <div key={bar.label} className="flex items-center gap-2">
              <span className="text-[10px] w-12 text-right" style={{ color: bar.color }}>
                {bar.label}
              </span>
              <div className="flex-1 bg-gray-900 rounded h-4 overflow-hidden">
                <div
                  className="h-full rounded transition-all duration-500"
                  style={{ width: `${bar.pct}%`, backgroundColor: bar.color }}
                />
              </div>
              <span className="text-[10px] text-gray-400 w-20 text-right">
                {bar.pct}% ({bar.count} agents)
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Routing explanation */}
      <div className="mt-3 pt-2 border-t border-gray-800 text-[9px] text-gray-600 italic">
        TDA classifies agents by trajectory topology: H0 clusters = behavioral modes,
        H1 loops = stuck cycling. Simple tasks → exploit agents. Complex → explore. Pivot agents need new strategy.
      </div>

      {/* Persistence Diagram */}
      <div className="mt-3 pt-3 border-t border-gray-800">
        <div className="text-[10px] text-gray-500 mb-2">Persistence Diagram (H0 + H1)</div>
        <svg viewBox="0 0 300 300" className="w-full max-w-[300px]" preserveAspectRatio="xMidYMid meet">
          {/* Background */}
          <rect x={30} y={10} width={260} height={260} fill="#0a0a1a" rx={4} />
          {/* Diagonal (birth = death) */}
          <line x1={30} y1={270} x2={290} y2={10} stroke="#333" strokeWidth={1} strokeDasharray="4,4" />
          {/* Axes */}
          <line x1={30} y1={270} x2={290} y2={270} stroke="#555" strokeWidth={1} />
          <line x1={30} y1={270} x2={30} y2={10} stroke="#555" strokeWidth={1} />
          <text x={160} y={295} fill="#666" fontSize={9} textAnchor="middle">Birth</text>
          <text x={10} y={145} fill="#666" fontSize={9} textAnchor="middle" transform="rotate(-90, 10, 145)">Death</text>
          {/* H0 points (clusters) — green circles */}
          {/* Near diagonal: short-lived */}
          <circle cx={60} cy={240} r={4} fill="#10b981" opacity={0.8}><title>H0: birth=0.1, death=0.2</title></circle>
          <circle cx={90} cy={220} r={4} fill="#10b981" opacity={0.8}><title>H0: birth=0.2, death=0.4</title></circle>
          <circle cx={120} cy={200} r={4} fill="#10b981" opacity={0.8}><title>H0: birth=0.3, death=0.5</title></circle>
          <circle cx={80} cy={235} r={4} fill="#10b981" opacity={0.8}><title>H0: birth=0.18, death=0.25</title></circle>
          <circle cx={140} cy={195} r={4} fill="#10b981" opacity={0.8}><title>H0: birth=0.4, death=0.55</title></circle>
          {/* Far from diagonal: persistent clusters */}
          <circle cx={50} cy={100} r={6} fill="#10b981" opacity={0.9}><title>H0: birth=0.05, death=0.85 (persistent)</title></circle>
          <circle cx={70} cy={50} r={6} fill="#10b981" opacity={0.9}><title>H0: birth=0.12, death=0.95 (persistent)</title></circle>
          <circle cx={100} cy={70} r={5} fill="#10b981" opacity={0.9}><title>H0: birth=0.25, death=0.92 (persistent)</title></circle>
          {/* H1 points (loops) — purple circles */}
          <circle cx={110} cy={160} r={5} fill="#a855f7" opacity={0.8}><title>H1: birth=0.28, death=0.65</title></circle>
          <circle cx={150} cy={120} r={5} fill="#a855f7" opacity={0.8}><title>H1: birth=0.42, death=0.78</title></circle>
          <circle cx={180} cy={150} r={4} fill="#a855f7" opacity={0.8}><title>H1: birth=0.55, death=0.7</title></circle>
          <circle cx={130} cy={140} r={4} fill="#a855f7" opacity={0.8}><title>H1: birth=0.35, death=0.72</title></circle>
          {/* Legend */}
          <circle cx={200} cy={25} r={4} fill="#10b981" />
          <text x={210} y={28} fill="#10b981" fontSize={9}>H0 (clusters)</text>
          <circle cx={200} cy={42} r={4} fill="#a855f7" />
          <text x={210} y={45} fill="#a855f7" fontSize={9}>H1 (loops)</text>
        </svg>
        <div className="text-[9px] text-gray-600 mt-1 italic">
          Points far from the diagonal = persistent topological features.
          Large H0 features = stable agent clusters. H1 loops = recurring behavior cycles.
        </div>
      </div>
    </div>
  );
}
