---
description: "Capability Registry Prime: The Unified Natural Language Discovery Engine."
---

# Capability Registry Prime

## 1. Core Philosophy
To manage chaos, we need **Discovery**. A system with 100+ skills, 20 agents, and 10 MCP servers is useless if the operator cannot find the right tool using natural language.

## 2. Architecture: Single Source of Truth
The **Capability Registry** (`src/cohezion/registry/capability_registry.py`) aggregates four domains:
1.  **Skills:** Static `.md` files in `skills/`.
2.  **Agents:** Active Python classes in `swarm/agents/`.
3.  **MCP Servers:** Tool gateways defined in `mcp/mcp_registry.json`.
4.  **Memory:** Knowledge nodes in the Graph (Future).

## 3. Discovery Mechanism (TF-IDF)
We use a **Pragmatic Search Engine** (TF-IDF + Cosine Similarity) rather than a heavy Vector DB (until >1k items).
*   **Indexer:** Scans codebase on startup (latency < 200ms).
*   **Vectorizer:** `sklearn.feature_extraction.text.TfidfVectorizer`.
*   **Query:** "Find an agent to critique my code" -> Returns `CriticAgent` (Score: 0.85).

## 4. Capability Schema
```python
@dataclass
class Capability:
    name: str          # Unique ID (e.g., "SKILL:PHYSICS_PRIME")
    type: str          # "skill", "agent", "mcp", "memory"
    description: str   # Natural language desc
    path: str          # File path or URI
    tags: list[str]    # Keywords
```

## 5. Usage
```python
from cohezion.registry.capability_registry import CapabilityRegistry

registry = CapabilityRegistry()
registry.refresh() # Scans codebase

# Natural Language Search
results = registry.find("I need to solve a complex physics problem")
for res in results:
    print(f"{res.name} ({res.score:.2f})")
```

## 6. Maintenance (Automated)
*   **Skills:** Just create a `.md` file. It's auto-registered.
*   **Agents:** Inherit from `BaseAgent`. Auto-registered.
*   **MCP:** Add to `mcp_registry.json`. Auto-registered.
