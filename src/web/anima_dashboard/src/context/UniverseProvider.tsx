"use client";

import {
  createContext,
  useContext,
  useCallback,
  type ReactNode,
} from "react";

import {
  useUniverseStream,
  type UniverseState,
  type SynthesisReport,
  type AlertEvent,
} from "@/hooks/useUniverseStream";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export interface UniverseContextValue {
  /** Current tick state (null until first event). */
  state: UniverseState | null;
  /** Latest synthesis report (emitted every 10th tick). */
  report: SynthesisReport | null;
  /** Rolling alert buffer (last 50). */
  alerts: AlertEvent[];
  /** Whether the SSE stream is connected. */
  connected: boolean;
  /** Error message if disconnected. */
  error: string | null;
  /** Inject a perturbation into the universe. */
  perturb: (kind: string, magnitude?: number) => Promise<void>;
  /** Fetch a one-shot synthesis report. */
  fetchReport: () => Promise<SynthesisReport | null>;
}

const UniverseContext = createContext<UniverseContextValue | null>(null);

export function UniverseProvider({ children }: { children: ReactNode }) {
  const stream = useUniverseStream();

  const perturb = useCallback(
    async (kind: string, magnitude = 0.2) => {
      try {
        await fetch(`${API_BASE}/api/universe/perturb`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind, magnitude }),
        });
      } catch {
        // Non-blocking — stream will show the result on next tick
      }
    },
    [],
  );

  const fetchReport = useCallback(async (): Promise<SynthesisReport | null> => {
    try {
      const resp = await fetch(`${API_BASE}/api/universe/report`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }, []);

  return (
    <UniverseContext.Provider value={{ ...stream, perturb, fetchReport }}>
      {children}
    </UniverseContext.Provider>
  );
}

/**
 * Access the shared universe state from any child of UniverseProvider.
 * Throws if used outside provider — intentional to catch wiring errors.
 */
export function useUniverse(): UniverseContextValue {
  const ctx = useContext(UniverseContext);
  if (!ctx) {
    throw new Error("useUniverse must be used within a UniverseProvider");
  }
  return ctx;
}
