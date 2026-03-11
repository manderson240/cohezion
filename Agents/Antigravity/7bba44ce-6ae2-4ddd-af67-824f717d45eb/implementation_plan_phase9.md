---
type: antigravity-artifact
session_id: 7bba44ce-6ae2-4ddd-af67-824f717d45eb
date: 2026-03-04
title: "Implementation Plan Phase9"
aspect: doer
neural:
  activation: 0.373
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Phase 9: Recursive Expansion & A2A

## Goal
Transform the "Universe-Class" prototype into a robust, containerized, agent-native platform with persistent memory and multimodal capabilities.

## User Review Required
> [!IMPORTANT]
> **Docker Requirements**: This plan assumes Docker and Docker Compose are installed on the local machine.
> **Model Weights**: Local multimodal models (Qwen3-VL, Kokoro/PocketTTS) require downloading weights. Ensure ~10GB disk space is available.

## Proposed Changes

### 1. Infrastructure Hardening (The "Entropy" Fixes)
- **Port Management**: Implement `get_free_port()` utility in scripts to avoid `EADDRINUSE`.
- **TS Config**: Fix module resolution in `tsconfig.json` for seamless script execution.
- **Dockerization**:
    *   [NEW] `apps/webapp/Dockerfile`
    *   [NEW] `apps/mcp-swarm/Dockerfile`
    *   [NEW] `apps/mcp-universe/Dockerfile`
    *   [NEW] `docker-compose.yml` (Orchestrates all + SurrealDB)
    *   *Research*: Optimize container sizes for local model serving (multistage builds).

### 2. SurrealDB Integration (Persistent Memory)
- **Database**: Add `surrealdb/surrealdb:latest` to `docker-compose.yml`.
- **MCP Resource**: Update `mcp-swarm` to store and retrieve "Thought History" from SurrealDB.
    *   [MODIFY] `apps/mcp-swarm/src/features/swarm/swarm-feature.ts`

### 3. Multimodal Capabilities (The "Omni-Senses")
- **TTS (Voice)**: `kyutai-labs/pocket-tts` (CPU).
- **Vision (Sight)**: `OpenBMB/MiniCPM-V-4_5` (~8GB VRAM).
    *   *Why*: Released Jan 2026. Optimized for edge. Unified 3D-Resampler. Beats Qwen2-VL in latency.
- **Reasoning**: `DeepSeek-R1-Distill-Llama-70B-GGUF` (Q4_K_M).
    *   *Why*: Jan 2026 Release. The new open-weight king of reasoning.
- **Orchestrator**: `Mistral-Small-24B-Instruct-2501` (Residents).

### 4. Interactive & Secure Architecture
- **WebApp Interaction**:
    *   [NEW] `ChatOverlay.tsx`: Interactive chat layer over the Nexus. Allows users to "Inject" thoughts into the Swarm flow.
- **Security Layer (Prompt Injection Defense)**:
    *   **Input Sanitization**: Regex filters for "Ignore previous instructions".
    *   **Plan-Then-Execute**: Swarm *proposes* a plan, user *approves* via UI (Human-in-the-Loop).
    *   **Output Redaction**: Strip PII tokens before SSE broadcast.

### 5. Local Fine-Tuning (The "Codebase LoRA")
- **Goal**: Models must know *Cohezion* internals (FLUME, 12D Manifold).
- **Pipeline**:
    *   **Data**: Evolve `src/` into a dataset (QA pairs) using the Orchestrator.
    *   **Training**: Use `Unsloth` (ROCm port) to train an adapter on `Mistral-Small-24B`.

### 6. Agent-to-Agent (A2A) Usability
- **Verification**: Create a "User Proxy" agent script (`scripts/verify_a2a.ts`) that:
    1.  **Audits**: Checks `wav` generation.
    2.  **Sees**: Uses `MiniCPM-V` to verify UI state.
    3.  **Hacks**: Attempts a known prompt injection (`/inject rm -rf`). Verifies rejection.

## Verification Plan

### Automated Tests
- `docker-compose up -d`: Verify HEALTHCHECKs (including Trivy security scan).
- `scripts/verify_a2a.ts`: Run the "User Proxy".

### Manual Verification
- **Interactive**: Chat with the Swarm via `http://localhost:5173`.
- **Security**: Try to trick the Swarm into revealing system prompts.
- **Monitor**: Ensure `radeontop` shows VRAM usage < 12GB (MiniCPM offloaded).

## Verification Plan

### Automated Tests
- `docker-compose up -d`: Verify all containers start healthy.
- `scripts/verify_a2a.ts`: Run the "User Proxy" to simulate an agentic user validating the system.

### Manual Verification
- **Visual/Interactive**:
    *   Open `http://localhost:5173` (WebApp) to see the `QuadraticNexus`.
- **System Monitor**:
    *   Watch `btop` / `radeontop`. Ensure RAM < 96GB during model swap.
