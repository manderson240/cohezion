# Yale Peaked Hackathon 2026 - Retrospective & Knowledge Capture Plan

## Objective
Institutionalize the critical lessons from the Yale Peaked Hackathon 2026 into the Cohezion ecosystem by capturing them as reusable skills and persisting them in the knowledge graph (Obsidian Vault and SurrealDB).

## Implementation Steps

### 1. Skill Creation (`QUANTUM_HACKATHON_PRIME`)
- **Action:** Create `src/cohezion/skills/QUANTUM_HACKATHON_PRIME.md` using the standard Cohezion skill template.
- **Content:** 
  - **Domain Expertise:** Quantum circuit execution, hardware transpilation, and statistical refinement on cloud infrastructure.
  - **Instruction 1: Endianness Verification:** Mandate running a trivial circuit to establish a "Truth Anchor" for endianness (LSB vs MSB) before processing challenge data.
  - **Instruction 2: Transpilation Layout Tracking:** Provide code examples for extracting the `initial_layout` from a transpiled Qiskit circuit and applying the inverse mapping to hardware measurement counts to recover the logical bitstrings.
  - **Instruction 3: Cloud Resource Limits:** Define protocols for verifying Account Plans (Free vs. Paid) separately from Credit Balances to prevent execution blocking.

### 2. Knowledge Graph Update (Obsidian Vault)
- **Action:** Append the three core lessons (Endianness, Qubit Routing, and Plan Limits) to `src/cohezion/knowledge_graph/KEY_LEARNINGS.md`.
- **Content:** Detail the specific failure modes experienced during the hackathon and the corresponding preventative measures.

### 3. SurrealDB Persistence
- **Action:** Utilize the Cohezion SurrealDB MCP tools to persist the knowledge as 12D state vectors.
- **Step A:** Execute `mcp_cohezion-surreal_store_learning` for the specific lessons (e.g., Transpilation Routing, Endianness).
- **Step B:** Execute `mcp_cohezion-surreal_sync_key_learnings` to ensure the updated markdown file is fully synchronized with the database for FLUME retrieval.

## Verification
- Confirm `QUANTUM_HACKATHON_PRIME.md` follows the required format.
- Verify learnings are successfully retrievable via `mcp_cohezion-surreal_query_learnings`.