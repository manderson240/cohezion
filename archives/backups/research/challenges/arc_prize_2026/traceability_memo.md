# ARC Prize 2026: Traceability Matrix

## 1. System Overviews
The ARC Prize 2026 track is governed by two key traceability systems within the Cohezion ecosystem:
1. **Bidirectional Knowledge Graph**: Links documentation (`.md`) to code implementation (`.py`).
2. **Plan Lifecycle Graph**: Links project plans to individual tasks and their completion status in SurrealDB.

## 2. Documentation ↔ Code Linkages (Local Vault)
The following linkages have been registered in the Cohezion Knowledge Vault:

| Documentation | Code Implementation | Section |
| :--- | :--- | :--- |
| `arc_deep_synthesis_plan.md` | `arc_gym_wrapper.py` | ARC-AGI-3 Environment Wrapper |
| `arc_deep_synthesis_plan.md` | `arc_jepa.py` | JEPA World Model & Encoder |
| `arc_deep_synthesis_plan.md` | `arc_topology_navigation.py` | Topological Navigation & Search |
| `arc_deep_synthesis_plan.md` | `arc_bioelectric.py` | Bioelectric Pattern Discovery |
| `arc_deep_synthesis_plan.md` | `arc_cosmogony_synthesizer.py` | Cosmogonic Program Synthesis |
| `arc_deep_synthesis_plan.md` | `src/cohezion/physics/cosmogony.py` | Cosmogony Foundation |

## 3. Plan ↔ Task Linkages (SurrealDB)
The `plan:arc_deep_synthesis_plan` has been registered in SurrealDB (port 8001) with the following tasks:

| Step | Task Title | Status |
| :--- | :--- | :--- |
| 1.1 | Synthesizer Core (`arc_cosmogony_synthesizer.py`) | PENDING |
| 1.2 | Primitive Operations Library (`arc_dsl.py`) | PENDING |
| 1.3 | ARC-AGI-2 Evaluation Pipeline (`evaluate_cosmogony.py`) | PENDING |
| 1.4 | Paper Track Adaptation | PENDING |

## 4. Verification Command
To verify the traceability graph for this plan, use:
```bash
# Query SurrealDB for task status
curl -u root:root -X POST -H "NS: cohezion" -H "DB: traceability" \
     -d "SELECT * FROM task WHERE <-plan_has_task<-plan.slug CONTAINS 'arc_deep_synthesis_plan';" \
     http://localhost:8001/sql
```
