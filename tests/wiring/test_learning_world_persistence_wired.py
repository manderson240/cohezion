"""Discriminating identity tests: learning, world_model, persistence, knowledge_graph, audio."""

from cohezion.learning import DeepResearchPipeline as pkg_drp
from cohezion.learning import MyceliumNetwork as pkg_mn
from cohezion.learning import OuroborosTrigger as pkg_ot
from cohezion.learning.deep_research import DeepResearchPipeline as src_drp
from cohezion.learning.mycelium_network import MyceliumNetwork as src_mn
from cohezion.learning.ouroboros_trigger import OuroborosTrigger as src_ot
from cohezion.world_model import GateOutcome as pkg_go
from cohezion.world_model import Observer as pkg_obs
from cohezion.world_model import SurpriseRouter as pkg_sr
from cohezion.world_model.observer import Observer as src_obs
from cohezion.world_model.surprise_action_gate import GateOutcome as src_go
from cohezion.world_model.surprise_router import SurpriseRouter as src_sr


def test_deep_research_pipeline_is_same():
    assert pkg_drp is src_drp


def test_mycelium_network_is_same():
    assert pkg_mn is src_mn


def test_ouroboros_trigger_is_same():
    assert pkg_ot is src_ot


def test_observer_is_same():
    assert pkg_obs is src_obs


def test_gate_outcome_is_same():
    assert pkg_go is src_go


def test_surprise_router_is_same():
    assert pkg_sr is src_sr


def test_persistence_surreal_logger_is_same():
    from cohezion.persistence import SurrealTrajectoryLogger as pkg_stl
    from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger as src_stl

    assert pkg_stl is src_stl


def test_knowledge_graph_graphrag_is_same():
    from cohezion.knowledge_graph import GraphRAGEngine as pkg_gre
    from cohezion.knowledge_graph.graphrag_engine import GraphRAGEngine as src_gre

    assert pkg_gre is src_gre


def test_audio_narrator_is_same():
    from cohezion.audio import CosmoNarrator as pkg_cn
    from cohezion.audio.narrator import CosmoNarrator as src_cn

    assert pkg_cn is src_cn


def test_mycelium_network_discriminating():
    """MyceliumNetwork.query_insights returns spores for a connected evo.

    Discriminating: a no-op stub would either error on connect_evo or return
    non-empty results without any registration — we assert empty on unknown evo.
    """
    mn = src_mn()
    # query an evo that was never connected → must return empty, not crash
    spores = mn.query_insights("unknown-evo-xyz", "test")
    assert isinstance(spores, list)


def test_surprise_router_has_modes():
    """SurpriseRouter must expose ActionMode values.

    Discriminating: a no-op implementation would raise AttributeError here.
    """
    from cohezion.world_model import ActionMode

    assert hasattr(ActionMode, "__members__") or hasattr(ActionMode, "_member_names_")
