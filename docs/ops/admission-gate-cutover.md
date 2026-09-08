# Admission gate cutover — lemond behind the byte-aware gate

2026-09-01. The prevent-half of the OOM remediation (the react-half — the guard actuator —
landed in v1.16.1). Module: `cohezion.platform.admission_gate` (+ `admission_proxy`);
unit: `scripts/cohezion-admission-gate.service`.

## Why this shape

lemonade's own cap counts models, not bytes, and its config is ephemeral. The gate is a
thin proxy on :13305 (invariant N1 — every client keeps its port) consulting the landed
byte-aware machinery (`check_oom_risk`, hard 16 GB floor, tier-blind below the floor —
the 08-31 killer was an FLM/NPU model).

## The three council tests, and where they live

| Council test | Enforced by |
|---|---|
| Uncapped-Window / TOCTOU (glm) | Gate has no warm-up state — enforces from request #1 (`test_gate_enforces_from_the_first_request`); the CUTOVER ORDER below closes the deployment-level window. |
| Cold-Boot Cap Persistence (deepseek) | Config = frozen dataclass from env; the systemd unit is the persistence layer (`test_config_rereads_environment_on_every_construction`). Reboot survival = the unit's `Environment=` lines. |
| Direct-to-Backend Bypass (gemma4) | Cannot be *prevented* by any proxy — same-host processes can hit lemond's internal port and the per-model backend ports (:8002…). The gate makes the surface auditable: `GET /admission/status` → `bypass_paths`. Trust boundary documented in the module docstring. |

## Cutover order (TOCTOU-safe: :13305 is never simultaneously lemond and unguarded)

1. `git pull` on the main checkout (gets this code).
2. Move lemond to the internal port: edit its unit/config so it binds **:13315**
   (drop-in override or lemonade config; verify with `curl :13315/api/v1/health`).
   NOTE: from the moment lemond leaves :13305 until step 3 completes, clients get
   connection-refused — a closed window, not an unguarded one. Keep it short.
3. Install + start the gate in SHADOW mode (unit ships `COHEZION_ADMISSION_ENFORCE=0`):
   `cp scripts/cohezion-admission-gate.service ~/.config/systemd/user/ &&
   systemctl --user daemon-reload && systemctl --user enable --now cohezion-admission-gate`
4. Verify: `curl :13305/api/v1/health` (proxied), `curl :13305/admission/status`
   (config + counters + bypass_paths).
5. **Shadow-watch ≥ 1 day**: `shadow_refusals` counts what enforcement WOULD have blocked.
   Zero surprises expected in normal load; each shadow refusal is a would-have-been save
   or a false positive to tune.
6. Flip `COHEZION_ADMISSION_ENFORCE=1` in the unit, `daemon-reload`, restart the gate.
7. Live drill (pairs with the guard-actuator drill): with headroom deliberately reduced,
   request a heavy non-resident model → expect HTTP 503 `admission_refused`.

## Rollback

`systemctl --user stop cohezion-admission-gate`, move lemond back to :13305. Two
commands, no state to migrate (the gate holds none — by design and by test).

## What this does NOT do

- Does not stop same-host processes that bypass :13305 (documented trust boundary).
- Does not bound GTT out-of-band (that's the amdgpu.gttsize / watermark / watchdog
  bundle — separate user-gated proposal).
- Well-behaved clients see 503 + JSON reason and fall back via their existing cascades;
  clients that retry-loop a 503 will keep being refused until headroom returns — that is
  the intended behavior.
