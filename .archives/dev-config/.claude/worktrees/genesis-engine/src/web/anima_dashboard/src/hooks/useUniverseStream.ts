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
export function useUniverseStream(): UniverseStreamState {
  const [state, setState] = useState<UniverseState | null>(null);
  const [report, setReport] = useState<SynthesisReport | null>(null);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef(1000);

  const connect = useCallback(() => {
    esRef.current?.close();
    const es = new EventSource(`${API_BASE}/api/universe/stream`);
    esRef.current = es;

    es.addEventListener("tick", (e: MessageEvent) => {
      try {
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
      setError("Connection lost — reconnecting...");
      es.close();
      // Exponential backoff reconnect
      const delay = Math.min(retryRef.current, MAX_RECONNECT_DELAY);
      retryRef.current = delay * 2;
      setTimeout(connect, delay);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
    };
  }, [connect]);

  return { state, report, alerts, connected, error };
}
