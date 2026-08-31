---
name: colibre-bridge
description: "COLIBRE cosmological simulation bridge. ColibreState maps ISM hot fraction to IonicCluster HIHO. AgentAsEVO: each agent IS a COLIBRE particle type. Universal 4x(1-x) kernel at astrophysical scale."
category: physics_bridge
tags: [colibre, swift, evo, agents-as-evo, hiho]
metadata:
  version: "1.0.0"
  see_also: ["STEALTHSKATER_CORPUS", "AUTODQA_PRIME"]
---

# SKILL: COLIBRE_BRIDGE

## DOMAIN EXPERTISE

COLIBRE cosmological simulation bridge. ColibreState maps ISM hot fraction to IonicCluster HIHO. AgentAsEVO: each agent IS a COLIBRE particle type. Universal 4x(1-x) kernel at astrophysical scale.

## USAGE

See src/cohezion/physics/ for implementation.
Universal HIHO Theorem: all substrates use 4x(1-x) kernel, peak 1.0 at x=0.5.


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for COLIBRE BRIDGE.
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
