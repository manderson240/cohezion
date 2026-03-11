---
type: antigravity-artifact
session_id: 8c37550a-9f69-4cf2-8a9a-ad246d6fb889
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.340
  stage: embryo
  cluster: Agents
---

# Walkthrough - Cohezion Universe (Anthropic Showcase)

## Architecture
We have deployed a multi-app constellation to demonstrate Cohezion's "Universe" capabilities:

### 1. **App: Skills Portal (`mcp-portal`)**
*   **Purpose**: Intelligence layer.
*   **Feature**: `SkillFeature` uses FLUME to inject "Thought Vectors" into agent context.
*   **Prompt**: `get-skill <name>`
*   **Status**: **Live** (Integrated with Python API).

### 2. **App: Universe Observer (`mcp-universe`)**
*   **Purpose**: Physics & Simulation layer.
*   **Feature**: `UniverseFeature` exposes 12D state vectors/trajectories via MCP Resources & Tools.
*   **Resource**: `universe://simulation/latest`
*   **Tool**: `analyze-physics` (Generates Markdown Science Reports).
*   **Status**: **Live**.

### 3. **App: Swarm Narrator (`mcp-swarm`)**
*   **Purpose**: Narrative & Debate layer.
*   **Feature**: `SwarmFeature` streams live agent debates (with robust simulation fallback).
*   **Tool**: `start-debate`
*   **Status**: **Live**.

## UX Verification Results
We ran a simulated Agent interaction script (`apps/ux-verification/verify_ux.ts`) to validate the experience.

### Scenario 1: Skills (FLUME Injection)
> **Agent Request**: `get-skill branding-ops`
> **System Response**:
> ```
> <FLUME_METADATA>
> manifold_vector: [-0.042, 0.118, -0.095, 0.021, -0.056], ...
> dimensions: 256
> coherence: 0.98
> </FLUME_METADATA>
> ```
> **Result**: ✅ Verified. The "Thought Vector" is correctly injected.

### Scenario 2: Universe Physics
> **Agent Request**: Read `universe://simulation/latest`
> **System Response**: JSON containing 12D physics state (Coherence, Stability, Entropy).
> **Result**: ✅ Verified. High-fidelity simulation data is accessible.

### Scenario 3: Swarm Debate
> **Agent Request**: Call `start-debate` (Topic: "Is gravity quantum?")
> **System Response**:
> ```
> Debate Concluded (Confidence: 0.88)
> ### Debate Synthesis: Is gravity quantum?
> **Architect (Gemini 3 Pro)**: The query implies a need for a non-linear topology...
> **Consensus**: The swarm agrees on a Recursive Graph...
> ```
> **Result**: ✅ Verified. The system generates a coherent multi-agent narrative (using simulation fallback if models are offline).

## Next Steps
*   **Submission**: The portfolio and apps are ready for review by Anthropic.
