# Cohezion Evolution Protocol

This protocol governs the autonomous improvement, healing, and experience mining of the Cohezion system.

## 1. Continuous Experience Mining
Agents must actively scan their session logs and outputs for recurring structural markers:
- **Pattern Extraction**: Identify successful workflows or logic. Patterns appearing 3+ times with >=0.85 confidence should be proposed as Skills.
- **Anti-Pattern Detection**: Document recurring failures or "locked" states.

## 2. Deterministic Agentic Execution
To move beyond "stochastic" behavior, the system implements **Determinism via Idempotency**.
- **Idempotency Keys**: Assign unique keys to all significant operations (file edits, deployments, complex reasoning steps).
- **Consistency**: Repeated execution with the same key must yield the same result, ensuring that agentic "retries" do not introduce entropy.

## 3. Automated Module Maintenance
Knowledge must remain lean and modular.
- **Module Generation**: When a specific domain (e.g., "Reporting") grows too large in `GEMINI.md`, the system should automatically generate a new specialized module in `.agent/` or `src/cohezion/knowledge_graph/`.
- **Refinement**: Regularly audit and prune modules to incorporate the latest findings from "Mission Journal" entries.

## 4. Abstraction & Compression
Prioritize conceptual clarity over mechanistic detail.
- **Resource Stewardship**: All autonomous actions (simulations, deployments) must be "cost-optimal." Avoid persistent billing and maximize use of local Ollama/Free Tier resources.
- **Multi-Session Coordination**: Agents must defer to a single active `browser_subagent` instance to avoid hardware-level process locks and host header errors in multi-session environments.
- **Scaling**: As logs accumulate, compress "Session Developments" into "Extracted Wisdom" in `KEY_LEARNINGS.md`.
- **High-Fidelity Abstractions**: Success is measured by how accurately a high-level abstraction represents the underlying complexity (Grounding Score >= 0.9).

## 5. Repository Healing & Hygiene
Monitor for technical debt and IDE performance degradation.
- **Bloat Mitigation**: Trigger `REPO_HYGIENE_PRIME` for excessive untracked files. The 8.6M file incident (2026-01-25) proved that autonomous simulations MUST write to .gitignored directories.
- **Build/Lint Restoration**: Treat "restoring the green state" as the primary objective if a change causes failure.
- **Untrack & Mine Protocol**: Never delete tracked files without first reading and extracting knowledge. See `.agent/GIT_HYGIENE.md`.
- **Cleanup is Multi-Pass**: Budget 2-3 passes for any major cleanup. Each removal reveals the next layer of bloat (the 8.6M cleanup needed 3 passes across 2 branches).

## 6. Hardware Safety & Lockup Prevention
The system lockup of 2026-01-27 (VRAM saturation → amdgpu hang → REISUB recovery) established these rules:
- **VRAM is the Bottleneck**: Monitor GTT (128GB unified pool), not VRAM carveout (512MB display scanout).
- **Swarms are Sacrificial**: Kill runaway agents before system integrity is threatened. Never allow swarm operations to exceed hardware safety margins.
- **Temporal Dilation**: Slow simulations dynamically when system pressure exceeds thresholds (`dilation_factor` in ResourceMonitor).
- **Desperation Mode**: Throttle all non-essential containers at 90% CPU.
- **Kernel Tuning**: Disable panic-on-oom, limit coredump size to prevent I/O lockup during instability.
