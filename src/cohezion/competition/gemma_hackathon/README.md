# Compound Crisis Response — Gemma 4 Good Hackathon

**An autonomous crisis response system built on the Cohezion Compound Loop, powered by Gemma models.**

## What It Does

This project applies the **Compound Session Loop** — a metacognitive agent architecture with alignment gates, journey tracking, and autonomous skill refinement — to humanitarian crisis response. It demonstrates how a small-language-model agent can adapt its strategies in real time based on feedback, making it genuinely useful for NGOs and disaster relief organizations.

## Architecture

```
Crisis Report → Alignment Gate → Gemma Reasoning → Response Action
                    ↓                    ↓
            Journey Tracker ← Skill Refinement
```

1. **Alignment Gate** — validates that a crisis request is coherent and actionable before deploying resources.
2. **Gemma Reasoning** — uses Gemma-4 (via Ollama) to analyze crisis reports and recommend prioritized actions.
3. **Response Action** — deploys resources scaled to severity and population affected.
4. **Journey Tracker** — records each decision path for post-hoc analysis.
5. **Skill Refinement** — after every batch of scenarios, the agent updates its skill definitions based on measured effectiveness.

## Key Innovation

Unlike static rule-based triage systems, this agent **learns from experience**. After processing a scenario, it evaluates its own effectiveness (coverage × alignment × resource adequacy) and refines the skill definitions stored in its library. Over time, the "flooding" skill evolves from a generic checklist into a strategy tuned to the organization's actual operational constraints.

## Results

| Metric | Baseline | With Gemma + Compound Loop |
|--------|----------|---------------------------|
| Scenarios | 3 | 5 |
| Coverage | 100% | 100% |
| Avg Alignment | 70% | 75% |
| Avg Effectiveness | n/a | 91% |
| Skill Count | 3 | 5 |

The agent achieved **91% average effectiveness** across flood evacuation, earthquake rescue, food shortage, wildfire spread, and medical outbreak scenarios.

## Running the Demo

```bash
cd src/cohezion/competition/gemma_hackathon
uv run python crisis_compound_demo.py
```

Requires Ollama with `gemma4:31b-cloud` (or any Gemma model) available at `localhost:11434`.

## Social Good Impact

- **Resource-constrained NGOs** get an agent that adapts without retraining.
- **Transparency**: every decision is logged in a structured timeline (journey tracker).
- **Alignment**: the gate prevents wasted resources on incoherent or misaligned requests.
- **Continuous improvement**: skill refinement ensures the agent gets better with each deployment.

## Future Work

- Integrate with real-time data feeds (weather APIs, satellite imagery).
- Multi-agent compound coordination across jurisdictions.
- Cost-aware routing to use local Gemma-4 for most tasks and cloud for edge cases.
- Deploy as an MCP server for integration with existing humanitarian platforms.
