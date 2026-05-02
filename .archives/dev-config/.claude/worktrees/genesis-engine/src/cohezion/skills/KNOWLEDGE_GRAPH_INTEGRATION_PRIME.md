# SKILL: KNOWLEDGE_GRAPH_INTEGRATION_PRIME

## DOMAIN EXPERTISE
You are a systems architect who bridges the **skill registry** with a **knowledge graph** representation of Cohezion’s concepts, dependencies, and execution flows. You understand graph data models (RDF/Property Graph), semantic linking, and how to keep the graph in sync with the markdown‑based skill definitions.

## KEY TEXTS & CONCEPTS
- **Knowledge Graph** – Nodes represent skills, concepts, and artifacts; edges capture relationships such as `USES`, `DEPENDS_ON`, `GENERATES`, and `SEE_ALSO`.
- **RDF Triples** – Subject‑Predicate‑Object statements that can be exported to Turtle or JSON‑LD for downstream tools.
- **Graph Update Loop** – Detect changes in skill files (via file timestamps or git diff) and apply incremental mutations to the graph.
- **Query Languages** – SPARQL for RDF graphs; Cypher for property graphs (e.g., Neo4j, Memgraph).
- **Synchronization** – Ensure the graph mirrors the registry JSON (`skill_registry.json`) and the actual markdown files on disk.

## INSTRUCTION
1. **Initialize the Graph Store**  
   - If a local Neo4j instance is available, connect via `neo4j://localhost:7687`.  
   - Otherwise, fall back to an in‑memory `networkx` graph that can be serialized to `knowledge_graph.json` after each update.
2. **Parse Skill Files** – For every markdown file in `cohezion/src/cohezion/skills/*.md`:
   - Create a node with label `Skill` and properties:  
     - `name` (e.g., `METAPHYSICS_PRIME`)  
     - `path` (relative path to the file)  
     - `description` (first paragraph after `## DOMAIN EXPERTISE`)  
     - `keywords` (list extracted from `## KEY TEXTS & CONCEPTS`)  
   - Add edges for each entry in the `## SEE ALSO` section: `(:Skill)-[:SEE_ALSO]->(:Skill)`.
3. **Link to Registry** – For each skill, add an edge `(:Skill)-[:REGISTERED_IN]->(:Registry)` where the Registry node holds the path to `skill_registry.json`.
4. **Link to Embeddings** – If embeddings exist (`skill_embeddings.json`), create a node `(:Embedding)` per skill and connect via `(:Skill)-[:HAS_EMBEDDING]->(:Embedding)`.
5. **Detect Changes** – On each run:
   - Compute a hash (e.g., SHA‑256) of each skill file’s contents.
   - Compare with hashes stored in a hidden file `.skill_hashes.json`.
   - For any changed or new skill, upsert the corresponding node/edges; for deleted skills, remove the node and all incident edges.
6. **Expose Query API** – Provide a thin wrapper function:
   ```python
   def query_graph(cypher: str) -> List[dict]:
       # Executes the Cypher query against the live graph store
       # Returns a list of dictionaries representing rows.
   ```
   This allows other skills (e.g., COMPOUND_PROMPT_PRIME) to ask questions like “Which skills depend on METAPHYSICS_PRIME?”.
7. **Persist Graph** – After updates, serialize the graph:
   - For Neo4j, it persists automatically.  
   - For `networkx`, write to `knowledge_graph.json` (node list + edge list) using `json.dump`.
8. **Automation Hook** – Add a call to this integration at the end of `populate_registry.py` (or a dedicated CI step) so the graph stays up‑to‑date whenever new skills are registered.
9. **Versioning** – Increment the `VERSION` block of this skill whenever the graph schema changes (e.g., new edge types).

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- EMBEDDING_STRATEGY_PRIME.md
- VECTOR_STORE_PRIME.md
- COMPOUND_ENGINEERING_PRIME.md