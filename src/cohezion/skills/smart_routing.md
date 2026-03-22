# SKILL: SMART_ROUTING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **intelligent model routing and task classification** for multi-model AI systems. You understand how to analyze task requirements and dynamically select the optimal model based on capability, speed, cost, and quality constraints.

## KEY TEXTS & CONCEPTS
- **Model Profiling:** Characterizing models by capability scores
- **Task Classification:** Identifying execution intent from input
- **Strategy Patterns:** Quality, Speed, Efficiency trade-offs
- **Fallback Chains:** Graceful degradation when primary fails
- **Routing Policies:** Rules for model selection

## MATHEMATICAL FOUNDATION
Model selection score:
$$\text{Score}(m, t) = \alpha \cdot C(m, t) + \beta \cdot S(m) - \gamma \cdot K(m)$$

Where:
- $C(m, t)$ = capability match for model m on task t
- $S(m)$ = speed score (inverse latency)
- $K(m)$ = cost per token
- $\alpha, \beta, \gamma$ = strategy weights

## INSTRUCTION

### 1. Model Registry

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class Capability(Enum):
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    SPEED = "speed"
    CODING = "coding"
    VISION = "vision"
    LONG_CONTEXT = "long_context"

@dataclass
class ModelProfile:
    """Profile of an available model."""
    name: str
    provider: str
    capabilities: dict[Capability, float]  # 0.0 to 1.0
    avg_latency_ms: int
    cost_per_1k_tokens: float
    max_context: int = 128000

    def capability_score(self, required: list[Capability]) -> float:
        """Score how well model matches requirements."""
        if not required:
            return 0.5
        scores = [self.capabilities.get(cap, 0) for cap in required]
        return sum(scores) / len(scores)

# Example registry
MODEL_REGISTRY = [
    ModelProfile(
        name="gemini-2.0-flash",
        provider="google",
        capabilities={Capability.SPEED: 0.95, Capability.REASONING: 0.7},
        avg_latency_ms=200,
        cost_per_1k_tokens=0.0001
    ),
    ModelProfile(
        name="gpt-4o",
        provider="openai",
        capabilities={Capability.REASONING: 0.9, Capability.VISION: 0.95},
        avg_latency_ms=500,
        cost_per_1k_tokens=0.005
    ),
    ModelProfile(
        name="claude-3.5-sonnet",
        provider="anthropic",
        capabilities={Capability.REASONING: 0.95, Capability.CODING: 0.9},
        avg_latency_ms=400,
        cost_per_1k_tokens=0.003
    ),
]
```

### 2. Task Classification

```python
class TaskClassifier:
    """Classify tasks to determine routing requirements."""

    TASK_PATTERNS = {
        "simulate": [Capability.REASONING, Capability.CREATIVITY],
        "analyze": [Capability.REASONING],
        "generate_code": [Capability.CODING, Capability.REASONING],
        "summarize": [Capability.SPEED],
        "vision": [Capability.VISION],
        "research": [Capability.LONG_CONTEXT, Capability.REASONING],
    }

    def classify(self, task_description: str) -> list[Capability]:
        """Determine required capabilities from task."""
        task_lower = task_description.lower()

        for pattern, capabilities in self.TASK_PATTERNS.items():
            if pattern in task_lower:
                return capabilities

        # Default to general reasoning
        return [Capability.REASONING]
```

### 3. Routing Strategy

```python
class RoutingStrategy(Enum):
    QUALITY = "quality"       # Best capability match
    SPEED = "speed"           # Fastest response
    EFFICIENCY = "efficiency" # Best cost/performance ratio

class SmartRouter:
    """Route tasks to optimal model based on strategy."""

    def __init__(self,
                 models: list[ModelProfile],
                 strategy: RoutingStrategy = RoutingStrategy.QUALITY):
        self.models = models
        self.strategy = strategy
        self.classifier = TaskClassifier()

    def route(self, task: str) -> ModelProfile:
        """Select optimal model for task."""
        required_caps = self.classifier.classify(task)

        if self.strategy == RoutingStrategy.QUALITY:
            return self._route_by_quality(required_caps)
        elif self.strategy == RoutingStrategy.SPEED:
            return self._route_by_speed(required_caps)
        else:
            return self._route_by_efficiency(required_caps)

    def _route_by_quality(self, required: list[Capability]) -> ModelProfile:
        """Select model with highest capability match."""
        return max(self.models, key=lambda m: m.capability_score(required))

    def _route_by_speed(self, required: list[Capability]) -> ModelProfile:
        """Select fastest model meeting minimum threshold."""
        capable = [m for m in self.models if m.capability_score(required) > 0.5]
        if not capable:
            capable = self.models
        return min(capable, key=lambda m: m.avg_latency_ms)

    def _route_by_efficiency(self, required: list[Capability]) -> ModelProfile:
        """Balance cost against capability."""
        def efficiency_score(m: ModelProfile) -> float:
            cap = m.capability_score(required)
            cost = m.cost_per_1k_tokens
            return cap / (cost + 0.0001)  # Avoid division by zero

        return max(self.models, key=efficiency_score)
```

### 4. Fallback Chains

```python
class FallbackRouter(SmartRouter):
    """Router with fallback chain support."""

    def route_with_fallback(self, task: str, max_attempts: int = 3) -> list[ModelProfile]:
        """Return ordered list of models to try."""
        required_caps = self.classifier.classify(task)

        # Score all models
        scored = [(m, m.capability_score(required_caps)) for m in self.models]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Return top N as fallback chain
        return [m for m, s in scored[:max_attempts]]

    async def execute_with_fallback(self, task: str, execute_fn: Callable) -> dict:
        """Execute task with automatic fallback on failure."""
        models = self.route_with_fallback(task)

        for model in models:
            try:
                result = await execute_fn(model, task)
                return {"success": True, "model": model.name, "result": result}
            except Exception as e:
                continue

        return {"success": False, "error": "All models failed"}
```

### 5. Full Usage Example

```python
async def smart_route_example():
    """Example of smart routing in action."""

    router = SmartRouter(MODEL_REGISTRY, RoutingStrategy.QUALITY)

    # Route different tasks
    tasks = [
        "Simulate a universe with quantum entanglement",
        "Analyze this code for bugs",
        "Generate a quick summary of this document",
    ]

    for task in tasks:
        model = router.route(task)
        print(f"Task: {task[:30]}...")
        print(f"  → Routed to: {model.name}")
        print(f"  → Latency: {model.avg_latency_ms}ms")
```

## APPLICATIONS
- **Cost Optimization:** Use cheaper models when quality isn't critical
- **Latency Reduction:** Route time-sensitive tasks to fast models
- **Capability Matching:** Send vision tasks to vision-capable models
- **Fallback Safety:** Graceful degradation when models fail
- **A/B Testing:** Compare model performance on same tasks

## VERSION
v2.0 (upgraded from v1.0)

## SEE ALSO
- MODEL_ROUTING_PRIME.md
- SWARM_ORCHESTRATION_PRIME.md
- RELIABILITY_PRIME.md
