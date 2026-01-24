# Cohezion Capability Map

A central registry of the swarm's tools, skills, and model routing strategies.

## 1. MCP Server Ecosystem
| Server Name | Role | Primary Use Case |
|-------------|------|------------------|
| `cloudrun` | Deployment | Deploying services (RESTRICTED TO FREE TIER) |
| `sequential-thinking` | Reasoning | Dynamic, reflective problem-solving |
| *[TBD]* | *[Discovery]* | *Auto-populate through evolution* |

## 2. Core Skill Domains (Functional Coverage)
The swarm currently utilizes 71+ skills registered in `src/cohezion/skills/`. Key domains include:
- **Architectural**: `GATEWAY_ARCHITECTURE_PRIME`, `SWARM_ORCHESTRATION_PRIME`
- **Technical**: `ADVERSARIAL_TESTING_PRIME`, `REPO_HYGIENE_PRIME`, `SURREALDB_OPTIMIZER_PRIME`
- **Domain-Specific**: `HIHO_STABILITY_PRIME`, `FLUME_ENCODER_PRIME`

## 3. Model Routing & Hardware Efficiency
- **Primary Reasoning**: `deepseek-r1:70b` (Ollama) or `Gemini 3 Pro`.
- **Coding Specialists**: `qwen3-coder:30b` (Ollama), `Devstral`.
- **Evaluation**: `phi3:mini` (Fast quality scoring).
- **Reasoning Architecture**: Utilizes 12D state vectors (3 Spatial + 1 Time + 8 Brane) for trajectory prediction.
- **Concurrency Limit**: GLOBAL_LIMIT = 4 (Prevents TTM lockups on Radeon 7700S).
- **Cost Guardrails**: Cloud Run deployments must adhere to Free Tier limits (min-instances=0, max-instances=1, ephemeral storage only).

## 4. Tool Usage Best Practices
- **Browser Subagent**: Use for deep research only; prefer `read_url_content` for static data to save time. **Warning**: Single-instance lock applies in multi-session environments.
- **Sub-Agent Delegation**: Delegate specialized tasks (e.g., security audits) to a fresh sub-agent context to prevent main-context bloat.
- **Verification First**: Always run a validation tool (lint, test, or Great Expectations) before considering a task complete.
