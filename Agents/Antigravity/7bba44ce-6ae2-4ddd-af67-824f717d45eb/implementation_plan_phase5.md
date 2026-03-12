---
type: antigravity-artifact
session_id: 7bba44ce-6ae2-4ddd-af67-824f717d45eb
date: 2026-03-04
title: "Implementation Plan Phase5"
aspect: doer
neural:
  activation: 0.312
  stage: embryo
  cluster: Agents
---

# IMPLEMENTATION PLAN: Swarm Visualization Bridge (Phase 5)

## Goal Description
Establish a real-time data pipe from the `mcp-swarm` (Ollama) to the `QuadraticNexus` (WebApp) using Server-Sent Events (SSE). This satisfies the "Use the FLUME" requirement by treating thought as a fluid stream.

## Proposed Changes

### [apps/mcp-swarm] SSE Gateway
#### [MODIFY] [server.ts](file:///home/mike-anderson/dev/cohezion/apps/mcp-swarm/server.ts)
- Initialize an Express app on port `3002`.
- proper CORS headers for `localhost:5173`.
- Expose `GET /events` endpoint for SSE.
- Expose `POST /debate` endpoint to trigger the swarm.
- When `start-debate` tool is called (via MCP or HTTP), broadcast chunks to `/events`.

### [apps/webapp] FLUME Integration
#### [NEW] [useSwarmStream.ts](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/hooks/useSwarmStream.ts)
- React hook to connect to `http://localhost:3002/events`.
- Manages `ready`, `streaming`, and `packet` states.

#### [MODIFY] [MissionControl.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/MissionControl.tsx)
- Replace `useJourney` (mock) with `useSwarmStream`.
- Pass real-time data to `SwarmNarration`.

## Verification Plan
1.  **Backend**: `curl -N http://localhost:3002/events` and trigger a debate.
2.  **Frontend**: Open WebApp, see "Connected" status in Control quadrant, trigger debate, watch text flow.

## Related Vault Notes

- [[cohezion]]
