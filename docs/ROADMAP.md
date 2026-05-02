# Cohezion Roadmap — Continued Improvements

**Horizon:** Next 4–8 weeks
**Anchor:** sprint-2026-04-18 deliverables + 13 review-derived follow-ups
**Optimization target:** Anthropic Research Engineer, Universes application + compound systems engineering capability

---

## Now (this week — ≤30 min fixes each)

| Priority | Item | Source | Effort | Status |
|----------|------|--------|--------|--------|
| ~~P0~~ | ~~Nested orchestrator budget pass-through (edge-case #10 — O3 completion)~~ | Adversarial review | 20 min | ✅ O3b invariant + 2 pytest cases; `run(budget_usd=…)` propagates |
| ~~P0~~ | ~~CLI liveness probe: swap `--version` for live `-p` dispatch~~ (edge-case #14) | Adversarial review | 15 min | ✅ `_probe_anthropic` uses `-p ping --bare --model haiku-4-5 --max-budget-usd 0.01`. **Note**: original roadmap text said `--max-tokens 1` — that flag does not exist in Claude Code CLI; corrected to `--max-budget-usd` |
| ~~P0~~ | ~~`httpx.Timeout(connect=5.0)` explicit on all `AsyncClient` instances~~ | Security MED | 10 min | ✅ 3 call sites in `fleet.py` now use `httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)` |
| ~~P1~~ | ~~Validate `claude_model in registry.models` before `extend_claude` local loop~~ | Edge-case #2 | 10 min | ✅ Validation moved to top of `extend_claude`; regression test asserts `route()` is never awaited when model is invalid |
| ~~P1~~ | ~~Config A stderr capture sidecar + Phase 2 harness I2b invariant~~ | Scientific rigor #2 | 25 min | ✅ `benchmark_fleet.py` writes `<report>.config_A.stderr.log` with full stdout+stderr per failed prompt; Phase 2 harness I2b asserts sidecar exists and is non-empty when Config A has 0 successes |
| ~~P1~~ | ~~Benchmark output path boundary check~~ | Security MED | 10 min | ✅ `_validate_output_path` rejects `--output` paths that `resolve().relative_to(cwd)` raises on |
| ~~P2~~ | ~~`launch_fleet_safe.sh`: verify model identity on port~~ | Edge-case #13 | 15 min | ✅ `verify_model_on_port` + 4th arg to `wait_for_port` grep the `/v1/models` body for the expected model id; all 4 lanes now pass `expected_model` |
| ~~P2~~ | ~~Narrow `except Exception` in `_inject_symmetry_axis`~~ | Edge-case #4 | 5 min | ✅ `except (ImportError, Exception)` (effectively bare-except) narrowed to `(ImportError, AttributeError, KeyError, TypeError, ValueError)`. `_get_symmetry_coherence` was already narrow (`except ImportError`) — no change needed |

**Gate:** all 8 land + `make vmodel-all` green + 41/41 tests passing.

**Progress (2026-04-18):**
- **Session 2** (3 P0 items): tests 41 → 44, V-model invariants 25 → 26 (+O3b).
- **Session 3** (5 P1/P2 items): tests 44 → 45, V-model invariants 26 → 27 (+I2b). All 8 "Now" items now landed.

## Carryover from Session 103 retrospective (housekeeping)

| Priority | Item | Effort | Source |
|----------|------|--------|--------|
| P1 | Push `isolated/session-oom-modularity` + cherry-pick `2cbc4d17f`+`00d1be0b8` onto fresh `feat/inference-fleet` off `main`, open PR (user-gated, shared-state) | 15 min | Landing |
| P1 | Replace (or delete) `.git/hooks/pre-commit.disabled` — references missing `scripts/resource-leak-detector.py` (L364). Session-start hook-health check should flag dangling references | 10 min | L364 |
| P2 | Ruff cleanup on sprint baseline: 40 pre-existing errors in `src/cohezion/inference/` (RUF002 docstring unicode ×/–, N806 `_BUDGET_EPS`, RUF100 unused noqa, F841 `last_ttft`, TC001 Task import). All pre-date S103 follow-ups — separate focused commit | 15 min | Inherited from sprint |
| P2 | Custom ruff rule candidate: flag `except (A, B)` tuples where `issubclass(A, B)` (L359 stealth bare-except) | 25 min | L359 |
| P2 | Update `skill_registry.json` from 133 → 235 entries (carry-over from S102) | 10 min | S102 carry-over |
| P2 | SurrealDB service unit: add `ExecStartPre=/usr/bin/mkdir -p /tmp/surrealdb` to prevent crash-loop; `/sql` endpoint on :8001 currently returns 404 even though `/health` is OK (S103 discovery) | 15 min | L291 + S103 |

## Near (2 weeks)

### Full benchmark (n=20) and replace informal TTFT numbers

- Cold-start the 4-lane fleet via `make serve-fleet` (requires lemond `max_loaded_models=4` config edit which is already in place, pending `systemctl restart lemonade-server`)
- Run `make benchmark-fleet` at `--prompts 20` for each config
- Write actual p50/p95 back into `registry.py` typed fields
- Update `SHOWCASE.md` + `COVER_LETTER_universes.md` with the real benchmark numbers
- Archive the informal warm-loop measurements in `docs/benchmarks/pilot-2026-04-18.md` for provenance

### TurboQuant activation on NPU path

- `src/cohezion/inference/turboquant/` — promote `research/turboquant/turboquant/` via `git mv`
- Wire PolarQuant rotation + QJL 1-bit correction into `fleet._dispatch_openai_compatible` streaming path
- Measure KV-cache footprint before/after on a 128k-context prompt
- Target: `128k context footprint ≤55 GB` (from ~80 GB baseline) per `STRIX_HALO_UNLOCK_GUIDE.md`

### Anthropic Advisor Tool wiring

- Replace `extend_claude()` naive escalation with the Anthropic SDK's Advisor Tool (`advisor-tool-2026-03-01` beta header)
- Primary model (Haiku) calls the advisor (Sonnet/Opus) mid-response via the SDK
- Persistent across sessions without requiring `/advisor` REPL invocation
- Tier path in `OrchestrationResult` surfaces which calls used the advisor

### Root archaeology execution (not just inventory)

- `docs/archaeology/INVENTORY.md` catalogued 6 categories; execute the batch `git mv` per category (1 commit per category)
- Write `docs/lessons/LESSONS.md` + `ANTI_PATTERNS.md` from the BREAKTHROUGH/COMPLETE status-file proliferation pattern
- Target: root-level item count 608 → ~50

## Mid (4 weeks)

### Agent-swarm substrate

- `TieredOrchestrator` today composes models. Extend to compose **agents** (each tier = a full agent with tool-use, memory, rollback)
- Integrate with `src/cohezion/swarm/team_executor.py` — tier 0 is a sub-agent, tier 1 is a super-agent that reviews tier 0's actions
- Recursive: sub-agents can have their own sub-orchestrators (design supports this via `Runnable` protocol; needs live demo)

### Capability eval harness (beyond the TTFT benchmark)

- `UniverseEvaluator` with JEPA plausibility rubric — rate each agent-action output for physical realism
- OpenEnv-compatible environment registry (`ManifoldEnv`, `SwarmEnv`, + new `ToolUseEnv`, `SandboxEnv`)
- Bootstrap CIs, ≥3 baselines per eval
- Deliverable: `make capability-eval` produces `docs/evaluations/<date>.md` with per-agent, per-env, per-model scoring

### GAIA SDK deeper integration

- `GaiaAgentTier` shipped as adapter today — extend to native `MCPAgent` usage
- MCP tool bridge: cohezion-exposed MCP tools reachable from inside GAIA agents (`cloud-vault-mcp`, `compound-mcp`, etc.)
- XDNA 2 NPU scheduling: use GAIA's native scheduler instead of spawning one `lemonade` invocation per call

### Benchmark cross-platform

- Today's benchmark runs against Strix Halo. Extend to run against:
  - MI300X (AMD CDNA server GPU — huge context window ceiling)
  - AMD EPYC CPU-only (AVX-512 on server silicon, no iGPU)
  - Optional: compare head-to-head against a standard Claude-API baseline client
- Deliverable: multi-platform `docs/benchmarks/cross-platform-2026-05.md`

## Long (8+ weeks)

### Universes-team application follow-through

- Submit Anthropic Universes application with the revised cover letter
- Prepare live demo session: `make demo-universes` + `make demo-orchestrate` + `make vmodel-all` + `make health-fleet` in a single 15-min walkthrough video
- Record the `benchmark_fleet.py` run live for reproducibility proof

### Manifest dirs the plan deferred

- `mcp_tool_server/` (Rust) — only if FastMCP saturates at scale (>40 tools)
- `latent_topology/` (C++/SWIFTSIM) — research-grade; schedule as a quarter-long spike after the application lands
- `vault_synapse/` (Obsidian TS plugin) — only if a demo-reviewer use case materializes

### Compound engineering loop upgrade

- Today the 11-step `CompoundExecutor` pipeline exists. Hook the new V-model AutoHarness pattern into each step: every `SkillRefiner` update runs `vmodel-phase{N}` for that skill's domain
- `make compound-validate` — full loop through all refined skills with harness gates

### Training-loop use case (the cover-letter proof)

- Build a tight agent-training loop (10 episodes × 100 steps × 1 LLM call per step = 1000 calls)
- Measure total wall-clock on 3 configurations: Claude-only, local-only, hybrid via `extend_claude`
- Target: hybrid matches Claude-only quality at ≤ 20% of wall-clock and ≤ 5% of cost
- Publish as `docs/case-studies/agent-training-throughput.md` — the empirical number that validates the Universes cover letter's "12.5× faster iteration" claim

---

## Non-goals (explicitly out of scope for this roadmap)

- Rebuilding Cohezion's existing swarm/agent framework — we compose with it, not replace it.
- Fighting the iGPU ROCm Binary Hard-Lock — the NPU path is primary. iGPU stays a secondary lane until a fixed PyTorch wheel lands.
- Porting to non-AMD silicon — Strix Halo is the optimization target. Generic paths work but this roadmap does not pursue them.
- Growing the cover letter's list of competitions — 3 is enough; the value is the platform, not the wins.

---

## Success metrics (4-week checkpoint)

1. **`make vmodel-all` passes without the PILOT flag** (n≥20 benchmark executed, typed p50/p95 populated, all 25 V-model invariants green)
2. **Zero HIGH-severity security findings in a re-run adversarial review**
3. **Root item count ≤ 100** (down from 608; target was 50 but staged execution will settle higher)
4. **TurboQuant NPU activation measured end-to-end** with before/after KV footprint in `docs/benchmarks/turboquant-activation.md`
5. **Anthropic application submitted** with a reproducible `make demo-universes` run committed to the public branch
