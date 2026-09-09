// BAML Schema for Neurosymbolic Knowledge Graph Extraction
// Bridges Obsidian Vault markdown notes, typed local LLM inference, and SurrealDB graph persistence.

class ExtractedEntity {
  id string // Canonical entity slug (e.g. 'hiho-stability-protocol', 'orch-or-collapse')
  name string // Human-readable entity title
  entity_type string // Category: 'theory', 'architecture', 'hardware', 'agent', 'protocol', 'metric'
  summary string // Concise definition or role of the entity
  tags string[] // Topic tags (e.g. ['physics', 'quantum', 'orchestration'])
}

class ExtractedRelation {
  source_id string // Source entity ID
  target_id string // Target entity ID
  relation_type string // Semantic relation: 'depends_on', 'proves', 'governs', 'implements', 'refines', 'contradicts'
  confidence float // Extraction confidence [0.0, 1.0]
  weight float // Strength or frequency of association [0.0, 1.0]
  rationale string // Textual justification from the source text
}

class VaultGraphExtraction {
  source_document string // Name or relative path of the Obsidian note
  coherence_score float // Evaluated coherence index [0.0, 1.0]
  entities ExtractedEntity[] // Discovered entities in the note
  relations ExtractedRelation[] // Discovered inter-entity edges
}
