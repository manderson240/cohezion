import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * EVOEvent — must mirror the Python dataclass in
 * `src/cohezion/api/services/journey_nexus.py` (EVOEvent). The FastAPI router
 * serializes via `_event_to_dict`, which produces snake_case keys, so the
 * TypeScript shape uses snake_case too (NOT camelCase).
 */
export interface EVOEvent {
  id: string;
  timestamp: number;
  z_256: number[];
  state_12d: number[];
  kind: string;
  voice: string;
  score: number;
  journey_id: string;
}

const MAX_EVENTS = 1000;
const POLL_INTERVAL_MS = 5000;
const MAX_BACKOFF_MS = 30000;
const INITIAL_BACKOFF_MS = 1000;

function useEVOStream(journeyId?: string): {
  events: EVOEvent[];
  connected: boolean;
  error: string | null;
} {
  const [events, setEvents] = useState<EVOEvent[]>([]);
  const [connected, setConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Refs for managing state without triggering re-renders during cleanup
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef<boolean>(true);

  // Helper to cap events
  const capEvents = useCallback((newEvents: EVOEvent[]) => {
    if (newEvents.length > MAX_EVENTS) {
      return newEvents.slice(newEvents.length - MAX_EVENTS);
    }
    return newEvents;
  }, []);

  // Helper to append and filter events
  const processNewEvents = useCallback((newEvents: EVOEvent[]) => {
    setEvents((prev) => {
      // Filter by journeyId if provided
      const filtered = journeyId
        ? newEvents.filter((e) => e.journey_id === journeyId)
        : newEvents;

      if (filtered.length === 0) return prev;

      // Append new events to existing ones
      const combined = [...prev, ...filtered];
      return capEvents(combined);
    });
  }, [journeyId, capEvents]);

  // Polling Fallback Handler
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    const fetchSnapshot = async () => {
      if (!isMountedRef.current) return;

      try {
        const response = await fetch('/api/journey-nexus/evo/snapshot');
        if (!response.ok) {
          throw new Error(`Polling failed: ${response.status}`);
        }
        const data = await response.json();
        // Snapshot returns a list of events; guard against an envelope shape.
        const newEvents: EVOEvent[] = Array.isArray(data) ? data : data.events ?? [];
        processNewEvents(newEvents);
        setConnected(true);
        setError(null);
      } catch {
        if (isMountedRef.current) {
          setError('Polling error. Retrying...');
          setConnected(false);
        }
      }
    };

    fetchSnapshot(); // Initial fetch
    pollIntervalRef.current = setInterval(fetchSnapshot, POLL_INTERVAL_MS);
  }, [processNewEvents]);

  // SSE Handler — defined after startPolling so it can fall back to polling
  // on constructor failure (e.g. EventSource unavailable in this environment).
  const startSSE = useCallback(() => {
    if (!isMountedRef.current) return;

    // Clean up existing SSE
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnected(false);
    setError(null);

    try {
      const url = `/api/journey-nexus/stream/evo`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (isMountedRef.current) {
          setConnected(true);
          setError(null);
        }
      };

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as EVOEvent;
          processNewEvents([parsed]);
        } catch (parseErr) {
          console.error('Failed to parse SSE message', parseErr);
        }
      };

      eventSource.onerror = () => {
        if (!isMountedRef.current) return;

        // EventSource closes automatically on error; reconnect with bounded backoff.
        if (eventSource.readyState === EventSource.CLOSED) {
          setConnected(false);
          setError('Connection lost. Reconnecting...');

          // Bounded exponential backoff with mild jitter to avoid thundering herd.
          const backoffTime = Math.min(
            INITIAL_BACKOFF_MS * Math.pow(2, Math.floor(Math.random() * 5)),
            MAX_BACKOFF_MS
          );

          setTimeout(() => {
            if (isMountedRef.current) {
              startSSE();
            }
          }, backoffTime);
        }
      };
    } catch {
      setError('EventSource not supported or failed to initialize.');
      // Fall back to polling when SSE cannot even construct.
      startPolling();
    }
  }, [processNewEvents, startPolling]);

  useEffect(() => {
    isMountedRef.current = true;

    // Check for EventSource support
    if (typeof EventSource !== 'undefined') {
      startSSE();
    } else {
      startPolling();
    }

    return () => {
      isMountedRef.current = false;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [journeyId, startSSE, startPolling]);

  return { events, connected, error };
}

export default useEVOStream;
