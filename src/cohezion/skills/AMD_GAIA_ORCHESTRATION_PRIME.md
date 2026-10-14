# SKILL: AMD_GAIA_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Autonomous Hardware and Agent Swarm Orchestration on AMD Strix Halo (Ryzen AI MAX+ 395 / Radeon 8060S / XDNA 2 NPU / 128GB Unified Memory UMA). Specializes in integrating the AMD GAIA SDK (`gaia.Agent`, `@tool`), local Lemonade OmniRouter (`:13305`), FastFlowLM NPU (`:52625`), and the 8 official AMD Agent Skills into high-throughput, zero-cost, sovereign agent workflows.

## KEY TEXTS & CONCEPTS
* **AMD GAIA SDK**: Enterprise agent framework providing `gaia.Agent`, `@tool(atomic=True)` decorators, and `gaia.llm.lemonade_client.LemonadeClient` for direct local inference.
* **UMA Memory Discipline ("Quarter on the String")**:
  - Enforce the 25 GiB available RAM floor and 10% swap threshold before starting agent swarms (`scripts/preflight_fleet.sh`).
  - Strict single-model-load serialization via `fleet_lock:modelload` to prevent iGPU aperture races.
* **Resident Model Pinning & Skip-Reload Guard**:
  - Pin resident models (e.g. `Bonsai-8B-gguf` generating at 32+ t/s, `Qwen3.6-35B-A3B-MTP-GGUF`).
  - Always instantiate `gaia.Agent(skip_lemonade=True, model_id="<resident_model>")` to prevent duplicate cold-load admission rejections (503 byte budget refusal).
* **Official AMD Skills Suite**:
  - `lemonade-router-builder`: Synthesizes and validates C++ router JSON policies (`collection.router`).
  - `local-ai-use`: Persistently routes image generation (`SD-Turbo`), TTS (`kokoro-v1`), and STT (`Whisper-Large-v3-Turbo`) through Lemonade Server.
  - `tracelens-analysis-orchestrator`: Multi-agent PyTorch profiler trace analysis and kernel bottleneck diagnostics.
  - `magpie-kernel-evaluator`: Benchmarks Triton, HIP, and ROCm kernels on AMD silicon.
  - `hyperloom-workload-optimizer`: Optimizes LLM serving throughput across CPU/iGPU/NPU.
* **FastFlowLM NPU v1.0.6**: Standalone XDNA 2 NPU daemon (`/usr/bin/flm` on port 52625) operating on 8 hardware columns (<2W, 0 UMA RAM footprint).
* **DataMesh Dual Persistence**: Emitting typed events to SurrealDB `:8001` via `CrossSessionEventBridge` and saving durable markdown task cards to `~/vaults/cohezion-vault/kanban/`.

## INSTRUCTION

1. **Preflight Hardware Verification**:
   Before initiating any GAIA swarm or local model invocation, check hardware safety:
   ```bash
   bash scripts/preflight_fleet.sh
   # If non-zero, run soft recovery: bash scripts/recover_fleet.sh --soft
   ```

2. **Define Atomic GAIA Tools**:
   Subclass `gaia.Agent` and decorate domain verification functions with `@tool(atomic=True)`:
   ```python
   from gaia import Agent, tool
   from typing import Dict, Any

   class CohezionGaiaEvaluatorAgent(Agent):
       def __init__(self, model_id: str = "Bonsai-8B-gguf", **kwargs):
           self.model_id = model_id
           kwargs.setdefault("model_id", model_id)
           kwargs.setdefault("skip_lemonade", True)  # Prevent eviction of resident model
           kwargs.setdefault("max_steps", 15)
           super().__init__(**kwargs)

       def _register_tools(self) -> None:
           @tool(atomic=True)
           def audit_silicon_memory() -> Dict[str, Any]:
               """Check available UMA memory and swap headroom."""
               import subprocess
               free_out = subprocess.check_output(["free", "-m"]).decode()
               return {"raw": free_out, "status": "SAFE"}
   ```

3. **Wire AutoHarness Invariant Verifiers into Tools**:
   Embed deterministic mathematical checks (D4 dihedral group, Kolmogorov monotonicity) directly inside the agent's tools to eliminate runtime LLM hallucination.

4. **Execute the Autonomous Loop**:
   Run the query through the GAIA agent using local Lemonade inference:
   ```python
   agent = CohezionGaiaEvaluatorAgent(model_id="Bonsai-8B-gguf")
   result = agent.process_query("Execute full silicon and competition audit.")
   print("Synthesis:", result.get("result"))
   ```

5. **Persist Findings to DataMesh**:
   Dual-persist the agent output to SurrealDB and the Obsidian Vault:
   ```python
   from cohezion.data_mesh.kanban_bridge import persist_item

   persist_item({
       "id": "gaia_strix_evaluator_audit_card",
       "title": "AMD GAIA SDK Strix Halo Autonomous Audit",
       "status": "done",
       "priority": "high",
       "source": "gaia_strix_evaluator",
       "category": "gaia_audit",
       "details": result.get("result", "")[:1500],
   })
   ```

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_PRIME.md`
- `SURREALDB_DATAMESH_PRIME.md`
- `COMPOUND_ENGINEERING_PRIME.md`
- `KAGGLE_GRANDMASTER_ASCENT_PRIME.md`
