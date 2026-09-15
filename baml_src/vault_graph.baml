// BAML Schema for Neurosymbolic Knowledge Graph Extraction
// Bridges Obsidian Vault markdown notes, typed local LLM inference, and SurrealDB graph persistence.

class ExtractedEntity {
  id string
  name string
  entity_type string
  summary string
  tags string[]
}

class ExtractedRelation {
  source_id string
  target_id string
  relation_type string
  confidence float @assert(valid_confidence, {{ this >= 0.0 and this <= 1.0 }})
  weight float @assert(valid_weight, {{ this >= 0.0 and this <= 1.0 }})
  rationale string
}

class VaultGraphExtraction {
  source_document string
  coherence_score float @assert(valid_coherence, {{ this >= 0.0 and this <= 1.0 }})
  entities ExtractedEntity[]
  relations ExtractedRelation[]
}

function ExtractVaultGraph(source_document: string, content: string) -> VaultGraphExtraction {
  client "HybridCohezion"
  prompt #"
    You are the Cohezion Neurosymbolic Knowledge Graph Extraction Engine.
    Source Document: {{ source_document }}
    Document Content:
    {{ content }}

    Analyze the technical concepts and their semantic dependencies:
    1. Extract all canonical entities (theories, architectures, hardware components, agents, protocols, metrics).
    2. Extract all directed semantic relations between them (depends_on, proves, governs, implements, refines, contradicts).
    3. Ensure confidence and weight are strictly bounded in [0.0, 1.0].
    4. Compute a global document coherence score (0.0 to 1.0) evaluating conceptual alignment with the HIHO stability protocol.
  "#
}

test TestExtractVaultGraph {
  functions [ExtractVaultGraph]
  args {
    source_document "01-Learnings/hiho_stability.md"
    content "The HIHO stability protocol enforces a 0.5 coherence rule across 4 fabrics: Space, Field, Control, and Precipitation. Awareness operates on the void as primary parameter."
  }
}
