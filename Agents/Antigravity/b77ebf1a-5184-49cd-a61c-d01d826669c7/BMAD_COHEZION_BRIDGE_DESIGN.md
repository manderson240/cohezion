---
type: antigravity-artifact
session_id: b77ebf1a-5184-49cd-a61c-d01d826669c7
date: 2026-03-04
title: "BMAD-Cohezion Bridge Design"
tags: [agent-output, antigravity, bmad, agent-architecture, bridge-design]
aspect: doer
neural:
  activation: 0.595
  stage: growing
  cluster: Agents
---

# BMAD ↔ Cohezion Bridge Design

_Date: 2026-03-02 | Based on BMAD V6 source review + Cohezion codebase audit_

---

## THE FUNDAMENTAL PARADIGM DIFFERENCE

You were right — BMAD's internal architecture is genuinely sophisticated and self-consistent.

The previous audit's critique of "shallow integration" missed the point because it assumed the wrong execution model:

| Dimension           | BMAD V6                                      | Cohezion                              |
| ------------------- | -------------------------------------------- | ------------------------------------- |
| **Runtime**         | The LLM _IS_ the runtime                     | Python process                        |
| **Execution**       | In-conversation, file-loaded context         | API calls, async tasks                |
| **Config contract** | 17-line `config.yaml`                        | SurrealDB, env vars, YAML             |
| **Workflow engine** | `workflow.xml` — XML tags interpreted by LLM | `CompoundSession`, `TeamOrchestrator` |
| **State**           | LLM session context + `_bmad/_memory/` files | SurrealDB journeys, Redis cache       |
| **Scaling**         | More agents/workflows in `_bmad/`            | More Python workers                   |

**The old bridge (`subprocess.run("python3 cohezion.py")`) was wrong because BMAD workflows don't call external processes — they generate context for the LLM to act on.**

---

## HOW BMAD V6 ACTUALLY WORKS

```
User says "/analyst" in IDE
           ↓
LLM reads _bmad/bmm/agents/analyst.md
           ↓
XML activation: load config.yaml → session vars ({user_name}, {output_folder})
           ↓
User picks menu item → exec="path/to/workflow.md" or workflow="path/to/workflow.yaml"
           ↓
For workflow= items: LLM reads _bmad/core/tasks/workflow.xml (the OS)
      ↓                                              ↓
Load workflow.yaml                    Execute steps: <ask>, <action>, <invoke-workflow>
Load template                                       <template-output> → save to file
      ↓                                              ↓
Output: artifact in _bmad-output/              LLM stays in loop, YOLO or interactive
```

**Key insight: The "bridge" BMAD needs is not a Python API call — it's a CONTEXT INJECTION at the right moment in the workflow.**

---

## THE THREE CORRECT BRIDGE PATTERNS

### Pattern 1: Cohezion as a BMAD `exec` Task

The cleanest native pattern. BMAD agents already support `exec="path/to/file.md"` — you write Cohezion-specific task files that agents reference in their menus.

**Example: Add a "Cohezion Analysis" menu item to analyst.md**

```xml
<item cmd="CA or fuzzy match on cohezion-analysis"
      exec="{project-root}/_bmad/core/tasks/cohezion-analysis.xml">
  [CA] Cohezion Analysis: Run skill selector + swarm analysis on current context
</item>
```

**New file: `_bmad/core/tasks/cohezion-analysis.xml`**

```xml
<task id="cohezion-analysis" name="Cohezion Skill Analysis">
  <objective>Leverage Cohezion skill registry to analyze current project context</objective>
  <flow>
    <step n="1">
      <action>Read {project-root}/src/cohezion/registry/skill_registry.json</action>
      <action>Identify top 5 skills most relevant to current workflow context</action>
      <template-output>Skill Recommendations for this context</template-output>
    </step>
    <step n="2">
      <action>Read {project-root}/src/cohezion/knowledge_graph/KEY_LEARNINGS.md</action>
      <action>Surface learnings relevant to current task domain</action>
      <template-output>Relevant Cohezion Knowledge</template-output>
    </step>
    <step n="3">
      <action>Read {project-root}/src/cohezion/swarm/STRATEGIES.md</action>
      <action>Recommend optimal model routing for this task type</action>
      <template-output>Routing Recommendation</template-output>
    </step>
  </flow>
</task>
```

**Why this works:** It's BMAD-native. No Python. LLM reads Cohezion's own files and surfaces their intelligence in the BMAD session.

---

### Pattern 2: Cohezion Knowledge Injection via `discover_inputs`

BMAD's `workflow.xml` has a `discover_inputs` protocol that intelligently loads files before a workflow runs. **Wire Cohezion's generated outputs as input sources.**

**Example: `_bmad/bmm/workflows/cohezion/dev-with-cohezion/workflow.yaml`**

```yaml
name: "Dev Story with Cohezion Intelligence"
config_source: "{project-root}/_bmad/bmm/config.yaml"
instructions: "{project-root}/_bmad/bmm/workflows/cohezion/dev-with-cohezion/instructions.md"
default_output_file: "{output_folder}/implementation-artifacts/story-{date}.md"

input_file_patterns:
  cohezion_skills:
    whole: "{project-root}/src/cohezion/registry/skill_registry.json"
    load_strategy: FULL_LOAD
  cohezion_learnings:
    whole: "{project-root}/src/cohezion/knowledge_graph/KEY_LEARNINGS.md"
    load_strategy: FULL_LOAD
  cohezion_models:
    whole: "{project-root}/model_registry.json"
    load_strategy: FULL_LOAD
  story:
    whole: "{output_folder}/planning-artifacts/*story*.md"
    load_strategy: SELECTIVE_LOAD
```

**Result:** Every dev story workflow is automatically pre-loaded with Cohezion's current model roster, skill recommendations, and learnings. **Zero Python code needed.**

---

### Pattern 3: Cohezion Python as a BMAD `invoke-task` Target

For cases where Python execution IS needed (run overnight driver, trigger SurrealDB query, etc.), the correct BMAD pattern is an `invoke-task` that calls a markdown task file — which itself contains instructions to run a terminal command.

**New file: `_bmad/core/tasks/run-cohezion-swarm.xml`**

```xml
<task id="run-cohezion-swarm" name="Run Cohezion Swarm">
  <objective>Execute a specific Cohezion swarm task and capture results</objective>
  <params>
    <param name="skill_name">The skill to execute</param>
    <param name="prompt">The task prompt</param>
  </params>
  <flow>
    <step n="1">
      <action>Run terminal: python3 -m cohezion.compound.progressive_api --skill {skill_name} --prompt "{prompt}" --output /tmp/bmad-cohezion-result.json</action>
      <action>Wait for completion</action>
    </step>
    <step n="2">
      <action>Read /tmp/bmad-cohezion-result.json</action>
      <action>Present results to user formatted for current workflow context</action>
    </step>
  </flow>
</task>
```

This makes Python execution BMAD-native — it's an `invoke-task` step within any workflow, not a subprocess bridge.

---

## THE FIVE REAL LEVERS (Revised)

### 🔴 LEVER 1: `_bmad/core/tasks/cohezion-*.xml` — Cohezion Task Library

**Create 5-7 reusable BMAD task files** that surface different Cohezion capabilities:

- `cohezion-skill-selector.xml` — reads `skill_registry.json`, recommends skills
- `cohezion-model-router.xml` — reads `model_registry.json`, recommends model for task
- `cohezion-knowledge-search.xml` — reads `KEY_LEARNINGS.md` + `MISSION_JOURNAL.md`
- `cohezion-journey-summary.xml` — reads last N journey files from `data/journeys/`
- `cohezion-compound-health.xml` — reads last hardware metrics + degradation alerts

Each is ~20 lines of XML. **Any BMAD agent can then add them as menu items.** This is the keystone.

---

### 🔴 LEVER 2: `_bmad/bmm/config.yaml` — Extend the Config Contract

The config is the universal session variable source. Add Cohezion paths:

```yaml
# Add to _bmad/bmm/config.yaml:
cohezion:
  skills_registry: "{project-root}/src/cohezion/registry/skill_registry.json"
  model_registry: "{project-root}/model_registry.json"
  knowledge_graph: "{project-root}/src/cohezion/knowledge_graph"
  output_folder: "{project-root}/_bmad-output"
  swarm_api: "http://localhost:8000" # for when Python API is running
```

Now all BMAD workflows can reference `{cohezion}` variables. All agents see them.

---

### 🟡 LEVER 3: Fix the `agent-manifest.csv` (5-minute fix)

**Lines 29-31 in `_config/agent-manifest.csv` are malformed** — wrong column schema (5 columns instead of 11). This means the Cohezion agents are invisible to the bmad-master orchestrator.

Fix by conforming to the full V6 schema:

```csv
"security-monitor","Sentinel","Security Monitor","🛡️","security scanning, vulnerability detection, threat intelligence","Security Intelligence Engine","Cohezion-powered security monitor that continuously scans the project for vulnerabilities.","Direct and alert-driven. Reports facts, not feelings.","Zero-tolerance for unpatched vulnerabilities. Every finding matters.","bmm","_bmad/bmm/agents/security-monitor.md"
```

---

### 🟡 LEVER 4: `_bmad-output/` as the Cohezion Write Target

Cohezion already writes to Python files, SurrealDB, and logs. **Add an output path that writes to `_bmad-output/` in BMAD-readable format.**

```python
# In compound/executor.py or compound/executor_post_steps.py
from pathlib import Path
import json

def write_bmad_artifact(result: ExecutionResult, output_folder: Path) -> None:
    """Write compound execution result as BMAD-readable artifact."""
    artifact = output_folder / "implementation-artifacts" / f"cohezion-{result.skill_name}-{result.timestamp}.md"
    artifact.write_text(f"""# Cohezion Execution: {result.skill_name}
**Model**: {result.model_used}
**Duration**: {result.duration_ms}ms
**Journey ID**: {result.journey_id}

## Result
{result.content}

## Metrics
- Tokens: {result.token_count}
- Cost: ${result.cost:.4f}
- Quality: {result.quality_score:.2f}
""")
```

BMAD workflows can then read these via `discover_inputs` with pattern `{output_folder}/implementation-artifacts/cohezion-*.md`.

---

### 🟢 LEVER 5: Cohezion BMAD Skills as a New Skill Module

Create `src/cohezion/skills/bmad_bridge/` with skills that are BMAD _workflow generators_ — they take requirements and produce BMAD workflow YAML files, stories, or task XML:

```
bmad_bridge/
  skill_to_bmad_workflow.md    # converts a skill into a BMAD workflow.yaml
  journey_to_bmad_story.md     # converts a Cohezion journey into a BMAD user story
  compound_to_bmad_epic.md     # converts a CompoundSession into a BMAD epic
```

**This is Compound Engineering:** Cohezion's execution feeds BMAD's planning artifacts, which feed Cohezion's next execution.

---

## THE EXECUTION ARCHITECTURE THAT EMERGES

```
┌─────────────────────── BMAD Session (IDE) ──────────────────────┐
│                                                                   │
│  /analyst → menu item "Cohezion Analysis"                        │
│      ↓ exec= _bmad/core/tasks/cohezion-skill-selector.xml        │
│      ↓ reads: skill_registry.json + KEY_LEARNINGS.md             │
│      ↓ surfaces: "For this task, use FLUME_METHODOLOGY + MODEL_ROUTING_PRIME" │
│                                                                   │
│  /dev → workflow= dev-with-cohezion/workflow.yaml                │
│      ↓ discover_inputs: loads model_registry.json, learnings     │
│      ↓ step 3: invoke-task run-cohezion-swarm.xml                │
│      ↓ writes result to: _bmad-output/implementation-artifacts/  │
│                                                                   │
│  /sm → workflow= sprint-planning.yaml                            │
│      ↓ discover_inputs: reads last Cohezion journey summaries    │
│      ↓ sprint velocity informed by actual compound metrics        │
└─────────────────────────────────────────────────────────────────┘
              ↕ _bmad-output/ as shared artifact space ↕
┌─────────────────────── Cohezion Python ─────────────────────────┐
│  overnight_driver.py → compound executor → writes to _bmad-output│
│  skill improvements → skill_registry.json (read by BMAD tasks)  │
│  journey records → journeys/ (read by BMAD sprint workflows)    │
│  model benchmark → model_registry.json (read by BMAD agent init)│
└─────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION ORDER (Start Here)

**15 minutes:**

1. Fix `_config/agent-manifest.csv` lines 29-31 schema
2. Add cohezion block to `_bmad/bmm/config.yaml`

**30 minutes:** 3. Create `_bmad/core/tasks/cohezion-skill-selector.xml` (20 lines) 4. Create `_bmad/core/tasks/cohezion-model-router.xml` (20 lines) 5. Add these as menu items to `_bmad/bmm/agents/dev.md` and `architect.md`

**1 hour:** 6. Create `_bmad/bmm/workflows/cohezion/dev-with-cohezion/workflow.yaml` with `input_file_patterns` 7. Add `write_bmad_artifact()` to `compound/executor_post_steps.py`

**2-4 hours (compound multiplier):** 8. Create `src/cohezion/skills/bmad_bridge/` module 9. Wire Cohezion journey summaries to agile sprint velocity

---

## KEY PRINCIPLE FOR ALL OF THIS

> **BMAD's LLM context IS the integration layer.**  
> Don't call Python from BMAD. Put Python outputs where BMAD can read them.  
> Don't call BMAD from Python. Write BMAD-formatted artifacts from Python.  
> The \_bmad-output/ folder is the event bus. The LLM session is the orchestrator.

## Related Vault Notes

- [[agent-architecture]]
- [[multi-agent-systems]]
- [[workflow-orchestration]]
