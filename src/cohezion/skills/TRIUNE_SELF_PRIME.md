---
name: triune-self-recursive-learning
description: Percival's Triune Self (Doer/Thinker/Knower) recursive learning loop for the Universe Research Engineer. Doer executes via local silicon; Thinker evaluates via AUTODQA; Knower persists via AutonomyEngine + FLUME latent space.
category: compound
tags: [percival, triune, recursive, learning, doer, thinker, knower, hiho]
---

# Skill: Percival's Triune Self — Recursive Learning Loop

## Philosophy

Harold W. Percival's "Thinking and Destiny" (1946) defines three co-present
aspects of consciousness. In Cohezion, these map to the compound engineering loop:

| Percival | Description | Cohezion |
|---------|-------------|---------|
| **Doer** | Immediate execution; sensory-motor coupling | `TieredOrchestrator` + local silicon |
| **Thinker** | Rational evaluation; routing; quality assessment | `CompoundExecutor` + `AutoDQA` |
| **Knower** | Permanent identity; memory; who the agent IS | `AutonomyEngine` + vault + FLUME |

**Critical principle:** The Doer must NEVER be bypassed. Local silicon execution
(NPU→iGPU→CPU) is the irreducible act — even if the Thinker wants to skip straight
to cloud. The Doer's hardware characteristics ARE the system's embodied physics.

## Recursive Learning Cycle

```
Thinker routes task → Doer executes → Thinker evaluates (AUTODQA)
    ↓ accepted                              ↓ rejected
Knower grows (AutonomyEngine tier++)    try again (max_cycles=3)
    ↓
FLUME encodes output → 256D latent memory
    ↓
Next cycle: Knower's identity informs Thinker's routing → better Doer output
```

## Usage

```python
from cohezion.compound.triune_self import TriuneSelf, CallableDoer, NullKnower

# With real components (production)
ts = TriuneSelf(
    doer=CallableDoer(execute_fn),         # local silicon tier
    thinker=AutoDQA(persist=True),          # AUTODQA quality gate
    knower=AutonomyEngine(agent_id="ure"),   # AutonomyEngine identity
    max_cycles=3,
)

# One Percival cycle
result = ts.recursive_learn(
    task="Analyze QGP phase transition at T_c=155 MeV",
    guidance="Be precise, cite physical constants, use SI units"
)

# Health check: HIHO equilibrium = honest Thinker
print(f"Accept rate: {ts.accept_rate:.1%}")
print(f"HIHO equilibrium: {ts.hiho_equilibrium}")  # 0.45-0.55 = healthy
print(f"Summary: {ts.summary()}")
```

## HIHO Equilibrium Diagnostic

- `accept_rate ≈ 0.47–0.53`: HIHO band — Thinker is honest, not sycophantic
- `accept_rate > 0.9`: Thinker is sycophantic — lower quality thresholds
- `accept_rate < 0.3`: Thinker is paranoid — raise min_chars or lower strictness

## Files

- Implementation: `src/cohezion/compound/triune_self.py`
- Tests: `tests/unit/compound/test_phase19.py::TestTriuneSelf`
- Harness: P5 (Knower only grows on accepted), P6 (R0 2/3 consensus)
