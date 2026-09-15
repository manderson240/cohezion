// Cohezion Core Domain BAML Schema Definitions
// Reference: https://github.com/boundaryml/baml
// Declarative type-safe schemas for multi-agent orchestration, Strix Halo APU routing, and compound verification.

class GoalSpecification {
  goal_id string // Unique deterministic goal identifier
  title string // Human-readable goal summary
  target_metric string // Target metric name (e.g. 'coherence', 'pass_rate', 'dirichlet_energy')
  target_threshold float // Numerical convergence threshold
  max_iterations int // Maximum allowed closed-loop iterations
  timeout_seconds float // Execution timeout floor
}

class TaskClassificationResult {
  node "npu" | "igpu" | "cpu" | "cloud" // Compute target tier
  output_type "short_answer" | "code" | "long_generation" | "structured" // Output intent
  quality_gate_chars int // Minimum character threshold for response
  confidence float @assert(valid_confidence, {{ this >= 0.0 and this <= 1.0 }}) // Classifier certainty
  rationale string // Explanation of tier selection
}

class RoutingDecision {
  model_id string // Model identifier (e.g. 'deepseek-r1-0528-8b-FLM', 'Qwen3-Coder-30B')
  tier "npu" | "igpu" | "cpu" | "cloud"
  port int @assert(valid_port, {{ this == 13305 or this == 11434 }})
  temperature float
  top_p float
  max_context int @assert(valid_context, {{ this > 0 and this <= 65536 }})
  evi_score float @assert(valid_evi, {{ this >= 0.0 and this <= 1.0 }})
}

class SheafDirichletState {
  num_nodes int
  num_edges int
  dirichlet_energy float @assert(non_negative, {{ this >= 0.0 }})
  is_concordant bool
  disputed_edges string[]
}

class ModelCardProfile {
  model_id string
  backend_recipe "flm" | "llamacpp" | "kokoro" | "sd-cpp" | "whispercpp"
  device "npu" | "igpu" | "cpu"
  sweet_spot_temp float
  min_memory_gb float
  supported_modes string[]
}

class KanbanItem {
  id string
  title string
  status "backlog" | "todo" | "in_progress" | "done" | "blocked"
  priority "critical" | "high" | "medium" | "low"
  source string
  category "architecture" | "bugfix" | "tech_debt" | "research"
  description string
}

class VModelTrace {
  concept_name string
  target_category string
  node_id string
  j_space_regime string
  ast_verified bool
  zkfv_verified bool
  multiperspective_score float @assert(valid_score, {{ this >= 0.0 and this <= 1.0 }})
}

class HardwareVitalsSnapshot {
  total_ram_gb float @assert(positive_ram, {{ this > 0.0 }})
  free_ram_gb float @assert(non_negative_ram, {{ this >= 0.0 }})
  gate_v2_safe bool
  lemonade_alive bool
  active_models string[]
}

// -----------------------------------------------------------------------------
// Core Domain Functions
// -----------------------------------------------------------------------------

function ClassifyTaskIntent(task_description: string) -> TaskClassificationResult {
  client "HybridCohezion"
  prompt #"
    You are the Cohezion Proactive Task Classifier.
    Task Description: {{ task_description }}

    Classify this task according to Strix Halo APU routing discipline:
    1. node: 'npu' for fast low-power reasoning/embeddings, 'igpu' for heavy coding/GGUF, 'cpu' for audio/deterministic tasks, 'cloud' for overflow.
    2. output_type: 'short_answer', 'code', 'long_generation', or 'structured'.
    3. quality_gate_chars: minimum characters expected for an acceptable answer.
    4. confidence: certainty score strictly between 0.0 and 1.0.
    5. rationale: concise technical justification.
  "#
}

function DecideHardwareRouting(task_type: string, input_tokens: int, required_modes: string[]) -> RoutingDecision {
  client "HybridCohezion"
  prompt #"
    You are the Cohezion Model Card Dispatch Router.
    Task Type: {{ task_type }}
    Estimated Input Tokens: {{ input_tokens }}
    Required Modes:
    {% for mode in required_modes %}
    - {{ mode }}
    {% endfor %}

    Determine the optimal card-aligned inference configuration:
    - model_id: exact model tag from the Cohezion local roster or cloud fallback
    - tier: 'npu', 'igpu', 'cpu', or 'cloud'
    - port: 13305 for local Lemonade, 11434 for Ollama
    - temperature: sweet-spot temperature for the model
    - top_p: nucleus sampling parameter
    - max_context: bounded context length (must be > 0 and <= 65536)
    - evi_score: Expected Value of Intervention score [0.0, 1.0]
  "#
}

function EvaluateHarmonicSheaf(stalk_values: string, restriction_maps: string) -> SheafDirichletState {
  client "HybridCohezion"
  prompt #"
    You are the Cohezion Topological Cellular Sheaf Analyzer.
    Stalk Values (Agent Beliefs / Observations):
    {{ stalk_values }}
    Restriction Maps (Information Flow Constraints):
    {{ restriction_maps }}

    Analyze cellular sheaf cohomology and compute Dirichlet energy:
    - num_nodes: number of stalk nodes
    - num_edges: number of restriction maps
    - dirichlet_energy: computed harmonic energy E_D = 1/2 x^T L_Sigma x (>= 0.0)
    - is_concordant: true if energy < 2.0 (no consensus deadlock), false otherwise
    - disputed_edges: list of edge identifiers where harmonic discrepancy is elevated
  "#
}

test TestClassifyTaskIntent {
  functions [ClassifyTaskIntent]
  args {
    task_description "Synthesize a 12-parameter quadrature model for HIHO field stabilization"
  }
}

test TestDecideHardwareRouting {
  functions [DecideHardwareRouting]
  args {
    task_type "coding"
    input_tokens 1500
    required_modes ["code", "tools"]
  }
}

test TestEvaluateHarmonicSheaf {
  functions [EvaluateHarmonicSheaf]
  args {
    stalk_values "Node A: [0.5, 0.5]; Node B: [0.5, 0.5]; Node C: [0.5, 0.5]"
    restriction_maps "A->B: Identity; B->C: Identity; A->C: Identity"
  }
}

