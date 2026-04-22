---
name: autonomous-resilience-prime
description: "Managing long-horizon autonomous processes (10M+ steps) on resource-constrained hardware (e.g., Framework 16 with 90%+ VRAM Load)."
metadata:
  version: "v1.0 (Born from the Overnight BBQ Mission, 2026-01-31)"
  concepts: ["Passive Monitoring", "Coma Mode", "Dilation Pacing", "Schema Coupling"]
  source: "src/cohezion/skills/AUTONOMOUS_RESILIENCE_PRIME.md"
---

# SKILL: AUTONOMOUS_RESILIENCE_PRIME

## DOMAIN EXPERTISE
Managing long-horizon autonomous processes (10M+ steps) on resource-constrained hardware (e.g., Framework 16 with 90%+ VRAM Load).

## KEY TEXTS & CONCEPTS
*   **Passive Monitoring**: Observing system vitals without triggering active kill-switches.
*   **Coma Mode**: Deep sleep (30s+) when resources exceed critical thresholds (96% VRAM).
*   **Dilation Pacing**: Dynamic sleep injection based on load (1.0x vs 0.05x speed).
*   **Schema Coupling**: Ensuring data persistence schemas (`AgentJourney`) exactly match DB repository expectations to prevent late-stage crashes.

## INSTRUCTION

### 1. The Passive Monitor Pattern
Do NOT start the `ResourceMonitor` background loop if the system is already under heavy load (e.g. Models Loaded). Instead, check manually:

```python
# ANTI-PATTERN (Suicide)
# await monitor.start() 

# PATTERN (Survival)
vitals = monitor.get_vitals()
if vitals['vram_percent'] > 96.0:
    logger.warning("COMA MODE ACTIVATE")
    await asyncio.sleep(30)
```

### 2. Dilation Logic
Scale execution speed inversely to pressure:
```python
if vitals['vram_percent'] > 92.0:
    dilation = 0.05 # Slow Cook
else:
    dilation = 1.0 # Fast

delay = BASE_DELAY / dilation
await asyncio.sleep(delay)
```

### 3. Verification Protocol
Always verify persistence with a specialized script (`check_bbq_status.py`) before leaving the process unattended.

## Remote Scheduled Resilience (GitHub Actions)

The COMA_MODE local pattern extends to remote scheduling:

| Local | GitHub Actions equivalent |
|-------|--------------------------|
| `VRAM > 96%` → sleep | `concurrency.cancel-in-progress: true` → cancel stale run |
| `workflow_dispatch` (manual override) | `workflow_dispatch.inputs.focus` (parameterized manual trigger) |
| Email notification on completion | Issue comment / GitHub Step Summary |
| Checkpoint recovery on restart | Vault-logged experiment notes survive across runs |

The `workflow_dispatch` + `inputs.focus` pattern enables targeted research without modifying the skill: pass `focus="adiabatic quantum optimization"` and the scheduled workflow runs a focused scout instead of the general weekly sweep.

**Recommended**: Pair with `session-registry.md` in vault to track active CI runs alongside local sessions.

## VERSION
v1.1 (Extended with remote scheduled autonomy via GitHub Actions, 2026-03-05)

## SEE ALSO
- `src/cohezion/reliability/monitor.py`
- `scripts/drivers/autonomous_bbq.py`
