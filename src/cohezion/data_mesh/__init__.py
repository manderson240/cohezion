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

import contextlib
import logging


logger = logging.getLogger(__name__)


# Wiring-sweep 2026-06-06: audio_telemetry was a genuine production orphan — its bioacoustic
# schema (TaxonomyLevel / BirdSpeciesNode / AudioSegmentMetadata / SpectrogramConfig /
# AudioTelemetryEvent, the BirdCLEF-2026 telemetry data product) had ZERO importers anywhere
# (the one "audio_telemetry" hit in learning/ouroboros.py is a method NAME, not an import).
# Guarded re-export (pydantic is a hard dep; suppress keeps the package importable if it is
# ever absent) puts the data product on the package surface and makes it statically reachable.
__all__: list[str] = []

with contextlib.suppress(Exception):
    from cohezion.data_mesh.audio_telemetry import (
        AudioSegmentMetadata as AudioSegmentMetadata,
    )
    from cohezion.data_mesh.audio_telemetry import (
        AudioTelemetryEvent as AudioTelemetryEvent,
    )
    from cohezion.data_mesh.audio_telemetry import (
        BirdSpeciesNode as BirdSpeciesNode,
    )
    from cohezion.data_mesh.audio_telemetry import (
        SpectrogramConfig as SpectrogramConfig,
    )
    from cohezion.data_mesh.audio_telemetry import (
        TaxonomyLevel as TaxonomyLevel,
    )

    __all__ += [
        "AudioSegmentMetadata",
        "AudioTelemetryEvent",
        "BirdSpeciesNode",
        "SpectrogramConfig",
        "TaxonomyLevel",
    ]

# Wiring-sweep 2026-06-22: data_product.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.data_product import DataProduct as DataProduct
    from cohezion.data_mesh.data_product import DataProductSchema as DataProductSchema
    from cohezion.data_mesh.data_product import DataProductStatus as DataProductStatus
    from cohezion.data_mesh.data_product import DataQualityTier as DataQualityTier
    from cohezion.data_mesh.data_product import (
        get_cohezion_data_products as get_cohezion_data_products,
    )

# Wiring-sweep 2026-06-22: corpus_quality_consumer.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.corpus_quality_consumer import (
        CorpusQualityConsumer as CorpusQualityConsumer,
    )
    from cohezion.data_mesh.corpus_quality_consumer import (
        make_corpus_quality_consumer as make_corpus_quality_consumer,
    )

# Wiring-sweep 2026-06-22: event_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.event_bridge import (
        DataMeshEventBridge as DataMeshEventBridge,
    )
    from cohezion.data_mesh.event_bridge import (
        make_event_bridge as make_event_bridge,
    )

# Wiring-sweep 2026-06-22: journey_telemetry.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.journey_telemetry import (
        FlumeJourneyEvent as FlumeJourneyEvent,
    )
    from cohezion.data_mesh.journey_telemetry import HardwareTier as HardwareTier
    from cohezion.data_mesh.journey_telemetry import (
        QuadratureFabrics as QuadratureFabrics,
    )

# Wiring-sweep 2026-06-22: lemonade_multimodal.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.lemonade_multimodal import (
        LemonadeMultimodalClient as LemonadeMultimodalClient,
    )

# Wiring-sweep 2026-06-22: universe_telemetry.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.universe_telemetry import (
        UniverseStateEvent as UniverseStateEvent,
    )

# GaiaDataAgent: event-driven domain ownership via local GAIA inference.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.gaia_domain_agent import GaiaDataAgent as GaiaDataAgent

# GapMiner: repeated roster actions -> proactive work-queue items (endorsement-ranked).
with contextlib.suppress(Exception):
    from cohezion.data_mesh.gap_miner import GapMiner as GapMiner
    from cohezion.data_mesh.gap_miner import make_gap_miner as make_gap_miner

# GaiaAgentRoster: top-tier GAIA agents (live-catalog model selection) per mesh domain.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.gaia_agent_roster import (
        DEFAULT_AGENT_SPECS as DEFAULT_AGENT_SPECS,
    )
    from cohezion.data_mesh.gaia_agent_roster import AgentSpec as AgentSpec
    from cohezion.data_mesh.gaia_agent_roster import GaiaAgentRoster as GaiaAgentRoster
    from cohezion.data_mesh.gaia_agent_roster import (
        deploy_gaia_agent_roster as deploy_gaia_agent_roster,
    )

# KanbanBridge: write-through projection to SurrealDB + Obsidian.
with contextlib.suppress(Exception):
    from cohezion.data_mesh.kanban_bridge import backfill_items as backfill_items
    from cohezion.data_mesh.kanban_bridge import persist_item as persist_item

# Wiring-sweep 2026-08-11: promote the datamesh/ orphan types onto the canonical
# data_mesh/ surface. NON-DESTRUCTIVE — neither package is removed and no module moves;
# the two near-identically-named packages remain a live consolidation question (card
# 7e066595c8c4). This only makes the orphans reachable.
#
# This re-export IS the missing wiring, not dormancy camouflage: the real integration
# already exists and works (DataProduct.from_unified_record consumes a UnifiedRecord, and
# DataMeshEventBridge.watch_federation takes a FederationLayer). What was missing is that
# no caller could reach the INPUT types through the canonical surface, so a working
# conversion had no reachable way to be fed.
#
# Logged rather than silently suppressed. datamesh.schema transitively imports torch, so
# on a torch-free install these symbols legitimately vanish — but a bare suppress makes
# that indistinguishable from a genuine breakage, and the caller then sees only a bare
# ImportError at the use site with no indication of the cause. The blanket `Exception`
# is kept deliberately: a broken torch install can raise OSError/RuntimeError, and the
# package must stay importable either way.
try:
    from cohezion.datamesh.federation import DomainEndpoint as DomainEndpoint
    from cohezion.datamesh.federation import FederationLayer as FederationLayer
    from cohezion.datamesh.schema import DataLineage as DataLineage
    from cohezion.datamesh.schema import Physics12D as Physics12D
    from cohezion.datamesh.schema import RecordType as RecordType
    from cohezion.datamesh.schema import UnifiedRecord as UnifiedRecord

    __all__ += [
        "DataLineage",
        "DomainEndpoint",
        "FederationLayer",
        "Physics12D",
        "RecordType",
        "UnifiedRecord",
    ]
except Exception as exc:
    logger.debug(
        "data_mesh: datamesh/ orphan types unavailable (%s: %s) — FederationLayer, "
        "DomainEndpoint, UnifiedRecord, Physics12D, RecordType and DataLineage will not "
        "be importable from cohezion.data_mesh",
        type(exc).__name__,
        exc,
    )
