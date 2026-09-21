// BAML source of truth for Cohezion LLM calls (adopted 2026-09-08).
// Prompts live here as typed functions; baml_client/ is generated from
// this directory (uv run baml-cli generate) and is type-checked by mypy
// like any other code. Routed through ClientRegistry at runtime — never
// hardcode provider names/ports in call sites (AGENTS.md port-bypass rule).

generator cohezion_target {
  output_type "python/pydantic"
  output_dir ".."
  default_client_mode "sync"
  version "0.226.2"
}

// OpenAI-compatible local endpoints. base_url comes from env at runtime;
// api_key is a placeholder the endpoints ignore but the SDK requires.
// Primary Local Lemonade Endpoint (Tier 1: AMD Strix Halo NPU/iGPU)
client<llm> LemonadeLocal {
  provider "openai-generic"
  options {
    base_url "http://127.0.0.1:13305/api/v1"
    api_key "local"
    model "qwen3-4b-FLM"
    request_timeout_ms 60000
  }
}

// Fallback Ollama Cloud Endpoint (Tier 2)
client<llm> OllamaCloud {
  provider "openai-generic"
  options {
    base_url "http://127.0.0.1:11434/v1"
    api_key "local"
    model "deepseek-v4-flash:cloud"
    request_timeout_ms 60000
  }
}

// Resilient Hybrid Cascade (Lemonade NPU primary -> Ollama Cloud fallback)
client<llm> HybridCohezion {
  provider fallback
  options {
    strategy [
      LemonadeLocal,
      OllamaCloud
    ]
  }
}

// -----------------------------------------------------------------------------
// 1. Next Step Recommendation (Mandate #7)
// -----------------------------------------------------------------------------
class NextStep {
  action string
  rationale string
  risk_level "low" | "medium" | "high"
}

function RecommendNextStep(context: string, candidates: string) -> NextStep {
  client "HybridCohezion"
  prompt #"
    {{ _.role("user") }}
    You are a senior engineer planning the next step for the Cohezion repo.
    Context: {{ context }}
    Candidate actions:
    {{ candidates }}
    Pick the highest-leverage next step. Respond with the action, a one-sentence
    rationale, and a risk level.

    {{ ctx.output_format }}
  "#
}

// -----------------------------------------------------------------------------
// 2. ARC & AIMO Task Invariants Derivation (AutoHarness arXiv:2603.03329v1)
// -----------------------------------------------------------------------------
class TaskInvariants {
  grid_dimension_rule "identity" | "constant" | "scaled" | "dynamic" | "crop"
  conserved_colors int[]
  forbidden_colors int[]
  symmetry_detected "none" | "horizontal" | "vertical" | "rotational_90" | "rotational_180" | "main_diagonal" | "anti_diagonal"
  description string
}

function DeriveTaskInvariants(task_context: string, train_examples: string) -> TaskInvariants {
  client "HybridCohezion"
  prompt #"
    {{ _.role("user") }}
    You are the Cohezion AutoHarness Invariant Extractor.
    Task Context: {{ task_context }}
    Train Examples:
    {{ train_examples }}

    Analyze the transformation across all training pairs:
    1. Grid dimensions: does output preserve input shape (identity), remain fixed size (constant), scale by an integer ratio (scaled), crop an object (crop), or dynamically vary?
    2. Colors: which colors appear in both input and output (conserved), and which colors are strictly illegal/alien (forbidden)?
    3. Symmetry: is the output invariant under horizontal reflection, vertical reflection, 90/180-deg rotation, or diagonal reflection?
    4. Provide a concise technical description of the governing rule.

    {{ ctx.output_format }}
  "#
}

// -----------------------------------------------------------------------------
// 3. Deterministic Code Harness Synthesis (AutoHarness Code-as-Action Verifiers)
// -----------------------------------------------------------------------------
class CodeHarness {
  harness_name string
  precondition_assertions string[]
  postcondition_assertions string[]
  python_verifier_code string
  estimated_latency_ms float
}

function SynthesizeCodeHarness(env_spec: string, failure_trace: string) -> CodeHarness {
  client "HybridCohezion"
  prompt #"
    {{ _.role("user") }}
    You are the Cohezion AutoHarness Zero-Cost Bytecode Compiler.
    Environment Specification:
    {{ env_spec }}
    Failure Trace or Edge Cases:
    {{ failure_trace }}

    Synthesize a deterministic python verification harness to enforce structural invariants without calling an LLM:
    - harness_name: camelCase identifier
    - precondition_assertions: array of python assert expressions for inputs
    - postcondition_assertions: array of python assert expressions for outputs
    - python_verifier_code: executable deterministic verifier function
    - estimated_latency_ms: expected execution latency in milliseconds (typically < 1.0ms)

    {{ ctx.output_format }}
  "#
}

// -----------------------------------------------------------------------------
// 4. Kaggle Leaderboard Audit & Next Action (Active Competitions Only)
// -----------------------------------------------------------------------------
class SubmissionStrategy {
  competition_id string
  target_metric_goal string
  recommended_action "generate_ensemble" | "hyperparameter_tune" | "submit_highest_cv" | "hold_for_audit"
  confidence_score float
  reasoning string
}

function AuditLeaderboardNextAction(competition: string, leaderboard_snapshot: string) -> SubmissionStrategy {
  client "HybridCohezion"
  prompt #"
    {{ _.role("user") }}
    You are the Cohezion Kaggle Competition Master Strategist.
    Competition: {{ competition }}
    Leaderboard Snapshot & Validation Scores:
    {{ leaderboard_snapshot }}

    Evaluate recent validation trajectories against leaderboard benchmarks:
    Recommend the single optimal next submission or modeling action, provide a confidence score (0.0 to 1.0), and concise strategic reasoning.

    {{ ctx.output_format }}
  "#
}