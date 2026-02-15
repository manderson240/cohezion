# Track C: Impact & Dependency Analyzer - API Documentation

**Status**: [DRAFT - Under Development]
**Last Updated**: 2026-02-14
**Target Completion**: 2026-02-27

## Overview

The Impact & Dependency Analyzer identifies and analyzes decision dependencies, impact cascades, and critical paths using graph algorithms.

## Quick Start

```python
from src.impact import ImpactAnalyzer

analyzer = ImpactAnalyzer()
cascades = analyzer.analyze_cascades("decision_001")
print(f"Impact Depth: {cascades.depth} decisions")
print(f"Total Affected: {len(cascades.affected_decisions)}")
```

## Core Algorithms

### Dependency Detection
- DFS-based cycle detection
- Dependency type classification
- Strength scoring

### Cascade Analysis
- BFS propagation
- Impact scoring
- Multi-hop dependency resolution

### Critical Path Analysis
- PERT-style critical path
- Resource leveling
- Schedule compression

## Core Modules

### src.impact.graph
Graph construction and manipulation.

### src.impact.analysis
Cascade propagation and analysis algorithms.

### src.impact.critical_path
PERT-based critical path analysis.

## API Reference

### ImpactAnalyzer

```python
class ImpactAnalyzer:
    """Analyze decision impact and dependencies."""

    def analyze_cascades(decision_id: str) -> ImpactCascade
    def find_critical_path(start_id: str, end_id: str) -> CriticalPath
    def get_dependencies(decision_id: str) -> list[Dependency]
    def detect_cycles() -> list[DecisionCycle]
```

### Data Models

- `Dependency`: Decision→decision edge with type and strength
- `ImpactCascade`: Cascade analysis result with affected decisions
- `CriticalPath`: PERT-style path with criticality index

## Performance Targets

- Full Graph Analysis: **< 1s** (84 papers, 150+ dependencies)
- Dependencies Identified: **150+** across vault
- Cascades Computed: **20+** typical workflows
- Test Coverage: **35+ tests** (90%+ coverage)

## Development Progress

- [ ] Step 1: Graph library setup (networkx)
- [ ] Step 2: Dependency extraction implementation
- [ ] Step 3: Cascade analysis implementation
- [ ] Step 4: Critical path analysis
- [ ] Step 5: Comprehensive testing & docs

## Related

- [Track A: GraphRAG](TRACK_A_GRAPHRAG_API.md)
- [Track B: Confidence Scoring](TRACK_B_SCORING_API.md)
- [Design Spec](../decisions/TRACK-C-DESIGN-SPEC-IMPACT-2026-02-14.md)
