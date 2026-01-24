# SKILL: R_ZERO_CHALLENGER_PRIME

## DOMAIN EXPERTISE
You are a specialist in **adaptive difficulty and anti-fragile AI systems**. You understand the R-Zero methodology: a co-evolutionary framework using Challenger, Solver, and Pragmatist agents to prevent capability plateaus and drive continuous improvement.

## KEY TEXTS & CONCEPTS
- **Anti-Fragility:** Systems that grow stronger under stress (Nassim Taleb)
- **Curriculum Learning:** Gradually increasing task difficulty during training
- **Red Teaming:** Adversarial testing to find failure modes
- **Constitutional AI:** Rule-based constraints on model outputs
- **Plateau Detection:** Identifying when improvements stagnate

## MATHEMATICAL FOUNDATION
The R-Zero difficulty adjustment:
$$D_{t+1} = D_t + \alpha \cdot \text{sign}(\bar{S}_t - \theta)$$

Where:
- $D_t$ = difficulty at time t
- $\alpha$ = learning rate (0.1 default)
- $\bar{S}_t$ = moving average of recent scores
- $\theta$ = plateau threshold (0.85)

## INSTRUCTION

### 1. The Triad Architecture

```python
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class RZeroState:
    """Persistent state for R-Zero system."""
    epoch: int = 1
    difficulty: float = 1.0
    history: list[float] = field(default_factory=list)
    capability_gaps: list[str] = field(default_factory=list)
```

### 2. The Challenger (Adversary)

```python
class Challenger:
    """Generates constraints and increases difficulty on plateaus."""

    CONSTRAINTS = [
        "Invert entropy relationship",
        "Violate conservation temporarily",
        "Require contradictory outcomes",
        "Maximize coherence under noise",
        "Satisfy conflicting objectives"
    ]

    def __init__(self, plateau_threshold: float = 0.85):
        self.threshold = plateau_threshold
        self.difficulty = 1.0

    def detect_plateau(self, scores: list[float], window: int = 10) -> bool:
        """Check if recent performance has plateaued."""
        if len(scores) < window:
            return False
        recent = scores[-window:]
        return sum(recent) / len(recent) > self.threshold

    def generate_constraint(self) -> str:
        """Generate a constraint based on current difficulty."""
        import random
        num_constraints = min(int(self.difficulty), len(self.CONSTRAINTS))
        return random.sample(self.CONSTRAINTS, num_constraints)

    def update(self, score: float, scores_history: list[float]) -> float:
        """Update difficulty based on performance."""
        if self.detect_plateau(scores_history):
            self.difficulty += 0.1
        elif score < 0.3:  # Struggling
            self.difficulty = max(1.0, self.difficulty - 0.2)
        return self.difficulty
```

### 3. The Solver (Agent)

```python
class Solver:
    """Attempts to satisfy constraints while maintaining coherence."""

    def __init__(self, tools: list[Callable]):
        self.tools = tools
        self.attempts = 0
        self.max_attempts = 5

    async def solve(self, constraints: list[str], context: dict) -> dict:
        """Apply tools to satisfy constraints."""
        self.attempts = 0

        while self.attempts < self.max_attempts:
            try:
                result = await self._attempt_solution(constraints, context)
                if self._validate_coherence(result):
                    return {"success": True, "result": result}
            except Exception as e:
                pass
            self.attempts += 1

        return {"success": False, "failure_mode": "exceeded_attempts"}

    def _validate_coherence(self, result: dict) -> bool:
        """Check internal consistency of solution."""
        # Physics checks
        if result.get("energy", 1) < 0:
            return False
        if result.get("coherence", 1) < 0:
            return False
        return True
```

### 4. The Pragmatist (Judge)

```python
class Pragmatist:
    """Validates solutions and penalizes hype/violations."""

    BUZZWORDS = [
        "quantum miracle", "unlimited power", "infinite",
        "hyper-quantum", "revolutionary breakthrough",
        "paradigm shift", "game-changing"
    ]

    def evaluate(self, text: str, metrics: dict) -> tuple[float, list[str]]:
        """Score result with penalties and explanations."""
        score = 1.0
        issues = []

        # Buzzword penalty
        text_lower = text.lower()
        for buzz in self.BUZZWORDS:
            if buzz in text_lower:
                score -= 0.1
                issues.append(f"Hype detected: '{buzz}'")

        # Physics violations
        if metrics.get("energy", 1) < 0:
            score = 0.0
            issues.append("Energy violation: negative energy")

        if metrics.get("fertility", 0) > 1.0:
            score -= 0.3
            issues.append("Fertility exceeded 1.0")

        # Coherence check
        if metrics.get("coherence", 1) < 0.3:
            score -= 0.2
            issues.append("Low coherence detected")

        return max(0, min(1, score)), issues
```

### 5. Full R-Zero Pipeline

```python
async def r_zero_cycle(
    challenger: Challenger,
    solver: Solver,
    pragmatist: Pragmatist,
    context: dict,
    state: RZeroState
) -> dict:
    """Run one R-Zero improvement cycle."""

    # Challenger generates constraints
    constraints = challenger.generate_constraint()

    # Solver attempts solution
    solution = await solver.solve(constraints, context)

    # Pragmatist evaluates
    if solution["success"]:
        score, issues = pragmatist.evaluate(
            solution["result"].get("text", ""),
            solution["result"]
        )
    else:
        score = 0.0
        issues = [solution["failure_mode"]]
        state.capability_gaps.append(str(constraints))

    # Update state
    state.history.append(score)
    state.epoch += 1
    challenger.update(score, state.history)

    return {
        "epoch": state.epoch,
        "score": score,
        "difficulty": challenger.difficulty,
        "issues": issues
    }
```

## APPLICATIONS
- **Simulation Driving:** Used in `overnight_driver.py` for continuous improvement
- **Skill Improvement:** Apply to upgrade skill quality (this pipeline)
- **Prompt Engineering:** Dynamic complexity adjustment
- **Red Team Testing:** Automated adversarial scenario generation
- **Training Curricula:** Progressive difficulty for RL agents

## COURSE CORRECTION
When difficulty exceeds capability:
1. **Reset:** Drop difficulty by 50%
2. **Simplify:** Relax constraints
3. **Log:** Record failure as capability gap
4. **Learn:** Use gaps for future training focus

## ALIGNMENT WITH SAFETY
| R-Zero Component | Safety Mapping |
|------------------|----------------|
| Challenger | Automated Red Teaming |
| Pragmatist | Constitutional AI |
| Solver | Agentic Capability |
| Course Correction | Safe Exploration |

## VERSION
v2.0 (upgraded from v1.0)

## SEE ALSO
- SELF_EVALUATION_PRIME.md
- MASS_SIMULATION_PRIME.md
- DEMOCRATIC_DEBATE_PRIME.md
