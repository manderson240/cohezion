# Memory Recovery Protocol (MRP)

This protocol standardized how agents synchronize with the Cohezion project's Collective Memory at the start of each session.

## The 5-Step Wake-Up Process

1.  **READ `GEMINI.md`**: Establish roles, global rules, and model routing tiers.
2.  **READ `KEY_LEARNINGS.md`**: Ingest cumulative wisdom and past architectural decisions.
3.  **READ `retrospectives/`**: Synthesize the latest 24-48 hours of progress and failures.
4.  **QUERY `SurrealDB`**: Hydrate the agent with the current live state of the Universe and active Mission Pulses.
5.  **BOOT `12D State Vector`**: Initialize the current session's state vector based on historical context and mission objectives.

## Execution Pattern
Agents should prioritize these steps before attempting new tasks. Failure to synchronize may result in "hallucinated complexity" or "re-solving" already addressed issues.
