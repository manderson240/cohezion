---
paths:
  - "src/cohezion/swarm/**"
---

# Swarm Orchestration Rules

- KISS principle: if simple one-pass logic works, do not use a multi-agent swarm
- All swarm operations must be observable — expose states and confidence levels before taking action
- Use idempotency keys for significant actions (Deterministic Responsibility)
- Route complex problems through Expert Domain Lattice: Architect, Engineer, Biologist, Quantum HW, Quantum Algo
- `smart_router.py` and `model_manager.py` are the central routing/model lifecycle modules
- Respect global Ollama concurrency limit of 4 — `dynamic_model_router.py` must enforce this
- Prefer local Ollama models over cloud API calls to stay within cost guardrails
- Democratic debates (`democratic_debate.py`, `glass_box_debate.py`) must log all agent votes and reasoning for transparency
