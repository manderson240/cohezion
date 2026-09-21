"""Data Mesh architecture for Cohezion's multi-agent system.

Maps Zhamak Dehghani's 4 Data Mesh principles to Cohezion:
  1. Domain ownership → Each specialist agent owns its data domain
  2. Data as product  → Typed products with schema, SLA, ownership
  3. Self-serve platform → SurrealDB + Vault + SemanticCache
  4. Federated governance → Compound loop quality gates

Smith fabric mapping: Field fabric (data topology)
  Gauge invariance = governance consistency across domains

Attribution: Zhamak Dehghani, "Data Mesh: Delivering Data-Driven Value at Scale"
  (O'Reilly, 2022)
"""

# 2026-09-21: every re-export below used to be an EAGER import. One of them (data_product)
# pulls governance -> core -> physics -> reliability -> compound -> flume -> transformers/JAX,
# so `import cohezion.data_mesh.event_consumer` -- a stdlib-only module run by a 5-min timer
# -- cost 13.6 s and ~590 MB per run. The names are now resolved on first access (PEP 562):
# `from cohezion.data_mesh import X` and `cohezion.data_mesh.X` behave as before, but only
# the module that defines X is imported. The TYPE_CHECKING block keeps the static import
# edges the wiring sweeps (2026-06-06 / 06-22 / 08-11) added for reachability, without
# executing them at runtime.
#
# Failure semantics are unchanged: the eager imports were wrapped in suppress(Exception),
# so a broken optional dependency made the name ABSENT. A lookup that fails to import now
# logs the cause and raises AttributeError (-> ImportError for `from ... import X`), which
# is what an absent name produced before. The datamesh/ types need torch; on a torch-free
# install they legitimately vanish, and the log line says why instead of a bare ImportError.
from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any


logger = logging.getLogger(__name__)

_LAZY_EXPORTS: dict[str, str] = {
    "AudioSegmentMetadata": "cohezion.data_mesh.audio_telemetry",
    "AudioTelemetryEvent": "cohezion.data_mesh.audio_telemetry",
    "BirdSpeciesNode": "cohezion.data_mesh.audio_telemetry",
    "SpectrogramConfig": "cohezion.data_mesh.audio_telemetry",
    "TaxonomyLevel": "cohezion.data_mesh.audio_telemetry",
    "DataProduct": "cohezion.data_mesh.data_product",
    "DataProductSchema": "cohezion.data_mesh.data_product",
    "DataProductStatus": "cohezion.data_mesh.data_product",
    "DataQualityTier": "cohezion.data_mesh.data_product",
    "get_cohezion_data_products": "cohezion.data_mesh.data_product",
    "CorpusQualityConsumer": "cohezion.data_mesh.corpus_quality_consumer",
    "make_corpus_quality_consumer": "cohezion.data_mesh.corpus_quality_consumer",
    "DataMeshEventBridge": "cohezion.data_mesh.event_bridge",
    "make_event_bridge": "cohezion.data_mesh.event_bridge",
    "FlumeJourneyEvent": "cohezion.data_mesh.journey_telemetry",
    "HardwareTier": "cohezion.data_mesh.journey_telemetry",
    "QuadratureFabrics": "cohezion.data_mesh.journey_telemetry",
    "LemonadeMultimodalClient": "cohezion.data_mesh.lemonade_multimodal",
    "UniverseStateEvent": "cohezion.data_mesh.universe_telemetry",
    "GaiaDataAgent": "cohezion.data_mesh.gaia_domain_agent",
    "GapMiner": "cohezion.data_mesh.gap_miner",
    "make_gap_miner": "cohezion.data_mesh.gap_miner",
    "DEFAULT_AGENT_SPECS": "cohezion.data_mesh.gaia_agent_roster",
    "AgentSpec": "cohezion.data_mesh.gaia_agent_roster",
    "GaiaAgentRoster": "cohezion.data_mesh.gaia_agent_roster",
    "deploy_gaia_agent_roster": "cohezion.data_mesh.gaia_agent_roster",
    "backfill_items": "cohezion.data_mesh.kanban_bridge",
    "persist_item": "cohezion.data_mesh.kanban_bridge",
    "DomainEndpoint": "cohezion.datamesh.federation",
    "FederationLayer": "cohezion.datamesh.federation",
    "DataLineage": "cohezion.datamesh.schema",
    "Physics12D": "cohezion.datamesh.schema",
    "RecordType": "cohezion.datamesh.schema",
    "UnifiedRecord": "cohezion.datamesh.schema",
}

# Unchanged from the eager version: audio_telemetry + the datamesh/ orphan types.
__all__: list[str] = [
    "AudioSegmentMetadata",
    "AudioTelemetryEvent",
    "BirdSpeciesNode",
    "SpectrogramConfig",
    "TaxonomyLevel",
    "DataLineage",
    "DomainEndpoint",
    "FederationLayer",
    "Physics12D",
    "RecordType",
    "UnifiedRecord",
]


def __getattr__(name: str) -> Any:
    """Resolve a re-export (or a not-yet-imported submodule) on first access."""
    module_name = _LAZY_EXPORTS.get(name)
    try:
        if module_name is None:
            # Submodule attribute access (`cohezion.data_mesh.kanban_bridge`) used to work
            # because the eager imports loaded the submodules as a side effect.
            if name.startswith("_"):
                raise AttributeError(name)
            value: Any = importlib.import_module(f"{__name__}.{name}")
        else:
            value = getattr(importlib.import_module(module_name), name)
    except ModuleNotFoundError as exc:
        if module_name is None and exc.name == f"{__name__}.{name}":
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
        logger.debug("data_mesh: %s unavailable (%s: %s)", name, type(exc).__name__, exc)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    except Exception as exc:  # a broken optional dep (e.g. torch) must not break the package
        logger.debug("data_mesh: %s unavailable (%s: %s)", name, type(exc).__name__, exc)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    globals()[name] = value  # cache: later lookups bypass __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


if TYPE_CHECKING:  # static import edges only; never executed
    from cohezion.data_mesh.audio_telemetry import AudioSegmentMetadata as AudioSegmentMetadata
    from cohezion.data_mesh.audio_telemetry import AudioTelemetryEvent as AudioTelemetryEvent
    from cohezion.data_mesh.audio_telemetry import BirdSpeciesNode as BirdSpeciesNode
    from cohezion.data_mesh.audio_telemetry import SpectrogramConfig as SpectrogramConfig
    from cohezion.data_mesh.audio_telemetry import TaxonomyLevel as TaxonomyLevel
    from cohezion.data_mesh.data_product import DataProduct as DataProduct
    from cohezion.data_mesh.data_product import DataProductSchema as DataProductSchema
    from cohezion.data_mesh.data_product import DataProductStatus as DataProductStatus
    from cohezion.data_mesh.data_product import DataQualityTier as DataQualityTier
    from cohezion.data_mesh.data_product import get_cohezion_data_products as get_cohezion_data_products
    from cohezion.data_mesh.corpus_quality_consumer import CorpusQualityConsumer as CorpusQualityConsumer
    from cohezion.data_mesh.corpus_quality_consumer import make_corpus_quality_consumer as make_corpus_quality_consumer
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge as DataMeshEventBridge
    from cohezion.data_mesh.event_bridge import make_event_bridge as make_event_bridge
    from cohezion.data_mesh.journey_telemetry import FlumeJourneyEvent as FlumeJourneyEvent
    from cohezion.data_mesh.journey_telemetry import HardwareTier as HardwareTier
    from cohezion.data_mesh.journey_telemetry import QuadratureFabrics as QuadratureFabrics
    from cohezion.data_mesh.lemonade_multimodal import LemonadeMultimodalClient as LemonadeMultimodalClient
    from cohezion.data_mesh.universe_telemetry import UniverseStateEvent as UniverseStateEvent
    from cohezion.data_mesh.gaia_domain_agent import GaiaDataAgent as GaiaDataAgent
    from cohezion.data_mesh.gap_miner import GapMiner as GapMiner
    from cohezion.data_mesh.gap_miner import make_gap_miner as make_gap_miner
    from cohezion.data_mesh.gaia_agent_roster import DEFAULT_AGENT_SPECS as DEFAULT_AGENT_SPECS
    from cohezion.data_mesh.gaia_agent_roster import AgentSpec as AgentSpec
    from cohezion.data_mesh.gaia_agent_roster import GaiaAgentRoster as GaiaAgentRoster
    from cohezion.data_mesh.gaia_agent_roster import deploy_gaia_agent_roster as deploy_gaia_agent_roster
    from cohezion.data_mesh.kanban_bridge import backfill_items as backfill_items
    from cohezion.data_mesh.kanban_bridge import persist_item as persist_item
    from cohezion.datamesh.federation import DomainEndpoint as DomainEndpoint
    from cohezion.datamesh.federation import FederationLayer as FederationLayer
    from cohezion.datamesh.schema import DataLineage as DataLineage
    from cohezion.datamesh.schema import Physics12D as Physics12D
    from cohezion.datamesh.schema import RecordType as RecordType
    from cohezion.datamesh.schema import UnifiedRecord as UnifiedRecord
