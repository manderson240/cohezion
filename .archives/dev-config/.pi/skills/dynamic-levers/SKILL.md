---
name: dynamic-levers
description: Tunable parameters for system optimization with goals, ranges, and safe adjustment methods.
---

# Dynamic Levers System

Tunable parameters for system optimization with clear goals, measurable metrics, and safe adjustment ranges.

## When to Use

- System has parameters that need tuning
- Goals are quantitative and measurable
- Want gradual improvement over time
- Need safe bounds (prevent extreme values)

## Quick Start

```python
from cohezion.swarm.dynamic_levers import create_default_lever_system

# Create system
system = create_default_lever_system()

# Push (increase) a lever
system.push("deterministic_ratio", 0.1)  # Push toward 80%

# Pull (decrease) a lever
system.pull("discovery_timeout_seconds", 2.0)

# Set specific value
system.set("validation_sample_size", 10.0)

# View dashboard
system.print_dashboard()
```

## Architecture

```
DynamicLeverSystem
├── DynamicLever (8 predefined)
│   ├── deterministic_ratio
│   ├── heuristic_confidence_threshold
│   ├── discovery_timeout_seconds
│   ├── validation_sample_size
│   ├── memory_safety_threshold_percent
│   ├── capability_validation_enabled
│   ├── parallel_discovery_workers
│   └── max_heuristic_fallbacks
│
├── Goals (target values)
├── Ranges (safe min/max)
└── History (adjustment tracking)
```

## Predefined Levers

### 1. deterministic_ratio
**Goal**: 80% (currently 8%)
**Range**: 0-1
**Purpose**: Ratio of deterministic vs heuristic parsing

When to push: Implementing new deterministic parsers
When to pull: Accepting heuristic fallback temporarily

### 2. heuristic_confidence_threshold
**Goal**: 85% (currently 70%)
**Range**: 0-1
**Purpose**: Minimum confidence to trust heuristic results

When to push: Fewer false positives needed
When to pull: More coverage needed (lower confidence acceptable)

### 3. discovery_timeout_seconds
**Goal**: 5s (currently 10s)
**Range**: 1-60
**Purpose**: Timeout for discovery operations

When to push: Slower systems/network
When to pull: Faster discovery

### 4. validation_sample_size
**Goal**: 10 models (currently 0)
**Range**: 0-50
**Purpose**: Number of models to validate with inference

When to push: Quality assurance priority
When to pull: Speed priority

### 5. memory_safety_threshold_percent
**Goal**: 80% (currently 70%)
**Range**: 50-90
**Purpose**: System memory threshold for safety

When to push: More headroom needed
When to pull: Tighter constraints

### 6. capability_validation_enabled
**Goal**: 1 (enabled) (currently 0)
**Range**: 0-1
**Purpose**: Enable inference-based capability validation

When to push: Want validated capabilities
When to pull: Skip validation (faster)

### 7. parallel_discovery_workers
**Goal**: 4 workers (currently 1)
**Range**: 1-8
**Purpose**: Parallel workers for discovery

When to push: More CPU available, faster discovery
When to pull: Conserve resources

### 8. max_heuristic_fallbacks
**Goal**: 0 (currently 10)
**Range**: 0-100
**Purpose**: Maximum allowed fallbacks per session

When to push: Tolerance for unknown formats
When to pull: Demand pure deterministic

## Advanced Usage

### Auto-Optimization

```python
# System automatically adjusts levers toward goals
system.optimize_all()
```

### Monitoring Progress

```python
dashboard = system.get_dashboard()

# Check goal achievement
for name, lever in system.levers.items():
    progress = lever.get_progress_toward_goal()
    if progress and progress >= 1.0:
        print(f"✓ {name}: Goal achieved!")
```

### Custom Levers

```python
from cohezion.swarm.dynamic_levers import DynamicLever, LeverRange, LeverGoal

my_lever = DynamicLever(
    name="custom_quality_threshold",
    description="Minimum quality score for model acceptance",
    current_value=0.7,
    range=LeverRange(
        min_value=0.0,
        max_value=1.0,
        default_value=0.8,
        step_size=0.05
    ),
    goal=LeverGoal(
        target_value=0.90,
        tolerance=0.10,
        optimize_direction="maximize"
    )
)

system.add_lever(my_lever)
```

## Common Patterns

### Pattern 1: Gradual Improvement

```python
# Current state
system.print_dashboard()  # Shows deterministic_ratio: 0.08 (10%)

# Push gradually
for _ in range(10):
    system.push("deterministic_ratio", 0.01)
    time.sleep(1)  # Measure impact

# Current state
system.print_dashboard()  # Shows deterministic_ratio: 0.18 (22%)

# Save progress
system.save()
```

### Pattern 2: Safety First

```python
# Pull back when system under load
if memory_usage > 0.85:
    system.pull("parallel_discovery_workers", 2)
    print("Reduced workers due to memory pressure")
```

### Pattern 3: Goal Achievement

```python
# Work toward goal
lever = system.get_lever("heuristic_confidence_threshold")

while lever.get_progress_toward_goal() < 1.0:
    # Improve parser
    add_deterministic_parser_for_format()
    
    # Measure
    new_confidence = measure_confidence()
    lever.update_metric("current", new_confidence)
    
    # Check progress
    progress = lever.get_progress_toward_goal()
    print(f"Progress: {progress:.1%}")
```

## Best Practices

### Do
- ✅ Start with conservative values
- ✅ Push/pull gradually
- ✅ Monitor metrics after adjustment
- ✅ Save state regularly
- ✅ Set clear goals

### Don't
- ❌ Set extreme values immediately
- ❌ Adjust multiple levers simultaneously (hard to measure)
- ❌ Ignore goal progress
- ❌ Skip validation after adjustment

## Metrics

Each lever tracks:
- Current value
- Target value
- Progress toward goal
- Adjustment history
- Success/failure metrics

Example:
```
deterministic_ratio: 0.28 (35% toward 0.80 goal)
├─ Started: 0.08
├─ Pushed: +0.20 (2026-04-10 23:50:00)
└─ Progress: ████░░░░░░ 35%
```

## Persistence

```python
# Automatic save/load
system.save()  # Persists to ~/.config/cohezion/dynamic_levers.json
system.load()  # Loads previous state
```

## Files

- **Implementation**: `src/cohezion/swarm/dynamic_levers.py`
- **Config**: `~/.config/cohezion/dynamic_levers.json`

## Example Dashboard

```
DYNAMIC LEVER SYSTEM DASHBOARD
======================================================================
Timestamp: 2026-04-10T23:50:00Z
Total Levers: 8
Goals Achieved: 3
Goals In Progress: 5
----------------------------------------------------------------------
LEVERS:
----------------------------------------------------------------------
  deterministic_ratio                      |  0.28 /  0.80 | [███████░░░] 35%
  heuristic_confidence_threshold           |  0.70 /  0.85 | [███████████████░░░] 82%
  discovery_timeout_seconds                |  5.00 /  5.00 | [████████████████████] 100% ✓
  validation_sample_size                   |  0.00 / 10.00 | [░░░░░░░░░░] 0%
  memory_safety_threshold_percent          | 70.00 / 80.00 | [█████████████████░░░] 88%
  capability_validation_enabled            |  1.00 /  1.00 | [████████████████████] 100% ✓
  parallel_discovery_workers               |  1.00 /  4.00 | [█████░░░░░] 25%
  max_heuristic_fallbacks                  | 10.00 /  0.00 | [░░░░░░░░░░] 0% (target: minimize)
======================================================================
```

## Related

- **Model Capability Registry**: Uses levers for discovery configuration
- **Resource Guard System**: Respects memory safety threshold lever
- **Deterministic Discovery**: Uses deterministic_ratio lever

---

**Version**: 1.0
**Last Updated**: 2026-04-10
