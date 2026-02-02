# Cohezion: A Self-Evolving Autonomous Agentic Platform

**Compound Engineering System with Universe Simulation v2.0**

> "Every feature makes every future feature easier."

## Overview

Cohezion is an autonomous agentic platform that implements:
- **Universe Simulation Engine** - 12D/512D manifold tracking for every task
- **Reward System** - XP, achievements, streaks, and capability unlocks
- **Meta-Programming** - Generate agents from YAML specifications
- **Self-Improvement** - Evolution orchestrator that detects and fixes patterns
- **System Monitoring** - Ouroboros flight recorder with reflex cycles
- **Test Generation** - Mycelium autonomous test synthesis

## Architecture

See [COHEZION_LAYOUT.md](COHEZION_LAYOUT.md) for:
- System architecture diagram
- 12D/512D manifold visualization
- Data flow diagrams
- XP tiers and capabilities
- CLI command map
- Compound engineering principles

## Quick Start

```bash
# Install
uv pip install -e .

# Journey management
uv run python -m cohezion journey start "Research quantum computing"

# Rewards and progress
uv run python -m cohezion rewards status

# Generate agents from YAML
uv run python -m cohezion generate list
uv run python -m cohezion generate agent --spec=specs/research_agent.yaml

# Self-improvement
uv run python -m cohezion evolve --detect_patterns --dry-run

# System monitoring
uv run python -m cohezion ouroboros status

# Test generation
uv run python -m cohezion mycelium grow src/cohezion/meta/generator.py

# Workflows
uv run python -m cohezion simulate --scenario=high_load --duration=1h
```

## Core Concepts

### 12D/512D Manifold (Universe Engine)

Every task becomes a journey through the dual-state manifold:

- **512D Latent** - Semantic intent, reasoning, meaning ("Soul")
- **12D Axiomatic** - Physical state, measurable, observable ("Body")
- **HIHO Coherence** - Target 0.5 for maximum stability

### Reward System

| Tier | XP Required | Capabilities |
|------|-------------|--------------|
| Novice | 0 | Basic access |
| Apprentice | 1,000 | phi3:mini, gemma |
| Journeyman | 2,500 | deepseek:7b, auto-deploy safe |
| Expert | 5,000 | deepseek:70b, full auto-deploy |
| Master | 10,000 | Meta-programming, generate agents |
| Architect | 25,000 | Modify constitution |

### Compound Engineering

Every feature compounds:

1. **Universe Engine** → Enables experience replay
2. **Rewards** → Motivates quality work
3. **Meta-Generator** → Creates 50 agents from 50 lines of YAML
4. **Evolution** → System improves itself continuously
5. **Ouroboros** → Monitors and triggers improvements
6. **Mycelium** → Tests verify quality

## Directory Structure

```
cohezion/
├── src/cohezion/
│   ├── __main__.py              # CLI entry point
│   ├── universe/                # 12D/512D manifold
│   ├── rewards/                 # XP, achievements
│   ├── meta/                    # Generator, evolution
│   ├── swarm/agents/            # 50+ agents
│   ├── system/ouroboros_recorder.py
│   ├── mycelium/shadow_scripter.py
│   └── ...
├── workflows/                   # YAML templates
├── scripts/                     # Migration tools
└── tests/shadow/                # Auto-generated tests
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `journey` | Manage universe journeys |
| `rewards` | View XP, achievements |
| `generate` | Create agents from YAML |
| `evolve` | Self-improvement mode |
| `ouroboros` | System monitoring |
| `mycelium` | Test generation |
| `interactive` | Interactive shell |

## Documentation

- [COHEZION_LAYOUT.md](COHEZION_LAYOUT.md) - Full architecture visualization
- [HANDOFF_UNIVERSE_V2.md](HANDOFF_UNIVERSE_V2.md) - Development handoff
- [docs/research/](docs/research/) - Research documentation

## License

Apache 2.0
