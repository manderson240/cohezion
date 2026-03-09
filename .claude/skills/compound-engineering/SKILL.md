---
name: compound-engineering
description: Compound AI orchestration methodology for multi-agent coordination,
  local model optimization, and hallucination mitigation within the Cohezion
  ecosystem. Use when implementing compound features, debugging coherence drift,
  setting up model routing, running skill refinement loops, or when user
  mentions "compound engineering", "skill refinement", "orchestration loop",
  or "compound impact".
metadata:
  author: Cohezion
  version: "1.0"
  mcp-server: cohezion-bridge
compatibility: Python 3.13+, Ollama (local models), SurrealDB. Requires uv
  package manager and the Cohezion ecosystem.
---

# Compound Engineering

Unified methodology for building compound AI systems where every feature
makes future features easier through skill refinement loops.

## Instructions

### Step 1: Plan the Compound Loop

Before implementing, create a gated implementation plan:

1. Identify the feature's compound impact (how does it make future tasks easier?)
2. Check model availability: `ollama list`
3. Consult truth anchors for hardware vitals: `get_truth_anchors()`
4. Define at least 3 future hooks

### Step 2: Execute with the 11-Step Pipeline

The CompoundExecutor runs this pipeline for each request:

```
Request -> RequestAlignmentAnalyzer (coherence check)
        -> SkillSelector (find relevant skills)
        -> PlanExecutor (tactical plan)
        -> ExecutionOrchestrator (execute)
        -> GlobalMetricsAggregator (record metrics)
        -> DegradationDetector (check thresholds)
        -> JourneyTracker (12D position)
        -> RetrospectionEngine (extract learnings)
        -> SkillRefiner (update skill)
        -> SkillConsensusVoter (validate)
        -> Result
```

Entry point: `src/cohezion/compound/executor.py`

### Step 3: Check Alignment Before Execution

```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(request_state, available_skills, agent_context)
if alignment.coherence < 0.5:  # HIHO threshold
    # Escalate or decompose into smaller requests
    pass
```

### Step 4: Offload Menial Tasks

Route supportive tasks (docstrings, formatting, READMEs) to local SLMs:
- Use `offload_task` or `BaseAgent.offload_to_local`
- Target: phi3:mini for verification, qwen3-coder for code generation

### Step 5: Extract Wisdom

After execution, the RetrospectionEngine:
1. Extracts learnings from the execution
2. Flags anomalies (coherence collapse, drift)
3. Updates the skill definition via SkillRefiner
4. Validates changes via SkillConsensusVoter

### Step 6: Verify Results

```bash
uv run pytest tests/compound/ -v           # Compound module tests
uv run pytest tests/ -q                    # Full suite regression
```

## Key Concepts

Consult `references/key-concepts.md` for detailed explanations of:
- Unified Configuration patterns
- MCP Bridge Topology
- Registry-Driven Swarm architecture
- Defensive Grounding with Truth Anchors
- Offload Parity principles

## Common Issues

### Low Coherence Score
Request alignment analyzer returns coherence below 0.5 (HIHO threshold).
**Fix:** Decompose the request into smaller, more focused sub-tasks.

### Singleton Pollution in Tests
Compound tests fail in full suite but pass individually.
**Fix:** Check `tests/conftest.py` for FLUME VAE and RL policy resets.

### Model Unavailable
Ollama model not loaded when executor needs it.
**Fix:** Run `ollama list` to verify, then `ollama pull <model>` if missing.
