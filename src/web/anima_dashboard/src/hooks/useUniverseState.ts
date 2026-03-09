"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/** Physics state of a single EVO charge cluster. */
export interface EvoState {
  charge_density: number;
  magnetic_helicity: number;
  toroidal_moment: number;
  coherence: number;
}

/** Snapshot of the universe physics state from the API. */
export interface UniverseState {
  tick: number;
  coherence: number;
  ca_grid: number[];
  evo_states: EvoState[];
  time: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/**
 * Polls the universe API, ticking the simulation on each interval.
 * Returns live physics state driven by the real HIHO engine.
 *
 * @param intervalMs - Polling interval in milliseconds (default 3000)
 */
export function useUniverseState(intervalMs = 3000) {
  const [state, setState] = useState<UniverseState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  const fetchTick = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/universe/tick`, {
        method: "POST",
        signal: controller.signal,
      });
      if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
      }
      const data: UniverseState = await resp.json();
      setState(data);
      setError(null);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchTick();

    const interval = setInterval(fetchTick, intervalMs);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetchTick, intervalMs]);

  return { state, error, loading };
}
