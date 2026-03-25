---
name: ollama-community-model-integration
description: |
  Add a new Ollama model to Cohezion's 5-file routing stack. Use when: (1) scout finds a new model
  candidate, (2) model is not in Ollama's official library (needs username/model format),
  (3) adding any new local model to the swarm roster. Covers all 5 files that need coordinated
  edits: DynamicModelRouter, CostAwareRouter, SmartRouter, ModelQualityClassifier, ModelPoolConfig.
author: Claude Code
version: 1.0.0
---

# Add an Ollama Model to Cohezion Swarm

## Problem

Adding a new model to Cohezion requires coordinated edits across 5 routing files. Missing any one causes the model to be invisible to certain routing strategies.

## Trigger Conditions

- Scout identified a new model candidate
- User wants to add a model to the local roster
- Model is a community upload (e.g., `alibayram/smollm3` not `smollm3`)

## Solution

### Step 0: Pull the Model

```bash
# Official library models
ollama pull modelname

# Community models (not in official library)
ollama pull username/modelname
# Example: ollama pull alibayram/smollm3
```

Verify: `ollama list | grep modelname`

### Step 1: DynamicModelRouter (hardware-aware routing)

**File**: `src/cohezion/swarm/dynamic_model_router.py`
**Location**: `load_model_registry()` method

```python
"username/model:latest": ModelConfig(
    name="username/model:latest",
    size_gb=2.0,            # Check: ollama list shows size
    quantization="Q4_K_M",  # Common default
    context_max=128000,     # From model card
    expected_tps=15.0,      # Estimate from similar-sized models
    cache_hit_rate=0.18,    # Default for small models
    template_format="chatml",  # Check model card
    optimal_for_ide=[IDEPriority.OPENCODE],
),
```

### Step 2: CostAwareRouter (query complexity routing)

**File**: `src/cohezion/swarm/cost_aware_router.py`
**Location**: Class-level dictionaries (4 entries)

```python
MODEL_COSTS["username/model:latest"] = 0.0        # Local = free
MODEL_QUALITY["username/model:latest"] = 0.72     # See calibration guide below
MODEL_TPS["username/model:latest"] = 14.0         # Tokens per second
MODEL_LATENCY["username/model:latest"] = 55.0     # First-token latency ms
```

### Step 3: SmartRouter (task-type routing)

**File**: `src/cohezion/swarm/smart_router.py`
**Location**: `LOCAL_MODELS` dictionary

```python
"username/model:latest": ModelProfile(
    name="username/model:latest",
    capabilities=[ModelCapability.FAST, ModelCapability.CODING],
    context_length=128000,
    speed_tier=1,       # 1=fastest, 5=slowest
    quality_tier=3,     # 1=lowest, 5=highest
),
```

### Step 4: ModelQualityClassifier (fallback chains)

**File**: `src/cohezion/compound/model_quality_classifier.py`
**Location**: `self._model_hierarchy` dictionary

```python
# Add new model's fallback chain
"username/model:latest": ["phi3:mini", "qwen3-coder:30b"],

# Add as fallback option for similar-tier models
"phi3:mini": ["username/model:latest", "qwen3-coder:30b", ...],
```

### Step 5: ModelPoolConfig (lifecycle management)

**File**: `src/cohezion/swarm/model_pool_config.py`
**Location**: `TierConfig` class defaults

| Model Size | Tier |
|-----------|------|
| < 4GB | `hot_models` (stays loaded) |
| 4-16GB | `warm_models` (loaded on demand) |
| > 16GB | `cold_models` (evicted after 10min idle) |

## Quality Score Calibration

The `MODEL_QUALITY` score (0.0-1.0) in CostAwareRouter determines routing preference:

| Score | Meaning | Reference Models |
|-------|---------|-----------------|
| 0.5-0.6 | Basic tasks only | phi3:mini (0.6) |
| 0.7-0.8 | Good reasoning, tool use | SmolLM3 (0.72) |
| 0.8-0.9 | Strong general purpose | qwen3-coder:32b (0.85) |
| 0.9-1.0 | Best quality | deepseek-r1:8b (0.95) |

**Rule**: Same cost + higher quality = router always prefers the higher-quality model. Set the score relative to phi3:mini (0.6) and qwen3-coder (0.85).

## Verification

Run this smoke test after all 5 edits:

```python
uv run python3 -c "
from cohezion.swarm.smart_router import LOCAL_MODELS
from cohezion.swarm.cost_aware_router import CostAwareRouter
from cohezion.swarm.dynamic_model_router import DynamicModelRouter
from cohezion.compound.model_quality_classifier import ModelQualityClassifier
from cohezion.swarm.model_pool_config import TierConfig

MODEL = 'username/model:latest'
assert MODEL in LOCAL_MODELS
assert MODEL in CostAwareRouter.MODEL_COSTS
assert MODEL in CostAwareRouter.MODEL_QUALITY
assert MODEL in DynamicModelRouter().models
assert MODEL in ModelQualityClassifier()._model_hierarchy
tc = TierConfig()
assert MODEL in tc.hot_models or MODEL in tc.warm_models or MODEL in tc.cold_models
print('All 5 registries verified.')
"
```

## Example

See the SmolLM3 integration (this session) for a complete working example:
- Model: `alibayram/smollm3:latest` (community upload, not in official library)
- Quality: 0.72 (rivals 4B models at 3B size, dual-mode reasoning)
- Tier: hot_models (2GB, stays loaded)
