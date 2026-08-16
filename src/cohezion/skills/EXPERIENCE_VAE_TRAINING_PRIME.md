---
name: experience-vae-training-prime
description: "Cohezion autonomous capability for EXPERIENCE VAE TRAINING PRIME."
metadata:
  version: "1.0"
  concepts: ["Cohezion", "FLUME", "AutoHarness"]
  source: "src/cohezion/skills/EXPERIENCE_VAE_TRAINING_PRIME.md"
---

# SKILL: EXPERIENCE_VAE_TRAINING_PRIME

## DOMAIN EXPERTISE
Experiential Learning, 12D FLUME Trajectory Encoding, SurrealDB 3.0+ HNSW Vector Search, and EventBus Cross-Session Synchronization for Agentic Swarms.

## KEY TEXTS & CONCEPTS
- **Experiential Replay Memory ($E$):** $E = (S_t, a_t, r_t, S_{t+1}, \pi_{\text{safety}})$ state-action-reward transitions.
- **Quality-Gated Retention:** Filtering trajectories ($r_t \ge 0.45$) to prevent low-coherence memory pollution.
- **SurrealDB 3.0+ HNSW Indexing:** Sub-millisecond $O(\log N)$ vector search using `<|k,efc|>` KNN operator and `type::record("table", $id)` syntax.
- **AutoHarness Policy & ZKFV:** 0 ms AST bytecode action-verifiers (arXiv:2603.03329v1) with zero-knowledge formal verification proofs ($\pi_{\text{safety}}$).
- **EventBus Synchronization:** Real-time cross-session event broadcasting via `CrossSessionEventBridge`.

## INSTRUCTION

1. **Capture Experience Trajectories:**
   Converts agent state actions into 12D FLUME Poincaré points ($x, y, z, t, \text{coherence}, \dots$).

2. **Verify Policy & Formal Safety:**
   ```python
   from cohezion.agi.autoharness_policy import AutoHarnessPolicy
   from cohezion.agi.zkfv_compiler import ZKFVCompiler

   policy_engine = AutoHarnessPolicy()
   p_res = policy_engine.evaluate_policy("action_name", {"available_gb": 128.0})
   gates = ZKFVCompiler.compile_ast_to_gates("grid_bounds")
   proof = ZKFVCompiler.generate_proof(gates, (1.0, 0.0, 1.0))
   ```

3. **Asynchronous SurrealDB 3.0+ Persistence:**
   ```python
   from cohezion.core.persistence.surreal_client import get_surreal_client

   client = get_surreal_client()
   table = "experiential_replay" if reward >= 0.45 else "failed_experience_log"
   await client.query(
       f"UPSERT type::record('{table}', $exp_id) CONTENT $data;",
       {"exp_id": exp_id, "data": exp_data},
   )
   ```

4. **EventBus Cross-Session Publication:**
   ```python
   from cohezion.core.event_bus import Event, EventType, get_event_bus

   event_bus = await get_event_bus()
   await event_bus.publish(
       Event(
           type=EventType.AGENT_COMPLETE,
           source="experiential_learning_engine",
           payload={"exp_id": exp_id, "reward": reward, "verified": True},
       )
   )
   ```

## VERSION
v1.0

## SEE ALSO
- [`SURREALDB_MOCK_PERSISTENCE_PRIME.md`](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SURREALDB_MOCK_PERSISTENCE_PRIME.md)
- [`JOURNEY_TRACKING_PRIME.md`](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/JOURNEY_TRACKING_PRIME.md)


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for EXPERIENCE VAE TRAINING PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
