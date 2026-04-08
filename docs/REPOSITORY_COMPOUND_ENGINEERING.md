# Repository Layer Compound Engineering

## Overview

The repository layer implements **compound engineering patterns** where every feature makes subsequent features easier to implement. This document captures the architectural decisions and compounding benefits.

## Core Principle

> "Every feature made makes every new feature easier to implement."

This is achieved through:
1. **Shared abstractions** (BaseRepository)
2. **Automatic metrics collection** (RepositoryMetrics)
3. **Batch operations** (BatchOperationResult)
4. **Adversarial review integration** (8-perspective testing)
5. **Token efficiency patterns** (cache tracking)

## Architecture

### Layer 1: Base Repository (`base.py`)

```python
class BaseRepository(ABC, Generic[T, TFilter]):
    """Shared foundation for all repositories."""
    
    # Automatic features:
    - Batch operations (batch_create, batch_get)
    - Metrics collection (_record_metrics)
    - Error handling (_execute_with_metrics)
    - Performance monitoring (get_metrics_summary)
```

**Compounding Benefits:**
- New repositories inherit batch operations automatically
- Metrics enable adversarial review without extra code
- Error handling is consistent across all repositories
- Cache tracking enables token optimization

### Layer 2: Concrete Repositories

```python
class SurrealSkillRepository(SkillRepository, BaseRepository[Skill, None]):
    """Inherits all base features + domain-specific logic."""
    
class SurrealUniverseRepository(UniverseRepository, BaseRepository[UniverseNode, UniverseRepositoryFilter]):
    """Inherits all base features + domain-specific logic."""
```

**Compounding Benefits:**
- Multiple inheritance provides both interface + implementation
- Type-safe generic parameters
- Domain logic focuses on business rules, not infrastructure

### Layer 3: Test Coverage

```python
# Unit tests (40 tests)
tests/core/persistence/repositories/test_base_repository.py
tests/core/persistence/repositories/test_surreal_skill_repository.py
tests/core/persistence/repositories/test_surreal_universe_repository.py

# Adversarial review tests (14 tests)
tests/compound/tdd_adversarial/test_repository_adversarial_review.py
```

**Compounding Benefits:**
- Base repository tests validate shared functionality once
- Adversarial review catches issues across 8 perspectives
- New repositories automatically get test coverage

## Metrics Collection

### RepositoryMetrics

```python
@dataclass
class RepositoryMetrics:
    operation: str
    duration_ms: float
    success: bool
    items_processed: int = 1
    cache_hit: bool = False
    batch_size: int = 1
    error_message: str | None = None
```

**Used By:**
1. **Batch Sizer**: Throughput prediction for optimal batch sizes
2. **Adversarial Review**: Performance perspective analysis
3. **Token Efficiency**: Cache hit rate optimization
4. **Monitoring**: Slow operation detection (>1s warning)

### BatchOperationResult

```python
@dataclass
class BatchOperationResult(Generic[T]):
    success: bool
    items_processed: int
    items_failed: int
    results: list[T]
    errors: list[tuple[int, str]]
    total_duration_ms: float
    cache_hits: int
    cache_misses: int
    
    @property
    def success_rate(self) -> float: ...
    @property
    def cache_hit_rate(self) -> float: ...
```

**Used By:**
1. **Batch Executor**: Bulk operation coordination
2. **Error Handling**: Partial failure recovery
3. **Performance Analysis**: Throughput calculation

## Adversarial Review Integration

### 8 Perspectives

1. **Security**: SQL injection prevention ✅
2. **Performance**: Query optimization ✅
3. **Reliability**: Error handling, fallbacks ✅
4. **Usability**: API design ✅
5. **Maintainability**: Code structure ✅
6. **Compliance**: Audit trails (metrics) ✅
7. **Innovation**: Novel patterns ✅
8. **Ethics**: Data handling ✅

### Test Coverage

```python
class TestRepositorySecurityReview:
    def test_sql_injection_prevention()  # Verifies parameterized queries
    
class TestRepositoryPerformanceReview:
    def test_query_optimization()  # Verifies LIMIT/WHERE usage
    def test_batch_operations_support()  # Verifies batch methods
    
class TestRepositoryReliabilityReview:
    def test_error_handling()  # Verifies try/except
    def test_fallback_strategies()  # Verifies InMemoryStore fallback
    
class TestRepositoryMaintainabilityReview:
    def test_code_structure()  # Verifies docstrings, types
    def test_testability()  # Verifies abstract base classes
    
class TestTDDAdversarialIntegration:
    def test_coordinator_pre_engineering_checks()
    def test_full_review_cycle()
    
class TestRepositoryBatchIntegration:
    def test_repository_batch_compatibility()
    def test_repository_metrics_collection()
    def test_token_efficiency_patterns()
```

## Token Efficiency Patterns

### Context Separation

Repositories separate:
1. **Static Context**: Table names, query structures (cacheable)
2. **Dynamic Context**: Query parameters, data values (per-request)

### Cache Tracking

```python
# Automatic cache hit/miss tracking
metrics = RepositoryMetrics(
    cache_hit=True,  # From L1/L2/L3 cache
    items_processed=10,
)

# Used for cache optimization decisions
summary = repo.get_metrics_summary()
cache_hit_rate = summary["cache_hit_rate"]  # 0.0-1.0
```

## Usage Examples

### Basic Repository Usage

```python
from cohezion.core.persistence.repositories import SurrealSkillRepository, Skill
from cohezion.core.persistence.surreal_client import SurrealClient

# Initialize
client = SurrealClient()
repo = SurrealSkillRepository(client)

# Create skill
skill = Skill(name="python_coding", description="Python programming")
skill_id = await repo.create(skill)

# Get skill
retrieved = await repo.get(skill_id)

# Batch operations
skills = [Skill(name=f"skill_{i}") for i in range(10)]
result = await repo.batch_create(skills)
print(f"Created {result.items_processed}/{len(skills)} skills")
print(f"Cache hit rate: {result.cache_hit_rate:.2%}")
```

### Metrics Analysis

```python
# Get performance metrics
summary = repo.get_metrics_summary()
print(f"Total operations: {summary['total_operations']}")
print(f"Success rate: {summary['success_rate']:.2%}")
print(f"Avg duration: {summary['avg_duration_ms']:.2f}ms")

# Analyze by operation type
for op, stats in summary["by_operation"].items():
    print(f"{op}: {stats['count']} ops, {stats['avg_duration_ms']:.2f}ms avg")
```

### Adversarial Review

```python
from cohezion.compound.tdd_adversarial import AdversarialReviewSystem

review_system = AdversarialReviewSystem(project_root=Path("."))
session = await review_system.run_full_adversarial_review("repo_review")

# Review findings across 8 perspectives
for finding in session.findings:
    print(f"[{finding.perspective.value}] {finding.title}")
    print(f"  Severity: {finding.severity}")
    print(f"  Confidence: {finding.confidence:.2f}")
```

## Test Results

```
======================== 53 passed ========================
- Repository tests: 40 passed
- Adversarial review: 13 passed
- No regressions introduced
```

## Future Extensions

### Planned Repositories

1. **PatternRepository**: Code pattern persistence
2. **JourneyRepository**: Agent journey tracking
3. **LearningRepository**: Skill acquisition records

### Planned Features

1. **Batch Update/Delete**: Extend batch operations
2. **Query Builder**: Type-safe query construction
3. **Transaction Support**: Multi-operation atomicity
4. **Streaming**: Large result set pagination

## Key Insights

1. **Base class pays for itself**: One implementation, inherited by all repositories
2. **Metrics enable optimization**: Can't improve what you don't measure
3. **Adversarial review catches blind spots**: 8 perspectives > 1 perspective
4. **Token efficiency compounds**: Small optimizations multiply across operations
5. **Test coverage compounds**: Base tests validate all derived repositories

## References

- `src/cohezion/core/persistence/repositories/base.py` - Base implementation
- `tests/core/persistence/repositories/` - Test coverage
- `tests/compound/tdd_adversarial/test_repository_adversarial_review.py` - Adversarial review
- `src/cohezion/compound/batch_executor.py` - Batch execution integration
- `src/cohezion/compound/tdd_adversarial/` - TDD + adversarial coordination
