# SKILL: HARNESS_ENGINEERING_ETCLOVG_PRIME

## DOMAIN EXPERTISE
Harness Engineering is the rigorous systems discipline governing the software infrastructure, sandboxing, execution runtimes, tool interfaces, memory architectures, and verification loops that surround foundation models to transform non-deterministic probabilistic reasoning into reliable, crash-free, long-horizon autonomous software agents. In accordance with the 2026 ETCLOVG framework (*Agent Harness Engineering: A Survey*), the fundamental equation of autonomous systems is **Agent = Model + Harness**, wherein intelligence operates as the perceptual engine while the harness provides stateful containment, resource governance, and formal verification.

## KEY TEXTS & CONCEPTS
- **The ETCLOVG 7-Layer Architecture**:
  1. **E - Execution**: Sandboxes, process isolation, cgroups v2 resource ceilings (`MemoryMax`, `MemorySwapMax`), and host OOM protection.
  2. **T - Tooling**: Strongly-typed interfaces, Model Context Protocol (MCP), Agent-to-Agent (A2A) protocols, and idempotent tool contracts.
  3. **C - Context**: Context window budgeting, Poincaré hyperbolic state caching, externalized memory artifacts, and anti-rot pruning.
  4. **L - Lifecycle**: Persistent execution loops (Plan-Execute-Verify), durable checkpoint resumption, and process-group teardown.
  5. **O - Observability**: Structured telemetry, OpenTelemetry spans, token cost accounting, and drift detection.
  6. **V - Verification**: Two-party IV&V, AutoHarness bytecode policies, AST invariants, and formal mathematical proofs.
  7. **G - Governance**: Hardware aperture concurrency locks (`FleetLock`), authorization gates, and audit trails.
- **The OOM Containment Invariant**: Unconstrained multi-agent swarms must never allocate directly against host physical memory; all executions must be scoped within isolated cgroups v2 slices with hard memory ceilings.
- **FleetLock Single-Flight Aperture Invariant**: On unified memory architectures (e.g., AMD Strix Halo UMA 120GB), only one concurrent model weight allocation may execute at any instant to prevent kernel aperture page-table collisions.

## INSTRUCTION

1. **Deploy Cgroup v2 Sandbox Isolation for Agent Workloads**:
   Wrap any long-running agent command, swarm batch, or multi-threaded worker in a systemd user scope with hard memory ceilings to guarantee host immunity from OOM:
   ```bash
   # scripts/ops/sandbox_run.sh isolates execution to 24G RAM, 2G swap
   ./scripts/ops/sandbox_run.sh --memory-max 24G --memory-swap-max 2G -- \
       python3 scripts/agent_swarm.py --workers 8
   ```

2. **Enforce Single-Flight Hardware Aperture Locking (`FleetLock`)**:
   Before initiating model weights initialization on local silicon (Lemonade port 13305 or Ollama port 11434), acquire the system-wide FleetLock mutex:
   ```python
   from cohezion.researcher.daily_researcher import FleetLock

   async def safe_model_load(model_id: str):
       async with FleetLock().acquire("modelload", timeout=120.0):
           # Safe single-flight model weight memory allocation
           await lemonade_client.load_model(model_id)
   ```

3. **Externalize Durable State for Long-Horizon Work**:
   Never maintain long-horizon task progress solely in ephemeral LLM conversation buffers. Checkpoint state after every decision step into structured databases (SurrealDB) and markdown vaults (Obsidian):
   ```python
   from cohezion.data_mesh.kanban_bridge import persist_item

   def checkpoint_agent_step(task_id: str, state: dict):
       persist_item({
           "id": f"task-{task_id}",
           "title": state["current_goal"],
           "status": "in_progress",
           "state_vector": state["poincare_coords"],
           "iteration": state["loop_count"],
       })
   ```

4. **Verify Action Safety Prior to Execution (AutoHarness Code-as-Action)**:
   Intercept tool invocations with deterministic Python bytecode verifiers. Reject any tool parameters violating security or resource invariants with 0 ms latency:
   ```python
   from cohezion.agi.autoharness_policy import AutoHarnessPolicy

   policy = AutoHarnessPolicy()
   is_valid, violation = policy.verify_action(tool_name="run_command", args={"CommandLine": "rm -rf /"})
   if not is_valid:
       raise PermissionError(f"AutoHarness blocked illegal action: {violation}")
   ```

5. **Execute Verification-Separation (Two-Party Rule)**:
   Mandate cryptographic separation between the code-creator agent and the independent verifier authority (`IVVAuthority`) before promoting code artifacts to production or submitting to Kaggle.

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/DYNAMIC_MODEL_HOTSWAP_PRIME.md`
- `src/cohezion/skills/LOCAL_MODEL_ROSTER_EVALUATION_PRIME.md`
- `src/cohezion/skills/SPINNING_PLATES_PROTOCOL_PRIME.md`
- `src/cohezion/skills/AUTOHARNESS_ZERO_LATENCY_POLICY_PRIME.md`
