# SPEC: Autonomous Compound Engineering System

## Overview

A self-improving engineering system where each session compounds capability through:
1. **Pattern extraction** from successful implementations
2. **Skill refinement** based on learnings
3. **Knowledge persistence** via vault + SurrealDB
4. **Parallel agent orchestration** for efficiency
5. **Integration verification** to prevent theater

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS COMPOUND ENGINEER              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   TASK       │───▶│  DECOMPOSE   │───▶│  PARALLEL    │  │
│  │   INPUT      │    │  & ANALYZE   │    │  EXECUTE     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                   │          │
│                                                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   SKILL      │◀───│   EXTRACT    │◀───│   VERIFY     │  │
│  │   REFINED    │    │   PATTERN    │    │   INTEGRATE  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                    │          │
│         ▼                   ▼                    ▼          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              KNOWLEDGE PERSISTENCE LAYER              │  │
│  │  ┌─────────────┐         ┌─────────────────────────┐ │  │
│  │  │ OBSIDIAN    │ ◀─────▶ │      SURREALDB          │ │  │
│  │  │ VAULT       │         │   (queryable index)     │ │  │
│  │  │ (markdown)  │         │                         │ │  │
│  │  └─────────────┘         └─────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Task Decomposer
**Location:** `src/cohezion/compound/task_decomposer.py`

```python
class TaskDecomposer:
    """Decompose tasks into parallelizable subtasks."""
    
    def decompose(self, task: str) -> DecompositionResult:
        """Analyze task and return subtasks with dependencies."""
        # 1. Parse task requirements
        # 2. Check vault for relevant patterns
        # 3. Identify independent subtasks
        # 4. Build dependency graph
        # 5. Return parallel execution plan
        pass
    
    def find_relevant_patterns(self, task: str) -> list[Pattern]:
        """Search vault for applicable patterns."""
        from cohezion.knowledge.vault_logger import find_relevant_context
        return find_relevant_context(task, limit=5)
```

### 2. Parallel Orchestrator
**Location:** `src/cohezion/compound/parallel_orchestrator.py`

```python
class ParallelOrchestrator:
    """Execute independent tasks in parallel via specialist agents."""
    
    async def execute_parallel(
        self, 
        tasks: list[Task],
        max_concurrent: int = 4,
    ) -> list[TaskResult]:
        """Execute tasks in parallel, respecting dependencies."""
        # 1. Build dependency graph
        # 2. Launch independent tasks
        # 3. Wait for dependencies
        # 4. Sequential execution for dependent tasks
        # 5. Aggregate results
        pass
```

### 3. Integration Verifier
**Location:** `scripts/verify_integration.py` (exists, enhance)

```python
class IntegrationVerifier:
    """Verify claimed integrations actually exist."""
    
    CLAIMED_PATHS: list[str] = []
    CLAIMED_DATACLASS_FIELDS: list[tuple[str, str]] = []
    
    def verify_all(self) -> VerificationReport:
        """Run all verification checks."""
        # Already implemented
        pass
    
    def add_claim(self, path: str, field: str | None = None):
        """Register new integration claim for verification."""
        pass
```

### 4. Pattern Extractor
**Location:** `src/cohezion/compound/pattern_extractor.py`

```python
class PatternExtractor:
    """Extract reusable patterns from implementations."""
    
    def extract_from_file(self, path: Path) -> list[Pattern]:
        """Analyze file for reusable patterns."""
        # 1. Parse AST
        # 2. Identify common patterns
        # 3. Extract with context
        # 4. Return candidate patterns
        pass
    
    def extract_from_session(self, session_id: str) -> list[Pattern]:
        """Analyze session artifacts for learnings."""
        pass
```

### 5. Skill Refiner
**Location:** `src/cohezion/compound/skill_refiner.py` (exists, enhance)

```python
class SkillRefiner:
    """Refine skills based on session learnings."""
    
    def refine_from_learning(self, learning: Learning) -> SkillUpdate:
        """Generate skill update from learning."""
        # 1. Find affected skills
        # 2. Generate update proposal
        # 3. Validate against anti-patterns
        # 4. Return update specification
        pass
    
    def apply_update(self, skill_path: Path, update: SkillUpdate):
        """Apply refinement to skill file."""
        pass
```

### 6. Knowledge Persistor
**Location:** `src/cohezion/knowledge/vault_logger.py` (exists, complete)

Already implements:
- `log_decision()`
- `log_learning()`
- `log_experiment()`
- `extract_pattern()`
- `find_relevant_context()`
- SurrealDB async persistence

## Execution Flow

### Step 1: Task Intake
```python
task = """
Implement user authentication with:
- OAuth2 support
- Session management
- Rate limiting
"""

decomposer = TaskDecomposer()
result = decomposer.decompose(task)
# Returns: ParallelExecutionPlan with 3 independent subtasks
```

### Step 2: Pattern Lookup
```python
patterns = decomposer.find_relevant_patterns("OAuth2 authentication")
# Returns patterns from vault about:
# - Previous auth implementations
# - Security best practices
# - Rate limiting patterns
```

### Step 3: Parallel Execution
```python
orchestrator = ParallelOrchestrator()
results = await orchestrator.execute_parallel(result.subtasks)
# Executes all 3 tasks in parallel via specialist agents
```

### Step 4: Integration Verification
```python
verifier = IntegrationVerifier()
# Auto-registered claims from each subtask:
# - cohezion.auth.oauth2.OAuth2Client
# - cohezion.auth.session.SessionManager
# - cohezion.auth.ratelimit.RateLimiter

report = verifier.verify_all()
assert report.all_passed, report.failures
```

### Step 5: Pattern Extraction
```python
extractor = PatternExtractor()
patterns = extractor.extract_from_session("session-60")

for pattern in patterns:
    extract_pattern(
        source_path=pattern.source,
        pattern_name=pattern.name,
        description=pattern.description,
        code_example=pattern.code,
        domain="authentication",
    )
```

### Step 6: Skill Refinement
```python
refiner = SkillRefiner()
for learning in session_learnings:
    update = refiner.refine_from_learning(learning)
    refiner.apply_update(update.skill_path, update)
```

## Token Efficiency Metrics

| Phase | Tokens | Target |
|-------|--------|--------|
| Task decomposition | 200-400 | <500 |
| Pattern lookup | 100-200 | <300 |
| Parallel execution | 500-1500 per task | <2000 |
| Verification | 50-100 | <150 |
| Pattern extraction | 100-200 | <300 |
| Skill refinement | 100-200 | <300 |
| **Total per session** | **1500-3500** | **<4000** |

## Integration with Existing Systems

### CompoundExecutor Integration
```python
# src/cohezion/compound/executor.py
class Executor:
    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.orchestrator = ParallelOrchestrator()
        self.verifier = IntegrationVerifier()
```

### JourneyTracker Integration
```python
# Already has fire coherence fields
# Add pattern extraction hooks
tracker.on_execution_complete = lambda: extractor.extract_from_session(session_id)
```

### SemanticCache Integration
```python
# Already has HIHO stabilization
# Add pattern-aware cache keys
cache.get_pattern_key = lambda task: hasher(patterns_found + task_hash)
```

## Anti-Pattern Detection

The system should detect and prevent:

```python
ANTI_PATTERNS = {
    "research_first": {
        "detector": lambda tokens, code: tokens > 5000 and code == 0,
        "message": "Research without implementation wastes tokens",
    },
    "pre_build_tests": {
        "detector": lambda test_count, code: test_count > 100 and code < 100,
        "message": "Write tests after implementation, not before",
    },
    "integration_theater": {
        "detector": lambda claims, actual: set(claims) - set(actual),
        "message": "Integration claims must be verified",
    },
    "inline_physics": {
        "detector": lambda code: "1.0 - abs(c - 0.5)" in code,
        "message": "Use HihoVectorEngine for HIHO calculations",
    },
}
```

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Session token efficiency | 45000 | 15000 | Phase 1 |
| Integration verification | 22 checks | 50+ checks | Phase 2 |
| Pattern extraction rate | Manual | Automatic | Phase 2 |
| Skill refinement velocity | 1/session | 5+/session | Phase 3 |
| Cache hit improvement | 95% | 97%+ | Phase 3 |

## Implementation Phases

### Phase 1: Foundation (2 sessions)
- [ ] Create TaskDecomposer with pattern lookup
- [ ] Enhance IntegrationVerifier with auto-registration
- [ ] Add anti-pattern detection

### Phase 2: Automation (2 sessions)
- [ ] Implement PatternExtractor
- [ ] Enhance SkillRefiner with automatic updates
- [ ] Integrate with JourneyTracker hooks

### Phase 3: Optimization (2 sessions)
- [ ] Add pattern-aware cache keys
- [ ] Implement parallel orchestrator
- [ ] Create session efficiency dashboard

## Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `src/cohezion/compound/task_decomposer.py` | Task decomposition | P0 |
| `src/cohezion/compound/pattern_extractor.py` | Pattern extraction | P1 |
| `src/cohezion/compound/parallel_orchestrator.py` | Parallel execution | P1 |
| `src/cohezion/compound/anti_pattern_detector.py` | Anti-pattern detection | P2 |
| `tests/compound/test_task_decomposer.py` | Decomposer tests | P0 |
| `tests/compound/test_pattern_extractor.py` | Extractor tests | P1 |

## See Also

- `AUTONOMOUS_COMPOUND_ENGINEERING_PRIME.md`
- `RETROSPECTIVE_SKILL.md`
- `scripts/verify_integration.py`
- `src/cohezion/knowledge/vault_logger.py`