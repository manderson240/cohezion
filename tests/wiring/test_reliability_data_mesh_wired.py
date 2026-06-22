"""Discriminating identity tests: reliability and data_mesh orphans wired round-5."""

from cohezion.data_mesh import CorpusQualityConsumer as pkg_cqc
from cohezion.data_mesh import DataMeshEventBridge as pkg_emb
from cohezion.data_mesh import DataProduct as pkg_dp
from cohezion.data_mesh import FlumeJourneyEvent as pkg_fje
from cohezion.data_mesh import UniverseStateEvent as pkg_use
from cohezion.data_mesh.corpus_quality_consumer import (
    CorpusQualityConsumer as src_cqc,
)
from cohezion.data_mesh.data_product import DataProduct as src_dp
from cohezion.data_mesh.event_bridge import DataMeshEventBridge as src_emb
from cohezion.data_mesh.journey_telemetry import FlumeJourneyEvent as src_fje
from cohezion.data_mesh.universe_telemetry import UniverseStateEvent as src_use
from cohezion.reliability import BlackwellHandshake as pkg_bwh
from cohezion.reliability import FileLock as pkg_fl
from cohezion.reliability import ResourceGuard as pkg_rg
from cohezion.reliability.blackwell_handshake import BlackwellHandshake as src_bwh
from cohezion.reliability.resource_guard import ResourceGuard as src_rg
from cohezion.reliability.sync import FileLock as src_fl


def test_data_product_is_same():
    assert pkg_dp is src_dp


def test_corpus_quality_consumer_is_same():
    assert pkg_cqc is src_cqc


def test_event_bridge_is_same():
    assert pkg_emb is src_emb


def test_flume_journey_event_is_same():
    assert pkg_fje is src_fje


def test_universe_state_event_is_same():
    assert pkg_use is src_use


def test_blackwell_handshake_is_same():
    assert pkg_bwh is src_bwh


def test_resource_guard_is_same():
    assert pkg_rg is src_rg


def test_file_lock_is_same():
    assert pkg_fl is src_fl


def test_data_product_instantiable():
    """Discriminating: DataProduct must be constructible with required fields."""
    from cohezion.data_mesh.data_product import (
        DataProductSchema,
        DataProductStatus,
        DataQualityTier,
    )

    dp = src_dp(
        product_id="test-001",
        name="test",
        owner_domain="cohezion.test",
        description="test product",
        status=DataProductStatus.ACTIVE,
        quality_tier=DataQualityTier.BRONZE,
        schema=DataProductSchema(fields={}),
    )
    assert dp.product_id == "test-001"
    assert dp.owner_domain == "cohezion.test"
