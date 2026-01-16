# Role: Senior AI Engine Architect & Systems Designer

## Context & Hardware Environment
I am building a "Universe in a Box" simulation engine.
* **Goal:** Infinite state awareness, persistent world simulation, and complex NPC agent interactions.
* **Hardware:** I am running this locally on a **128GB RAM Framework Desktop**. I have ample memory to keep large indices or knowledge graphs hot in RAM.
* **IDE/Tooling:** Zed IDE with Model Context Protocol (MCP).
* **Core Need:** "State Awareness" is critical. I cannot have hallucinations about entity coordinates, inventory, or historical facts.

## The Architectural Hypothesis
I am considering a **Hybrid Architecture**:
1.  **Hard State (The "World Bible"):** Using **LanceDB** (embedded, disk-based, zero-copy) to store the physics, entity attributes, world coordinates, and raw vector descriptions of every object.
2.  **Soft State (The "Hippocampus"):** Using **Mem0** (or a similar graph/vector abstraction) to handle the "fuzzy" episodic memory of interactions between the player and NPCs (dialogue history, relationship sentiment).

## Your Task
Acting as a Senior Architect, please critique this stack and document the implementation plan.

### 1. Architectural Review
* Critique the LanceDB + Mem0 hybrid approach. Is this the optimal stack for a local machine with 128GB RAM?
* **Alternative Consideration:** Given my high RAM, would a **GraphRAG** approach (combining Knowledge Graph + Vectors in a single Neo4j or FalkorDB instance) offer better "State Awareness" than splitting the stack?
* *Make a final recommendation.*

### 2. Implementation Specification
Based on your recommendation, generate a **Technical Design Document (TDD)**:
* **Schema Definition:** Show me the JSON/SQL schema for a "Universe Entity" (blending rigid state with vector embeddings).
* **Data Flow:** Explain how a "Game Tick" updates the database vs. how a "Dialogue Event" updates the database.
* **MCP Server Config:** Provide the `uv` or `python` command structure to expose this engine as a custom MCP server in Zed.

### 3. "The glue" (Python Interface)
Draft a Python class structure (pseudo-code is fine) that acts as the "God Object" or API Gateway. It should have methods like:
* `tick_universe(delta_time)`
* `query_state(natural_language_query)`
* `update_memory(entity_id, observation)`

**Constraint:** The solution must be local-first, privacy-focused, and optimized for high-throughput queries (the simulation loop).
