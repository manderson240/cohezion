---
name: agui-event-streaming-prime
description: "Expert in Cohezion AG-UI typed Server-Sent Events protocol (CopilotKit AG-UI, Apache 2.0). Use when: implementing new AG-UI event producers in FastAPI (agui_events.py), adding React SSE consumers in anima_dashboard, extending the 15+ typed event catalog, debugging stream disconnects or reconnect loops, or wiring agent progress to the /api/agui/stream endpoint. Skip: general frontend work (use FRONTEND_DESIGN_PRIME); A2UI declarative components (use VISUALIZATION_PRIME or FRONTEND_DESIGN_PRIME); non-streaming API work (use api_patterns skill)."
version: v0.1-stub
tier: PRIME
domain: A2UI/AG-UI
status: stub
created: 2026-06-02
see_also: [FRONTEND_DESIGN_PRIME, JOURNEY_DASHBOARD_PRIME, VISUALIZATION_PRIME]
---

# SKILL: AGUI_EVENT_STREAMING_PRIME

## STATUS
This is a stub. `src/cohezion/api/agui_events.py` defines 15+ typed SSE event types and `/api/agui/stream` is a production endpoint. No skill covered this until now. A future session should expand this stub with verified code patterns.

## DOMAIN EXPERTISE
You are a specialist in Cohezion AG-UI typed Server-Sent Events (SSE) protocol. You implement the CopilotKit AG-UI specification for streaming agent events to React frontends via FastAPI `StreamingResponse`.

## KEY COMPONENTS
- `src/cohezion/api/agui_events.py` — 15+ typed event types
- `/api/agui/stream` — FastAPI SSE endpoint
- `src/web/anima_dashboard/` — React consumer side

## TODO (to be filled in by a future session)
1. Enumerate all 15+ typed event types from `agui_events.py` with their payload shapes
2. FastAPI SSE producer pattern (`StreamingResponse` + `asyncio.Queue`)
3. React `useEventSource` or `EventSource` hook pattern in anima_dashboard
4. Error recovery / reconnect protocol (exponential backoff, heartbeat)
5. Testing SSE streams: mock `EventSource`, assert event sequence
6. Event lifecycle: START → PROGRESS → COMPLETE / ERROR types
7. How to add a new event type without breaking existing consumers

## REFERENCE
CopilotKit AG-UI (Apache 2.0). CLAUDE.md: "AG-UI — Event streaming transport: Strong (typed SSE events, /api/agui/stream, 15+ event types)"
