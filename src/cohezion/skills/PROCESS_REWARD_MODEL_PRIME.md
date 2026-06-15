---
name: process-reward-model
description: Step-level dense reward scoring for CompoundExecutor pipeline steps using Lemonade :13305 (arXiv:2509.02547)
version: "1.0.0"
tags: [compound, loop-engineering, rl, prm, reward, lemonade, step-scoring]
---

# Process Reward Model (PRM) — Step-Level Dense Reward

## Purpose

Closes the gap identified by arXiv:2509.02547 (Agentic RL Survey): MakerCheckerVerifier gives one
final outcome verdict. PRMs score each intermediate step of the compound loop, yielding a dense
reward signal that tells SkillRefiner WHICH step caused quality loss.

## Module

`src/cohezion/compound/process_reward_model.py`

## Key Components

### StepVerdict
Per-step quality verdict:
- `step_id`: pipeline step number ("3", "3.5", "7")
- `step_name`: human label ("execute_fn", "maker_checker", "skill_refiner")
- `score`: 0.0–1.0 (normalized from 0–10 integer from LLM)
- `is_pass`: True when score >= 0.6
- `reason`: raw text from scoring model
- `latency_seconds`: wall-clock time for HTTP call

### StepScoreRecord
Execution-level collection:
- `dense_reward`: mean score across all steps (0.0–1.0)
- `pass_rate`: fraction of steps where is_pass=True
- `min_step_score`: lowest step score (weakest link)

### ProcessRewardModel

```python
from cohezion.compound.process_reward_model import build_process_reward_model

prm = build_process_reward_model()  # wired to :13305, Gemma-4-E4B

# In CompoundExecutor pipeline:
record_id = prm.begin_execution(task_description)
verdict = prm.record_step(record_id, "3", "execute_fn", output, "Produce task output")
record = prm.finalize(record_id)
metrics.update(prm.to_metrics_dict(record))
# → prm_dense_reward, prm_step_count, prm_pass_rate, prm_min_step_score
```

## Integration Points

- **CompoundExecutor Step 3**: scores `execute_fn` output
- **CompoundExecutor Step 3.5**: scores `maker_checker` verdict  
- **ExecutorFactory**: auto-creates `build_process_reward_model()` and injects it
- **metrics dict**: `prm_dense_reward`, `prm_step_count`, `prm_pass_rate`, `prm_min_step_score`

## Scoring Model

Uses **Gemma-4-E4B-it-GGUF** at Lemonade :13305 — always present in Strix Halo catalog,
ctx=16384 (N3-safe), fast iGPU.

System prompt: "Rate quality 0-10. Reply with one integer only."
Max tokens: 8 (integer response, no over-generation)

## Non-Blocking Contract

All errors return `StepVerdict(score=0.5, is_pass=True, reason="prm_error: ...")`.
The PRM never raises, never blocks the main execution path.

## Design Rationale

- `score >= 0.6` threshold (not 0.5): ensures "neutral" doesn't automatically pass
- `urllib.request` (not `aiohttp`): simpler mock in tests via `@patch("...urllib.request.urlopen")`
- `max_tokens=8`: prevents verbose explanations from overwriting the integer score
- `temperature=0.0`: deterministic scoring

## Source

arXiv:2509.02547 — "The Landscape of Agentic Reinforcement Learning for LLMs: A Survey"
Identified step-level scoring (PRM) as the largest gap vs. outcome-level verification (ORM).
