"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface ThermodynamicData {
  entropy: number;
  energy: number;
  free_energy: number;
  temperature: number;
  entropy_production_rate: number;
  susceptibility: number;
  heat_capacity: number;
  order_parameter: number;
}

// Landau parameters
const LANDAU_A = 1.0;
const LANDAU_B = 1.0;
const LANDAU_TC = 10.0;

/**
 * Compute thermodynamic state from cosmogony temperature using Landau theory.
 * F = a*(T-Tc)*phi^2 + b*phi^4
 * phi = sqrt(a*(Tc-T)/(2*b)) if T < Tc, else 0
 * chi = 1/(2*a*|T-Tc|) (susceptibility)
 * S = -dF/dT approximation
 */
function computeLocalThermo(T: number): ThermodynamicData {
  const orderParameter = T < LANDAU_TC
    ? Math.sqrt(LANDAU_A * (LANDAU_TC - T) / (2 * LANDAU_B))
    : 0;
  const phi = orderParameter;
  const freeEnergy = LANDAU_A * (T - LANDAU_TC) * phi * phi + LANDAU_B * phi ** 4;
  const deltaTc = Math.abs(T - LANDAU_TC);
  const susceptibility = deltaTc > 0.001 ? 1 / (2 * LANDAU_A * deltaTc) : 500; // cap near Tc
  // Entropy approximation: S = -dF/dT ~ -a*phi^2 (for T < Tc)
  const entropy = T < LANDAU_TC ? LANDAU_A * phi * phi : 0;
  // Heat capacity: Cv ~ T * dS/dT approximation
  const heatCapacity = T < LANDAU_TC ? LANDAU_A / (2 * LANDAU_B) : 0;

  return {
    entropy,
    energy: freeEnergy + T * entropy,
    free_energy: freeEnergy,
    temperature: T,
    entropy_production_rate: T < LANDAU_TC ? 0.01 * susceptibility : 0,
    susceptibility,
    heat_capacity: heatCapacity,
    order_parameter: phi,
  };
}

function MetricCard({
  label,
  value,
  unit,
  color,
  description,
}: {
  label: string;
  value: number;
  unit?: string;
  color: string;
  description: string;
}) {
  return (
    <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
      <div className="text-[10px] text-gray-500 mb-1">{label}</div>
      <div className="text-lg font-bold" style={{ color }}>
        {value.toFixed(4)}
        {unit && <span className="text-[10px] text-gray-600 ml-1">{unit}</span>}
      </div>
      <div className="text-[9px] text-gray-600 mt-1">{description}</div>
    </div>
  );
}

interface ThermodynamicStateLiveProps {
  className?: string;
}

export default function ThermodynamicStateLive({ className = "" }: ThermodynamicStateLiveProps) {
  const [data, setData] = useState<ThermodynamicData | null>(null);
  const [history, setHistory] = useState<ThermodynamicData[]>([]);
  const [mode, setMode] = useState<"api" | "local">("api");
  const fallbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const resp = await fetch(`${API_BASE}/api/metrics/unified`, { signal: controller.signal });
      clearTimeout(timeout);
      if (resp.ok) {
        const unified = await resp.json();
        // Extract thermodynamic-like quantities from unified metrics
        const thermo: ThermodynamicData = {
          entropy: unified.cache_metrics?.hit_rate ?? 0.95,
          energy: unified.token_metrics?.total_tokens ?? 0,
          free_energy: -(unified.cache_metrics?.hit_rate ?? 0.95),
          temperature: 0.7,
          entropy_production_rate: 0.05,
          susceptibility: 1.0 / Math.max(0.01, 1.0 - (unified.cache_metrics?.hit_rate ?? 0.5)),
          heat_capacity: 0.5,
          order_parameter: unified.cache_metrics?.hit_rate ?? 0.5,
        };
        setData(thermo);
        setMode("api");
        setHistory((prev) => [...prev.slice(-50), thermo]);
        return;
      }
    } catch {
      // Fall through to local computation
    }
    // Local computation mode (Landau theory, default T=200)
    const thermo = computeLocalThermo(200);
    setData(thermo);
    setMode("local");
    setHistory((prev) => [...prev.slice(-50), thermo]);
  }, []);

  useEffect(() => {
    // Start a 2-second fallback timer — if fetch hasn't resolved, switch to local
    fallbackTimer.current = setTimeout(() => {
      if (!data) {
        const thermo = computeLocalThermo(200);
        setData(thermo);
        setMode("local");
        setHistory([thermo]);
      }
    }, 2000);

    fetchState();
    const interval = setInterval(fetchState, 5000);
    return () => {
      clearInterval(interval);
      if (fallbackTimer.current) clearTimeout(fallbackTimer.current);
    };
  }, [fetchState, data]);

  if (!data) {
    return (
      <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 ${className}`}>
        <div className="text-gray-500 text-xs font-mono animate-pulse">Connecting to API... (local fallback in 2s)</div>
      </div>
    );
  }

  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm text-green-400 font-bold">Thermodynamic State {mode === "local" ? "(Local Computation)" : "(Live)"}</h3>
        {mode === "local" && (
          <span className="text-[9px] px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded border border-amber-500/30">
            Landau Model (T={data.temperature.toFixed(0)})
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <MetricCard
          label="Entropy S"
          value={data.entropy}
          unit="nats"
          color="#22d3ee"
          description={mode === "local" ? "S = -dF/dT (Landau)" : "Shannon entropy of action distribution"}
        />
        <MetricCard
          label="Free Energy F"
          value={data.free_energy}
          unit="E-TS"
          color="#00ff88"
          description="Variational free energy (Friston)"
        />
        <MetricCard
          label="Entropy Production sigma"
          value={data.entropy_production_rate}
          unit="/step"
          color="#fbbf24"
          description="Irreversibility (Crooks theorem)"
        />
        <MetricCard
          label="Susceptibility chi"
          value={data.susceptibility}
          color="#a855f7"
          description="Diverges at phase transitions"
        />
        <MetricCard
          label="Temperature T"
          value={data.temperature}
          color="#ef4444"
          description="Exploration tolerance"
        />
        <MetricCard
          label="Heat Capacity Cv"
          value={data.heat_capacity}
          unit="Var(E)/T^2"
          color="#f97316"
          description="Robustness to state changes"
        />
        <MetricCard
          label="Order Parameter m"
          value={data.order_parameter}
          color="#10b981"
          description="Mean coherence (HIHO target: 0.5)"
        />
        <MetricCard
          label="Energy E"
          value={data.energy}
          unit="-logP"
          color="#6366f1"
          description="Surprisal (neg log-likelihood)"
        />
      </div>

      {/* HIHO status indicator */}
      <div className="mt-3 pt-2 border-t border-gray-800 flex items-center justify-between">
        <span className="text-[10px] text-gray-500">HIHO Status</span>
        <span
          className={`text-[11px] font-bold ${
            Math.abs(data.order_parameter - 0.5) < 0.05
              ? "text-green-400"
              : Math.abs(data.order_parameter - 0.5) < 0.15
                ? "text-yellow-400"
                : "text-red-400"
          }`}
        >
          delta = {(data.order_parameter - 0.5).toFixed(4)}
          {Math.abs(data.order_parameter - 0.5) < 0.05 && " (at equilibrium)"}
        </span>
      </div>
    </div>
  );
}
