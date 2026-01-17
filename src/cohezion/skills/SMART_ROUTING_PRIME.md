# SKILL: SMART_ROUTING_PRIME

## DOMAIN EXPERTISE
Intelligent task classification and dynamic model selection based on strategy (Speed, Quality, or Efficiency).

## CORE CONCEPTS
1.  **Task Classification:** Analyze input execution intent (e.g., "Simulate" vs "Analyze").
2.  **Model Profiling:** Maintain a registry of models with capability scores (reasoning, creativity, speed).
3.  **Strategic Selection:**
    - **Quality:** Select highest capability score (e.g., Gemini 1.5 Pro).
    - **Speed:** Select fastest response time (e.g., Gemma 2 Flash).
    - **Efficiency:** Balance cost/compute vs performance.
4.  **Fallback Chains:** Always define primary, secondary, and tertiary models.

## PATTERNS
- **Router Class:** Centralized logic for dispatching actions.
- **Capability Constants:** Define `TASK_REQUIREMENTS` mapping task types to required capabilities.
- **Feedback Loop:** Log routing decisions and success rates to tune selection logic.

## USAGE
See `src/cohezion/swarm/smart_router.py` for reference implementation.
