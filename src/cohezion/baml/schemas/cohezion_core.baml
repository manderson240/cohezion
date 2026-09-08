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
  node string // Compute target: 'npu', 'igpu', 'cpu', 'cloud'
  output_type string // Output intent: 'short_answer', 'code', 'long_generation', 'structured'
  quality_gate_chars int // Minimum character threshold for response
  confidence float // Classifier certainty score [0.0, 1.0]
  rationale string // Explanation of tier selection
}

class RoutingDecision {
  model_id string // Model identifier (e.g. 'deepseek-r1-0528-8b-FLM', 'Qwen3-Coder-30B-GGUF')
  tier string // 'npu', 'igpu', 'cpu', 'cloud'
  port int // Port endpoint (strictly 13305 for local)
  temperature float // Card-aligned sampling temperature
  top_p float // Card-aligned nucleus sampling
  max_context int // Bounded context length (<= 16384)
  evi_score float // Expected Value of Intervention score
}

class SheafDirichletState {
  num_nodes int // Number of stalks in the cellular sheaf
  num_edges int // Number of restriction maps
  dirichlet_energy float // Harmonic energy E_D = 1/2 x^T L_Sigma x
  is_concordant bool // True if energy < 2.0 (no contradiction)
  disputed_edges string[] // List of edge IDs exceeding harmonic discrepancy threshold
}

class ModelCardProfile {
  model_id string // Model name
  backend_recipe string // 'flm', 'llamacpp', 'kokoro', 'sd-cpp', 'whispercpp'
  device string // 'npu', 'gpu', 'cpu'
  sweet_spot_temp float // Optimal temperature
  min_memory_gb float // Memory requirement in GiB
  supported_modes string[] // e.g. ['code', 'chat', 'tools', 'math']
}

class KanbanItem {
  id string // Task card identifier
  title string // Task title
  status string // 'backlog', 'todo', 'in_progress', 'done', 'blocked'
  priority string // 'critical', 'high', 'medium', 'low'
  source string // Session or agent emitter
  category string // 'architecture', 'bugfix', 'tech_debt', 'research'
  description string // Comprehensive task specification
}

class VModelTrace {
  concept_name string // Core architectural concept
  target_category string // Subsystem category
  node_id string // SurrealDB relational node identifier
  j_space_regime string // J-Space latent workspace depth
  ast_verified bool // AutoHarness AST policy check
  zkfv_verified bool // ZK-FV Plonkish constraint proof
  multiperspective_score float // Adversarial agent consensus score
}

class HardwareVitalsSnapshot {
  total_ram_gb float // Total physical memory
  free_ram_gb float // Free physical memory
  gate_v2_safe bool // True if free RAM >= 16.0 GiB
  lemonade_alive bool // Port 13305 health status
  active_models string[] // List of loaded model IDs
}
