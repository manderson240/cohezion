"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/**
 * Compute local Landau cosmogony state when backend is unreachable.
 */
function computeLocalCosmogony(temp: number): CosmogonyState {
  const criticalTemps = [100, 10, 1.0, 0.1, 0.01];
  const symmetries = ["void", "SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"];

  let stageIdx = 0;
  for (let i = 0; i < criticalTemps.length; i++) {
    if (temp < criticalTemps[i]) stageIdx = i + 1;
  }
  const sym = symmetries[stageIdx];
  const stage = stageIdx - 1;

  const a = 1.0;
  const b = 0.5;
  const criticalTemp = criticalTemps[Math.max(0, stageIdx - 1)] ?? 100;
  const orderParameter =
    temp < criticalTemp
      ? Math.sqrt(a * (criticalTemp - temp) / (2 * b))
      : 0;
  const landauFreeEnergy =
    orderParameter > 0
      ? a * (temp - criticalTemp) * orderParameter ** 2 + b * orderParameter ** 4
      : 0;

  const closestTc = criticalTemps.reduce((closest, tc) =>
    Math.abs(tc - temp) < Math.abs(closest - temp) ? tc : closest
  );
  const fisherEig = closestTc > 0 ? 1 / (Math.abs(temp - closestTc) + 0.01) : 0;

  const transitionNames = ["SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"];
  const transitions = criticalTemps
    .filter((tc) => temp < tc)
    .map((tc, i) => ({
      from: i === 0 ? "void" : transitionNames[i - 1],
      to: transitionNames[i],
      T_critical: tc,
      stage: i,
    }));

  return {
    temperature: temp,
    symmetry: sym,
    stage,
    order_parameters: { fabric_differentiation: orderParameter },
    transitions,
    fisher_eigenvalue_max: fisherEig,
    landau_free_energy: landauFreeEnergy,
  };
}

export interface CosmogonyState {
  temperature: number;
  symmetry: string;
  stage: number;
  order_parameters: Record<string, number>;
  transitions: Array<{
    from: string;
    to: string;
    T_critical: number;
    stage: number;
  }>;
  fisher_eigenvalue_max: number;
  landau_free_energy: number;
}

export interface ManifoldSummary {
  cosmogony: CosmogonyState;
  fiber_bundle: {
    base: number[];
    fiber: number[][];
    fabric_norms: Record<string, number>;
  };
  gauge: {
    fabrics: Record<string, { energy_density: number; norm: number }>;
    yang_mills_action: number;
    is_hiho: boolean;
  };
  spinor: {
    bloch_vector: number[];
    coherence: number;
    charge_polarity: number;
    spin_rotation: number;
    spin_precession: number;
    hiho_deviation: number;
  };
  state_12d: number[];
}

interface CosmogonyControls {
  state: CosmogonyState | null;
  summary: ManifoldSummary | null;
  loading: boolean;
  setTemperature: (t: number) => void;
  cool: (dt: number) => void;
  reset: () => void;
  fetchSummary: () => Promise<void>;
}

export function useCosmogony(): CosmogonyControls {
  const [state, setState] = useState<CosmogonyState | null>(null);
  const [summary, setSummary] = useState<ManifoldSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const prevSymmetryRef = useRef<string>("");

  const setTemperature = useCallback((t: number) => {
    // Local Landau math — no API needed
    setState(computeLocalCosmogony(t));
  }, []);

  const cool = useCallback(async (dt: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/cosmogony/cool`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delta_t: dt }),
      });
      if (resp.ok) setState(await resp.json());
    } catch { /* offline */ }
  }, []);

  const reset = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/cosmogony/reset`, {
        method: "POST",
      });
      if (resp.ok) setState(await resp.json());
    } catch { /* offline */ }
  }, []);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/manifold-summary`);
      if (resp.ok) {
        const data = await resp.json();
        setSummary(data);
        setState(data.cosmogony);
      }
    } catch { /* offline */ }
    setLoading(false);
  }, []);

  // Initial fetch
  useEffect(() => {
    setTemperature(200.0);
  }, [setTemperature]);

  return { state, summary, loading, setTemperature, cool, reset, fetchSummary };
}
