# Cohezion: Compound Engineering Framework for Agentic AI

A production-ready framework for orchestrating multi-agent compound engineering with automatic error recovery, trajectory-based learning, and intelligent skill selection.

## Overview

Cohezion implements a complete compound engineering pipeline for agentic AI systems, featuring:

- **Intelligent Skill Selection**: Vault-guided skill recommendations based on historical performance
- **Multi-Agent Coordination**: Distributed task execution with dependency management
- **Automatic Error Recovery**: Feedback loop with intelligent retry strategies
- **Journey Tracking**: 12D FLUME trajectory monitoring for quality analysis
- **Thread-Safe Operations**: File locking for safe concurrent resource access
- **Comprehensive Testing**: 3,146 tests with 99.1% pass rate

## System Architecture

```
CompoundFeedbackLoop (anomaly-driven re-execution)
├── CompoundExecutor (task execution engine)
│   ├── SkillSelector (vault-guided selection)
│   └── TokenEfficientClient (caching + batching)
├── InflectionDetector (quality monitoring)
├── JourneyTracker (12D trajectory recording)
├── TeamExecutor (multi-agent coordination)
└── SkillRefiner (continuous learning)
```

## Features

### 1. File Locking (Task 23.5)
Thread-safe resource sharing with atomic read-modify-write operations
- Configurable timeouts and retry logic
- Support for SkillRegistry, CapabilityUsageTracker
- 14 comprehensive tests

### 2. Experience-Guided Skill Selection (Task 23.6)
Intelligent skill recommendation using vault performance patterns
- Vault pattern analysis for skill performance
- Composite scoring (coherence 50%, efficiency 30%, success 20%)
- Dynamic skill ranking based on execution context
- 29 integration tests

### 3. Multi-Agent Team Execution (Task 23.7)
Distributed task execution with dependency management
- Topological sorting for correct execution order
- Vault-guided skill selection per agent task
- Compound scoring for team performance
- Support for alternative skill selection
- 30 comprehensive tests

### 4. Compound Feedback Loop (Task 23.8)
Automatic re-execution with intelligent retry strategies
- 4-level escalation: adjusted parameters → alternative skill → model escalation
- Anomaly detection integration
- Comprehensive retry history tracking
- Learning persistence from retry trajectories
- 25 tests covering all retry scenarios

### 5. Journey Tracker (Task 23.9)
12D FLUME trajectory monitoring for quality analysis
- Deterministic SHA-256 embeddings (2048D)
- Holographic projection (2048D → 12D)
- Operation-specific modulation profiles
- Phi score computation (coherence*0.5 + smoothness*0.3 + convergence*0.2)
- 35 comprehensive tests

## Installation

### Requirements
- Python 3.13+
- `uv` package manager
- `ruff` for code formatting
- SurrealDB (optional, for persistence)

### Setup

```bash
# Clone repository
git clone https://github.com/manderson240/cohezion.git
cd cohezion

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -q
```

## Quick Start

### Basic Task Execution

```python
from cohezion.compound import CompoundExecutor, ExecutorFactory
from cohezion.core.mcp_client import MCPClient

# Initialize
mcp_client = MCPClient(config={...})
executor = ExecutorFactory.create(mcp_client)

# Execute task
result = executor.execute_task(
    task_description="Generate creative ideas",
    skill_name="generator",
    operation_type="generate",
    execute_fn=my_task_function,
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Metrics: {result.metrics}")
```

### Feedback Loop with Auto-Recovery

```python
from cohezion.compound import CompoundFeedbackLoopFactory

# Create loop with retry support
loop = CompoundFeedbackLoopFactory.create(
    executor=executor,
    max_retries=3,
    critical_threshold=0.5,
    enable_learning=True,
)

# Execute with automatic re-execution on failures
result = asyncio.run(loop.execute_with_feedback(
    task_description="Generate ideas",
    skill_name="generator",
    operation_type="generate",
    execute_fn=my_task,
    available_alternative_skills=["analyzer", "transformer"],
))

print(f"Retries: {result.total_retries}")
print(f"Success: {result.success}")
```

### Journey Tracking

```python
from cohezion.compound import JourneyTrackerFactory

tracker = JourneyTrackerFactory.create(seed=42)

# Track execution as 12D trajectory point
point = tracker.track_execution(
    execution_result=result,
    task_description="Generate ideas",
    operation_type="generate",
)

print(f"12D Coordinates: {point.dimensions}")
print(f"Quality Score: {point.metadata['phi_score']:.2f}")

# Analyze trajectory
points = [tracker.track_execution(...) for _ in range(10)]
quality = tracker.compute_trajectory_quality(points)
print(f"Mean Coherence: {quality['mean_coherence']:.2f}")
```

### Multi-Agent Team Execution

```python
from cohezion.compound import TeamExecutor, AgentTask

executor1 = ExecutorFactory.create(mcp_client)
executor2 = ExecutorFactory.create(mcp_client)

team = TeamExecutor(
    agents={"agent1": executor1, "agent2": executor2},
    mcp_client=mcp_client,
)

tasks = [
    AgentTask(
        task_id="analyze",
        agent_id="agent1",
        description="Analyze data",
        operation_type="analyze",
        available_skills=["analyzer", "reviewer"],
    ),
    AgentTask(
        task_id="synthesize",
        agent_id="agent2",
        description="Synthesize results",
        operation_type="generate",
        dependencies=["analyze"],
        available_skills=["synthesizer", "writer"],
    ),
]

result = asyncio.run(team.execute_team(tasks))
print(f"Team Success: {result.success}")
print(f"Compound Score: {result.compound_score:.2f}")
```

## API Endpoints

### Metrics
- `GET /metrics/tokens` - Token efficiency metrics
- `GET /metrics/compound` - Compound execution metrics

### Execution
- `POST /swarm/execute` - Execute team plan

### Skills
- `POST /skills/execute` - Execute skill with guidance
- `GET /skills/list` - List available skills
- `GET /skills/suggest` - Get skill recommendations

## Testing

### Run All Tests
```bash
uv run pytest tests/compound/ -q
```

### Run Specific Test Suite
```bash
uv run pytest tests/compound/test_feedback_loop.py -v
uv run pytest tests/compound/test_journey_tracker.py -v
```

### Test Coverage
```bash
uv run pytest tests/compound/ --cov=src/cohezion/compound --cov-report=html
```

## Documentation

- **CLAUDE.md**: Root orchestration instructions
- **.agent/CONSTITUTION.md**: Core ethics and values
- **.agent/CAPABILITY_MAP.md**: Verified capabilities by domain
- **docs/**: Additional documentation

## Repository Structure

```
cohezion/
├── src/cohezion/
│   ├── compound/          # Compound engineering system
│   │   ├── executor.py    # Core executor
│   │   ├── skill_selector.py
│   │   ├── team_executor.py
│   │   ├── feedback_loop.py
│   │   ├── journey_tracker.py
│   │   └── __init__.py
│   ├── core/              # Core infrastructure
│   ├── cache/             # Caching systems
│   ├── security/          # Security and guardrails
│   └── skills/            # Skill definitions (132 PRIME files)
├── tests/
│   ├── compound/          # Compound system tests (275 tests)
│   ├── core/              # Core infrastructure tests
│   └── cache/             # Cache tests
├── scripts/
│   ├── codebase_refinement.py
│   ├── health_assessment.py
│   └── repo_cleanup_plan.py
├── .claude/
│   ├── agents/            # Custom agents (7 agents)
│   └── skills/            # PRIME skill definitions
├── pyproject.toml         # Project configuration
├── .pre-commit-config.yaml
└── README.md              # This file
```

## Performance

### Baseline Metrics (Phase 1)
- **Token Efficiency**: 85 tokens/sec
- **Cache Hit Rate**: 24.5%
- **Compound Score**: 0.82 (on 0-1 scale)

### Optimization Goals (Phase 1)
- **Target**: 155 tok/sec (1.81× improvement)
- **DynamicConcurrencyGate**: +45% throughput
- **PersistentCache**: +15% throughput
- **LRU Eviction**: Adaptive memory management

## Development Workflow

### Making Changes
1. Create feature branch from `main`
2. Make changes following code style
3. Run tests: `uv run pytest tests/ -q`
4. Update documentation
5. Create pull request

### Code Style
- **Formatter**: `ruff format`
- **Linter**: `ruff check --fix`
- **Type Checking**: `mypy` (optional)

### Pre-commit Hooks
- Automatic formatting with `ruff`
- Lint checking
- Type validation

## Known Limitations

1. Rust FlumePhysics unavailable - using Python fallback for journey tracking
2. SurrealDB persistence optional - JSON fallback available
3. Local models only - Ollama required for inference
4. Hardware-specific optimizations for AMD Ryzen AI MAX+

## Future Work

1. **Journey Persistence**: SurrealDB integration for trajectory storage
2. **Experience-Guided Execution**: Use past journeys to inform future decisions
3. **Harder RL Training**: Adversarial perturbations and curriculum learning
4. **Production Deployment**: Cloud Run integration with cost optimization

## Contributing

Contributions welcome! Please:
1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Submit pull request

## License

See LICENSE file for details.

## Contact & Support

For issues, questions, or contributions:
- **GitHub**: https://github.com/manderson240/cohezion
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Citation

If you use Cohezion in your research, please cite:
```bibtex
@software{cohezion2026,
  title={Cohezion: Compound Engineering Framework for Agentic AI},
  author={Anderson, Mike},
  year={2026},
  url={https://github.com/manderson240/cohezion}
}
```

---

**Status**: ✅ Production Ready (Sessions 40-55 Complete)
**Last Updated**: February 15, 2026
**Version**: 1.0.0-phase-18
**Latest**: Phase 18 GitHub Migration Complete, GitHub Flow established
