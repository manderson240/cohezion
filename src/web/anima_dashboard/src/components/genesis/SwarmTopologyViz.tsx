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
        <div className="flex gap-2">
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
      </div>

      {/* Routing explanation */}
      <div className="mt-3 pt-2 border-t border-gray-800 text-[9px] text-gray-600 italic">
        TDA classifies agents by trajectory topology: H0 clusters = behavioral modes,
        H1 loops = stuck cycling. Simple tasks → exploit agents. Complex → explore. Pivot agents need new strategy.
      </div>
    </div>
  );
}
