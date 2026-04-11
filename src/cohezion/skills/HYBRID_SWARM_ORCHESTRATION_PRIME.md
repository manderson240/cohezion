# SKILL: HYBRID_SWARM_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Expert in orchestrating multi-provider AI swarms that combine massive-context cloud models (Gemini 2.5) with specialized local models (Ollama). Focuses on maximizing reasoning depth while respecting hardware concurrency constraints (e.g., VRAM limits).

## KEY TEXTS & CONCEPTS
- **Context Tiering**: Routing global architectural tasks to 2M context (Pro) and high-volume tasks to 1M context (Flash).
- **Concurrency Guard**: Managing fixed slots for local models (e.g., 3-model limit) to prevent OOM.
- **Provider Affinity**: Mapping tasks to the provider best suited for the complexity (Cloud for synthesis, Local for math/scripting).

## INSTRUCTION
1. **Define Team**: Create a configuration JSON (e.g., `hybrid_specialist_agents.json`) specifying roles, models, and providers.
2. **Set Concurrency**: Define `max_ollama_slots` and `reserved_slots` to ensure system stability.
3. **Route by Context**:
   - Architect: Gemini 2.5 Pro (2M)
   - Engineer: Gemini 2.5 Flash (1M)
   - Math/Algo: Local Ollama (phi4)
4. **Register BMAD Agents**: Use the `create_agent` tool to provide activation commands for each specialist.

## VERSION
v1.0

## SEE ALSO
- MODEL_ROUTING_PRIME.md
- COST_AWARE_ORCHESTRATION_PRIME.md
