"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// Re-export shared types (canonical source for all universe state types)
export interface EvoState {
  charge_density: number;
  magnetic_helicity: number;
  toroidal_moment: number;
  coherence: number;
}

export interface UniverseState {
  tick: number;
  coherence: number;
  ca_grid: number[];
  evo_states: EvoState[];
  time: number;
}

export interface SynthesisReport {
  tick: number;
  time: number;
  hiho_status: {
    mean_coherence: number;
    stability: string;
    deviation_from_target: number;
    target: number;
  };
  ca_analysis: {
    density: number;
    active_cells: number;
    total_cells: number;
    rule: number;
  };
  evo_health: Array<{
    id: number;
    coherence: number;
    charge_density: number;
    charge_status: string;
    magnetic_helicity: number;
    toroidal_moment: number;
  }>;
  summary: string;
  topology: {
    persistence_pairs: Array<{
      birth: number;
      death: number;
      dimension: number;
      persistence: number;
    }>;
    entropy: number;
    n_clusters: number;
    n_loops: number;
  } | null;
}

export interface AlertEvent {
  kind: string;
  message: string;
}

export interface UniverseStreamState {
  state: UniverseState | null;
  report: SynthesisReport | null;
  alerts: AlertEvent[];
  connected: boolean;
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
const MAX_RECONNECT_DELAY = 30_000;

/**
 * SSE hook that streams live universe ticks from the Master Clock.
 * Replaces polling — all Triune modes share one connection via UniverseProvider.
 */
/**
 * Generate fallback physics locally when backend is unreachable.
 * Ticks coherence toward HIHO 0.5, generates a simple CA grid,
 * and creates wandering EVO states.
 */
function createFallbackTick(prev: UniverseState | null): UniverseState {
  const tick = (prev?.tick ?? 0) + 1;
  const prevCoherence = prev?.coherence ?? 0.3;
  const coherence = Math.max(
    0,
    Math.min(
      1,
      prevCoherence + (0.5 - prevCoherence) * 0.05 + (Math.random() - 0.5) * 0.02
    )
  );

  // Simple CA grid: 100 cells, random flip ~5% each tick
  const prevGrid = prev?.ca_grid ?? Array.from({ length: 100 }, () => (Math.random() > 0.5 ? 1 : 0));
  const ca_grid = prevGrid.map((cell) => (Math.random() < 0.05 ? 1 - cell : cell));

  // 3-5 mock EVOs with wandering positions
  const nEvos = prev?.evo_states?.length ?? 3 + Math.floor(Math.random() * 3);
  const evo_states: EvoState[] = Array.from({ length: nEvos }, (_, i) => {
    const prevEvo = prev?.evo_states?.[i];
    return {
      charge_density: (prevEvo?.charge_density ?? Math.random()) + (Math.random() - 0.5) * 0.02,
      magnetic_helicity: (prevEvo?.magnetic_helicity ?? Math.random() * 0.5) + (Math.random() - 0.5) * 0.01,
      toroidal_moment: (prevEvo?.toroidal_moment ?? Math.random() * 0.3) + (Math.random() - 0.5) * 0.01,
      coherence: Math.max(0, Math.min(1, coherence + (Math.random() - 0.5) * 0.1)),
    };
  });

  return {
    tick,
    coherence,
    ca_grid,
    evo_states,
    time: Date.now() / 1000,
  };
}

export function useUniverseStream(): UniverseStreamState {
  const [state, setState] = useState<UniverseState | null>(null);
  const [report, setReport] = useState<SynthesisReport | null>(null);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef(1000);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start local fallback physics simulation
  const startFallback = useCallback(() => {
    if (fallbackRef.current) return; // Already running
    fallbackRef.current = setInterval(() => {
      setState((prev) => createFallbackTick(prev));
    }, 100);
  }, []);

  // Stop local fallback when real connection resumes
  const stopFallback = useCallback(() => {
    if (fallbackRef.current) {
      clearInterval(fallbackRef.current);
      fallbackRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    esRef.current?.close();
    const es = new EventSource(`${API_BASE}/api/universe/stream`);
    esRef.current = es;

    es.addEventListener("tick", (e: MessageEvent) => {
      try {
        stopFallback();
        setState(JSON.parse(e.data));
        setConnected(true);
        setError(null);
        retryRef.current = 1000; // Reset backoff on success
      } catch {
        // Ignore malformed events
      }
    });

    es.addEventListener("report", (e: MessageEvent) => {
      try {
        setReport(JSON.parse(e.data));
      } catch {
        // Ignore malformed events
      }
    });

    es.addEventListener("alert", (e: MessageEvent) => {
      try {
        const alert: AlertEvent = JSON.parse(e.data);
        setAlerts((prev) => [...prev.slice(-49), alert]); // Keep last 50
      } catch {
        // Ignore malformed events
      }
    });

    es.onerror = () => {
      setConnected(false);
      setError("Backend offline — running local physics simulation");
      es.close();
      // Start fallback physics while disconnected
      startFallback();
      // Exponential backoff reconnect
      const delay = Math.min(retryRef.current, MAX_RECONNECT_DELAY);
      retryRef.current = delay * 2;
      setTimeout(connect, delay);
    };
  }, [startFallback, stopFallback]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      stopFallback();
    };
  }, [connect, stopFallback]);

  return { state, report, alerts, connected, error };
}
