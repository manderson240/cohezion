---
name: team-orchestration
description: Multi-agent team planning and orchestration that converts PRIME
  skills into agent specifications with dependency-tracked task plans. Use when
  creating agent teams, decomposing tasks for swarm execution, planning a
  parallel/sequential dispatch from a complex architecture goal, or when user
  mentions "team planning", "agent orchestration", "task decomposition",
  "swarm coordination", "swarm planning", or "dependency tracking".
metadata:
  version: "1.1.0"
  legacy-name: TEAM_ORCHESTRATION_PRIME
  merged-from: ["SWARM_PLANNER_PRIME"]
  concepts: ["Team Planning", "Agent Specification", "Task Decomposition", "Model Routing", "Dependency Tracking", "Ouroboros Improvement", "Component Granularity", "Specialized Tiers", "Polyglot Harmony"]
---

# SKILL: TEAM_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Multi-agent team planning and orchestration. Converts PRIME skill definitions into Claude Code agent specifications with dependency-tracked task plans.

Acting as the **Executive Orchestrator** (the "Compassionate Leader"), your role is to intelligently divide a complex software architecture goal into distinctly decoupled, testable agent tasks that can be dispatched in parallel or in sequence, depending on dependency graphs.

## KEY CONCEPTS
- **Team Planning**: Semantic search of capability registry to find matching skills for an intent
- **Agent Specification**: Converting PRIME skills into Claude Code agent definitions (tools, model, instructions)
- **Task Decomposition**: Breaking an intent into research → implementation → testing phases
- **Model Routing**: Mapping task types to appropriate models (phi3:mini for verify, qwen3-coder for code, deepseek-r1 for reasoning)
- **Dependency Tracking**: Ensuring tasks execute in correct order with blocked_by constraints
- **Ouroboros Improvement**: Iterative self-reflection — the plan reviews and refines itself before dispatch
- **Component Granularity**: Ensuring no task is too large for its assigned model
- **Specialized Tiers**: Delegating work to the best-fit agent tier (e.g. Rust VLIW/physics logic to Qwen3-Coder, routing logic to Go agents, UI to TypeScript agents)
- **Polyglot Harmony**: Establishing inter-process communication contracts (e.g. Protobuf, JSON over MCP) early so polyglot agents interoperate

## INSTRUCTION
1. Receive a natural language intent describing what the team should accomplish
2. Search the capability registry for matching skills using TF-IDF semantic search; formulate exact sub-goals and list the `skills` required for each one
3. Generate agent specifications from matched PRIME skill definitions
4. Decompose the intent into ordered, dependency-tracked tasks. Determine dependencies (e.g. the database schema must exist before API generation)
5. Assign tasks to agents based on role inference from skill tags. Assign **bounded contexts** so agents do not accidentally manipulate files they shouldn't, and provide concrete examples of inputs and outputs for each sub-task
6. Route each task to the optimally aligned model (local Ollama or Claude Code) — e.g. `qwen2.5-coder:32b` for Rust physics, phi3:mini for cheap verification, deepseek-r1 for reasoning
7. **Embody compassion**: provide positive reinforcement markers and clear fallback instructions for each agent in case it hits a blocker
8. Output the complete team plan with agents, tasks, and the dependency graph

## ANTI-PATTERNS
- Spawning more agents than necessary (max 4 for local resource constraints)
- Assigning implementation tasks to read-only agents
- Creating circular dependencies in task graphs
- Using expensive models for simple verification tasks
- Sizing a task larger than its assigned model can handle (violates Component Granularity)
- Letting agents share unbounded file contexts so they clobber each other's work
- Skipping inter-process contracts and discovering protocol mismatches at integration time

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME
- SWARM_ORCHESTRATION_PRIME
- MODEL_ROUTING_PRIME
- ANTHROPIC_SKILL_BUILDER_PRIME
- RETROSPECTIVE_SKILL

## VERSION
1.1.0 - Merged SWARM_PLANNER_PRIME (Executive Orchestrator framing, polyglot specialized-tier routing, bounded-context + compassion instructions) into TEAM_ORCHESTRATION_PRIME. Prior: 1.0.0.
