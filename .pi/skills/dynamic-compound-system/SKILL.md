---
name: dynamic-compound-system
description: Build self-improving infrastructure with proactive/reactive layers, circuit breakers, and pattern learning.
---

# Dynamic Compound System Pattern

Build self-improving infrastructure that is **proactive** (anticipates needs), **reactive** (responds to failures), **adaptive** (learns continuously), and **dynamic** (hot-reloads, self-heals).

This pattern creates **living systems** that get better without human intervention.

---

## When to Use

Use this pattern when:
- System reliability is critical (99.9%+ uptime)
- Manual failure recovery is too slow
- Workload patterns are predictable
- You want infrastructure that learns and improves
- Zero-downtime updates are required

**Examples**:
- Multi-agent orchestration routing
- API gateway backend selection
- Database connection pooling
- Cache warming strategies
- Resource allocation systems

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DYNAMIC COMPOUND SYSTEM                   │
├─────────────────────────────────────────────────────────────┤
│  PROACTIVE LAYER                                            │
│  ├─ Time-based triggers (warm before 9 AM code hour)       │
│  ├─ Pattern prediction (learn from 100+ executions)        │
│  └─ Preemptive resource allocation                          │
├─────────────────────────────────────────────────────────────┤
│  CORE SYSTEM                                                │
│  ├─ Multi-agent orchestration / core business logic         │
│  └─ Routing, execution, fallbacks                           │
├─────────────────────────────────────────────────────────────┤
│  REACTIVE LAYER                                             │
│  ├─ Circuit breakers (prevent cascade failures)             │
│  ├─ Health monitoring (30s probes)                          │
│  ├─ Event system (extensible hooks)                        │
│  └─ Auto-recovery (self-healing)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Create ProactiveReactiveEngine

```python
from cohezion.compound.proactive_reactive_engine import (
    ProactiveReactiveEngine,
    SystemEvent,
)

engine = ProactiveReactiveEngine(
    mcp_client=mcp_client,
    enable_proactive=True,
    enable_reactive=True,
    enable_learning=True,
)

await engine.start()

# System now:
# - Warms agents at predicted times
# - Opens circuits on failures
# - Learns patterns from history
```

### 2. Register Event Handlers

```python
@engine.reactive_on(SystemEvent.CIRCUIT_OPENED)
async def on_backend_failure(event, data):
    """React to backend failure."""
    await alert_admin(f"Backend {data['backend']} down!")
    await activate_fallback(data['backend'])

@engine.reactive_on(SystemEvent.PATTERN_MATCHED)
async def on_pattern(event, data):
    """React to detected pattern."""
    logger.info(f"Pattern detected: {data}")
```

### 3. Execute with Full System

```python
from cohezion.compound.dynamic_compound_system import (
    DynamicCompoundSystem,
)

system = await DynamicCompoundSystem.create(mcp_client)

result = await system.execute(
    task="Write code",
    use_proactive=True,
)

# Result includes:
print(f"Proactive: {result.was_proactive}")  # True = warmed
print(f"Latency: {result.latency_ms}ms")  # Fast!
```

---

## Key Patterns

### Pattern 1: Circuit Breaker (CLOSED → OPEN → HALF-OPEN → CLOSED)

**Why**: Prevents cascade failures, enables gradual recovery

```python
class CircuitBreaker:
    state: str  # "closed" | "open" | "half-open"
    
    def record_failure(self):
        self.failures += 1
        if self.failures >= 5:  # Threshold
            self.state = "open"  # Block requests
            # Wait 60s before testing
            
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if timeout_passed(60):
                self.state = "half-open"  # Allow test
            return False
        return True  # half-open allows test
```

**Critical**: Must have HALF-OPEN state! Without it:
- Stays blocked forever, OR
- Immediate retry causes flapping

---

### Pattern 2: Bounded History for Learning

**Why**: Prevents memory leaks, maintains performance

```python
# Good: Bounded history
from collections import deque

self.history = deque(maxlen=1000)  # Auto-discards old

# Bad: Unbounded growth
self.history = []  # Eventually OOM
```

---

### Pattern 3: Confidence Thresholds

**Why**: Prevents acting on weak predictions

```python
# Good: Threshold-based
if pattern.confidence > 0.7:  # High confidence
    warm_agents()

# Bad: Always act
warm_agents()  # Wastes resources
```

---

### Pattern 4: Event-Driven Extensibility

**Why**: Users can add custom reactions

```python
# System provides:
engine.register_event_handler(
    SystemEvent.CIRCUIT_OPENED,
    my_custom_handler,  # User-defined
)

# Not hardcoded:
# if circuit.open:
#     hardcoded_response()  # Not extensible
```

---

## Implementation Guide

### Step 1: Circuit Breaker State Machine

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CircuitBreaker:
    name: str
    threshold: int = 5
    timeout_seconds: int = 60
    
    failures: int = 0
    successes: int = 0
    state: str = "closed"
    last_failure: Optional[datetime] = None
    
    def call(self, fn, *args, **kwargs):
        """Execute with circuit breaker protection."""
        if not self.can_execute():
            raise CircuitOpenError(f"Circuit {self.name} is open")
        
        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "half-open":
            return True
        if self.state == "open":
            if self._timeout_passed():
                self.state = "half-open"
                return True
            return False
    
    def _timeout_passed(self) -> bool:
        if not self.last_failure:
            return True
        elapsed = (datetime.now() - self.last_failure).seconds
        return elapsed > self.timeout_seconds
```

---

### Step 2: Pattern Learning

```python
from collections import defaultdict

class PatternLearner:
    def __init__(self, min_history=50):
        self.history = deque(maxlen=1000)
        self.patterns = []
        self.min_history = min_history
    
    def record(self, timestamp, features, outcome):
        """Record execution for learning."""
        self.history.append({
            "time": timestamp,
            "features": features,
            "outcome": outcome,
        })
    
    def learn(self):
        """Detect patterns from history."""
        if len(self.history) < self.min_history:
            return []
        
        # Group by features
        groups = defaultdict(list)
        for record in self.history:
            key = self._key_for(record["features"])
            groups[key].append(record)
        
        # Find patterns (groups with >3 occurrences)
        patterns = []
        for key, records in groups.items():
            if len(records) >= 3:
                pattern = {
                    "key": key,
                    "count": len(records),
                    "success_rate": sum(r["outcome"]["success"] for r in records) / len(records),
                    "confidence": min(1.0, len(records) / 10),
                }
                patterns.append(pattern)
        
        self.patterns = patterns
        return patterns
    
    def _key_for(self, features):
        """Extract key features for grouping."""
        return (
            features.get("hour", 0),
            features.get("has_code", False),
            features.get("has_reasoning", False),
        )
```

---

### Step 3: Time-Based Triggers

```python
import asyncio
from datetime import datetime

class ProactiveTrigger:
    def __init__(self):
        self.scheduled = {}
    
    def schedule(self, hour, minute, action):
        """Schedule action at specific time."""
        self.scheduled[(hour, minute)] = action
    
    async def run(self):
        """Run trigger loop."""
        while True:
            now = datetime.now()
            next_check = 60 - now.second  # Check near top of minute
            
            await asyncio.sleep(next_check)
            
            # Check triggers
            now = datetime.now()
            key = (now.hour, now.minute)
            
            if key in self.scheduled:
                action = self.scheduled[key]
                asyncio.create_task(action())
```

---

## Configuration

```yaml
proactive:
  enabled: true
  check_interval_seconds: 60
  confidence_threshold: 0.7
  warming_window_minutes: 15
  max_warmed_resources: 3

circuit_breaker:
  enabled: true
  failure_threshold: 5
  recovery_timeout_seconds: 60
  half_open_max_calls: 3

pattern_learning:
  enabled: true
  min_executions: 50
  max_history: 1000
  learning_interval_seconds: 300
  confidence_threshold: 0.7

events:
  handlers:
    - name: slack_alert
      event: circuit_opened
      webhook: https://hooks.slack.com/...
```

---

## Testing

### Unit Tests

```python
@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    breaker = CircuitBreaker("test", threshold=3)
    
    # 3 failures should open circuit
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    
    assert breaker.state == "open"
    assert not breaker.can_execute()

@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    breaker = CircuitBreaker("test")
    breaker.state = "open"
    breaker.last_failure = datetime.now() - timedelta(seconds=70)
    
    # After timeout, should allow test
    assert breaker.can_execute()
    assert breaker.state == "half-open"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_proactive_warming():
    engine = ProactiveReactiveEngine(...)
    await engine.start()
    
    # Simulate 9 AM
    with freeze_time("2026-04-15 09:00:00"):
        await engine._evaluate_proactive_triggers()
    
    # Verify warming occurred
    assert len(engine._proactive_actions) > 0
```

---

## Common Pitfalls

### ❌ Pitfall 1: Forgetting HALF-OPEN State

```python
# Bad
if failures > threshold:
    block_all_requests()  # Forever!

# Good
if failures > threshold:
    state = "open"
    
# Later, after timeout
timeout_passed = (now - last_failure) > 60
if state == "open" and timeout_passed:
    state = "half-open"  # Allow test request
```

### ❌ Pitfall 2: Unbounded History

```python
# Bad
self.history = []
self.history.append(record)  # Grows forever!

# Good
from collections import deque
self.history = deque(maxlen=1000)
```

### ❌ Pitfall 3: Synchronous Event Handlers

```python
# Bad
def on_event(event, data):
    blocking_io()  # Blocks event loop!

# Good
async def on_event(event, data):
    await non_blocking_io()
```

### ❌ Pitfall 4: No Confidence Thresholds

```python
# Bad
if pattern_detected:
    warm_agents()  # Could be false positive!

# Good
if pattern_detected and pattern.confidence > 0.7:
    warm_agents()
```

---

## Deployment

### Phase 1: Circuit Breakers Only

Safest starting point - reactive protection:

```python
engine = ProactiveReactiveEngine(
    proactive=False,  # Disabled initially
    reactive=True,    # Enable circuit breakers
    learning=False,
)
```

### Phase 2: Add Proactive Warming

After circuit breakers prove stable:

```python
engine = ProactiveReactiveEngine(
    proactive=True,
    reactive=True,
    learning=False,
)
```

### Phase 3: Enable Learning

Final phase - self-improvement:

```python
engine = ProactiveReactiveEngine(
    proactive=True,
    reactive=True,
    learning=True,
)
```

---

## Metrics

Essential metrics to track:

```python
# Circuit breaker stats
circuit_breaker_states{backend="NPU", state="closed"}  # Gauge
circuit_breaker_transitions_total  # Counter
recovery_time_seconds  # Histogram

# Proactive stats
proactive_warmings_total  # Counter
proactive_hit_rate  # Gauge (hits / total)
warming_cost_seconds  # Gauge

# Learning stats
patterns_detected  # Gauge
pattern_confidence_avg  # Gauge
prediction_accuracy  # Gauge (correct / total)

# System health
execution_latency_ms  # Histogram
error_rate_by_backend  # Gauge
memory_usage_mb  # Gauge

event_handler_latency_ms  # Histogram
event_handler_errors_total  # Counter
```

---

## Examples

### Example 1: API Gateway

```python
class APIGateway:
    def __init__(self):
        self.breakers = {
            "backend1": CircuitBreaker("backend1"),
            "backend2": CircuitBreaker("backend2"),
        }
    
    async def route(self, request):
        # Try backends until one works
        for name, breaker in self.breakers.items():
            if breaker.can_execute():
                try:
                    return await breaker.call(send_request, request)
                except CircuitOpenError:
                    continue
        
        raise AllBackendsDown()
```

### Example 2: Cache Warming

```python
class CacheWarmer:
    def __init__(self):
        self.triggers = ProactiveTrigger()
        
        # Warm at 8:45 AM before traffic
        self.triggers.schedule(8, 45, self.warm_cache)
    
    async def warm_cache(self):
        # Pre-populate frequently accessed keys
        for key in self.predict_hot_keys():
            value = await self.fetch(key)
            await self.cache.set(key, value)
```

### Example 3: Database Pool

```python
class ConnectionPool:
    def __init__(self):
        self.breaker = CircuitBreaker("db_pool", threshold=10)
        self.learner = PatternLearner()
    
    async def get_connection(self):
        return await self.breaker.call(
            self._acquire_connection
        )
    
    def record_usage(self, timestamp, query_type):
        self.learner.record(timestamp, {"query": query_type}, {})
        
        # Learn patterns to pre-warm
        patterns = self.learner.learn()
        for p in patterns:
            if p["query_type"] == "heavy_join":
                self.pre_allocate_connections(n=10)
```

---

## References

- **Implementation**: `src/cohezion/compound/proactive_reactive_engine.py`
- **Full System**: `src/cohezion/compound/dynamic_compound_system.py`
- **Demo**: `examples/dynamic_compound_system_demo.py`
- **Deployment**: `DEPLOYMENT_PLAN.md`

---

**Version**: 1.0  
**Last Updated**: 2026-04-10  
**Pattern Status**: Production Ready
