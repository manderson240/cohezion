"""
Repositories Package - SurrealDB persistence for journeys, skills, universes, and patterns.

Compound Engineering Features:
- Base repository with batch operations
- Metrics collection for throughput analysis
- Token-efficient context patterns
- Adversarial review integration points
"""

from cohezion.core.persistence.repositories.base import (
    BaseRepository,
    BatchOperationResult,
    RepositoryMetrics,
)
from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
    JourneyRepository,
    JourneyStep,
)
from cohezion.core.persistence.repositories.pattern_repository import (
    CodeAntiPattern,
    CodePattern,
    PatternRepository,
)
from cohezion.core.persistence.repositories.skill_repository import (
    SkillRepository,
)
from cohezion.core.persistence.repositories.surreal_journey_repository import (
    SurrealJourneyRepository,
)
from cohezion.core.persistence.repositories.surreal_skill_repository import (
    SurrealSkillRepository,
)
from cohezion.core.persistence.repositories.surreal_universe_repository import (
    SurrealUniverseRepository,
)
from cohezion.core.persistence.repositories.universe_repository import (
    UniverseRepository,
    UniverseRepositoryFilter,
)


__all__ = [
    # Base classes
    "BaseRepository",
    "BatchOperationResult",
    "RepositoryMetrics",
    # Journey
    "AgentJourney",
    "JourneyMetrics",
    "JourneyRepository",
    "JourneyStep",
    "SurrealJourneyRepository",
    # Skill
    "SkillRepository",
    "SurrealSkillRepository",
    # Universe
    "UniverseRepository",
    "UniverseRepositoryFilter",
    "SurrealUniverseRepository",
    # Pattern
    "CodeAntiPattern",
    "CodePattern",
    "PatternRepository",
]
