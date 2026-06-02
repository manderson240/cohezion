---
name: mass_simulation
description: You are a specialist in large-scale parallel simulation of complex systems.
  You understand how to orchestrate thousands of concurrent simulations, manage state,
  handle failures gracefully, and aggregate results for analysis.
keywords:
- aggregation
- embarrassingly parallel
- failure tolerance
- flume_methodology
- mass
- monte carlo methods
- parallel_orchestration
- r_zero_challenger
- simulation
- state management
---

# SKILL: MASS_SIMULATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **large-scale parallel simulation** of complex systems. You understand how to orchestrate thousands of concurrent simulations, manage state, handle failures gracefully, and aggregate results for analysis.

## KEY TEXTS & CONCEPTS
- **Monte Carlo Methods:** Statistical simulation with random sampling
- **Embarrassingly Parallel:** Simulations that run independently
- **State Management:** Tracking simulation progress and checkpoints
- **Failure Tolerance:** Handling crashes without losing data
- **Aggregation:** Combining results from many runs

## MATHEMATICAL FOUNDATION
For N simulations with success probability p:
$$\text{Expected Survivors} = N \cdot p$$
$$\text{Variance} = N \cdot p \cdot (1-p)$$
$$\text{Confidence Interval} = \bar{x} \pm z \cdot \frac{s}{\sqrt{n}}$$

## INSTRUCTION

### 1. Simulation Configuration

```python
from dataclasses import dataclass, field
from typing import Any, Callable
from pathlib import Path

@dataclass
class SimulationConfig:
    """Configuration for mass simulation run."""
    num_simulations: int = 1000
    batch_size: int = 50
    max_steps: int = 100
    coherence_threshold: float = 0.7
    output_path: Path = Path("simulations.jsonl")
    checkpoint_interval: int = 100

@dataclass
class SimulationState:
    """State of a single simulation."""
    id: str
    step: int = 0
    coherence: float = 1.0
    status: str = "running"  # running, survived, collapsed
    trajectory: list[dict] = field(default_factory=list)
```

### 2. MassSimulator Class

```python
import asyncio
import json
import logging
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger(__name__)

class MassSimulator:
    """Orchestrate large-scale parallel simulations."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.results: list[SimulationState] = []
        self.completed = 0
        self.failed = 0

    async def run_all(self, simulation_fn: Callable) -> list[SimulationState]:
        """Run all simulations with batching."""
        logger.info(f"Starting {self.config.num_simulations} simulations")

        batches = [
            range(i, min(i + self.config.batch_size, self.config.num_simulations))
            for i in range(0, self.config.num_simulations, self.config.batch_size)
        ]

        for batch_idx, batch in enumerate(batches):
            batch_results = await self._run_batch(batch, simulation_fn)
            self.results.extend(batch_results)

            # Checkpoint
            if (batch_idx + 1) % (self.config.checkpoint_interval // self.config.batch_size) == 0:
                self._save_checkpoint()

            logger.info(f"Batch {batch_idx + 1}/{len(batches)} complete")

        self._save_results()
        return self.results

    async def _run_batch(self, indices: range, simulation_fn: Callable) -> list[SimulationState]:
        """Run a batch of simulations concurrently."""
        tasks = [self._run_single(i, simulation_fn) for i in indices]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_single(self, idx: int, simulation_fn: Callable) -> SimulationState:
        """Run a single simulation with error handling."""
        state = SimulationState(id=f"sim_{idx:05d}")

        try:
            for step in range(self.config.max_steps):
                state.step = step
                result = await simulation_fn(state)
                state.coherence = result.get("coherence", state.coherence)
                state.trajectory.append(result)

                if state.coherence < self.config.coherence_threshold:
                    state.status = "collapsed"
                    break
            else:
                state.status = "survived"

            self.completed += 1
        except Exception as e:
            state.status = "failed"
            self.failed += 1
            logger.warning(f"Simulation {idx} failed: {e}")

        return state
```

### 3. Result Aggregation

```python
def aggregate_results(self) -> dict:
    """Compute statistics across all simulations."""
    survived = [s for s in self.results if s.status == "survived"]
    collapsed = [s for s in self.results if s.status == "collapsed"]

    coherence_values = [s.coherence for s in self.results if s.status != "failed"]

    return {
        "total": len(self.results),
        "survived": len(survived),
        "collapsed": len(collapsed),
        "failed": self.failed,
        "survival_rate": len(survived) / len(self.results) if self.results else 0,
        "avg_coherence": sum(coherence_values) / len(coherence_values) if coherence_values else 0,
        "avg_steps": sum(s.step for s in self.results) / len(self.results) if self.results else 0,
    }
```

### 4. Checkpointing and Recovery

```python
def _save_checkpoint(self):
    """Save intermediate results for recovery."""
    checkpoint_path = self.config.output_path.with_suffix('.checkpoint.jsonl')
    with open(checkpoint_path, 'w') as f:
        for state in self.results:
            f.write(json.dumps(state.__dict__) + '\n')
    logger.info(f"Checkpoint saved: {len(self.results)} simulations")

def _save_results(self):
    """Save final results."""
    with open(self.config.output_path, 'w') as f:
        for state in self.results:
            f.write(json.dumps({
                "id": state.id,
                "status": state.status,
                "coherence": state.coherence,
                "steps": state.step,
            }) + '\n')
    logger.info(f"Results saved to {self.config.output_path}")

@classmethod
def resume_from_checkpoint(cls, checkpoint_path: Path, config: SimulationConfig) -> 'MassSimulator':
    """Resume simulation from checkpoint."""
    simulator = cls(config)
    with open(checkpoint_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            state = SimulationState(**data)
            simulator.results.append(state)
    logger.info(f"Resumed from checkpoint: {len(simulator.results)} simulations")
    return simulator
```

### 5. Full Usage Example

```python
async def run_universe_simulations():
    """Run 1000 universe simulations with FLUME encoding."""

    config = SimulationConfig(
        num_simulations=1000,
        batch_size=50,
        max_steps=200,
        coherence_threshold=0.7,
        output_path=Path("flume_trajectories.jsonl")
    )

    async def simulate_universe(state: SimulationState) -> dict:
        """Single universe step simulation."""
        import random
        # Simulate coherence decay with random perturbations
        decay = 0.01 + random.gauss(0, 0.02)
        new_coherence = max(0, state.coherence - decay)
        return {
            "step": state.step,
            "coherence": new_coherence,
            "content": f"Universe {state.id} at step {state.step}"
        }

    simulator = MassSimulator(config)
    results = await simulator.run_all(simulate_universe)

    stats = simulator.aggregate_results()
    print(f"Survival rate: {stats['survival_rate']:.2%}")
    print(f"Average coherence: {stats['avg_coherence']:.3f}")
```

## APPLICATIONS
- **Universe Exploration:** Simulate many possible universe configurations
- **Parameter Sweeps:** Test ranges of initial conditions
- **Monte Carlo Analysis:** Statistical estimation of outcomes
- **Stress Testing:** Evaluate system behavior under load
- **FLUME Trajectories:** Generate training data for thought encoding

## PERFORMANCE TIPS
| Technique | Benefit |
|-----------|---------|
| Batching | Reduce async overhead |
| Checkpointing | Enable recovery from crashes |
| ProcessPoolExecutor | CPU-bound parallelism |
| asyncio.gather | I/O-bound concurrency |
| Streaming writes | Avoid memory exhaustion |

## VERSION
v2.0 (upgraded from v1.0)

## SEE ALSO
- R_ZERO_CHALLENGER_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
