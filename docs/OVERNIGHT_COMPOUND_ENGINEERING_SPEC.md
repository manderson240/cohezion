# Overnight Compound Engineering Specification

## Overview

This document defines the architecture and implementation for **overnight compound engineering** - autonomous, long-running AI engineering sessions that leverage off-peak compute to perform deep skill refinement, knowledge synthesis, and self-improvement cycles at massive scale.

> **FLUME**: Fluid Latent Understanding through Manifold Encoding - encodes thought trajectories into 256D latent space, enabling semantic interpolation and trajectory prediction as continuous fluid dynamics rather than discrete token sequences.

## Goals

1. **Autonomous Operation**: Sessions run unattended for 8-12 hours overnight
2. **Recursive Self-Improvement**: Each cycle improves the improvement mechanism itself
3. **Massive Scale**: Target 1,000,000+ iterations per session through parallelization
4. **Skill Compounding**: Each cycle builds on previous knowledge, accumulating expertise
5. **Journey Capture**: Full agentic trajectories stored in SurrealDB via FLUME
6. **Fault Tolerance**: Automatic checkpoint/resume on failure
7. **Energy Efficiency**: Leverage off-peak hours for computationally intensive work
8. **Knowledge Persistence**: All learnings saved to vault for future sessions

## Architecture

### Session Manager

```
┌─────────────────────────────────────────────────────────────┐
│               RecursiveOvernightSessionManager               │
├─────────────────────────────────────────────────────────────┤
│  - session_id: str                                          │
│  - start_time: datetime                                     │
│  - target_duration: timedelta (default: 8h)                 │
│  - target_iterations: int (default: 1_000_000)             │
│  - checkpoint_interval: int (default: 1000 cycles)           │
│  - recursion_depth: int (default: 3)                      │
│  - energy_profile: EnergyProfile                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lifecycle Phases                          │
├─────────────────────────────────────────────────────────────┤
│  1. WARM_START        - Load cache, metrics, journey       │
│  2. FLUME_INIT        - Initialize 256D latent encoder     │
│  3. RECURSIVE_CYCLES  - Run self-improving compound loops  │
│  4. QUADRATURE_NEXUS  - Merge trajectories via nexus       │
│  5. CHECKPOINT        - Persist state to SurrealDB        │
│  6. CLEAN_SHUTDOWN   - Save cache, metrics, learnings      │
└─────────────────────────────────────────────────────────────┘
```

**FLUME (Fluid Latent Understanding through Manifold Encoding)**:
- Encodes agent journeys into 256D continuous latent space
- Projects to 12D manifold for QuadratureNexus trajectory merging
- Enables semantic interpolation between concepts
- Models thought as fluid dynamics: velocity, momentum, trajectory
┌─────────────────────────────────────────────────────────────┐
│               RecursiveOvernightSessionManager               │
├─────────────────────────────────────────────────────────────┤
│  - session_id: str                                          │
│  - start_time: datetime                                     │
│  - target_duration: timedelta (default: 8h)                 │
│  - target_iterations: int (default: 1_000_000)             │
│  - checkpoint_interval: int (default: 1000 cycles)         │
│  - recursion_depth: int (default: 3)                       │
│  - energy_profile: EnergyProfile                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lifecycle Phases                          │
├─────────────────────────────────────────────────────────────┤
│  1. WARM_START        - Load cache, metrics, journey       │
│  2. FLUME_INIT        - Initialize 12D latent encoder      │
│  3. RECURSIVE_CYCLES  - Run self-improving compound loops  │
│  4. QUADRATURE_NEXUS  - Merge trajectories via nexus       │
│  5. CHECKPOINT        - Persist state to SurrealDB         │
│  6. CLEAN_SHUTDOWN   - Save cache, metrics, learnings      │
└─────────────────────────────────────────────────────────────┘
```

## Recursive Self-Improvement Architecture

The system implements **recursive self-improvement** where each iteration not only improves the target skill but also improves the improvement mechanism itself:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RECURSION LAYERS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 0: Base Skills                                                       │
│  ├── Execute skill with parameters                                          │
│  └── Measure coherence/success                                              │
│                                                                             │
│  Layer 1: Skill Refinement                                                  │
│  ├── Analyze Layer 0 outputs                                               │
│  ├── Generate improved prompt/instructions                                 │
│  └── Loop back to Layer 0                                                  │
│                                                                             │
│  Layer 2: Meta-Improvement                                                  │
│  ├── Analyze Layer 1 patterns                                              │
│  ├── Improve refinement strategy                                           │
│  └── Loop back to Layer 1                                                  │
│                                                                             │
│  Layer 3: Recursion Optics                                                 │
│  ├── Analyze Layer 2 trajectories                                          │
│  ├── Optimize the optimization process                                     │
│  └── Loop back to Layer 2                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. RecursiveOvernightSessionManager

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import asyncio

@dataclass
class EnergyProfile:
    """Profile for energy-efficient operation."""
    prefer_low_power_models: bool = True
    batch_size: int = 32
    max_concurrent_agents: int = 8
    thermal_threshold_celsius: float = 75.0

@dataclass
class RecursiveConfig:
    """Configuration for recursive overnight session."""
    target_duration: timedelta = timedelta(hours=8)
    target_iterations: int = 1_000_000
    checkpoint_interval_cycles: int = 1000
    recursion_depth: int = 3
    min_coherence_threshold: float = 0.7
    improvement_ratio_threshold: float = 1.05  # 5% improvement required
    enable_self_reflection: bool = True
    parallel_branches: int = 4
    energy_profile: EnergyProfile = field(default_factory=EnergyProfile)

class RecursiveOvernightSessionManager:
    """Manages autonomous recursive overnight compound engineering sessions."""

    def __init__(self, config: RecursiveConfig | None = None):
        self.config = config or RecursiveConfig()
        self._session_id: str = ""
        self._start_time: datetime | None = None
        self._iteration_count: int = 0
        self._recursion_level: int = 0
        self._journey_state: dict[str, Any] = {}
        self._improvement_history: list[dict[str, Any]] = []
        self._flume_encoder: Any = None
        self._quadrature_nexus: Any = None

    async def start(self) -> dict[str, Any]:
        """Initialize session: warm cache, load metrics, initialize FLUME."""
        # Initialize FLUME encoder for 12D latent space
        from cohezion.flume import VAEEncoder
        self._flume_encoder = VAEEncoder()
        
        # Initialize QuadratureNexus for trajectory merging
        from cohezion.flume.quadrature_nexus import QuadratureNexus
        self._quadrature_nexus = QuadratureNexus(depth=12)
        
        # Load persisted state from previous sessions
        # Initialize compound client with warm cache
        pass

    async def run_recursive_cycles(self) -> dict[str, Any]:
        """Execute recursive compound engineering cycles."""
        results = {
            "total_iterations": 0,
            "recursion_levels_completed": 0,
            "final_coherence": 0.0,
            "improvement_factor": 1.0,
            "journey_trajectories": [],
        }

        while self._iteration_count < self.config.target_iterations:
            # Run parallel refinement branches
            tasks = [
                self._run_branch(branch_id=i)
                for i in range(self.config.parallel_branches)
            ]
            branch_results = await asyncio.gather(*tasks)
            
            # Merge results through QuadratureNexus
            merged = await self._quadrature_nexus.merge(branch_results)
            
            # Store journey in SurrealDB via FLUME
            await self._persist_journey(merged)
            
            # Self-reflect and adapt strategy
            if self._iteration_count % 10000 == 0:
                await self._self_reflect()
            
            # Checkpoint periodically
            if self._iteration_count % self.config.checkpoint_interval_cycles == 0:
                await self.checkpoint()

            self._iteration_count += 1

        return results

    async def _run_branch(self, branch_id: int) -> dict[str, Any]:
        """Run a single branch of recursive improvement."""
        for level in range(self.config.recursion_depth):
            # Execute improvement at current recursion level
            result = await self._execute_improvement(level)
            
            # Encode result into FLUME 12D latent space
            latent = self._flume_encoder.encode(result)
            
            # Track improvement trajectory
            self._improvement_history.append({
                "branch": branch_id,
                "level": level,
                "latent": latent,
                "iteration": self._iteration_count,
            })
            
        return {"branch_id": branch_id, "latents": self._improvement_history}

    async def _persist_journey(self, trajectory_data: dict[str, Any]) -> None:
        """Persist journey to SurrealDB through JourneyPersistence."""
        from cohezion.compound.exp_persistence.journey import get_journey_persistence
        
        persistence = get_journey_persistence()
        
        journey_record = {
            "timestamp": datetime.now().isoformat(),
            "mission_id": self._session_id,
            "agent_id": f"recursive-agent-{self._recursion_level}",
            "skill_name": "recursive_compound",
            "input_preview": str(trajectory_data.get("input", ""))[:500],
            "output_preview": str(trajectory_data.get("output", ""))[:500],
            "phi_score": trajectory_data.get("coherence", 0.0),
            "novelty": trajectory_data.get("novelty", 1.0),
            "flume_version": "1.0",
            "state_trajectory": trajectory_data.get("latents", []),
            "recursion_depth": self._recursion_level,
            "iteration_count": self._iteration_count,
        }
        
        await persistence.persist_batch([journey_record])

    async def checkpoint(self) -> bool:
        """Persist current state to vault (primary) or JSONL (fallback)."""
        pass

    async def shutdown(self) -> dict[str, Any]:
        """Clean shutdown: save cache, metrics, learnings."""
        pass
```

#### 2. FLUME Integration (256D → 12D Manifold)

```python
from cohezion.flume.vae_encoder import VAEEncoder, get_encoder
from cohezion.flume.navigator import Navigator

class FlumeJourneyEncoder:
    """Encode agent journeys into FLUME latent space (Fluid Latent Understanding through Manifold Encoding)."""
    
    def __init__(self):
        self.encoder = get_encoder()  # 256D latent space
        self.navigator = Navigator()  # Trajectory prediction
        self.latent_dim = 256  # FLUME default
    
    def encode_journey(self, journey_data: dict[str, Any]) -> np.ndarray:
        """Encode journey trajectory into FLUME latent vector."""
        # Combine skill inputs, outputs, coherence scores
        combined = self._combine_journey_data(journey_data)
        # Encode into FLUME 256D latent space
        latent = self.encoder.encode(combined)
        # Project to 12D manifold for QuadratureNexus
        return self._project_to_12d(latent)
    
    def predict_trajectory(self, z: np.ndarray, steps: int = 10) -> np.ndarray:
        """Predict thought trajectory in latent space using FLUME Navigator."""
        return self.navigator.predict_sequence(z, steps=steps, momentum=0.3)
    
    def _project_to_12d(self, latent: np.ndarray) -> np.ndarray:
        """Project 256D latent to 12D manifold for QuadratureNexus."""
        # Use learned projection or PCA
        pass
```

#### 3. Quadrature Nexus (Trajectory Merging)

```python
class QuadratureNexus:
    """Merge agent trajectories through quadrature integration."""
    
    def __init__(self, depth: int = 12):
        self.depth = depth
        self.trajectory_buffer: list[np.ndarray] = []
    
    async def merge(self, branch_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple branch trajectories via quadrature."""
        latents = [r.get("latent", np.zeros(12)) for r in branch_results]
        
        # Quadrature integration: weighted sum with phase alignment
        merged = self._quadrature_integrate(latents)
        
        # Extract coherent patterns
        coherence = self._calculate_coherence(merged)
        novelty = self._calculate_novelty(merged)
        
        return {
            "merged_trajectory": merged,
            "coherence": coherence,
            "novelty": novelty,
        }
    
    def _quadrature_integrate(self, latents: list[np.ndarray]) -> np.ndarray:
        """Integrate trajectories using numerical quadrature."""
        # Trapezoidal rule with phase alignment
        pass
    
    def _calculate_coherence(self, trajectory: np.ndarray) -> float:
        """Measure trajectory coherence."""
        pass
    
    def _calculate_novelty(self, trajectory: np.ndarray) -> float:
        """Measure trajectory novelty vs history."""
        pass
```

#### 4. SurrealDB Journey Persistence

```python
from cohezion.compound.exp_persistence.journey import JourneyPersistence

class SurrealJourneyStore:
    """Store recursive improvement journeys in SurrealDB."""
    
    def __init__(self):
        self.persistence = get_journey_persistence()
    
    async def store_recursion_step(
        self,
        session_id: str,
        iteration: int,
        recursion_level: int,
        latent_vector: np.ndarray,
        coherence: float,
        improvement_delta: float,
    ) -> None:
        """Store a single recursion step."""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "mission_id": session_id,
            "agent_id": f"recursion-l{recursion_level}",
            "skill_name": "recursive_improvement",
            "phi_score": coherence,
            "novelty": improvement_delta,
            "flume_version": "1.0",
            "state_trajectory": latent_vector.tolist(),
            "recursion_depth": recursion_level,
            "iteration_count": iteration,
        }
        
        await self.persistence.persist_batch([record])
    
    async def query_journeys(
        self,
        session_id: str,
        min_coherence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Query journey history from SurrealDB."""
        # Use SurrealDB SQL-like queries
        pass
```

## Execution Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     RECURSIVE OVERNIGHT SESSION                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │ WARM START   │───▶│ 1. Load persisted state (cache, metrics, journey)│   │
│  └──────────────┘    │ 2. Initialize FLUME encoder (12D latent space)    │   │
│         │            │ 3. Initialize QuadratureNexus                     │   │
│         ▼            └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      RECURSION LOOP (Target: 1M iterations)           │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  While (iteration < target_iterations):                              │   │
│  │    │                                                                  │   │
│  │    ├─ Parallel Branches (4x):                                        │   │
│  │    │   ├─ Branch 0: Execute improvement at recursion level L        │   │
│  │    │   ├─ Branch 1: Execute improvement at recursion level L        │   │
│  │    │   ├─ Branch 2: Execute improvement at recursion level L        │   │
│  │    │   └─ Branch 3: Execute improvement at recursion level L        │   │
│  │    │                                                                  │   │
│  │    ├─ FLUME Encode: Project each branch to 12D latent               │   │
│  │    │                                                                  │   │
│  │    ├─ Quadrature Nexus: Merge trajectories via quadrature          │   │
│  │    │                                                                  │   │
│  │    ├─ SurrealDB: Store journey trajectory                           │   │
│  │    │                                                                  │   │
│  │    ├─ Check improvement ratio:                                       │   │
│  │    │   ├─ If improved: advance recursion level                      │   │
│  │    │   └─ If stalled: rollback to checkpoint                         │   │
│  │    │                                                                  │   │
│  │    └─ Every N iterations: checkpoint state                         │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────┐                                                         │
│  │ CLEAN         │───▶ Persist cache to vault                              │
│  │ SHUTDOWN      │───▶ Save metrics snapshot                              │
│  └──────────────┘───▶ Save journey trajectory to SurrealDB                 │
│                      Delete checkpoints                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Scaling to 1 Million Iterations

### Parallelization Strategy

```python
class MassiveScaleRunner:
    """Run 1M+ iterations through parallel execution."""
    
    def __init__(self, config: RecursiveConfig):
        self.config = config
        self.iteration = 0
        self.workers = 4  # Parallel branches
        self.queue = asyncio.Queue()
    
    async def run(self) -> dict[str, Any]:
        """Execute 1M iterations with throughput tracking."""
        
        start_time = time.time()
        
        # Create worker pool
        workers = [
            asyncio.create_task(self._worker(worker_id=i))
            for i in range(self.workers)
        ]
        
        # Track progress
        while self.iteration < self.config.target_iterations:
            await asyncio.sleep(60)  # Report every minute
            elapsed = time.time() - start_time
            rate = self.iteration / elapsed
            remaining = (self.config.target_iterations - self.iteration) / rate
            
            logger.info(
                f"Progress: {self.iteration:,}/{self.config.target_iterations:,} "
                f"({rate:.1f} iter/sec, ~{remaining/3600:.1f}h remaining)"
            )
        
        # Wait for completion
        await asyncio.gather(*workers)
        
        return {"total_iterations": self.iteration, "elapsed": time.time() - start_time}
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine processing iterations from queue."""
        while self.iteration < self.config.target_iterations:
            iteration = self.iteration
            self.iteration += 1
            
            # Process iteration
            await self._process_iteration(iteration, worker_id)
```

### Performance Targets

| Metric | Target |
|--------|--------|
| Iterations per second | 35+ |
| Total iterations per 8h session | 1,000,000 |
| Journey persistence latency | <10ms |
| Memory footprint | <8GB |
| Thermal throttling threshold | 75°C |

## Configuration

```yaml
# overnight_recursive_config.yaml
session:
  target_duration_hours: 8
  target_iterations: 1_000_000
  checkpoint_interval_cycles: 1000
  recursion_depth: 3
  parallel_branches: 4
  min_coherence_threshold: 0.7
  improvement_ratio_threshold: 1.05

energy:
  prefer_low_power_models: true
  batch_size: 32
  max_concurrent_agents: 8
  thermal_threshold_celsius: 75.0

persistence:
  vault_enabled: true
  surreal_enabled: true
  local_fallback: true
  checkpoint_dir: "data/checkpoints/overnight"
  journey_dir: "data/journeys"

flume:
  latent_dim: 256
  projection_dim: 12
  encoder_model: "vae_v1"
  navigation_momentum: 0.3

quadrature:
  depth: 12
  integration_method: "trapezoidal"
  phase_alignment: true
```

## SurrealDB Schema

```sql
-- Mission journeys table (created by JourneyPersistence)
DEFINE TABLE mission_journey SCHEMAFULL;

-- Fields for recursive improvement tracking
FIELD timestamp TYPE string;
FIELD mission_id TYPE string;
FIELD agent_id TYPE string;
FIELD skill_name TYPE string;
FIELD phi_score TYPE float;
FIELD novelty TYPE float;
FIELD flume_version TYPE string;
FIELD state_trajectory TYPE array;
FIELD recursion_depth TYPE int;
FIELD iteration_count TYPE int;

-- Indexes for efficient querying
INDEX idx_mission ON mission_id;
INDEX idx_iteration ON iteration_count;
INDEX idx_phi ON phi_score;
```

## Monitoring & Alerts

- **Health Check**: Every 30 minutes
- **Progress Report**: Every 1000 iterations to vault + SurrealDB
- **Throughput Tracking**: iterations/second dashboard
- **Alert on**:
  - Thermal threshold exceeded (pause session)
  - Coherence degradation >20%
  - Improvement ratio <1.0 for 1000 iterations
  - Checkpoint save failures
  - SurrealDB connection lost

## Session-Level Context Awareness (Added: 2026-02-22)

Compound engineering sessions must be context-aware at the agent level, not just resource-aware. Key patterns from Sessions 67-68:

### Context Guard Protocol

Every compound cycle must check context pressure before starting the next layer:

```python
async def _check_context_before_layer(self, layer: int) -> bool:
    """Return False if context is too full to safely start next layer."""
    import subprocess, json
    result = subprocess.run(
        ["~/.pilot/bin/pilot", "check-context", "--json"],
        capture_output=True, text=True
    )
    status = json.loads(result.stdout)
    if status["percentage"] >= 80:
        logger.warning(f"Context at {status['percentage']:.1f}% — skipping layer {layer}")
        await self._save_checkpoint_and_handoff()
        return False
    return True
```

**Rule**: Never start a new recursion layer above 80% context. Each layer needs headroom.

### Token Budget by Operation

Calibrated from Sessions 40-68:

| Operation | Token Budget | Anti-Pattern |
|-----------|-------------|--------------|
| Single skill execution | 500-1,500 | Pre-loading 50+ skills upfront |
| Research + implement | 2,000-3,000 | Exhaustive research before POC |
| Skill refinement loop | 1,500-2,500 | Re-running same tests without change |
| Retrospective + vault log | 800-1,200 | Writing MEMORY.md directly (use vault) |
| Full test suite | ~100 | Running with `-v` in compound loops |
| Context handoff | 200-400 | Missing the handoff (total context loss) |

### Vault-First in Compound Loops

Every retrospection cycle must log to vault, not accumulate in-memory:

```python
async def _retrospect_and_log(self, execution_result: dict) -> None:
    """Retrospect + immediately persist to vault."""
    learnings = self.retrospection_engine.analyze(execution_result)
    # Log to vault immediately — don't buffer
    for learning in learnings.key_insights:
        await vault_log_experiment(
            project="cohezion",
            hypothesis=learning.hypothesis,
            method=learning.method,
            result=learning.result,
            learnings=learning.takeaway,
        )
    # Regenerate MEMORY.md every N cycles
    if self.cycle_count % 100 == 0:
        await self._recompile_memory()
```

### Predictive Throttling (Session 68 Pattern)

Replace reactive thresholds with velocity-based prediction:

```python
# REACTIVE (old) — responds after saturation
if cpu_percent > 90:
    self.dilation_factor = 0.5

# PREDICTIVE (new) — anticipates saturation
velocity = np.linalg.norm(position_now - position_prev)
if velocity > self.gradient_threshold:
    self.dilation_factor *= 0.5  # Throttle before hitting the wall
    logger.warning(f"Predictive throttle: velocity={velocity:.3f}")
```

### Recursive Challenger Integration (Session 68)

`CompoundExecutor.execute_skill()` now closes the autonomous loop:

```python
# The missing piece: execute_skill enables fully autonomous improvement
executor = CompoundExecutor()
challenger = RecursiveChallenger(executor)

# This loop now runs without human intervention
async for improvement in challenger.run(target_module="self_healing"):
    logger.info(f"Improvement: {improvement.delta:.3%} coherence gain")
```

**Next targets for RecursiveChallenger**: `self_healing` module, then `swarm/team_executor.py`.

### Environment Recovery Guard

Every overnight session start must validate the environment:

```python
async def _pre_flight_env_check(self) -> None:
    """Verify venv is intact before running overnight. (L129)"""
    import subprocess
    result = subprocess.run(
        ["uv", "run", "python", "-m", "pytest", "--collect-only", "-q"],
        capture_output=True, text=True, cwd=self.project_root
    )
    if result.returncode != 0:
        # Auto-recover: reinstall dev deps
        subprocess.run(
            ["uv", "add", "pytest", "pytest-cov", "pytest-asyncio", "--dev"],
            check=True
        )
        logger.warning("Venv recovered: reinstalled pytest plugins (L129)")
```

---

## Testing

```python
class TestRecursiveOvernightSession:
    """Tests for recursive overnight compound engineering."""

    @pytest.mark.fast
    async def test_flume_encoding(self):
        """Verify FLUME encodes journeys to 12D."""

    @pytest.mark.fast
    async def test_quadrature_nexus_merge(self):
        """Verify QuadratureNexus merges trajectories."""

    @pytest.mark.fast
    async def test_recursive_improvement_loop(self):
        """Verify recursion improves improvement mechanism."""

    @pytest.mark.fast
    async def test_surreal_journey_persistence(self):
        """Verify journeys stored in SurrealDB."""

    @pytest.mark.integration
    async def test_1M_iterations(self):
        """Test 1M iteration simulation (abbreviated)."""
```

## Files

| File | Purpose |
|------|---------|
| `src/cohezion/compound/overnight_recursive.py` | Main recursive session manager |
| `src/cohezion/flume/vae_encoder.py` | FLUME VAE encoder (Fluid Latent Understanding - 256D) |
| `src/cohezion/flume/navigator.py` | FLUME trajectory prediction with momentum |
| `src/cohezion/flume/quadrature_nexus.py` | NEW: Quadrature trajectory merging (TBD) |
| `src/cohezion/compound/exp_persistence/journey.py` | SurrealDB journey persistence |
| `src/cohezion/compound/recursive_improver.py` | NEW: Recursive self-improvement engine (TBD) |
| `config/overnight_recursive.yaml` | Session configuration |
| `tests/compound/test_overnight_recursive.py` | Unit tests |

## Key Metrics

| Metric | Description |
|--------|-------------|
| `iteration_count` | Total improvement iterations executed |
| `recursion_depth` | Current recursion level (0-3) |
| `coherence` | Phi score from FLUME encoder |
| `improvement_delta` | Ratio of current/previous performance |
| `novelty` | Distance from previous trajectories |
| `quadrature_phase` | Phase alignment in nexus merge |
