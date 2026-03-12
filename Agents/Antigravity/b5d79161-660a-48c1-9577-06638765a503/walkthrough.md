---
type: antigravity-artifact
session_id: b5d79161-660a-48c1-9577-06638765a503
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.395
  stage: growing
  cluster: Agents
---

# Walkthrough: Local Inference & IDE Optimization

This walkthrough documents the successful optimization of the Cohezion local inference ecosystem for the **AMD RYZEN AI MAX+ 395 (Strix Halo)** hardware substrate.

## 1. Hardware Audit & Verification

We confirmed the system specifications to ensure optimal resource allocation and prevent documentation-based hallucinations.

- **CPU**: AMD RYZEN AI MAX+ 395 (Strix Halo) - 16 Cores / 32 Threads.
- **RAM**: 128GB DDR5-5600.
- **GPU**: Radeon 8060S (iGPU with GTT access to system RAM).

## 2. Ollama Performance Tuning

Implemented performance-critical environment variables in `~/.bashrc` to leverage the NUMA architecture and massive RAM.

- **Dynamic VRAM**: Set `OLLAMA_MAX_VRAM` to 75% of total system RAM (~94GB) for massive model visibility.
- **NUMA Optimization**: Enabled `OLLAMA_NUMA=true` for multi-socket/chiplet awareness.
- **Inference Speed**: Enabled `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_SCHED_SPREAD=true`.
- **Parallelism**: Increased `OLLAMA_MAX_LOADED_MODELS` to 5 for fast context switching.

## 3. Model Registry Expansion

Registered and prioritized state-of-the-art models for the Cohezion swarm.

- **Coding Specialist**: Added `qwen3-coder-next` (80B MoE) in both `latest` (Q4) and `q8_0` quantizations.
- **OCR/Vision**: Added `glm-ocr:latest` for elite document understanding.
- **Priority Routing**: Updated fallback order to prioritize `qwen3-coder-next` for all complex coding tasks.

## 4. IDE Bridge Intelligence (MCP)

Enhanced the delegation logic to preserve token credits by offloading routine work to local models.

- **Offload Management**: Expanded heuristics to include docstrings, formatting, and simple refactors.
- **Dynamic Context Scaling**: Implemented 4x context expansion when system RAM is > 64GB available.

---

## 5. System Identity & Persistent Memory

### 5.1 Codifying Hardware Residency
We implemented `src/cohezion/reliability/residency_awareness.py` to hardcode the "Truth Anchors" of the system. This ensures that every agent session starts with a perfect understanding of its physical substrate.

### 5.2 Sovereign Memory Manager
To resolve the "Cold Start" issue, we implemented a **Sovereign Memory Manager** (`src/cohezion/reliability/memory_manager.py`). 
- **100% Local**: Uses local Ollama embeddings and a local Qdrant vector store.
- **MCP Bridge**: Exposed via `remember_fact` and `recall_context` tools in `cohezion_mcp.py`.

### 5.3 Vanguard Research (Daily Scout Agent)
Formalized automated research of new SOTA models with the `DailyScoutAgent`, ensuring the system follows the "Tip of the Spear" directive.

## 6. Verification Results

### Integration Pulse Check
Running `scripts/verify_mcp_extensions.py` confirmed:
- ✅ **Residency Anchors**: Correctly injected into context.
- ✅ **Memory Persistence**: Facts stored and recalled semantically (100% local).
- ✅ **Daily Scout**: Proposals generated for hardware-compatible models.

```bash
# Verify it yourself
uv run env PYTHONPATH=src python scripts/verify_mcp_extensions.py
```

> [!IMPORTANT]
> The system is now fully optimized and identity-grounded, leveraging the **128GB Strix Halo** substrate with maximum sovereignty and cross-session persistence.

---

## Phase 3: Adaptive Templates & Compound Engineering

### 1. Adaptive Template Pattern
We implemented the `ADAPTIVE_TEMPLATE_PRIME` skill, which shifts our structural blueprints from static definitions to dynamic, evolving entities. Templates now "learn" from task outcomes.

### 2. Template Evolver Utility
Implemented `src/cohezion/evolution/template_evolver.py` to automate the patching of templates.
- **Pattern Extraction**: Scans retrospectives for `[TEMPLATE IMPROVEMENT]` blocks.
- **Versioned Patching**: Programmatically updates `.md` templates and bumps structural versions.

### 3. Verification of Structural Evolution
Running `scripts/verify_template_adaptation.py` demonstrated the full loop:
1. **Initial State**: Template at `v0.1`.
2. **Insight Generation**: A retrospective identifies a missing "12D Brane" requirement.
3. **Automated Patching**: The `TemplateEvolver` injects the missing section and bumps the template to `v0.2`.
4. **Final State**: Verified pattern presence in the source template.

```bash
# Verify the template evolution loop
uv run scripts/verify_template_adaptation.py
```

> [!NOTE]
> This completes the "Compound Engineering" objective, ensuring that every successful task makes all future tasks easier through structural refinement.

## Related Vault Notes

- [[cohezion]]
- [[compound-engineering]]
