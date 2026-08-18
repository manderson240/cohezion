# SKILL: SPINNING_PLATES_PROTOCOL_PRIME

## DOMAIN EXPERTISE
Continuous Autonomous Workload Scheduling, Sovereign Local Inference Maximization, and Asynchronous Research Cascade across AMD Strix Halo Local Silicon (NPU/iGPU/CPU), Ollama Cloud Frontier Models, and Headless Claude Architect Sessions.

## KEY TEXTS & CONCEPTS
- **Spinning Plates Invariant**: Zero-Idle Time for Local Silicon. If the agent is waiting on external events or cloud syntheses, local inference cores (NPU: `qwen3.6-moe-35b-a3b-FLM`, `qwen3vl-it-4b-FLM`; iGPU: `Qwen3-Coder-30B`; CPU: `llama3.2:1b`) MUST continuously process background plates (retrospective extraction, AST mutation sweeps, vector embedding, topological calibration).
- **Plate Registry & Schedulers**: A multi-queue round-robin governor maintaining 6 concurrent persistent plates:
  1. *Plate 1 (Local Code Verification)*: Continuous AST verification & deterministic bytecode compilation.
  2. *Plate 2 (Local Manifold Calibrator)*: Continuous 2048D Poincaré Fréchet centroid recalculation and conformal factor updates.
  3. *Plate 3 (Local Retrospective Distiller)*: Background extraction of session trajectories into SurrealDB `learning` table.
  4. *Plate 4 (Local Multimodal Monitor)*: Tri-silicon memory headroom inspection and zero-copy UMA buffer health.
  5. *Plate 5 (Ollama Cloud Frontier Researcher)*: Long-horizon deep mathematical & architectural exploration (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`).
  6. *Plate 6 (Headless Claude Synthesizer)*: Strategic high-order invariant evaluation and meta-architecture governance.
- **Hardware Aperture Safety**: All local plates must respect `FleetLock("modelload")` and `OOMGuard.get_memory_state()` (20.0 GiB floor) to guarantee crash-free concurrent execution.

## INSTRUCTION

1. **Initialize the Spinning Plates Protocol Governor**:
   ```python
   from cohezion.proactive.spinning_plates_protocol import SpinningPlatesGovernor
   governor = SpinningPlatesGovernor(min_available_gb=20.0)
   await governor.start_spinning_plates()
   ```

2. **Register a Background Workload Plate**:
   ```python
   async def background_manifold_plate():
       while True:
           await governor.execute_local_inference_plate("manifold_calibration")
           await asyncio.sleep(10.0)
   ```

3. **Cascade Frontier Cloud & Headless Claude Research**:
   When local plates detect architectural ambiguity or higher-order invariant drift ($\dim H^1 > 0$), automatically trigger a background subagent or Ollama Cloud / Headless Claude task.

4. **Verify Autonomous Multi-Plate Concurrency**:
   Ensure all active plates log execution telemetry into SurrealDB `spinning_plates_log` and Obsidian vault `01-Learnings/`.

## VERSION
v1.0.0

## SEE ALSO
- [PROACTIVE_MULTIMODAL_SWARM_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/PROACTIVE_MULTIMODAL_SWARM_PRIME.md)
- [MULTI_PERSPECTIVE_REVIEW_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/MULTI_PERSPECTIVE_REVIEW_PRIME.md)
- [LOCAL_INFERENCE_ROUTING](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/LOCAL_INFERENCE_ROUTING.md)
