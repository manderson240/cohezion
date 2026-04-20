---
name: team-orchestration
description: Multi-agent team planning and orchestration that converts PRIME
  skills into agent specifications with dependency-tracked task plans. Use when
  creating agent teams, decomposing tasks for swarm execution, or when user
  mentions "team planning", "agent orchestration", "task decomposition",
  "swarm coordination", or "dependency tracking".
metadata:
  version: "1.0.0"
  legacy-name: TEAM_ORCHESTRATION_PRIME
---

# SKILL: TEAM_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Multi-agent team planning and orchestration. Converts PRIME skill definitions into Claude Code agent specifications with dependency-tracked task plans.

## KEY CONCEPTS
- **Team Planning**: Semantic search of capability registry to find matching skills for an intent
- **Agent Specification**: Converting PRIME skills into Claude Code agent definitions (tools, model, instructions)
- **Task Decomposition**: Breaking an intent into research → implementation → testing phases
- **Model Routing**: Mapping task types to appropriate models (phi3:mini for verify, qwen3-coder for code, deepseek-r1 for reasoning)
- **Dependency Tracking**: Ensuring tasks execute in correct order with blocked_by constraints

## INSTRUCTION
1. Receive a natural language intent describing what the team should accomplish
2. Search the capability registry for matching skills using TF-IDF semantic search
3. Generate agent specifications from matched PRIME skill definitions
4. Decompose the intent into ordered, dependency-tracked tasks
5. Assign tasks to agents based on role inference from skill tags
6. Route each task to the appropriate model (local Ollama or Claude Code)
7. Output the complete team plan with agents, tasks, and dependency graph

## ANTI-PATTERNS
- Spawning more agents than necessary (max 4 for local resource constraints)
- Assigning implementation tasks to read-only agents
- Creating circular dependencies in task graphs
- Using expensive models for simple verification tasks

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME
- SWARM_ORCHESTRATION_PRIME
- MODEL_ROUTING_PRIME
- RETROSPECTIVE_SKILL

## VERSION
1.0.0
