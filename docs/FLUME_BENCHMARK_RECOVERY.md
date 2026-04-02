# FLUME Journey Benchmark Platform - Session Recovery Guide

## IMPORTANT: Two Different APIs Exist in Committed Code

The committed repository has TWO different benchmark systems:

### 1. `cohezion/benchmarks/` (committed) - "CohezionBenchmark"
- `benchmark_suite.py`: `CohezionBenchmark` class with `compute_intrinsic_metrics()`, `run_ablation_study()`, etc.
- `agentic_metrics.py`: `AgenticMetrics` class with `AgenticResults` dataclass
- Tests: `test_agentic_metrics.py` with `TestAgenticResults`

### 2. `cohezion/eval/` FLUME Journey (we built this) - "BenchmarkSuite"  
- `benchmark_suite.py`: `BenchmarkSuite` + `BenchmarkTask` + 15 task implementations (HIHOBasinEasy, etc.)
- `pipeline.py`: `RalphLoop` + `EvalPipeline` (different from committed version)
- `capability_scorecard.py`: `CapabilityScorecard` + `RadarChart` + `LongitudinalTracker`
- `huggingface_export.py`: `HuggingFaceExporter` for JSONL + benchmark harness
- `compound_integration.py`: `BenchmarkSessionManager` + `SelfImprovingBenchmarkLoop`

**OUR FLUME Journey files are NEW and NOT committed.** They were lost on session reset.

---

## What Was Built This Session (NOT COMMITTED - LOST)

### New Source Files to Recreate

1. **`src/cohezion/eval/compound_integration.py`** (~253 lines)
   - Classes: `BenchmarkSessionManager`, `SelfImprovingBenchmarkLoop`, `CurriculumState`
   - Purpose: Compound integration for benchmark sessions with vault persistence

2. **`tests/benchmarks/conftest.py`** (~17 lines)
   - Gym environment registration fixture

3. **`tests/benchmarks/test_benchmark_suite.py`** (~270 lines, 19 tests)
   - Tests for BenchmarkSuite, BenchmarkTask, and all 15 task implementations

4. **`tests/eval/test_huggingface_export.py`** (~87 lines, 5 tests)
   - Tests for HuggingFaceExporter

5. **`tests/eval/test_compound_integration.py`** (~180 lines, 12 tests)
   - Tests for compound integration module

### Modified Files (already in git - need verification)

The committed files may need their FLUME additions restored:
- `src/cohezion/benchmarks/__init__.py` - needs FLUME exports added
- `src/cohezion/eval/__init__.py` - needs FLUME exports added
- `src/cohezion/benchmarks/benchmark_suite.py` - may have FLUME additions OR be original
- `src/cohezion/eval/pipeline.py` - may have FLUME additions OR be original (579 lines committed)

---

## Key EVO Interface Notes

When restoring `pipeline.py`, use correct EVO interface:
```python
# CORRECT:
evo.update_physics(coherence=0.8, step=steps, doer_state=state, thinker_state=None, knower_state=None)
float(evo.coherence_amplitude)
evo.to_exotic_vacuum_biography()

# WRONG (doesn't exist):
evo.update_physics(coherence=0.8, hiho_distance=0.5)  # hiho_distance doesn't exist
evo.coherence  # doesn't exist
evo.export_biography()  # doesn't exist
```

## Lint Rules to Follow

- Use `zip(values, self.MAX_VALUES, strict=True)` for zip
- `before_episode` should be concrete with `pass` body (not `@abstractmethod`)
- Use `TYPE_CHECKING` block for type-only imports like `Callable`
- Sort `__all__` alphabetically

## Verification After Reboot

Run these to verify FLUME files exist:
```bash
ls src/cohezion/eval/compound_integration.py
ls tests/benchmarks/conftest.py
ls tests/benchmarks/test_benchmark_suite.py
uv run pytest tests/benchmarks/ tests/eval/ -q --no-cov
```

Expected when rebuilt: 87 passed

### Source Files (in `src/cohezion/eval/` and `src/cohezion/benchmarks/`)

1. **`src/cohezion/eval/compound_integration.py`** (NEW - NOT in git)
   - Classes: `BenchmarkSessionManager`, `SelfImprovingBenchmarkLoop`, `CurriculumState`
   - Purpose: Compound integration for benchmark sessions with vault persistence

2. **`tests/benchmarks/conftest.py`** (NEW - NOT in git)
   - Gym environment registration fixture

3. **`tests/benchmarks/test_benchmark_suite.py`** (NEW - NOT in git)
   - 19 tests for BenchmarkSuite, BenchmarkTask, and all task implementations

4. **`tests/eval/test_huggingface_export.py`** (NEW - NOT in git)
   - 5 tests for HuggingFaceExporter

5. **`tests/eval/test_compound_integration.py`** (NEW - NOT in git)
   - 12 tests for compound integration module

### Files That Need Updates (already in git, may need restoration)

1. **`src/cohezion/benchmarks/__init__.py`** - Needs exports for:
   - ALPHA, N_BOOTSTRAP, BonferroniCorrection, BootstrapResult
   - CoherenceMetric, EVOPhysicsMetrics, ExoticChargeMetric
   - KordylewskiOrbitMetric, SPINPhaseMetric, StabilityMetric
   - StatisticalComparison, TRIUNEBalanceMetric
   - BenchmarkResult, BenchmarkSuite, BenchmarkTask, Policy, TaskResult
   - All task classes (HIHOBasinEasy/Medium/Hard, TRIUNEBalanceEasy/Medium/Hard, etc.)

2. **`src/cohezion/eval/__init__.py`** - Needs exports for:
   - AXES, MAX_VALUES, CapabilityScorecard, LongitudinalTracker, RadarChart
   - StatisticalComparison, ConvergenceLevel, EpisodeStatus, EvalPipeline
   - PipelineProgress, RalphLoop, RalphLoopConfig
   - BenchmarkSessionManager, CurriculumState, SelfImprovingBenchmarkLoop

## What Was Working (87 tests passing)

### Source Modules (all committed to git)
- `agentic_metrics.py` - EVO physics metrics with bootstrap CI
- `benchmark_suite.py` - 15 benchmark tasks, 5 archetypes
- `pipeline.py` - RalphLoop FOR-DONE-ESCALATE pattern
- `capability_scorecard.py` - 6-axis radar chart, longitudinal tracking
- `huggingface_export.py` - JSONL dataset + benchmark harness export

### Test Modules (NOT committed - need recreation)
- `tests/benchmarks/test_agentic_metrics.py` - 17 tests
- `tests/benchmarks/test_benchmark_suite.py` - 19 tests
- `tests/benchmarks/conftest.py` - gym registration fixture
- `tests/eval/test_pipeline.py` - 9 tests
- `tests/eval/test_capability_scorecard.py` - 17 tests
- `tests/eval/test_huggingface_export.py` - 5 tests
- `tests/eval/test_compound_integration.py` - 12 tests

## Key EVO Interface Notes

When restoring `pipeline.py`, use correct EVO interface:
```python
# CORRECT:
evo.update_physics(coherence=0.8, step=steps, doer_state=state, thinker_state=None, knower_state=None)
float(evo.coherence_amplitude)
evo.to_exotic_vacuum_biography()

# WRONG (doesn't exist):
evo.update_physics(coherence=0.8, hiho_distance=0.5)  # hiho_distance doesn't exist
evo.coherence  # doesn't exist
evo.export_biography()  # doesn't exist
```

## Lint Rules to Follow

- Use `zip(values, self.MAX_VALUES, strict=True)` for zip
- `before_episode` should be concrete with `pass` body (not `@abstractmethod`)
- Use `TYPE_CHECKING` block for type-only imports like `Callable`
- Sort `__all__` alphabetically

## Restoration Commands

After reboot, recreate these files with the content from session logs or recreate tests based on the actual API in the committed source files.

Run tests to verify:
```bash
uv run pytest tests/benchmarks/ tests/eval/ -q --no-cov
```

Expected: 87 passed
