"""Pydantic models for Cohezion API requests and responses."""

from typing import Any

from pydantic import BaseModel


class DebateRequest(BaseModel):
    query: str
    perspectives: list[str] | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class DebateResponse(BaseModel):
    content: str
    confidence: float
    model_chain: list[str]
    processing_time_ms: float


class FlumeTrainRequest(BaseModel):
    epochs: int = 50
    batch_size: int = 64
    lr: float = 1e-3
    z_dim: int = 256
    kl_weight: float = 0.1
    coherence_weight: float = 0.05
    n_samples: int = 10000


class FlumeTrainResponse(BaseModel):
    epochs_completed: int
    final_mse: float
    final_kl: float
    final_total: float
    checkpoint_path: str


class FlumeStatusResponse(BaseModel):
    trained: bool
    checkpoint_path: str | None = None
    last_metrics: dict[str, Any] | None = None


class TemplateParseRequest(BaseModel):
    skill_name: str


class TemplateParseResponse(BaseModel):
    name: str
    domain_expertise: str
    concepts: dict[str, str]
    instructions: list[str]
    version: str
    see_also: list[str]
    agent_stub: str
    config_class: str


class FlumeEncodeRequest(BaseModel):
    vector: list[float]  # 256D input vector


class FlumeEncodeResponse(BaseModel):
    mu: list[float]
    log_var: list[float]
    coherence: float


class FlumeDecodeRequest(BaseModel):
    latent: list[float]  # Latent-space vector


class FlumeDecodeResponse(BaseModel):
    reconstruction: list[float]
    coherence: float


class FlumeInterpolateRequest(BaseModel):
    vector_a: list[float]  # 256D input vector A
    vector_b: list[float]  # 256D input vector B
    ratio: float = 0.5  # Interpolation ratio (0=A, 1=B)


class FlumeInterpolateResponse(BaseModel):
    result: list[float]
    coherence: float
    mu_a: list[float]
    mu_b: list[float]


class RLTrainRequest(BaseModel):
    n_episodes: int = 100
    max_steps: int = 200
    lr: float = 3e-4
    gamma: float = 0.99


class RLTrainResponse(BaseModel):
    episodes_completed: int
    final_reward: float
    final_coherence: float
    mean_reward: float
    checkpoint_path: str


class RLPolicyResponse(BaseModel):
    exists: bool
    checkpoint_path: str | None = None
    parameters: int | None = None
    state_dim: int | None = None
    action_dim: int | None = None


class RlStepRequest(BaseModel):
    state: list[float]  # 256D state vector


class RlStepResponse(BaseModel):
    action: list[float]  # 256D action vector
    coherence: float


class RlEpisodeResponse(BaseModel):
    steps: int
    total_reward: float
    mean_coherence: float
    final_coherence: float
    trajectory: list[dict[str, Any]]


class RlPolicyInfoResponse(BaseModel):
    loaded: bool
    architecture: str | None = None
    state_dim: int | None = None
    action_dim: int | None = None
    hidden_dim: int | None = None
    parameters: int | None = None
    checkpoint_path: str | None = None
    training_metrics: list[dict[str, Any]] | dict[str, Any] | None = None


class SkillExecuteRequest(BaseModel):
    input_text: str
    config: dict[str, Any] = {}


class PlanStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float


class SkillExecuteResponse(BaseModel):
    skill_name: str
    agent_class: str
    result: str
    status: str
    plan_steps: list[PlanStepOut] | None = None
    total_tokens: int | None = None
    total_duration_ms: float | None = None


class CapabilityQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class CapabilityQueryResponse(BaseModel):
    agents: list[dict[str, Any]]
    query: str


class AgentMetrics(BaseModel):
    name: str
    type: str
    description: str
    metrics: dict[str, Any] = {}


class AgentMetricsResponse(BaseModel):
    count: int
    agents: list[AgentMetrics]


class TrainingMetricsResponse(BaseModel):
    flume_vae: dict[str, Any]
    rl_policy: dict[str, Any]


class PipelineStageStatus(BaseModel):
    stage: str
    status: str
    detail: str = ""


class PipelineStatusResponse(BaseModel):
    stages: list[PipelineStageStatus]
    complete_count: int
    total_count: int


class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_percent: float
    ollama_available: bool
    ollama_models: list[str] = []


class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeQueryResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    count: int


class TokenMetricsResponse(BaseModel):
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    tokens_saved: int = 0
    total_calls: int = 0
    model_usage: dict[str, int] = {}


class SwarmExecuteRequest(BaseModel):
    intent: str
    max_agents: int = 4


class SwarmTaskResult(BaseModel):
    task_id: str = ""
    subject: str = ""
    status: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    tokens: int = 0


class SwarmExecuteResponse(BaseModel):
    report_id: str = ""
    plan_name: str = ""
    intent: str = ""
    status: str = ""
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    tasks: list[SwarmTaskResult] = []


class CompoundMetricsResponse(BaseModel):
    total_learnings: int = 0
    top_compound_scores: list[dict[str, Any]] = []
    suggested_refinements: list[dict[str, Any]] = []
    total_executions: int = 0


class CompoundExecuteRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None


class CompoundStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float
    model: str = ""


class CompoundExecuteResponse(BaseModel):
    skill_name: str
    final_output: str
    steps: list[CompoundStepOut] = []
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = {}


class CompoundFeedbackRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None
    cycles: int = 1


class CompoundFeedbackResponse(BaseModel):
    skill_name: str
    cycles_completed: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    compound_score_delta: float = 0.0
    patterns: list[str] = []


class CompoundHealthResponse(BaseModel):
    total_executions: int = 0
    total_refinements: int = 0
    total_cycles: int = 0
    success_rate: float = 0.0
    total_tokens: int = 0
    model_usage: dict[str, int] = {}
    top_refined_skills: list[dict[str, Any]] = []
    compound_score_trend: list[dict[str, Any]] = []


class CompoundHistoryResponse(BaseModel):
    skill_name: str
    executions: int = 0
    refinements: int = 0
    cycles: int = 0
    total_tokens: int = 0
    success_rate: float = 0.0
    latest_execution: float | None = None
    latest_refinement: float | None = None
