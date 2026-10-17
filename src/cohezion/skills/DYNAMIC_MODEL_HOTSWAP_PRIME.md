# SKILL: DYNAMIC_MODEL_HOTSWAP_PRIME

## DOMAIN EXPERTISE
Atomic Zero-Freeze Local Model Hot-Swapping, Dynamic Modularity, and OOM Safeguards on AMD Strix Halo Heterogeneous Unified Memory Architectures (UMA).

## KEY TEXTS & CONCEPTS
- **FleetLock Single-Flight Mutex**: Any model loading/unloading operation (`DELETE /v1/models/active`, `lemonade load`, `ollama pull`) MUST acquire `FleetLock("modelload")` to prevent iGPU aperture memory faults.
- **OOM Safety Floor & Dynamic Modularity**:
  - `RAM_FLOOR_GB = 20.0` (Hard threshold).
  - `SIZE_SAFETY_FACTOR = 2.1` (Accounting for FP4/GGUF KV cache expansion).
  - Explicit garbage collection (`gc.collect()`) and memory settlement pause ($1.0\text{s}$).
- **Cross-Session Event Synchronization**: Broadcasting `HOTSWAP_REQUEST`, `HOTSWAP_COMPLETE`, and `RELEASE_RAM_LOCK` across `EventBus` and dual-persisting Kanban cards to SurrealDB.

## INSTRUCTION

1. **Perform an Atomic Hot-Swap**:
   > **Note (2026-10-06 Mandate)**: Local Tier 1 hot-swapping is restricted to NPU (`-FLM`) and CPU ($\le 4\text{GB}$). Heavy models (30B+) must be routed to Tier 2 (Ollama Cloud / Headless Claude).
   ```python
   from cohezion.inference.hotswap import demand_swap, ensure_resident
   from cohezion.inference.aperture_guard import assert_safe_tier1

   # High-level demand-driven resident swap
   assert_safe_tier1("deepseek-r1-0528-8b-FLM")
   success = await ensure_resident("deepseek-r1-0528-8b-FLM")
   if not success:
       raise RuntimeError("Hot-swap failed to verify residency")
   ```

   **Via CLI Command**:
   ```bash
   python3 scripts/npu_hotswap.py swap deepseek-r1-0528-8b-FLM
   python3 scripts/npu_hotswap.py active
   python3 scripts/npu_hotswap.py list
   ```

2. **Verify Memory Settlement & Safety**:
   The engine automatically:
   - Evicts active models from Lemonade Server.
   - Collects Python cyclic references.
   - Confirms post-settlement available memory exceeds $20.0\text{ GiB} + (2.1 \times \text{model\_size})$.

3. **Broadcast Hot-Swap Completion to Peer Swarms**:
   Peers listening on `EventBus` dynamically update their routing tables without restarting daemons.

## VERSION
v1.0.0

## SEE ALSO
- [LOCAL_INFERENCE_ROUTING](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/LOCAL_INFERENCE_ROUTING.md)
- [SPINNING_PLATES_PROTOCOL_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SPINNING_PLATES_PROTOCOL_PRIME.md)
- [PROACTIVE_MULTIMODAL_SWARM_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/PROACTIVE_MULTIMODAL_SWARM_PRIME.md)
