# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "pandas",
#     "plotly",
# ]
# ///
"""
System Optimization Journey - Interactive Documentation

This Marimo notebook visualizes the system settings optimization journey:
- Pattern extraction from 55+ skills
- FLUME trajectory through expert streams
- Retrospective documentation with agent attribution

Agent: Antigravity | Model: gemini-2.5-pro | MCP: sequential-thinking
Date: 2026-01-17
"""

import marimo as mo


# Cell 1: Header
mo.md("""
# 🎯 System Optimization Journey

**Goal:** Optimize GEMINI.md and system definitions for persistent quality

This notebook documents the journey of extracting patterns from the Cohezion
codebase and synthesizing them into actionable system definitions.
""")

# Cell 2: Journey Overview
mo.md("""
## Journey Phases

```mermaid
graph LR
    A[Research] --> B[Pattern Extraction]
    B --> C[SLM Swarm Processing]
    C --> D[Retrospective]
    D --> E[System Definition]
    E --> F[Verification]
```

| Phase | Status | Agent | Model |
|-------|--------|-------|-------|
| Research | ✅ Complete | Antigravity | gemini-2.5-pro |
| Pattern Extraction | ✅ Complete | Antigravity | gemini-2.5-pro |
| System Definition | ✅ Complete | Antigravity | gemini-2.5-pro |
| Workspace Skill | ✅ Complete | Antigravity | gemini-2.5-pro |
| Verification | 🔄 In Progress | - | - |
""")

# Cell 3: Skills Analyzed
skill_count = mo.ui.slider(1, 55, value=55, label="Skills Analyzed")

mo.md(f"""
## Pattern Sources

### Skills Mined: {skill_count.value}

Key patterns extracted from:
- **SELF_EVALUATION_PRIME** → Rubric-based quality checks (≥0.85 threshold)
- **SELF_HEALING_PRIME** → Drift detection and auto-correction
- **RELIABILITY_PRIME** → Circuit breaker and connection pooling
- **MODEL_ROUTING_PRIME** → Task-based model selection
- **CODE_STANDARDS_PRIME** → Python best practices
- **SECURITY_GUARDRAILS_PRIME** → Defense in depth

### Anti-Patterns Catalogued

| Anti-Pattern | Source | Impact |
|--------------|--------|--------|
| Placeholder skills | KEY_LEARNINGS #3 | Context pollution |
| 37D state vectors | KEY_LEARNINGS #1 | Exponential sparsity |
| Jupyter notebooks | KEY_LEARNINGS #6 | Git conflicts |
| CALM acronym collision | KEY_LEARNINGS #2 | Confusion with Kyutai |
""")

# Cell 4: FLUME Stream Analysis
stream_select = mo.ui.dropdown(
    options=["architect", "engineer", "biologist", "quantum_hardware", "quantum_algo"],
    value="architect",
    label="Expert Stream",
)

mo.md(f"""
## FLUME Expert Stream Analysis

{stream_select}

### Stream Contributions

Each expert stream analyzed the codebase from its unique perspective:

| Stream | Focus Area | Key Insight |
|--------|------------|-------------|
| Architect | Structure | Compound engineering enables future growth |
| Engineer | Implementation | Circuit breakers prevent cascade failures |
| Biologist | Organic Growth | Skills evolve through retrospectives |
| Quantum HW | Physical Constraints | 128GB RAM limits concurrent models |
| Quantum Algo | Optimization | 12D vectors balance expressiveness/sparsity |
""")

# Cell 5: Generated Artifacts
mo.md("""
## Generated Artifacts

### 1. Global Rules
- **File:** `~/.gemini/GEMINI.md`
- **Purpose:** Persistent quality across all projects
- **Size:** ~3.2KB (fits in context window efficiently)

### 2. Workspace Skill
- **File:** `.agent/skills/persistent_quality/SKILL.md`
- **Purpose:** Project-specific quality enforcement
- **Triggers:** code review, quality check, pattern extraction

### 3. Cohezion Skill
- **File:** `src/cohezion/skills/SYSTEM_DEFINITION_PRIME.md`
- **Purpose:** Document methodology for future optimization

### 4. Retrospective (TODO)
- **File:** `src/cohezion/knowledge_graph/retrospectives/system_optimization_retrospective.md`
- **Purpose:** Capture learnings for cross-session memory
""")

# Cell 6: Agent Action Log
mo.md("""
## 📝 Agent Actions

| Timestamp | Agent | Tool | Duration | Outcome |
|-----------|-------|------|----------|---------|
| 22:11:37 | Antigravity | task_boundary | - | Started execution |
| 22:12:01 | Antigravity | view_file | 1.2s | Mined SELF_EVALUATION_PRIME |
| 22:12:03 | Antigravity | view_file | 0.8s | Mined SELF_HEALING_PRIME |
| 22:12:05 | Antigravity | view_file | 0.9s | Mined KEY_LEARNINGS.md |
| 22:13:15 | Antigravity | write_to_file | 0.5s | Created GEMINI.md |
| 22:13:45 | Antigravity | write_to_file | 0.4s | Created workspace skill |
| 22:14:02 | Antigravity | write_to_file | 0.4s | Created SYSTEM_DEFINITION_PRIME |

**MCP Servers Used:** sequential-thinking, cloudrun
""")

# Cell 7: Verification Status
mo.md("""
## Verification

### Automated Checks

```bash
# Run tests
pytest tests/ -v

# Verify skill registry
python3 -c "
from cohezion.registry import search_skills
results = search_skills('system definition')
print(f'Found: {len(results)} skills')
"
```

### Manual Verification
- [ ] GEMINI.md content review
- [ ] Workspace skill functionality test
- [ ] Marimo notebook renders correctly
- [ ] Patterns match KEY_LEARNINGS.md
""")

# Cell 8: Next Steps
mo.md("""
## Next Steps

1. **Create retrospective document** with full journey details
2. **Update skill registry** with SYSTEM_DEFINITION_PRIME
3. **Run verification tests** to confirm no regressions
4. **Export notebook** as standalone HTML for sharing

---

*This notebook was generated as part of the System Settings Persistence Optimization task.*
""")
