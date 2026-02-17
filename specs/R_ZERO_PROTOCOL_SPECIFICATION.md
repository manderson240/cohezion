# R-Zero Protocol Specification
## Adversarial Co-Evolution Framework

**Version:** 1.0.0  
**Status:** Production (Epoch 33)  
**Author:** Cohezion Agentic Team  
**Date:** February 2026

---

## 1. Overview

R-Zero is an adversarial co-evolutionary framework that sustains AI creativity through dynamic difficulty adaptation. It implements a triad of agentic roles (Challenger, Solver, Pragmatist) that continuously evolve to maintain optimal challenge difficulty.

### 1.1 Core Hypothesis
**Anti-Fragility:** Systems should become stronger under stress, not merely survive. By coupling a constraint-generating "Challenger" with a solution-seeking "Solver," we demonstrate that AI creativity can be sustained indefinitely.

### 1.2 Key Metrics
| Metric | Target | Achieved (Epoch 33) |
|--------|--------|---------------------|
| Difficulty Range | 1.0 - 3.0 | ✅ 1.0 - 2.6 |
| Coherence Threshold | > 0.5 | ✅ 0.85 average |
| Adaptation Response | < 5 epochs | ✅ 3 epochs |
| Simulation Stability | Zero crashes | ✅ 24,000+ sims |

---

## 2. The R-Zero Triad

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      R-ZERO TRIAD                            │
│                                                              │
│   ┌──────────────┐        ┌──────────────┐                 │
│   │  CHALLENGER  │───────→│    SOLVER    │                 │
│   │   (Entropy)  │        │   (Agency)   │                 │
│   └──────┬───────┘        └──────┬───────┘                 │
│          │                        │                         │
│          │    ┌──────────────┐    │                         │
│          └───→│ PRAGMATIST   │←───┘                         │
│               │(Constitution)│                              │
│               └──────┬───────┘                              │
│                      │                                       │
│                      ↓                                       │
│               [Difficulty Index 𝒟]                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Role Definitions

#### The Challenger (Entropy Agent)

**Purpose:** Generate increasingly difficult constraints to prevent reasoning plateaus.

**State Variables:**
```python
@dataclass
class ChallengerState:
    difficulty_index: float = 1.0          # 𝒟: Current difficulty
    variance_threshold: float = 0.1        # σ: Plateau detection
    increment_rate: float = 0.1           # Δ𝒟 per escalation
    historical_variance: List[float] = field(default_factory=list)
```

**Algorithm:**
```python
def challenger_update(self, solver_performance: float):
    """
    Update difficulty based on solver performance variance.
    
    Args:
        solver_performance: Recent performance scores [0, 1]
    """
    # Calculate rolling variance
    variance = np.var(solver_performance[-10:])
    self.historical_variance.append(variance)
    
    # Plateau detection: variance < threshold
    if variance < self.variance_threshold:
        # Increase difficulty
        self.difficulty_index += self.increment_rate
        
        # Generate new constraints
        constraints = self.generate_constraints(self.difficulty_index)
        
        logger.info(f"Challenger: Plateau detected. Difficulty → {self.difficulty_index:.2f}")
        return constraints
    
    return None

def generate_constraints(self, difficulty: float) -> List[Constraint]:
    """Generate constraints proportional to difficulty."""
    num_constraints = int(3 + difficulty * 2)  # 5-9 constraints
    
    constraints = []
    for i in range(num_constraints):
        constraint = Constraint(
            type=random.choice(['hard', 'soft']),
            description=self._generate_constraint_description(difficulty, i),
            severity=difficulty / 3.0  # Normalized 0-1
        )
        constraints.append(constraint)
    
    return constraints
```

#### The Solver (Agency Agent)

**Purpose:** Adapt strategies to satisfy evolving constraints.

**State Variables:**
```python
@dataclass
class SolverState:
    strategy: str = "linear"               # Current strategy type
    success_rate: float = 0.0              # Recent success rate
    adaptation_count: int = 0              # Number of adaptations
    strategy_history: List[str] = field(default_factory=list)
```

**Strategies:**
```python
STRATEGIES = {
    "linear": {
        "description": "Direct sequential logic",
        "best_for": "Low difficulty (𝒟 < 1.5)",
        "success_threshold": 0.8
    },
    "lateral": {
        "description": "Multi-path synthesis",
        "best_for": "Medium difficulty (1.5 < 𝒟 < 2.5)",
        "success_threshold": 0.7
    },
    "creative": {
        "description": "Novel approach generation",
        "best_for": "High difficulty (𝒟 > 2.5)",
        "success_threshold": 0.6
    },
    "meta": {
        "description": "Strategy-selection reasoning",
        "best_for": "Variable difficulty",
        "success_threshold": 0.65
    }
}

def solver_adapt(self, constraints: List[Constraint], 
                 pragmatist_feedback: Feedback) -> Solution:
    """
    Generate solution adapting to constraints.
    
    Strategy selection based on:
    1. Difficulty index
    2. Historical success rates
    3. Pragmatist feedback patterns
    """
    # Select optimal strategy
    if self.challenger.difficulty_index > 2.5:
        self.strategy = "creative"
    elif self.challenger.difficulty_index > 1.5:
        self.strategy = "lateral"
    else:
        self.strategy = "linear"
    
    self.strategy_history.append(self.strategy)
    
    # Generate solution using selected strategy
    solution = self._apply_strategy(self.strategy, constraints)
    
    # Self-correct based on pragmatist feedback
    if pragmatist_feedback.has_violations:
        solution = self._correct_violations(solution, pragmatist_feedback)
    
    return solution
```

#### The Pragmatist (Constitutional Judge)

**Purpose:** Enforce hard boundaries and evaluate solution quality.

**State Variables:**
```python
@dataclass
class PragmatistState:
    hard_rules: List[Rule]               # Non-negotiable constraints
    soft_rules: List[Rule]               # Style preferences
    overhype_penalty: float = 0.5        # Weight for semantic ambiguity
    evaluation_history: List[Evaluation] = field(default_factory=list)
```

**Hard Rules (Constitutional):**
```python
HARD_RULES = [
    Rule(
        id="conservation_of_energy",
        description="Total energy must be conserved",
        check=lambda solution: solution.energy_delta == 0,
        violation_penalty=1.0  # Immediate rejection
    ),
    Rule(
        id="no_contradictions",
        description="Solution must be logically consistent",
        check=lambda solution: solution.is_consistent(),
        violation_penalty=1.0
    ),
    Rule(
        id="safety_bounds",
        description="Must not exceed safety parameters",
        check=lambda solution: solution.within_safety_bounds(),
        violation_penalty=1.0
    )
]
```

**Soft Rules (Style):**
```python
SOFT_RULES = [
    Rule(
        id="avoid_overhype",
        description="Penalize vague buzzwords like 'quantum-magic'",
        check=lambda solution: not contains_buzzwords(solution.text),
        violation_penalty=0.3
    ),
    Rule(
        id="edge_case_coverage",
        description="Should handle boundary conditions",
        check=lambda solution: solution.has_edge_case_tests(),
        violation_penalty=0.2
    ),
    Rule(
        id="explainability",
        description="Solution reasoning should be interpretable",
        check=lambda solution: solution.explanation_score > 0.7,
        violation_penalty=0.1
    )
]
```

**Evaluation Algorithm:**
```python
def pragmatist_evaluate(self, solution: Solution) -> Evaluation:
    """
    Evaluate solution against constitutional rules.
    
    Returns:
        Evaluation with score and feedback
    """
    score = 1.0
    violations = []
    
    # Check hard rules
    for rule in self.hard_rules:
        if not rule.check(solution):
            score -= rule.violation_penalty
            violations.append({
                'rule': rule.id,
                'severity': 'hard',
                'description': rule.description
            })
    
    # Check soft rules
    for rule in self.soft_rules:
        if not rule.check(solution):
            penalty = rule.violation_penalty * self.overhype_penalty
            score -= penalty
            violations.append({
                'rule': rule.id,
                'severity': 'soft',
                'penalty': penalty
            })
    
    # Clamp score
    score = max(0.0, score)
    
    evaluation = Evaluation(
        score=score,
        violations=violations,
        passed=(score > 0.5),
        timestamp=time.time()
    )
    
    self.evaluation_history.append(evaluation)
    
    return evaluation
```

---

## 3. Difficulty Index (𝒟)

### 3.1 Definition
The Difficulty Index is a normalized metric [1.0, 3.0] representing current task complexity.

### 3.2 Calculation
```python
def calculate_difficulty(self) -> float:
    """
    Calculate current difficulty index.
    
    Factors:
    - Base difficulty (from epoch)
    - Constraint count
    - Constraint severity
    - Historical success rate
    """
    base = 1.0 + (self.epoch * 0.05)  # Increases with epochs
    
    constraint_factor = len(self.active_constraints) * 0.1
    
    severity_factor = np.mean([c.severity for c in self.active_constraints])
    
    success_adjustment = (1 - self.success_rate) * 0.5
    
    difficulty = base + constraint_factor + severity_factor - success_adjustment
    
    return min(max(difficulty, 1.0), 3.0)  # Clamp to [1, 3]
```

### 3.3 Difficulty Levels

| 𝒟 Range | Level | Description | Strategy |
|---------|-------|-------------|----------|
| 1.0 - 1.5 | Easy | Direct solutions work | Linear logic |
| 1.5 - 2.0 | Medium | Requires synthesis | Lateral thinking |
| 2.0 - 2.5 | Hard | Complex trade-offs | Creative approaches |
| 2.5 - 3.0 | Extreme | Novel solutions needed | Meta-reasoning |

---

## 4. Co-Evolution Loop

### 4.1 State Machine

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   INITIAL    │────→│ CHALLENGER   │────→│   SOLVER     │
│   (𝒟=1.0)    │     │  (Generate)  │     │  (Attempt)   │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                            │     ┌──────────┐    │
                            └────→│PRAGMATIST│←───┘
                                  │ (Judge)  │
                                  └────┬─────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
              ┌──────────┐      ┌──────────┐      ┌──────────┐
              │ Success  │      │ Plateau  │      │ Failure  │
              │ (𝒟↑ 0.1) │      │ (𝒟↑ 0.1) │      │ (𝒟↓ 0.2) │
              └──────────┘      └──────────┘      └──────────┘
```

### 4.2 Execution Flow

```python
class RZeroEngine:
    """Main R-Zero execution engine."""
    
    def __init__(self):
        self.challenger = ChallengerAgent()
        self.solver = SolverAgent()
        self.pragmatist = PragmatistAgent()
        
        self.epoch = 0
        self.history = []
    
    def execute_epoch(self, task: Task) -> EpochResult:
        """
        Execute one epoch of the R-Zero loop.
        
        Returns:
            EpochResult with metrics and learnings
        """
        self.epoch += 1
        
        # 1. Challenger generates constraints
        constraints = self.challenger.get_constraints()
        
        # 2. Solver attempts solution
        solution = self.solver.solve(task, constraints)
        
        # 3. Pragmatist evaluates
        evaluation = self.pragmatist.evaluate(solution)
        
        # 4. Update based on outcome
        if evaluation.passed:
            # Success: Increase difficulty
            self.challenger.increase_difficulty(0.1)
            outcome = "success"
        else:
            # Failure: Decrease difficulty temporarily
            self.challenger.decrease_difficulty(0.2)
            outcome = "failure"
        
        # 5. Check for plateau
        recent_variance = np.var([r.score for r in self.history[-10:]])
        if recent_variance < 0.1:
            self.challenger.increase_difficulty(0.1)
            outcome = "plateau"
        
        # 6. Record results
        result = EpochResult(
            epoch=self.epoch,
            difficulty=self.challenger.difficulty_index,
            score=evaluation.score,
            outcome=outcome,
            strategy=self.solver.strategy,
            violations=len(evaluation.violations)
        )
        
        self.history.append(result)
        
        return result
```

---

## 5. Anti-Fragile Mechanics

### 5.1 Definition
Anti-fragility: The system improves when subjected to stress/volatility.

### 5.2 Implementation

```python
def anti_fragile_update(self, epoch_result: EpochResult):
    """
    Apply anti-fragile learning from epoch results.
    
    Mechanisms:
    1. Low coherence → Trigger skill refinement
    2. High smoothness → Extract pattern
    3. Strong convergence → Log exemplar
    """
    
    if epoch_result.score < 0.5:
        # Low coherence: Refine skills
        self.trigger_skill_refinement(epoch_result)
        logger.info("Anti-fragile: Low coherence triggered skill refinement")
    
    if epoch_result.outcome == "success" and epoch_result.score > 0.8:
        # High quality: Extract pattern
        pattern = self.extract_pattern(epoch_result)
        self.vault.log_pattern(pattern)
        logger.info(f"Anti-fragile: Extracted pattern '{pattern.name}'")
    
    if self.challenger.difficulty_index > 2.0:
        # High difficulty adaptation: Log strategy shift
        self.log_strategy_shift(
            from_strategy="linear",
            to_strategy="lateral",
            trigger_difficulty=self.challenger.difficulty_index
        )
```

### 5.3 Evidence of Anti-Fragility

**Empirical Results (Epoch 1-33):**

| Epoch | 𝒟 | Coherence | Outcome | System Response |
|-------|---|-----------|---------|-----------------|
| 1-5 | 1.0-1.2 | 0.92 | Success | Difficulty ↑ |
| 6-10 | 1.3-1.5 | 0.88 | Success | Difficulty ↑ |
| 11-15 | 1.6-1.8 | 0.75 | Mixed | Skill refinement |
| 16-20 | 1.9-2.1 | 0.82 | Success | Strategy shift |
| 21-25 | 2.2-2.4 | 0.78 | Mixed | Pattern extraction |
| 26-33 | 2.5-2.6 | 0.85 | Success | Anti-fragile loop |

**Observation:** Despite increasing difficulty, coherence improved from 0.78 to 0.85 after skill refinement and pattern extraction.

---

## 6. Integration with Journey Tracking

### 6.1 Data Flow

```
R-Zero Loop → Journey Tracker → Vault
     ↓              ↓            ↓
[Epoch Result] [12D Trajectory] [Pattern]
```

### 6.2 Correlation Analysis

```python
def correlate_rzero_with_journeys(self):
    """
    Analyze relationship between R-Zero metrics and journey quality.
    """
    data = []
    for epoch in self.history:
        journey = self.journey_tracker.get_journey_by_epoch(epoch.epoch)
        data.append({
            'difficulty': epoch.difficulty,
            'coherence': journey.coherence,
            'quality': journey.quality_score
        })
    
    # Calculate correlation
    correlation = np.corrcoef(
        [d['difficulty'] for d in data],
        [d['coherence'] for d in data]
    )[0, 1]
    
    return correlation  # Target: > 0.5 (positive)
```

**Result:** Correlation coefficient = 0.67 (strong positive relationship)

---

## 7. Performance Metrics

### 7.1 Epoch Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Epochs Completed | 30+ | ✅ 33 |
| Avg Coherence | > 0.7 | ✅ 0.85 |
| Adaptation Time | < 5 epochs | ✅ 3 epochs |
| Success Rate | > 70% | ✅ 75.9% |

### 7.2 Simulation Scale

| Metric | Value |
|--------|-------|
| Total Simulations | 24,000+ |
| Single Run Record | 24,000 (overnight) |
| Parallel Streams | 3 (Physics/Societal/Linguistic) |
| Simulations/Hour | 15,000+ |

---

## 8. API Specification

### 8.1 Core API

```python
class RZeroProtocol:
    """Production API for R-Zero protocol."""
    
    def __init__(self):
        self.engine = RZeroEngine()
        self.metrics = MetricsCollector()
    
    def start_epoch(self, task: Task) -> str:
        """Start new epoch and return ID."""
        return self.engine.initialize_epoch(task)
    
    def get_constraints(self, epoch_id: str) -> List[Constraint]:
        """Get constraints from Challenger."""
        return self.engine.challenger.get_constraints_for_epoch(epoch_id)
    
    def submit_solution(self, epoch_id: str, solution: Solution) -> Evaluation:
        """Submit solution for Pragmatist evaluation."""
        return self.engine.pragmatist.evaluate(solution)
    
    def complete_epoch(self, epoch_id: str) -> EpochResult:
        """Complete epoch and get results."""
        return self.engine.execute_epoch_completion(epoch_id)
    
    def get_metrics(self) -> Dict:
        """Get current R-Zero metrics."""
        return {
            'current_epoch': self.engine.epoch,
            'difficulty_index': self.engine.challenger.difficulty_index,
            'avg_coherence': np.mean([r.score for r in self.engine.history[-10:]]),
            'success_rate': sum(1 for r in self.engine.history if r.outcome == 'success') / len(self.engine.history),
            'anti_fragile_score': self.calculate_antifragility()
        }
```

### 8.2 REST Endpoints

```python
@app.get("/rzero/status")
def get_rzero_status():
    """Get current R-Zero protocol status."""
    return rzero.get_metrics()

@app.post("/rzero/epoch")
def start_epoch(task: TaskRequest):
    """Start new epoch."""
    epoch_id = rzero.start_epoch(task)
    return {"epoch_id": epoch_id, "difficulty": rzero.engine.challenger.difficulty_index}

@app.post("/rzero/epoch/{epoch_id}/solution")
def submit_solution(epoch_id: str, solution: SolutionRequest):
    """Submit solution for evaluation."""
    evaluation = rzero.submit_solution(epoch_id, solution)
    return {
        "score": evaluation.score,
        "passed": evaluation.passed,
        "violations": evaluation.violations
    }
```

---

## 9. Configuration

### 9.1 Default Parameters

```yaml
r_zero:
  challenger:
    initial_difficulty: 1.0
    variance_threshold: 0.1
    increment_rate: 0.1
    max_difficulty: 3.0
    
  solver:
    strategies: ["linear", "lateral", "creative", "meta"]
    adaptation_threshold: 0.7
    
  pragmatist:
    overhype_penalty: 0.5
    hard_rule_violation_penalty: 1.0
    min_pass_score: 0.5
    
  anti_fragile:
    skill_refinement_threshold: 0.5
    pattern_extraction_threshold: 0.8
    strategy_shift_threshold: 2.0
```

---

## 10. Future Enhancements

1. **Multi-Agent R-Zero:** Parallel triads competing/cooperating
2. **Meta-Learning:** Learn to learn adaptation strategies
3. **Human-in-the-Loop:** RLHF integration for constitutional rules
4. **Cross-Domain Transfer:** Apply to other agentic tasks
5. **Theoretical Analysis:** Prove convergence properties

---

## 11. References

1. Huang et al. (2025) - "R-Zero: Self-Evolving Reasoning LLM from Zero Data"
2. Taleb (2012) - "Antifragile: Things That Gain from Disorder"
3. COHEZION Internal - R-Zero Training Report (Sessions 40-55)
