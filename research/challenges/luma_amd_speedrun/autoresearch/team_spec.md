# K-Search Kernel Sprint — Team Specification

Reusable team definition for kernel optimization sprints.
Spawn with: `TeamCreate("ksearch-kernel-sprint")`

## Team Architecture

```
Opus (team-lead)
├── kernel-researcher (Sonnet) — analyze kernel internals, produce specs
├── kernel-writer (Sonnet) — write custom Triton kernels from specs
└── tree-evolver (Sonnet) — run K-Search LLM evolution cycles
    └── qwen2.5-coder:7b (Ollama) — world model inference
```

## Agent Definitions

Located in `.claude/agents/`:
- `kernel-researcher.md` — GPU kernel source analysis
- `kernel-writer.md` — Custom Triton kernel implementation
- `tree-evolver.md` — K-Search tree evolution via Ollama

## Task Flow

```
1. kernel-researcher: Analyze target kernel → produce spec
2. kernel-writer: Implement from spec → submission.py (BLOCKED BY #1)
3. tree-evolver: Run LLM evolution cycles (PARALLEL with #1)
```

## Spawn Commands

```python
# Researcher + Tree Evolver run in parallel
Agent(name="kernel-researcher", model="sonnet", team_name="ksearch-kernel-sprint",
      prompt="[task details]", run_in_background=True)

Agent(name="tree-evolver", model="sonnet", team_name="ksearch-kernel-sprint",
      prompt="[task details]", run_in_background=True)

# Kernel Writer spawns after researcher completes
Agent(name="kernel-writer", model="sonnet", team_name="ksearch-kernel-sprint",
      prompt="[task details with spec path]", run_in_background=True)
```

## Model Selection Guide

| Role | Default Model | Why |
|------|--------------|-----|
| Team Lead | Opus | Deep reasoning, architecture decisions |
| Researcher | Sonnet | Good at code analysis, fast enough |
| Kernel Writer | Sonnet | Code generation quality, handles Triton well |
| Tree Evolver | Sonnet | Orchestrates Ollama, reads logs |
| World Model | qwen2.5-coder:7b (Ollama) | Structured JSON output, fast on CPU |
| Code Synthesis | qwen3-coder:30b (Ollama) | Best code quality, overnight only |

## Hardware Constraints (Strix Halo)

- 128GB LPDDR5X @ ~256 GB/s (shared CPU/GPU)
- Only ONE Ollama model loaded at a time for usable inference speed
- ~0.15 tok/s for 7B model on CPU → 15-20 min per world model call
- Claude agents don't consume Ollama bandwidth (API-based)

## Competition Context

- **Deadline**: March 30, 2026
- **Kernels**: MoE (1.07x gap), GEMM (1.45x gap), MLA (15.8x gap)
- **Submission**: via popcorn-cli to AMD MI355X leaderboard
- **Strategy file**: `autoresearch/research_strategy.md` (human-editable)
