# SKILL: PROACTIVE_MULTIMODAL_SWARM_PRIME

## DOMAIN EXPERTISE
Tri-Silicon Multimodal Orchestration, Micro-Sandboxed Execution, and Continuous Proactive Adversarial Self-Evolution on AMD Strix Halo Heterogeneous Unified Memory Architectures (NPU, iGPU, CPU).

## KEY TEXTS & CONCEPTS
- **Tri-Silicon Hardware Allocation**: Routing Text MoE (`qwen3.6-moe-35b-a3b-FLM`) and Vision (`qwen3vl-it-4b-FLM`) to NPU, Diffusion (`Flux-2-Klein-9B-GGUF`) and 3D Mesh (`TRELLIS-3D`) to iGPU, and Speech/Audio (`kokoro-v1`) to CPU via zero-copy UMA buffers.
- **Micro-Sandbox Resource Isolation**: Bounding untrusted subprocess executions with `resource.setrlimit` (RLIMIT_CPU, RLIMIT_AS) combined with AST static pre-verification before code execution.
- **Topological & Sheaf Consistency**: Čech Cohomology Nerve generation across complete pairwise combinations ($\dim H^1 = 0$) and Poincaré 12D/256D hyperbolic Fréchet centroids.
- **Autonomous Proactive Loop Protocol**: Iterative cycle execution with immediate multi-model adversarial review by cloud models (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`) and local fallback consultation.

## INSTRUCTION

1. **Verify Multimodal Matrix Availability**:
   Query `UnifiedMultimodalOrchestrator` across 6 distinct modalities before executing swarm tasks:
   ```python
   from cohezion.multimodal.orchestrator import UnifiedMultimodalOrchestrator, MultimodalModality

   for modality in MultimodalModality:
       entry = UnifiedMultimodalOrchestrator.resolve_model(modality, prefer_npu=True)
       print(f"Modality {modality.name} mapped to {entry.model_id} on {entry.hardware_lane}")
   ```

2. **Execute Sandboxed Actions with Strict Pre-flight AST Guards**:
   ```python
   from cohezion.security.micro_sandbox import MicroSandboxEngine

   sandbox = MicroSandboxEngine(timeout_sec=3.0)
   result = sandbox.execute_sandboxed_action(python_code)
   if not result.passed:
       raise RuntimeError(f"Sandbox rejection: {result.output}")
   ```

3. **Enforce Čech Cohomology Consensus Across Agent Beliefs**:
   ```python
   import itertools
   import numpy as np
   from cohezion.governance.sheaf_consistency_gate import SheafConsistencyGate

   gate = SheafConsistencyGate(tolerance=0.15)
   keys = list(agent_claims.keys())
   intersections = list(itertools.combinations(keys, 2)) if len(keys) > 1 else []
   report = gate.evaluate_consistency(agent_claims, intersections)
   assert report.is_consistent, (
       f"Cohomological obstruction detected: dim H^1 = {report.dim_h1_obstructions}"
   )
   ```

4. **Continuous Proactive Fleet Consultation Loop**:
   Always execute an adversarial review query upon completing major milestones to surface blind spots and higher-order topological invariants before declaring completion.

## VERSION
v1.0

## SEE ALSO
- [AUTOHARNESS_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/AUTOHARNESS_PRIME.md)
- [TOPOLOGICAL_VERIFICATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/TOPOLOGICAL_VERIFICATION_PRIME.md)
- [SOVEREIGN_LORA_SILICON_ORCHESTRATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SOVEREIGN_LORA_SILICON_ORCHESTRATION_PRIME.md)
