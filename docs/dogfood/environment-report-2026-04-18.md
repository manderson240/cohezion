# Dogfood environment report — 2026-04-18

Session 104, Phase 1 of the dogfood plan. Snapshot of the live inference surface at the start of dogfood execution. Cross-referenced with `local_environment_quirks.md` and `SHOWCASE.md` claims.

## Lane-by-lane state

| Lane | Port | Health probe | Status | Notes |
|------|------|--------------|--------|-------|
| NPU | 13306 | `/v1/models` 200 OK | ✅ UP | 10 models served. Confirmed entries include `DeepSeek-Qwen3-8B-GGUF` (Q4_1 reasoning) and `gemma-4-E2B-it-GGUF` (sensing lane per Symphony). |
| iGPU ROCWMMA | 13307 | connection refused | ❌ DOWN | Cold-boot-only recovery per `local_environment_quirks.md` — DO NOT restart live. |
| iGPU Unified | 13308 | connection refused | ❌ DOWN | Same as above. |
| CPU | 13309 | connection refused | ❌ DOWN | Not launched. `make serve-fleet` would bring up but requires lemonade-server restart. |
| Ollama | 11434 | `/api/tags` 200 OK | ✅ UP | 14 models in pool. Free for local routing. |
| SurrealDB | 8001 | `/health` 200 OK | ⚠️ PARTIAL | `/health` green but `/sql` returns 404 (S103 discovery, L291 carryover). Service unit shows `failed (exit 2)` yet port is listening. |
| Claude CLI | n/a | `/home/mike-anderson/.local/bin/claude` exists | ⚠️ CAUTION | Binary installed. Live `-p ping --max-budget-usd 0.01` probe exited 1 during S103 benchmark — auth or config. From inside a Claude Code session the auth is the session's; from a standalone script it may not be. |
| Gemini CLI | n/a | `/home/linuxbrew/.linuxbrew/bin/gemini` exists | ✅ UP | 0.38.2 per last probe. Used as secondary headless lane. |

## Effective local routing surface

**Fully usable without incident:** NPU (13306), Ollama (11434), Gemini CLI.

**Conditionally usable:** Claude CLI (works from within this Claude Code session; unreliable in spawned subprocesses).

**Unusable this session:** iGPU lanes (13307, 13308), CPU lane (13309), SurrealDB write path.

## Implications for dogfood claims

| Claim | Can dogfood now? | Why / mitigation |
|-------|------------------|------------------|
| A — Fleet routes correctly | Partial | Can verify NPU + Ollama paths; iGPU/CPU paths require their lanes UP |
| B — TieredOrchestrator budget propagation | ✅ Yes | Pure unit test, no live fleet needed |
| C — `extend_claude()` fast-fails | ✅ Yes | Unit test with mocked `route()` |
| D — CLI liveness probe uses `-p` | ✅ Yes | Unit test with mocked `subprocess.run` |
| E — `make vmodel-all` 27/27 | ✅ Yes | Deterministic |
| F — `pytest tests/inference/` 45/45 | ✅ Yes | Deterministic |
| G — except-subclass linter | ✅ Yes | Deterministic |
| H — Hook-health warns on missing script | ✅ Yes | Bash self-test |
| I — skill_registry sync idempotent | ✅ Yes | Deterministic |
| J — Config A stderr sidecar | ⚠️ Partial | Needs `make benchmark-fleet` which requires Claude CLI or local lane. With NPU up, Config B (local-only) will succeed; Config A likely fails with timeout as in S103, producing the sidecar we want to verify. |

**7 of 10 claims fully verifiable without infrastructure changes.**
Claim A is partial (can verify routing logic + NPU path; iGPU/CPU paths deferred).
Claim J works in degraded mode (Config A failure is itself what we want to observe).

## Non-silicon tools reachable from Claude Code session

- `uv run pytest` against main worktree's 3.11 venv (`/home/mike-anderson/dev/cohezion/.venv`)
- `uv run python scripts/...` for our shipped tools
- `uv run ruff check`, `make vmodel-all`, `make benchmark-fleet`
- `gh` CLI for PRs + merges
- `git` worktree operations

## /autoresearch invocation

The `/autoresearch` skill / command was not invoked in this Phase 1 — the environment probe was complete and unambiguous via direct `curl` + `which`. `/autoresearch` would add value for broader research tasks (e.g. literature on specific JEPA variants, competitive kernel approaches), not for "is this port open." Reserved for Phase 4 synthesis if useful.

## Carryover from environment report → ROADMAP

- **iGPU cold-boot recovery workflow documented** — S103 learning noted the aperture can enter zombie state; document the cold-boot sequence explicitly with expected latency (currently implicit in quirks.md).
- **Claude CLI live-dispatch auth matrix** — L360 corrected the flag shape but the "works from CC session, fails from script" observation is new. Add to `local_environment_quirks.md` in a later PR.
- **SurrealDB 8001 `/sql` endpoint 404** — repeated finding from S102 → S103 → S104. Likely a systemd unit ordering issue. User-only fix (needs `systemctl`). Already on ROADMAP as carryover P2.

## Next phase

Phase 2 — exercise Claims A–D with throwaway `scripts/dogfood/*.py` drivers. Starting with the deterministic claims B-D (no fleet dependency).
