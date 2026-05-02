# Compound Engineering Key Concepts

## Unified Configuration
Centralizing shared parameters (compound_engineering, logging, performance)
in standalone JSON blocks to avoid tool-specific schema conflicts.

## MCP Bridge Topology
Using the `cohezion-bridge` (`cohezion_mcp.py`) as the single source of
truth for telemetry, model selection, and dynamic tool discovery across
Gemini, IDE, and Claude environments.

## Registry-Driven Swarm
Dynamically configuring model rosters based on `model_registry.json` and
verification of local availability via `ollama list`.

## Defensive Grounding
The mandatory use of "Truth Anchors" and `HallucinationResolver` to prevent
spec-attribution errors. Always consult `get_truth_anchors` for hardware
and path vitals before making claims about system capabilities.

## Offload Parity
Ensuring menial tasks (docs, formatting) are always routed to local SLMs
with a dedicated `ContextHarness`. This keeps expensive models focused on
high-value reasoning tasks.

## HIHO Stability (50% Coherence)
The optimal balance between exploitation (using known patterns) and
exploration (trying new approaches). Coherence scores below 0.5 indicate
the system needs to either escalate or decompose the request.

## Future Hooks Pattern
Every new skill/feature MUST include a `## FUTURE HOOKS` section listing
at least 3 ways this feature makes future tasks easier. This is the core
compound engineering principle: build for compounding returns.
