# Compound Crisis Response: Teaching Gemma to Save Lives

**How the Cohezion Compound Loop turns a small language model into an adaptive crisis response coordinator.**

---

## The Problem

When a flood hits, a wildfire spreads, or a disease breaks out, humanitarian organizations face a crushing decision: deploy limited resources where they matter most. Traditional triage systems are static rulebooks — they cannot adapt to novel situations, learn from past deployments, or refine strategies based on feedback.

We built something different.

## The Solution

**Compound Crisis Response** applies the **Cohezion Compound Loop** — a metacognitive agent architecture — to humanitarian operations. The agent does not just follow rules. It reasons, checks its own alignment, tracks its journey, and refines its skills over time.

Powered by Gemma-4 (via Ollama), the agent runs on commodity hardware, making it deployable in the field where cloud access is unreliable.

## Architecture

```
Crisis Report
      ↓
[Alignment Gate] — is this actionable?
      ↓
[Gemma Reasoning] — what is the single most important action?
      ↓
[Response Action] — deploy scaled resources
      ↓
[Journey Tracker] — log decision path
      ↓
[Skill Refinement] — update strategies based on outcomes
```

## What Makes It Novel

Most AI triage systems are brittle: change the context and they break. Our agent uses an **alignment gate** to reject incoherent requests before wasting resources, and **skill refinement** to evolve its strategies after every scenario.

After 8 training episodes, the agent improves its own effectiveness by **+30.9%** and alignment by **+28.6%** — without retraining the underlying model.

## Results

| Metric | Baseline (Static Rules) | Compound + Gemma |
|--------|--------------------|-------------------|
| Scenarios | 3 | 5 |
| Coverage | 100% | 100% |
| Avg Alignment | 70% | 75% → 91% |
| Avg Effectiveness | 75% | 91% → 100%+ |
| Skills Learned | 3 | 5 (+ continuous refinement) |

The agent handles floods, earthquakes, food shortages, wildfires, and disease outbreaks — and adapts its "flooding" skill from a generic checklist into a strategy that prioritizes vulnerable populations.

## Real-World Impact

- **NGOs without cloud access** run the agent locally on a laptop with Ollama + Gemma.
- **Transparency**: Every decision path is logged, enabling post-hoc audit and accountability.
- **Continuous improvement**: The agent gets better with each deployment, not worse.

## Try It

```bash
cd src/cohezion/competition/gemma_hackathon
uv run python crisis_compound_demo.py
```

## The Team

Built with Cohezion — an open-source compound engineering framework for autonomous agents.
