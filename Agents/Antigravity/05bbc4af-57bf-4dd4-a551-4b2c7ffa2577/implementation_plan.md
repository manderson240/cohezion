---
type: antigravity-artifact
session_id: 05bbc4af-57bf-4dd4-a551-4b2c7ffa2577
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.373
  stage: embryo
  cluster: Agents
---

# implementing Code Simplifier Agent

## Goal Description
Create a "Code Simplifier" capability to enforce elegance, simplicity, and efficiency in the codebase. This involves a new Skill (`CODE_SIMPLIFICATION_PRIME`) and an automated agent (`simplify.py`) that uses static analysis (complexity metrics) to identify targets and an LLM to refactor them.

## User Review Required
> [!NOTE]
> The simplifier will target functions with Cyclomatic Complexity > 15 (consistent with `deep_audit.py`).
> It will prioritize "flattening" logic (guard clauses) and removing dead code.

## Proposed Changes

### Skills
#### [NEW] [src/cohezion/skills/code_simplification.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/code_simplification.md)
- Define the "Elegance Protocol": Flattening, Early Return, Composition over Inheritance.

### Scripts
#### [NEW] [scripts/drivers/code_simplifier.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/code_simplifier.py)
- CLI tool that:
    1.  Scans files using `DeepAuditor`.
    2.  Identifies high-complexity functions.
    3.  Uses an LLM (via `cohezion.mcp`) to propose a refactored version.
    4.  Runs tests to verify behavior preservation.

### Enforcement (Persistence)
#### [NEW] [scripts/hooks/check-complexity.sh](file:///home/mike-anderson/dev/cohezion/scripts/hooks/check-complexity.sh)
- Pre-commit hook that uses `DeepAuditor` to block commits with:
    - Files having Cyclomatic Complexity > 50 (Critical).
    - Functions with Score > 25 (Warning).
- *Flexibility principle*: Can be bypassed with `git commit --no-verify` or configured thresholds.

#### [MODIFY] [.pre-commit-config.yaml](file:///home/mike-anderson/dev/cohezion/.pre-commit-config.yaml)
- Register the `check-complexity` hook.

### Resource Guardrails (OOM Prevention)
#### [MODIFY] [src/cohezion/core/resource_monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/core/resource_monitor.py)
- Enhance the existing monitor to:
    - Run as a standalone daemon (`scripts/daemons/resource_guard.py`).
    - **Active Defense**: Kill low-priority processes (e.g., `git diff` workers) if RAM usage > 90%.
    - **Alerting**: Notify user via terminal broadcast.

#### [NEW] [scripts/drivers/resource_guard.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/resource_guard.py)
- The daemon entry point.

### Overnight Mission (Evolutionary Engine)
#### [NEW] [scripts/drivers/evolutionary_driver.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/evolutionary_driver.py)
This is not a loop; it is a **Self-Improvement Spiral**.
- **State**: Tracks `evolution_level` (0-50) and `complexity_threshold` (starts low, increases).
- **The Gateway Protocol**:
    1.  **Scan**: Find the weakest link (highest complexity or lowest coverage).
    2.  **Transform**: Apply `Code Simplifier` or generator to upgrade it.
    3.  **Verify**: Run tests. If pass -> **Compound**: Register improvement as a new baseline (Ratchet).
    4.  **Evolve**: Increase difficulty (e.g., lower max allowed complexity) for the next round.
- **Reporting**:
    - "Evolutionary update" emails every 10 levels.
    - Final report: "Trajectory of Improvement" (Graph of reduced entropy).

### Integration
#### [MODIFY] [scripts/drivers/assess_git_health.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/assess_git_health.py)
- **Scope Expansion**: Transform from a simple checker to a **Communication Engine**.
- **Outputs**:
    - **Presentation Layer**: Generate "Executive Summaries" (Markdown/HTML) suitable for email.
    - **Visualization**: Embed "The Pulse" - A 12D Interactive Radar (D3/Plotly) tracking:
        - *Coherence, Stability, Complexity, Velocity, Coverage, Coupling, etc.*
    - **Interactive**: HTML Output allowing users to rotate/filter the hyper-dimensional state.

### Research & Creativity
#### [NEW] [research/notebooks/12d_visualization_prototype.ipynb](file:///home/mike-anderson/dev/cohezion/research/notebooks/12d_visualization_prototype.ipynb)
- **Goal**: Prototype an intuitive 12D glyph representing "Cohezion Health".
- **Tech**: Plotly (Python) -> HTML export.

## Verification Plan
1.  **Skill Verification**: Create the skill file and verify it follows the template.
2.  **Tool Check**: Run `python scripts/drivers/code_simplifier.py --dry-run` to see proposed simplifications.
3.  **Refactor Test**: Apply it to a known complex file (e.g., `src/cohezion/swarm/agents/base.py`) and inspect the diff.

## Related Vault Notes

- [[cohezion]]
