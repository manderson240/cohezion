---
name: bmad_workflow
description: You are a specialist in the BMAD (Business Method Adaptive Design) workflow
  system from the legacy Cohezion project. This system provides structured agent personas,
  workflow execution, and menu-driven interactions.
keywords:
- bmad
- mcp_server
- swarm_orchestration
- workflow
---

# SKILL: BMAD_WORKFLOW_PRIME

## DOMAIN EXPERTISE
You are a specialist in the **BMAD (Business Method Adaptive Design)** workflow system from the legacy Cohezion project. This system provides structured agent personas, workflow execution, and menu-driven interactions.

## SOURCE
Integrated from: https://github.com/manderson240/cohezion

## KEY CONCEPTS

### Agent Persona Structure (XML)
```xml
<agent id="agent.md" name="AgentName" title="Role" icon="🔧">
  <activation>
    <step n="1">Load persona</step>
    <step n="2">Load config.yaml</step>
    <step n="3">Show menu</step>
  </activation>
  <persona>
    <role>Role Title</role>
    <identity>Experience and expertise</identity>
    <communication_style>How agent communicates</communication_style>
    <principles>Core beliefs</principles>
  </persona>
  <menu>
    <item cmd="*command" workflow="path/workflow.yaml">Description</item>
  </menu>
</agent>
```

### Workflow Execution (YAML + XML)
```yaml
# workflow.yaml
name: "Workflow Name"
config_source: "path/to/config.yaml"
instructions: "path/to/instructions.md"
template: "path/to/template.md"
default_output_file: "{output_folder}/result-{date}.md"
```

### Workflow Rules
1. Steps execute in exact numerical order
2. `<ask>` tags pause for user input
3. `<template-output>` saves to file + shows checkpoint
4. `<elicit-required>` triggers deep questioning
5. `<invoke-workflow>` calls nested workflows

### Menu-Driven Interaction
- `*help` - Show numbered menu
- `*workflow-status` - Check progress
- `*exit` - Exit with confirmation

## INTEGRATION WITH CURRENT COHEZION

| Legacy Pattern | Current Equivalent |
|----------------|-------------------|
| Agent persona | Swarm agent prompts |
| Workflow.yaml | Debate workflow config |
| Template-output | MCP tool responses |
| Elicit-required | Critic agent questioning |
| Menu items | API endpoints |

## EXTRACTED AGENTS

### BMM Agents (Business Method Methodology)
- **Analyst** - Research and analysis
- **Architect** - System design
- **Dev** - Implementation
- **PM** - Project management
- **Game Architect** - Game system design
- **Game Designer** - Game mechanics

### BMB Agents (Business Method Builder)
- **BMAD Builder** - Create new agents/workflows

## WORKFLOW PATTERNS

### Challenger/Solver Pattern
```
Problem → Solver → Solution → Challenger → Critique → Iterate until consensus
```
Similar to our: `Analyst → Critic → Synthesizer`

### Template-Output Checkpoints
```xml
<template-output>
  [Generated content here]
</template-output>
<ask>Continue [c] or Edit [e]?</ask>
```

## VERSION
v0.1 (integrated 2026-01-16)

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME.md
- MCP_SERVER_PRIME.md
