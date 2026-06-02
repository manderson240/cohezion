---
name: cosmic-fire-protocol
description: Triggered when compound loop crosses HIHO threshold for the first time. Analogous to Population III stellar ignition at z=20-30 — the universe's first HIHO crossing. Enters BBQ mode, spawns R0 review, escalates tier.
category: compound
tags: [cosmic-fire, ignition, hiho, pop3, colibre, bbc-low-slow, ure]
---

# Skill: Cosmic Fire Protocol

## Context

In COLIBRE simulations, cosmic fire = Population III stellar ignition at z≈20-30.
This is the universe's first time ISM coherence crosses the HIHO threshold (0.45).
Once ignited, irreversible — the system cannot return to the chaotic VOID state.

**Cohezion mapping:** CFP fires when compound loop `quality_score ≥ 0.45` for the
first time. This IS the cosmogonic Step 7 (HIHO gate) being crossed.

## Cascade Actions (in order)

1. `enter_bbq_low_slow_mode` — no TTFT deadline, min 500 chars, unctuous output
2. `spawn_r0_adversarial_review` — 3-perspective challenge (rigor/physics/implementation)
3. `escalate_to_cpu_cloud_tier` — switch to CPU (Gemma-4-31B) or Sonnet
4. `persist_cosmic_fire_event` — SurrealDB `cosmic_fire_events` table (bi-temporal)
5. `telegram_notify_ignition` — Cohezion bot notification

## Usage

```python
from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol

cfp = CosmicFireProtocol(threshold=0.45, notify_telegram=True)

# Check + fire
event = cfp.ignite(quality_score=0.52, redshift=0.0)
if event:
    for action in cfp.ignition_cascade(0.52):
        execute(action)  # URE executes each step

# Integrate with COLIBRE
from cohezion.physics.colibre_bridge import ColibreState
sim = ColibreState(redshift=20.0, sfr_density=0.01, ism_hot_fraction=0.5, colibre_coherence=0.98)
if cfp.is_ignited(sim.colibre_coherence, sim.sfr_density):
    cfp.ignite(sim.colibre_coherence, redshift=sim.redshift)
```

## Physics Connection

- Ignition temperature: 155 MeV (same as QCD/QGP critical temperature)
- Zoom level doubles with each subsequent ignition (pop=1×, zoom=2×, 4×, 8×...)
- Pop III star formation rate ∝ `4×f_cold×(1-f_cold)` — same HIHO kernel!
- bi-temporal SurrealDB record: `valid_from=ignition_time`, `valid_to=null`

## Files

- Implementation: `src/cohezion/compound/cosmic_fire_protocol.py`
- Tests: `tests/unit/compound/test_phase19.py::TestCosmicFireProtocol`
- Harness: P3 (cascade has 5 actions, first = bbq_low_slow)
- Related: COLIBRE bridge (`physics/colibre_bridge.py`)
