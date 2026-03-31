"use client";

/**
 * AG-UI Event Stream Consumer for the Cohezion Genesis Engine.
 *
 * Connects to the /api/agui/stream SSE endpoint and routes typed
 * AG-UI events to the appropriate handlers. Replaces ad-hoc SSE parsing
 * with protocol-compliant event consumption.
 *
 * Event types handled:
 * - RUN_STARTED / RUN_FINISHED → lifecycle tracking
 * - TEXT_MESSAGE_* → narration text
 * - TOOL_CALL_* → phase transitions
 * - STATE_SNAPSHOT / STATE_DELTA → universe state
 * - CUSTOM → HIHO equilibrium, etc.
 */

import { useState, useCallback, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// --- AG-UI Event Types ---

interface AGUIBaseEvent {
  type: string;
  timestamp?: string;
}

interface AGUIRunStarted extends AGUIBaseEvent {
  type: "RUN_STARTED";
  threadId: string;
  runId: string;
}

interface AGUIRunFinished extends AGUIBaseEvent {
  type: "RUN_FINISHED";
  threadId: string;
  runId: string;
  result?: Record<string, unknown>;
}

interface AGUITextMessageContent extends AGUIBaseEvent {
  type: "TEXT_MESSAGE_CONTENT";
  messageId: string;
  delta: string;
}

interface AGUIToolCallResult extends AGUIBaseEvent {
  type: "TOOL_CALL_RESULT";
  toolCallId: string;
  toolCallName: string;
  content: {
    from: string;
    to: string;
    temperature: number;
    stage: string;
  };
}

interface AGUIStateDelta extends AGUIBaseEvent {
  type: "STATE_DELTA";
  delta: Array<{ op: string; path: string; value: unknown }>;
}

interface AGUIStateSnapshot extends AGUIBaseEvent {
  type: "STATE_SNAPSHOT";
  snapshot: Record<string, unknown>;
}

interface AGUICustom extends AGUIBaseEvent {
  type: "CUSTOM";
  name: string;
  value: unknown;
}

type AGUIEvent =
  | AGUIRunStarted
  | AGUIRunFinished
  | AGUITextMessageContent
  | AGUIToolCallResult
  | AGUIStateDelta
  | AGUIStateSnapshot
  | AGUICustom
  | AGUIBaseEvent;

// --- State ---

interface UniverseState {
  temperature: number;
  symmetry: string;
  coherence: number;
  orderParameter: number;
  landauFreeEnergy: number;
}

interface AGUIStreamState {
  connected: boolean;
  running: boolean;
  universe: UniverseState;
  narrationText: string | null;
  lastTransition: { from: string; to: string } | null;
  events: AGUIEvent[];
  error: string | null;
}

interface AGUIStreamControls extends AGUIStreamState {
  start: () => void;
  stop: () => void;
}

export function useAGUIStream(): AGUIStreamControls {
  const [state, setState] = useState<AGUIStreamState>({
    connected: false,
    running: false,
    universe: {
      temperature: 200,
      symmetry: "void",
      coherence: 0,
      orderParameter: 0,
      landauFreeEnergy: 0,
    },
    narrationText: null,
    lastTransition: null,
    events: [],
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleEvent = useCallback((event: AGUIEvent) => {
    setState((prev) => {
      const newState = { ...prev, events: [...prev.events.slice(-99), event] };

      switch (event.type) {
        case "RUN_STARTED":
          return { ...newState, running: true };

        case "RUN_FINISHED":
          return { ...newState, running: false };

        case "TEXT_MESSAGE_CONTENT": {
          const textEvent = event as AGUITextMessageContent;
          return { ...newState, narrationText: textEvent.delta };
        }

        case "TEXT_MESSAGE_END":
          // Keep narration visible for a while, then clear
          return newState;

        case "TOOL_CALL_RESULT": {
          const toolEvent = event as AGUIToolCallResult;
          if (toolEvent.toolCallName === "symmetry_breaking") {
            return {
              ...newState,
              lastTransition: {
                from: toolEvent.content.from,
                to: toolEvent.content.to,
              },
            };
          }
          return newState;
        }

        case "STATE_SNAPSHOT": {
          const snapEvent = event as AGUIStateSnapshot;
          return {
            ...newState,
            universe: {
              temperature: (snapEvent.snapshot.temperature as number) ?? 200,
              symmetry: (snapEvent.snapshot.symmetry as string) ?? "void",
              coherence: (snapEvent.snapshot.coherence as number) ?? 0,
              orderParameter: (snapEvent.snapshot.orderParameter as number) ?? 0,
              landauFreeEnergy: (snapEvent.snapshot.landauFreeEnergy as number) ?? 0,
            },
          };
        }

        case "STATE_DELTA": {
          const deltaEvent = event as AGUIStateDelta;
          const universe = { ...newState.universe };
          for (const patch of deltaEvent.delta) {
            if (patch.op === "replace") {
              const key = patch.path.slice(1); // remove leading /
              if (key in universe) {
                (universe as Record<string, unknown>)[key] = patch.value;
              }
            }
          }
          return { ...newState, universe };
        }

        case "CUSTOM": {
          const customEvent = event as AGUICustom;
          if (customEvent.name === "hiho_equilibrium") {
            return {
              ...newState,
              universe: {
                ...newState.universe,
                coherence: 0.5,
              },
            };
          }
          return newState;
        }

        default:
          return newState;
      }
    });
  }, []);

  const start = useCallback(() => {
    if (eventSourceRef.current) return;

    const es = new EventSource(`${API_BASE}/api/agui/stream`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setState((prev) => ({ ...prev, connected: true, error: null }));
    };

    es.onmessage = (msg) => {
      try {
        const event: AGUIEvent = JSON.parse(msg.data);
        handleEvent(event);
      } catch {
        // Skip unparseable events
      }
    };

    es.onerror = () => {
      setState((prev) => ({
        ...prev,
        connected: false,
        error: "Connection lost",
      }));
      es.close();
      eventSourceRef.current = null;
    };
  }, [handleEvent]);

  const stop = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setState((prev) => ({ ...prev, connected: false, running: false }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  return { ...state, start, stop };
}
