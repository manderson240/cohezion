"""
Platform-level infrastructure for Charter compliance.

This package contains foundational systems required by the Charter:
- CoherenceTracker: HIHO stability measurement (0.5 baseline)
- ExpertDomainRouter: EDL consensus routing (5 expert streams)
- JourneyLogger: SurrealDB persistence with FLUME trajectories
- ObservableActionProposer: Transparent reasoning display
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.platform.agent_evaluation import AgentEvaluationResult as AgentEvaluationResult
    from cohezion.platform.agent_evaluation import AgentExecutionContext as AgentExecutionContext
    from cohezion.platform.agent_evaluation import (
        AnthropicAlignedEvaluator as AnthropicAlignedEvaluator,
    )
    from cohezion.platform.agent_evaluation import (
        CharterComplianceScore as CharterComplianceScore,
    )
    from cohezion.platform.agent_evaluation import (
        ConstitutionalPrinciple as ConstitutionalPrinciple,
    )
    from cohezion.platform.agent_evaluation import SafetyViolation as SafetyViolation
    from cohezion.platform.agent_evaluation import ViolationSeverity as ViolationSeverity
    from cohezion.platform.agent_evaluation import get_agent_evaluator as get_agent_evaluator
    from cohezion.platform.agent_evaluation import reset_agent_evaluator as reset_agent_evaluator

# Wiring-sweep 2026-06-06: agnostic_integrations was a genuine Class-A file-level orphan
# (0 static importers anywhere; cycle-safe). Guarded re-export makes its IDE-adapter surface
# statically reachable + part of the platform package API. Names listed in __all__ (ruff-safe).
with contextlib.suppress(Exception):
    from cohezion.platform.agnostic_integrations import (
        AgnosticExecutionBroker as AgnosticExecutionBroker,
    )
    from cohezion.platform.agnostic_integrations import (
        AntigravityIDEAdapter as AntigravityIDEAdapter,
    )
    from cohezion.platform.agnostic_integrations import ClaudeCodeAdapter as ClaudeCodeAdapter
    from cohezion.platform.agnostic_integrations import (
        IDEIntegrationAdapter as IDEIntegrationAdapter,
    )
    from cohezion.platform.agnostic_integrations import ZedCodeAdapter as ZedCodeAdapter

with contextlib.suppress(Exception):
    from cohezion.platform.coherence_tracker import CoherenceMetrics as CoherenceMetrics
    from cohezion.platform.coherence_tracker import CoherenceTracker as CoherenceTracker
    from cohezion.platform.coherence_tracker import get_coherence_tracker as get_coherence_tracker
    from cohezion.platform.coherence_tracker import (
        reset_coherence_tracker as reset_coherence_tracker,
    )

with contextlib.suppress(Exception):
    from cohezion.platform.daily_health_digest import CICDMetrics as CICDMetrics
    from cohezion.platform.daily_health_digest import DailyHealthDigest as DailyHealthDigest
    from cohezion.platform.daily_health_digest import DependencyMetrics as DependencyMetrics
    from cohezion.platform.daily_health_digest import HealthCheckResult as HealthCheckResult
    from cohezion.platform.daily_health_digest import HealthDigest as HealthDigest
    from cohezion.platform.daily_health_digest import HealthStatus as HealthStatus
    from cohezion.platform.daily_health_digest import RepositoryMetrics as RepositoryMetrics
    from cohezion.platform.daily_health_digest import TestMetrics as TestMetrics
    from cohezion.platform.daily_health_digest import (
        get_daily_health_digest as get_daily_health_digest,
    )
    from cohezion.platform.daily_health_digest import (
        reset_daily_health_digest as reset_daily_health_digest,
    )

with contextlib.suppress(Exception):
    from cohezion.platform.edl_router import EDLConsensus as EDLConsensus
    from cohezion.platform.edl_router import ExpertDomainRouter as ExpertDomainRouter
    from cohezion.platform.edl_router import ExpertStream as ExpertStream
    from cohezion.platform.edl_router import StreamRecommendation as StreamRecommendation
    from cohezion.platform.edl_router import get_edl_router as get_edl_router
    from cohezion.platform.edl_router import reset_edl_router as reset_edl_router

with contextlib.suppress(Exception):
    from cohezion.platform.journey_logger import Journey as Journey
    from cohezion.platform.journey_logger import JourneyLogger as JourneyLogger
    from cohezion.platform.journey_logger import get_journey_logger as get_journey_logger
    from cohezion.platform.journey_logger import reset_journey_logger as reset_journey_logger

with contextlib.suppress(Exception):
    from cohezion.platform.observable_action import ActionProposal as ActionProposal
    from cohezion.platform.observable_action import (
        ObservableActionProposer as ObservableActionProposer,
    )
    from cohezion.platform.observable_action import (
        get_observable_proposer as get_observable_proposer,
    )
    from cohezion.platform.observable_action import (
        reset_observable_proposer as reset_observable_proposer,
    )

with contextlib.suppress(Exception):
    from cohezion.platform.skill_analytics_charter import (
        CharterAlignedSkillAnalytics as CharterAlignedSkillAnalytics,
    )
    from cohezion.platform.skill_analytics_charter import (
        CharterSkillInsights as CharterSkillInsights,
    )
    from cohezion.platform.skill_analytics_charter import get_skill_analytics as get_skill_analytics
    from cohezion.platform.skill_analytics_charter import (
        reset_skill_analytics as reset_skill_analytics,
    )

with contextlib.suppress(Exception):
    from cohezion.platform.skill_scorer_charter import (
        CharterAlignedSkillScorer as CharterAlignedSkillScorer,
    )
    from cohezion.platform.skill_scorer_charter import CharterSkillScore as CharterSkillScore
    from cohezion.platform.skill_scorer_charter import get_skill_scorer as get_skill_scorer
    from cohezion.platform.skill_scorer_charter import reset_skill_scorer as reset_skill_scorer

with contextlib.suppress(Exception):
    from cohezion.platform.skill_tracker_charter import (
        CharterAlignedSkillTracker as CharterAlignedSkillTracker,
    )
    from cohezion.platform.skill_tracker_charter import SkillUsageEvent as SkillUsageEvent
    from cohezion.platform.skill_tracker_charter import get_skill_tracker as get_skill_tracker
    from cohezion.platform.skill_tracker_charter import reset_skill_tracker as reset_skill_tracker


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
