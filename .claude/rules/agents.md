---
paths:
  - "src/cohezion/agents/**"
  - "src/cohezion/swarm/agents/**"
---

# Agent Development Rules

- All agents MUST inherit from `cohezion.agents.base.BaseAgent`
- Agent classes must define `name`, `description`, and `async def execute()` at minimum
- Use `cohezion.reliability.get_circuit()` for any external calls (Ollama, SurrealDB, HTTP)
- Every external call must have an explicit timeout (never rely on defaults)
- Agent docstrings are extracted by `capability_registry.py` for TF-IDF indexing — keep first line a clear one-sentence purpose description
- Agents in `swarm/agents/` are swarm-specialized (adversarial, bug audit, modularization); agents in `agents/` are general-purpose
- No quarter-on-string stubs: every agent method must have real implementation or raise `NotImplementedError` with a reason
- Respect global Ollama concurrency limit of 4 — use semaphores when calling local models
