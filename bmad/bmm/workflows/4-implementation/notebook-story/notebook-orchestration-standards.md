# Notebook Story Orchestration Standards

## Overview

This document defines the standards for documenting agent orchestration in notebook stories. All notebook stories must include metadata tracking which agents, tools, and models were used during execution.

## Required Metadata

Every notebook story MUST include the following metadata:

### 1. Markdown Header Cell (First Cell)

The first cell of every notebook story must be a markdown cell with the following structure:

```markdown
# Story Notebook: [Story ID] - [Title]

## Agent Orchestration Record

- **Story ID**: [Epic.Story format, e.g., 0.7]
- **Story Title**: [Descriptive title]
- **Primary Agent**: [Agent name from agent-manifest.csv]
- **Agent Model**: [Model name and version]
- **Execution Date**: [ISO 8601 format: YYYY-MM-DD]
- **Status**: [drafted | in-progress | completed | verified]

### Tools & Skills Used

- `[module.path.to.tool]` - [Brief description]
- `[module.path.to.skill]` - [Brief description]

### Orchestration Pattern

[Description of the orchestration pattern demonstrated, e.g., "Loop with Threshold", "HRM Router Verification", "Sequential Pipeline", "Challenger/Solver"]

### Purpose

[1-2 sentence description of what this notebook demonstrates or verifies]
```

### 2. JSON Metadata (Notebook Metadata)

The notebook's metadata section must include an `agent_orchestration` object:

```json
{
  "metadata": {
    "agent_orchestration": {
      "story_id": "0.7",
      "story_title": "Sample Orchestration",
      "primary_agent": "bmad-master",
      "agent_model": "gemini-2.0-flash-exp",
      "execution_date": "2025-11-20",
      "status": "completed",
      "tools_used": [
        "bmad.skills.text_processing.summarize",
        "bmad.core.router.route_task"
      ],
      "orchestration_pattern": "loop_with_threshold",
      "multi_agent": false,
      "collaborating_agents": []
    }
  }
}
```

## Field Definitions

### Primary Agent

The primary agent is the agent from `agent-manifest.csv` that orchestrated or executed the notebook. Valid values:

- `bmad-master` - Master orchestrator
- `dev` - Developer agent (Amelia)
- `architect` - System architect (Winston)
- `analyst` - Business analyst (Mary)
- `pm` - Product manager (John)
- `tea` - Test architect (Murat)
- Any other agent name from agent-manifest.csv

### Agent Model

The specific LLM model used. Format: `[provider]-[model]-[version]`

Examples:
- `gemini-2.0-flash-exp`
- `gemini-1.5-pro`
- `gpt-4-turbo`
- `claude-3.5-sonnet`
- `local-llama-3.1-70b`

### Tools & Skills Used

Full Python import path to any tools, skills, or utilities invoked in the notebook.

Format: `module.submodule.function_or_class`

Examples:
- `bmad.skills.text_processing.summarize`
- `bmad.core.router.route_task`
- `bmad.core.hrm.hierarchical_resource_manager`
- `bmad.skills.code_generation.generate_function`

### Orchestration Pattern

The type of orchestration pattern demonstrated. Common patterns:

- `loop_with_threshold` - Iterative processing with conditional logic
- `sequential_pipeline` - Linear sequence of operations
- `tiered_routing` - HRM-based model selection
- `challenger_solver` - Iterative improvement through critique
- `parallel_execution` - Concurrent task execution
- `contingency_handling` - Error recovery and fallback logic
- `mle_star_experiment` - ML experimentation workflow

### Status Values

- `drafted` - Notebook created but not yet executed
- `in-progress` - Currently being developed/executed
- `completed` - Execution complete, results documented
- `verified` - Tested and validated
- `archived` - Superseded by newer version

## Multi-Agent Orchestration

For notebooks involving multiple agents:

1. Set `multi_agent: true` in JSON metadata
2. List all participating agents in `collaborating_agents` array
3. In the markdown header, add a "Collaborating Agents" section:

```markdown
### Collaborating Agents

1. **bmad-master** (Orchestrator) - Coordinates workflow
2. **architect** (Designer) - Designs system architecture
3. **dev** (Implementer) - Executes implementation
```

## Tool Tracking Best Practices

1. **Be Specific**: Use full import paths, not just function names
2. **Document Purpose**: Add brief description of what each tool does in context
3. **Track Dependencies**: If a tool calls other tools, document the chain
4. **Version Awareness**: If tool behavior changes, note version in comments

## Integration with Dev Agent Record

Notebook stories should reference or complement the Dev Agent Record in markdown story files:

- Notebooks demonstrate **execution** and **verification**
- Markdown stories document **planning** and **acceptance criteria**
- Cross-reference between them using Story ID

## Validation

Use the notebook metadata validator to ensure compliance:

```bash
python bmad/bmm/utils/notebook_metadata_validator.py --path docs/stories/notebooks/
```

The validator checks:
- ✅ Markdown header cell exists and is first cell
- ✅ All required fields are present
- ✅ Agent names match agent-manifest.csv
- ✅ Tools/skills paths are valid Python imports
- ✅ JSON metadata matches markdown header
- ✅ Dates are in ISO 8601 format

## Examples

See:
- [notebook-story-template.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/notebook-story/notebook-story-template.ipynb) - Template with all fields
- [0-7-sample-orchestration.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/docs/stories/notebooks/0-7-sample-orchestration.ipynb) - Loop with threshold pattern
- [0-8-hrm-verification.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/docs/stories/notebooks/0-8-hrm-verification.ipynb) - HRM router verification

## References

- [Agent Manifest](file:///g:/My%20Drive/agentic_development/cohezion/bmad/_cfg/agent-manifest.csv) - All available agents
- [Dev Story Template](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/create-story/template.md) - Markdown story format
- [Cohezion Method](file:///g:/My%20Drive/agentic_development/cohezion/docs/cohezion-method.md) - Core principles
