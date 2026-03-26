"use client";

import { useState, useCallback, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

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

  const setTemperature = useCallback(async (t: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/cosmogony/set-temperature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ temperature: t }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setState(data);
      }
    } catch {
      // Offline — set minimal state
      setState((prev) => prev ? { ...prev, temperature: t } : null);
    }
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
