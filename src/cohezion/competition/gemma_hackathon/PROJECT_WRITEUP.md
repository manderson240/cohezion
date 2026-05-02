# Compound Crisis Response: An Autonomous Agent for Humanitarian Operations

**Gemma 4 Good Hackathon — Global Resilience Track**

## 30-Second Pitch

When a flood hits or a wildfire spreads, NGOs waste precious hours deciding where to send limited resources. Compound Crisis Response is an autonomous coordination agent that uses metacognitive alignment gates and continuous skill refinement to adapt crisis strategies in real time — running entirely offline on commodity hardware.

## Problem

Humanitarian crisis response is broken:
- **Static playbooks** cannot adapt to novel disaster types
- **Cloud-dependent AI** fails in the field where connectivity is unreliable
- **Opaque decisions** erode trust with field teams
- **No learning loop** — the same mistakes repeat across deployments

## Solution: The Compound Loop

Instead of hardcoded rules, our agent uses a metacognitive control architecture:

```
Crisis Report → Alignment Gate → Gemma-4 Reasoning → Response Action
                    ↓                        ↓
          Journey Tracker ← Skill Refinement
```

### 1. Alignment Gate
Validates incoming reports before deploying resources. Incoherent or misaligned requests are blocked, preventing wasted effort.

### 2. Gemma-4 Reasoning
Uses Gemma-4B instruction-tuned model for on-device inference. No cloud calls needed. Falls back to fast heuristic simulation when GPU is unavailable.

### 3. Response Action
Deploys resources scaled to severity and population affected, with full reasoning trace.

### 4. Journey Tracker
Every decision is logged with: task signature, reasoning chain, resources deployed, and outcome effectiveness. This creates an auditable decision history.

### 5. Skill Refinement
After each deployment batch, the agent evaluates its own effectiveness and updates skill definitions. The "flooding" skill evolves from generic rules to strategies that prioritize vulnerable populations, based on measured outcomes.

## Results

| Metric | Baseline (Static Rules) | Compound + Gemma |
|--------|------------------------|-----------------|
| Scenarios handled | 3 | 5 |
| Coverage | 100% | 100% |
| Avg Alignment | 70% | 75% |
| Avg Effectiveness | 75% | 91% |
| Skill improvements | 0 | 15 refinements over 8 episodes |

The agent achieves **91% average effectiveness** across floods, earthquakes, food shortages, wildfires, and disease outbreaks — and improves its own strategies over time.

## Why Gemma 4

- **Local inference**: Runs on a laptop with Ollama, no internet required
- **Apache 2.0 license**: Deployable in any field environment without legal friction
- **Function calling**: Native tool-use enables integration with existing humanitarian systems
- **Multilingual**: Supports crisis zones where local languages are critical

## Technical Architecture

- **Language**: Python 3.11+
- **Inference**: `transformers` pipeline with conditional GPU/CPU fallback
- **Skill storage**: JSON experience vault (hot-swappable, no retraining)
- **Testing**: pytest with auto-generated mycelium coverage tests
- **Failure recovery**: Ouroboros anomaly detection + self-healing patches
- **Deployment**: Single-file Kaggle notebook or local `uv run`

## Open Source

All code is available at: `github.com/manderson240/cohezion`
- MIT licensed
- Includes Compound Loop framework, journey tracker, and skill refinement pipeline
- Kaggle notebook: `kaggle.com/code/manderson240/gemma-compound-crisis-response`

## Demo

The Kaggle notebook runs end-to-end in < 30 seconds on CPU, or < 10 seconds on GPU with real Gemma inference. It outputs:
1. Scenario-by-scenario response breakdown
2. Effectiveness metrics per deployment
3. Skill refinement progress over 8 learning episodes
4. Final adapted skill library

## Impact

- **Field-ready**: Offline-capable, runs on NGO laptops
- **Transparent**: Every decision is auditable through the journey tracker
- **Self-improving**: Gets better with each deployment
- **Trustworthy**: Alignment gate prevents misaligned resource allocation

## Team

Built with Cohezion — an open-source compound engineering framework for autonomous agents.
