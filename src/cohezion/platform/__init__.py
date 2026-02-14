"""
Platform-level infrastructure for Charter compliance.

This package contains foundational systems required by the Charter:
- CoherenceTracker: HIHO stability measurement (0.5 baseline)
- ExpertDomainRouter: EDL consensus routing (5 expert streams)
- JourneyLogger: SurrealDB persistence with FLUME trajectories
- ObservableActionProposer: Transparent reasoning display
"""

from cohezion.platform.coherence_tracker import (
    CoherenceTracker,
    CoherenceMetrics,
    get_coherence_tracker,
    reset_coherence_tracker,
)
from cohezion.platform.edl_router import (
    ExpertDomainRouter,
    ExpertStream,
    StreamRecommendation,
    EDLConsensus,
    get_edl_router,
    reset_edl_router,
)
from cohezion.platform.journey_logger import (
    JourneyLogger,
    Journey,
    get_journey_logger,
    reset_journey_logger,
)
from cohezion.platform.observable_action import (
    ObservableActionProposer,
    ActionProposal,
    get_observable_proposer,
    reset_observable_proposer,
)
from cohezion.platform.skill_tracker_charter import (
    CharterAlignedSkillTracker,
    SkillUsageEvent,
    get_skill_tracker,
    reset_skill_tracker,
)
from cohezion.platform.skill_scorer_charter import (
    CharterAlignedSkillScorer,
    CharterSkillScore,
    get_skill_scorer,
    reset_skill_scorer,
)
from cohezion.platform.skill_analytics_charter import (
    CharterAlignedSkillAnalytics,
    CharterSkillInsights,
    get_skill_analytics,
    reset_skill_analytics,
)
from cohezion.platform.agent_evaluation import (
    AnthropicAlignedEvaluator,
    AgentExecutionContext,
    AgentEvaluationResult,
    CharterComplianceScore,
    SafetyViolation,
    ViolationSeverity,
    ConstitutionalPrinciple,
    get_agent_evaluator,
    reset_agent_evaluator,
)
from cohezion.platform.daily_health_digest import (
    DailyHealthDigest,
    HealthDigest,
    HealthStatus,
    RepositoryMetrics,
    TestMetrics,
    DependencyMetrics,
    CICDMetrics,
    HealthCheckResult,
    get_daily_health_digest,
    reset_daily_health_digest,
)

__all__ = [
    "CoherenceTracker",
    "CoherenceMetrics",
    "get_coherence_tracker",
    "reset_coherence_tracker",
    "ExpertDomainRouter",
    "ExpertStream",
    "StreamRecommendation",
    "EDLConsensus",
    "get_edl_router",
    "reset_edl_router",
    "JourneyLogger",
    "Journey",
    "get_journey_logger",
    "reset_journey_logger",
    "ObservableActionProposer",
    "ActionProposal",
    "get_observable_proposer",
    "reset_observable_proposer",
    "CharterAlignedSkillTracker",
    "SkillUsageEvent",
    "get_skill_tracker",
    "reset_skill_tracker",
    "CharterAlignedSkillScorer",
    "CharterSkillScore",
    "get_skill_scorer",
    "reset_skill_scorer",
    "CharterAlignedSkillAnalytics",
    "CharterSkillInsights",
    "get_skill_analytics",
    "reset_skill_analytics",
    "AnthropicAlignedEvaluator",
    "AgentExecutionContext",
    "AgentEvaluationResult",
    "CharterComplianceScore",
    "SafetyViolation",
    "ViolationSeverity",
    "ConstitutionalPrinciple",
    "get_agent_evaluator",
    "reset_agent_evaluator",
    "DailyHealthDigest",
    "HealthDigest",
    "HealthStatus",
    "RepositoryMetrics",
    "TestMetrics",
    "DependencyMetrics",
    "CICDMetrics",
    "HealthCheckResult",
    "get_daily_health_digest",
    "reset_daily_health_digest",
]
