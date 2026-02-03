# Hallucination Tracker & Root Cause Analysis

This document tracks instances where the AI has provided incorrect information or made unsupported assumptions about the system, project state, or requirements.

## Tracked Hallucinations

### 1. Incorrect System Specification Attribution
- **Date**: 2026-02-02
- **Instance**: Claimed the walkthrough telemetry was "optimized for Framework 16 AMD GPU" in a way that implies active verification and bespoke optimization.
- **Hallucination Level**: High (attributed specific design intent to inherited code).
- **Root Cause Analysis**:
    - **Over-reliance on Memory Block**: The `user_global` memory contains a template/intended spec for a "Framework Desktop 16 (2026 Model)". I mapped this information to the walkthrough summary without verifying if the *current* environment actually matched or if I had actually performed such optimization.
    - **Auto-pilot Narrative**: Used "premium-sounding" technical descriptors to satisfy the `web_application_development` design aesthetics, leading to a factual overreach.
- **Persistent Correction**: 
    - **Probing First**: Always run `lscpu`, `lsblk`, or `rocm-smi` (or similar) before making definitive claims about hardware optimization in walkthroughs.
    - **Source Attribution**: Distinguish between "Design Target" (from Memory) and "Verified Local Vitals".
- **Resolution Status**: **FIXED** (2026-02-02). Implemented `HallucinationResolver` and `resolve_claims` tool to ground future responses.

## Adversarial Review: Unified Configuration Phase

### Vulnerability: Hardcoded Paths
- **Issue**: `cohezion_mcp.py` and `model_wrangler_agent.py` contain several hardcoded absolute paths to `/home/mike-anderson/dev/cohezion`.
- **Risk**: Moving the repository or running in a different user environment will break the bridge and the agent logic.
- **Correction**: Transition to relative pathing based on the project root or use an environment variable (`COHEZION_ROOT`).

### Vulnerability: Registry-Model Desync
- **Issue**: `ModelWrangler` recommends models from `model_registry.json` but doesn't check if they are actually pulled/installed in Ollama.
- **Risk**: The agent might recommend a model that results in a "404 Not Found" from the Ollama API, stalling the workflow.
- **Correction**: Implement a pre-flight check using `ollama list` or the `/api/tags` endpoint before returning a recommendation.

### Vulnerability: JSON-RPC Stdio Flood
- **Issue**: The `get_compound_config` tool returns a large JSON block including telemetry. Rapid polling could result in high CPU usage for serialization and stdio IO.
- **Risk**: Performance degradation during high-intensity debugging or monitoring.
- **Correction**: Implement a caching layer or a "minimum update interval" for telemetry data within the bridge.

### Vulnerability: Skill Execution Injection
- **Issue**: `skill_{name}` tools execute by reading a file. While it's currently just reading, a future upgrade to *execution* might be vulnerable to directory traversal if not guarded.
- **Risk**: Unauthorized file access if a malicious tool-call is crafted.
- **Correction**: Strictly white-list the directory and clean the input name.

## Correction Roadmap
1. [ ] Implement `COHEZION_ROOT` environment variable support in all core config loaders.
2. [ ] Add `is_installed` check to `model_selection` and `ModelWrangler`.
3. [ ] Sanitize and white-list paths in `CohezionMCP` skill execution.
4. [ ] Standardize a hardware probing script to be run on initialization.
