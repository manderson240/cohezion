"""
Platform-level infrastructure for Charter compliance.

This package contains foundational systems required by the Charter:
- CoherenceTracker: HIHO stability measurement (0.5 baseline)
- ExpertDomainRouter: EDL consensus routing (5 expert streams)
- JourneyLogger: SurrealDB persistence with FLUME trajectories
- ObservableActionProposer: Transparent reasoning display
"""

import contextlib

from cohezion.platform.agent_evaluation import (
    AgentEvaluationResult,
    AgentExecutionContext,
    AnthropicAlignedEvaluator,
    CharterComplianceScore,
    ConstitutionalPrinciple,
    SafetyViolation,
    ViolationSeverity,
    get_agent_evaluator,
    reset_agent_evaluator,
)

# Wiring-sweep 2026-06-06: agnostic_integrations was a genuine Class-A file-level orphan
# (0 static importers anywhere; cycle-safe). Guarded re-export makes its IDE-adapter surface
# statically reachable + part of the platform package API. Names listed in __all__ (ruff-safe).
from cohezion.platform.agnostic_integrations import (
    AgnosticExecutionBroker,
    AntigravityIDEAdapter,
    ClaudeCodeAdapter,
    IDEIntegrationAdapter,
    ZedCodeAdapter,
)
from cohezion.platform.coherence_tracker import (
    CoherenceMetrics,
    CoherenceTracker,
    get_coherence_tracker,
    reset_coherence_tracker,
)
from cohezion.platform.daily_health_digest import (
    CICDMetrics,
    DailyHealthDigest,
    DependencyMetrics,
    HealthCheckResult,
    HealthDigest,
    HealthStatus,
    RepositoryMetrics,
    TestMetrics,
    get_daily_health_digest,
    reset_daily_health_digest,
)
from cohezion.platform.edl_router import (
    EDLConsensus,
    ExpertDomainRouter,
    ExpertStream,
    StreamRecommendation,
    get_edl_router,
    reset_edl_router,
)
from cohezion.platform.journey_logger import (
    Journey,
    JourneyLogger,
    get_journey_logger,
    reset_journey_logger,
)
from cohezion.platform.observable_action import (
    ActionProposal,
    ObservableActionProposer,
    get_observable_proposer,
    reset_observable_proposer,
)
from cohezion.platform.skill_analytics_charter import (
    CharterAlignedSkillAnalytics,
    CharterSkillInsights,
    get_skill_analytics,
    reset_skill_analytics,
)
from cohezion.platform.skill_scorer_charter import (
    CharterAlignedSkillScorer,
    CharterSkillScore,
    get_skill_scorer,
    reset_skill_scorer,
)
from cohezion.platform.skill_tracker_charter import (
    CharterAlignedSkillTracker,
    SkillUsageEvent,
    get_skill_tracker,
    reset_skill_tracker,
)


# Wiring-sweep 2026-06-22: mcp_server.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.platform.mcp_server import ObsidianVaultMCP as ObsidianVaultMCP

# Wiring-sweep 2026-06-22: resource_manager.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.platform.resource_manager import (
        OOMRiskError as OOMRiskError,
    )
    from cohezion.platform.resource_manager import (
        PlatformMemoryState as PlatformMemoryState,
    )
    from cohezion.platform.resource_manager import (
        ResourceClient as ResourceClient,
    )
    from cohezion.platform.resource_manager import (
        ResourceDaemon as ResourceDaemon,
    )
    from cohezion.platform.resource_manager import (
        ResourceUnavailableError as ResourceUnavailableError,
    )
    from cohezion.platform.resource_manager import (
        TrainingLock as TrainingLock,
    )

# Wiring-sweep 2026-06-22: session_tracker.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.platform.session_tracker import (
        ModelUsageEvent as ModelUsageEvent,
    )
    from cohezion.platform.session_tracker import (
        SessionRecord as SessionRecord,
    )
    from cohezion.platform.session_tracker import (
        SessionTracker as SessionTracker,
    )

# Wiring-sweep 2026-06-22: tier_optimizer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.platform.tier_optimizer import (
        TierChange as TierChange,
    )
    from cohezion.platform.tier_optimizer import (
        TierOptimizer as TierOptimizer,
    )
    from cohezion.platform.tier_optimizer import (
        TierRecommendation as TierRecommendation,
    )


__all__ = [
    "ActionProposal",
    "AgentEvaluationResult",
    "AgentExecutionContext",
    "AgnosticExecutionBroker",
    "AnthropicAlignedEvaluator",
    "AntigravityIDEAdapter",
    "CICDMetrics",
    "CharterAlignedSkillAnalytics",
    "CharterAlignedSkillScorer",
    "CharterAlignedSkillTracker",
    "CharterComplianceScore",
    "CharterSkillInsights",
    "CharterSkillScore",
    "ClaudeCodeAdapter",
    "CoherenceMetrics",
    "CoherenceTracker",
    "ConstitutionalPrinciple",
    "DailyHealthDigest",
    "DependencyMetrics",
    "EDLConsensus",
    "ExpertDomainRouter",
    "ExpertStream",
    "HealthCheckResult",
    "HealthDigest",
    "HealthStatus",
    "IDEIntegrationAdapter",
    "Journey",
    "JourneyLogger",
    "ModelUsageEvent",
    "OOMRiskError",
    "ObservableActionProposer",
    "ObsidianVaultMCP",
    "PlatformMemoryState",
    "RepositoryMetrics",
    "ResourceClient",
    "ResourceDaemon",
    "ResourceUnavailableError",
    "SafetyViolation",
    "SessionRecord",
    "SessionTracker",
    "SkillUsageEvent",
    "StreamRecommendation",
    "TestMetrics",
    "TierChange",
    "TierOptimizer",
    "TierRecommendation",
    "TrainingLock",
    "ViolationSeverity",
    "ZedCodeAdapter",
    "get_agent_evaluator",
    "get_coherence_tracker",
    "get_daily_health_digest",
    "get_edl_router",
    "get_journey_logger",
    "get_observable_proposer",
    "get_skill_analytics",
    "get_skill_scorer",
    "get_skill_tracker",
    "reset_agent_evaluator",
    "reset_coherence_tracker",
    "reset_daily_health_digest",
    "reset_edl_router",
    "reset_journey_logger",
    "reset_observable_proposer",
    "reset_skill_analytics",
    "reset_skill_scorer",
    "reset_skill_tracker",
]
