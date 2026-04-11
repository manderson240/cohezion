# Comprehensive Model Discovery

## When to Use This Skill

Use this pattern when:
- Building orchestration systems that need complete model inventory
- Discovering models across heterogeneous backends (NPU, GPU, Local)
- You need capability mapping without loading every model
- System resources are constrained (can't load all models)
- Want to capture operational learnings for future discovery

## What Problem It Solves

**Challenge**: Models are scattered across:
- SDK registries (FLM, Lemonade, Ollama)
- Local cache directories (GGUF files)
- Remote repositories
- Multiple backends with different formats

## Architecture

```
Discovery Pipeline:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Source Layer   │────▶│  Parse/Extract  │────▶│  Enrich/Validate│
│                 │     │                 │     │                 │
│ - FLM list      │     │ - Format rules  │     │ - Capability    │
│ - Known models  │     │ - Name patterns │     │   inference     │
│ - File system   │     │ - Error handling│     │ - Merge dupes   │
│ - Validated     │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘

Learning Capture (parallel):
- Parsing patterns discovered
- Capability mappings learned
- Error patterns identified
- Resource constraints observed
```

## Quick Start

### Basic Discovery

```python
from cohezion.swarm.model_capability_registry import ModelCapabilityRegistry

registry = ModelCapabilityRegistry()

# Discover all models across sources
models = await registry.discover_all_models()

# Results:
# - 12 NPU models from FLM
# - 35 GPU models from local cache
# - 3 validated with performance metrics

print(f"Discovered {len(models)} models total")
```

### Resource-Safe Discovery

```python
from cohezion.swarm.model_capability_registry_resource_safe import (
    ResourceSafeModelCapabilityRegistry,
    ResourceConstraints,
)

# Set memory limits
constraints = ResourceConstraints(
    max_memory_usage_percent=70,  # Stop if system > 70%
    max_single_model_mb=8192,     # Skip models > 8GB
    min_free_memory_mb=16384,     # Keep 16GB free
)

registry = ResourceSafeModelCapabilityRegistry(constraints=constraints)
models = await registry.discover_all_models()

# Large models automatically skipped if memory tight
```

## Complete Example

### Comprehensive Discovery with Learning Capture

```python
import asyncio
import psutil
from pathlib import Path

async def discover_with_learning_capture():
    """Discover all models and capture operational learnings."""
    
    learnings = []
    all_models = []
    
    # Source 1: FLM (NPU) with error handling
    print("Discovering from FLM...")
    try:
        result = subprocess.run(
            ['flm', 'list'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        for line in result.stdout.split('\n'):
            # Parse: "qwen3:4b ⏬"
            if ':' in line and '⏬' in line:
                name = line.split()[0]
                all_models.append({
                    'name': name,
                    'backend': 'NPU',
                    'source': 'FLM'
                })
        
        learnings.append({
            'category': 'parsing',
            'insight': 'FLM format: {model}:{size} ⏬'
        })
        
    except Exception as e:
        learnings.append({
            'category': 'error_handling',
            'insight': f'FLM discovery failed: {e}'
        })
    
    # Source 2: Known models (fallback)
    known_models = [
        ('qwen3:4b', 'NPU', 'code'),
        ('gemma3:4b', 'NPU', 'general'),
        ('Gemma-4-E2B-it', 'GPU_VULKAN', 'reasoning'),
    ]
    
    for name, backend, category in known_models:
        if not any(m['name'] == name for m in all_models):
            all_models.append({
                'name': name,
                'backend': backend,
                'category': category,
                'source': 'known_registry'
            })
    
    # Enrich with capability inference
    for model in all_models:
        model['capabilities'] = infer_capabilities(model['name'])
    
    # Resource check
    memory = psutil.virtual_memory()
    if memory.percent > 70:
        learnings.append({
            'category': 'resource_safety',
            'insight': f'System memory at {memory.percent}%, skipping heavy validation'
        })
    
    return all_models, learnings


def infer_capabilities(model_name: str) -> List[str]:
    """Infer capabilities from naming patterns."""
    name = model_name.lower()
    capabilities = []
    
    # Code models
    if any(x in name for x in ['qwen', 'code', 'coder']):
        capabilities.extend(['code_generation', 'code_completion'])
    
    # Vision models
    if any(x in name for x in ['vl', 'vision']):
        capabilities.extend(['vision_understanding'])
    
    # Reasoning
    if any(x in name for x in ['instruct', 'reasoning']):
        capabilities.extend(['instruction_following', 'reasoning'])
    
    # General
    capabilities.extend(['text_generation'])
    
    return capabilities
```

## Key Learnings

### Learning 1: Graceful Degradation

**Pattern**: Each source has independent error handling.

```python
try:
    npu_models = discover_flm()
except Exception as e:
    learnings.append({"source": "flm", "error": str(e)})
    npu_models = []  # Continue with other sources
```

**Value**: System doesn't crash if one SDK fails.

---

### Learning 2: Name-Based Capability Inference

**Pattern**: Model names encode intent.

| Name Pattern | Inferred Capability |
|--------------|----------------------|
| `qwen`, `code` | code_generation |
| `vl`, `vision` | vision_understanding |
| `whisper` | audio_transcription |
| `instruct` | instruction_following |

**Code**:
```python
def infer_capabilities(name: str) -> List[str]:
    name = name.lower()
    capabilities = []
    
    if 'code' in name or 'qwen' in name:
        capabilities.append('code_generation')
    
    if 'vl' in name or 'vision' in name:
        capabilities.append('vision_understanding')
    
    return capabilities
```

---

### Learning 3: Memory-Aware Operations

**Pattern**: Check resources BEFORE expensive operations.

```python
async def validate_model_safely(model: dict) -> dict:
    memory = psutil.virtual_memory()
    
    if memory.percent > 70:
        return {
            'status': 'skipped',
            'reason': f'System memory at {memory.percent}%'
        }
    
    # Only proceed if safe
    return await light_validation(model)
```

**Value**: Prevents OOM during discovery.

---

### Learning 4: Learning Capture

**Pattern**: Capture insights as you go.

```python
learnings = []

def log_learning(category: str, insight: str):
    learnings.append({
        'category': category,
        'insight': insight,
        'timestamp': now()
    })

# During discovery:
log_learning('parsing', 'FLM uses {model}:{size} ⏬ format')
log_learning('error_handling', 'FLM timeout at 10s, retry with backoff')
```

**Value**: Builds organizational knowledge.

---

## Common Pitfalls

### ❌ Pitfall 1: Loading All Models

```python
# BAD: Crashes system
for model_name in discovered_models:
    load_full_model(model_name)  # OOM!
```

### ✅ Solution: Metadata Only

```python
# GOOD: Metadata only
for model_name in discovered_models:
    metadata = get_model_info(model_name)  # Light
    # Full load only when serving
```

---

### ❌ Pitfall 2: Ignoring Errors

```python
# BAD: Entire discovery fails
def discover():
    models = discover_flm()  # Raises if FLM down
    models += discover_local()
    return models
```

### ✅ Solution: Error Isolation

```python
# GOOD: Graceful degradation
def discover():
    models = []
    
    try:
        models += discover_flm()
    except:
        log_error("FLM unavailable")
    
    models += discover_local()  # Continue
    return models
```

---

## Examples

### Example 1: Complete Discovery

```python
async def full_discovery():
    """Discover all models with complete metadata."""
    
    registry = ModelCapabilityRegistry()
    
    # Phase 1: Discovery (lightweight)
    models = await registry.discover_all_models()
    # → Discovers 47 models from FLM + local + known
    
    # Phase 2: Validation (resource-aware)
    await registry.benchmark_all()
    # → Validates 5 models (others skipped for memory safety)
    
    # Query
    best_code_model = registry.find_best_model(
        task="Write Python function",
        required_capabilities={'code_generation'},
        preferred_backend='NPU'
    )
    # → qwen3:4b (NPU, 75 TPS, validated)
    
    return registry
```

### Example 2: Export for Orchestration

```python
# Export in format ready for routing decisions
registry = await full_discovery()

# Get routing map
routing_map = {
    'code_tasks': registry.get_ranking({'code_generation'}),
    'reasoning_tasks': registry.get_ranking({'reasoning'}),
    'vision_tasks': registry.get_ranking({'vision_understanding'}),
}

# Result:
# {
#   'code_tasks': [
#     ('qwen3:4b', 75.0),
#     ('qwen3.5:4b', 75.0),
#   ],
#   'reasoning_tasks': [
#     ('Gemma-4-E2B-it-GGUF', 97.26),
#   ]
# }
```

---

## Files

- **Implementation**: `src/cohezion/swarm/model_capability_registry.py`
- **Resource-Safe Version**: `src/cohezion/swarm/model_capability_registry_resource_safe.py`
- **Example Script**: `comprehensive_discovery_with_learnings.py`
- **Output Format**: `comprehensive_model_registry.json`

---

## References

**Related Skills**:
- Multi-Agent Orchestration
- Resource-Guarded Operations
- TDD Integration

---

**Version**: 1.0
**Last Updated**: 2026-04-10
