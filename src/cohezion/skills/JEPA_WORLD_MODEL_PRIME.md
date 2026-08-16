---
name: jepa-world-model-prime
description: "Expert in the Cohezion JEPA (Joint Embedding Predictive Architecture) world model (~2M params, causal masking, CPU-trainable). Use when: training or fine-tuning the JEPA predictor (jepa_world_model.py), diagnosing SurpriseExplorer anomalies, adjusting SIGReg regularization, interpreting JEPAWorldModel latent predictions, or wiring JEPA surprise events to JourneyTracker. Skip: general RL environment design (use RL_ENVIRONMENT_DESIGN_PRIME), generic PyTorch training patterns (use TRAINING_DIAGNOSTIC_LOOP_PRIME)."
version: v0.1-stub
tier: PRIME
domain: World-Model
status: stub
created: 2026-06-02
see_also: [RL_ENVIRONMENT_DESIGN_PRIME, TRAINING_DIAGNOSTIC_LOOP_PRIME, JOURNEY_TRACKING_PRIME, FLUME_METHODOLOGY_PRIME]
---

# SKILL: JEPA_WORLD_MODEL_PRIME

## STATUS
This is a stub. The JEPA world model is a production component in `src/cohezion/world_model/jepa_world_model.py` but lacks a dedicated skill document. A future session should expand this stub with verified procedure.

## DOMAIN EXPERTISE
You are a specialist in Cohezion's JEPA (Joint Embedding Predictive Architecture) world model — a ~2M parameter causal masking predictor that runs CPU-locally. You understand how to train, evaluate, checkpoint, and integrate this model with the broader compound engineering loop.

## KEY COMPONENTS
- `src/cohezion/world_model/jepa_world_model.py` — JEPAWorldModel class
- `SurpriseExplorer` — detects high-surprise states to guide exploration
- `SIGReg` — regularization module (TODO: document hyperparameter guidance)

## TODO (to be filled in by a future session)
1. Document `JEPAWorldModel.train()` / `predict()` / `encode()` API
2. SurpriseExplorer trigger conditions and surprise threshold defaults
3. SIGReg regularization budget guidance (underfitting vs overfitting)
4. Checkpoint/restore pattern via `SessionPersistence`
5. Integration with `JourneyTracker` (how to record surprise events)
6. CPU-trainable constraint — confirm no GPU assumptions in training path
7. Connection to RL environments: how JEPA world model feeds into `ManifoldEnv`

## RELATED ARCHITECTURE
From CLAUDE.md: "JEPA predictor (~2M params, causal masking), `SurpriseExplorer`, `SIGReg`" lives in `src/cohezion/world_model/`. See `docs/deep-dive-world-model.md` for architecture overview.


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for JEPA WORLD MODEL PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## INSTRUCTION

### 1. Initialize Context
```python
from cohezion.flume import PoincareManifoldND
from cohezion.agi.autoharness_policy import AutoHarnessPolicy

policy = AutoHarnessPolicy()
state = PoincareManifoldND.project([0.05] * 2048, target_dim=12)
```

### 2. Execute Deterministic Action
```python
# Verify state invariants with 0ms overhead
res = policy.verify_action("standard_execution", state)
assert res.allowed is True
```


## VERSION
v1.0 (Auto-Standardized & Verified)


## SEE ALSO
- **AUTOHARNESS_POLICY_PRIME**
- **JOURNEY_TRACKING_PRIME**
