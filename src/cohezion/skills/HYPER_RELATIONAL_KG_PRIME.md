---
name: hyper-relational-kg-prime
description: "Hyper-Relational Knowledge Graph engineering with W3C RDF-Star qualifiers, Bayesian epistemic confidence, and SHACL closed-world structural validation."
metadata:
  version: "v1.0"
  concepts: ["Hyper-Relational Statements", "RDF-Star Qualifiers", "SHACL Validation", "Closed-World Reasoning", "Epistemic Confidence", "SurrealQL Graph Serialization"]
  see_also: ["ASSUME_GUARANTEE_MBSE_PRIME", "VMODEL_COMPOUND_GRAPH_PRIME", "AUTOHARNESS_POLICY_PRIME"]
  source: "src/cohezion/skills/HYPER_RELATIONAL_KG_PRIME.md"
---

# SKILL: HYPER_RELATIONAL_KG_PRIME

## DOMAIN EXPERTISE
Hyper-relational knowledge engineering, W3C RDF-Star edge qualification, Bayesian epistemic confidence propagation, and SHACL (Shapes Constraint Language) closed-world structural and relational validation for autonomous agent swarms and engineering traceability.

## KEY TEXTS & CONCEPTS
- **Hyper-Relational Statements ($\langle h, r, t, Q \rangle$)**: Extends standard RDF triples $(h, r, t)$ with a structured qualifier map $Q$ specifying Bayesian confidence $p \in [0.0, 1.0]$, cryptographic IV&V tokens, bitemporal valid intervals, and provenance URIs.
- **SHACL Closed-World Validation**: Replaces open-world RDF assumptions with closed-world constraints. Ensures every architectural entity (e.g., `Requirement`, `Component`, `Test`) strictly conforms to property shapes and required outgoing relations before commitment.
- **Epistemic Qualification**: Allows multi-agent swarms to express hypotheses with calibrated epistemic uncertainty without polluting authoritative truth.
- **Dual Persistence Architecture**: Dual-writes knowledge graph entities and hyper-edges to SurrealDB (`UPSERT` and `RELATE ... CONTENT`) and markdown frontmatter for Obsidian Vault navigation.

## INSTRUCTION
1. **Initialize Graph**: Instantiate `HyperRelationalGraph` from `cohezion.knowledge_graph.hyper_relational_kg`.
2. **Register Nodes and Statements**: Add typed entities via `add_node(id, type, props)` and qualified relationships via `add_statement(head, relation, tail, qualifier=HyperQualifier(...))`.
3. **Define SHACL Shapes**: Define `NodeShape` with `PropertyShape` constraints (datatype, min_count, allowed_values) and cardinality constraints for outgoing relations.
4. **Enforce Closed-World Integrity**: Run `graph.validate_shacl()` before any commit or automated merge. Reject graph mutations if `report.conforms` is False.
5. **Serialize to Storage Mesh**: Generate idempotent graph mutations via `graph.to_surrealql()` to sync with SurrealDB and update Obsidian Vault notes.

## VERSION
v1.0

## SEE ALSO
- ASSUME_GUARANTEE_MBSE_PRIME
- VMODEL_COMPOUND_GRAPH_PRIME
- AUTOHARNESS_POLICY_PRIME
