"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface JourneyStatusData {
  journey_id: string;
  state: "running" | "paused" | "completed" | "error" | "not_found";
  elapsed_hours: number;
  total_hours: number;
  domains_completed: number;
  total_domains: number;
  hypotheses_completed: number;
  total_hypotheses: number;
  current_domain: string;
  current_hypothesis: string;
  gpu_temp: number;
  cpu_temp: number;
  tdp_consumed_percent: number;
  thermal_events: number;
  total_paused_minutes: number;
  coherence: number;
}

interface UseJourneyStatusOptions {
  journeyId?: string;
  pollIntervalMs?: number;
  enableSSE?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/**
 * Hook for real-time journey status monitoring.
 * 
 * Supports both polling and SSE (Server-Sent Events) for live updates.
 * Falls back to polling if SSE is not available.
 * 
 * Usage:
 *   const { data, isLoading, error, refetch } = useJourneyStatus({
 *     journeyId: "8hr_12345",
 *     pollIntervalMs: 5000,
 *   });
 */
export function useJourneyStatus({
  journeyId = "8hr_current",
  pollIntervalMs = 5000,
  enableSSE = true,
}: UseJourneyStatusOptions = {}) {
  const [data, setData] = useState<JourneyStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/journey/status/${journeyId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const status = await response.json();
      
      if (status.exists) {
        setData({
          journey_id: status.journey_id,
          state: status.state.toLowerCase(),
          elapsed_hours: 0, // Calculate from timestamps
          total_hours: 8,
          domains_completed: status.hypotheses_completed / 5, // Approximate
          total_domains: 4,
          hypotheses_completed: status.hypotheses_completed,
          total_hypotheses: status.total_hypotheses,
          current_domain: status.phase?.split("_")[0] ?? "unknown",
          current_hypothesis: status.phase ?? "Starting...",
          gpu_temp: status.gpu_temp ?? 0,
          cpu_temp: status.cpu_temp ?? 0,
          tdp_consumed_percent: 0, // Not yet available
          thermal_events: 0,
          total_paused_minutes: 0,
          coherence: 0.5,
        });
      } else {
        // No active journey
        setData(null);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      // Keep previous data if available
    }
  }, [journeyId]);

  // Setup SSE connection
  useEffect(() => {
    if (!enableSSE) return;

    const connectSSE = () => {
      try {
        const eventSource = new EventSource(
          `${API_BASE}/api/journey/stream/${journeyId}`
        );

        eventSource.onopen = () => {
          setIsConnected(true);
          setError(null);
        };

        eventSource.onmessage = (event) => {
          try {
            const status = JSON.parse(event.data);
            
            if (status.error) {
              setError(status.error);
              return;
            }

            if (status.exists) {
              setData({
                journey_id: status.journey_id,
                state: status.state?.toLowerCase() ?? "unknown",
                elapsed_hours: ((Date.now() / 1000 - status.last_updated) / 3600),
                total_hours: 8,
                domains_completed: Math.floor(status.hypotheses_completed / 5),
                total_domains: 4,
                hypotheses_completed: status.hypotheses_completed,
                total_hypotheses: status.total_hypotheses,
                current_domain: status.phase?.split("_")[0] ?? "unknown",
                current_hypothesis: status.phase ?? "Initializing...",
                gpu_temp: status.gpu_temp ?? 0,
                cpu_temp: status.cpu_temp ?? 0,
                tdp_consumed_percent: status.progress?.tdp_percent ?? 0,
                thermal_events: status.progress?.thermal_events ?? 0,
                total_paused_minutes: status.progress?.paused_minutes ?? 0,
                coherence: status.progress?.coherence ?? 0.5,
              });
            }
          } catch (err) {
            console.error("Failed to parse SSE data:", err);
          }
        };

        eventSource.onerror = () => {
          setIsConnected(false);
          setError("SSE connection error - falling back to polling");
          eventSource.close();
          
          // Fall back to polling
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          pollIntervalRef.current = setInterval(fetchStatus, pollIntervalMs);
        };

        eventSourceRef.current = eventSource;
      } catch (err) {
        // SSE not supported, use polling
        console.log("SSE not available, using polling");
        pollIntervalRef.current = setInterval(fetchStatus, pollIntervalMs);
      }
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [journeyId, enableSSE, pollIntervalMs, fetchStatus]);

  // Initial fetch
  useEffect(() => {
    setIsLoading(true);
    fetchStatus().finally(() => setIsLoading(false));
  }, [fetchStatus]);

  const refetch = useCallback(() => {
    setIsLoading(true);
    return fetchStatus().finally(() => setIsLoading(false));
  }, [fetchStatus]);

  return {
    data,
    isLoading,
    error,
    isConnected,
    refetch,
  };
}

/**
 * Hook for listing all active journeys.
 */
export function useActiveJourneys() {
  const [journeys, setJourneys] = useState<Array<{
    journey_id: string;
    phase: string;
    hypotheses_completed: number;
    total_hypotheses: number;
    state: string;
  }> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJourneys = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/journey/active`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setJourneys(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJourneys();
    const interval = setInterval(fetchJourneys, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchJourneys]);

  return { journeys, isLoading, error, refetch: fetchJourneys };
}

/**
 * Hook for controlling a journey (pause/resume).
 */
export function useJourneyControl() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pauseJourney = async (journeyId: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/journey/pause/${journeyId}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const resumeJourney = async (journeyId: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/journey/resume/${journeyId}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return { pauseJourney, resumeJourney, isLoading, error };
}
