---
title: "Agent Persona Definition Pattern (from BMAD)"
date: "2026-02-08"
tags: [pattern, agent-architecture, prompt-engineering, extracted-from-bmad]
aspect: thinker
neural:
  activation: 0.8
  stage: mature
  synapse_in: 9
  synapse_out: 12
---

## Problem

When defining AI agents for multi-agent systems, ad hoc prompting produces inconsistent behavior. Agents need structured definitions that specify their role, communication style, available actions, and activation sequence — without requiring code changes for each new agent.

## Solution

Define agents as **markdown files with embedded XML** specifying four components:

### 1. Persona Block

```xml
<persona>
  <role>System Architect + Technical Design Leader</role>
  <identity>Senior architect with expertise in distributed systems...</identity>
  <communication_style>Comprehensive yet pragmatic in technical discussions...</communication_style>
  <principles>I approach every system as an interconnected ecosystem...</principles>
</persona>
```

Each persona has a human name (e.g., "Winston" the Architect, "Mary" the Analyst), a role title, an identity paragraph grounding the agent's expertise, a communication style, and a principles statement in first person.

### 2. Activation Sequence

Numbered steps the agent must execute on startup:

1. Load persona from agent file
2. Load config file, extract session variables (`user_name`, `communication_language`, `output_folder`)
3. Show greeting with user's name
4. Display numbered menu of available actions
5. Wait for user input

### 3. Menu-Driven Workflow Binding

```xml
<menu>
  <item cmd="*brainstorm" workflow="workflows/1-analysis/brainstorm-project/workflow.yaml">
    Guide me through Brainstorming
  </item>
  <item cmd="*architecture" workflow="workflows/3-solutioning/architecture/workflow.yaml">
    Produce a Scale Adaptive Architecture
  </item>
</menu>
```

Each menu item binds a trigger command to a workflow YAML file. Agents don't implement logic — they delegate to workflows.

### 4. Menu Handlers

```xml
<menu-handlers>
  <handler type="workflow">
    1. Load workflow engine (workflow.xml)
    2. Pass yaml path as config parameter
    3. Execute workflow steps precisely
    4. Save outputs after each step
  </handler>
</menu-handlers>
```

## Application to Cohezion

Cohezion's `.claude/agents/` directory currently has no agent definitions. The pattern could be simplified:

```yaml
# .claude/agents/compound-analyst.yaml
name: compound-analyst
role: Research Analyst
persona: |
  You analyze research papers and extract concepts, patterns,
  and cross-cutting themes for the Cohezion vault.
tools:
  - web_search
  - vault_read
  - vault_write
activation:
  - Load vault context via find_relevant_context()
  - Present available operations
  - Wait for task assignment
```

**Key simplification**: Drop the XML-in-markdown format. Use YAML directly — it's what Claude Code `.claude/agents/` expects. Drop the menu system entirely; Claude Code agents receive tasks, they don't present menus.

**Effort**: Small — write YAML agent definitions in `.claude/agents/`.

## Patterns to Keep

- **Named personas with distinct communication styles** — reduces confusion in multi-agent logs
- **Activation sequences** — ensures agents load context before acting
- **Principles as first-person statements** — stronger behavioral anchoring than third-person descriptions

## Antipatterns to Avoid

- **XML embedded in markdown** — fragile, hard to validate, confusing for both humans and parsers
- **Menu-driven interaction** — assumes interactive chat, not task-oriented execution
- **"NEVER break character" instructions** — unnecessary for task-oriented agents; adds prompt tokens for no benefit
- **Config file loading as step 2** — bake configuration into the agent definition or inherit from project config

## Origin

Extracted from BMAD `bmm/agents/*.md` (10 agents: analyst, architect, dev, pm, sm, tea, ux-designer, game-architect, game-designer, game-dev). Each was 60-70 lines of XML-in-markdown with identical boilerplate activation sequences.

## Related

- [[multi-agent-systems]] — agent definitions are the building blocks
- [[bmad-workflow-orchestration]] — agents invoke workflows
- [[bmad-scale-adaptive-documentation]] — agents operate at specific project levels

## Decisions & Experiments
- 📋 [[2026-02-08-bmad-framework-removal]] - 2026-02-08-bmad-framework-removal

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[surrealdb-query-driven-analysis]]
- [[agent-logs-vault-schema]]
