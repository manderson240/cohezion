"""Discriminating tests for the ``_offline_fuse`` autouse fixture in conftest.py.

The fuse exists so the compound suite's results do not depend on whether Lemonade
(:13305) and SurrealDB (:8001) happen to be running. A fuse that is merely *declared*
proves nothing, so each test below is written against the most plausible WRONG
implementation:

* Patching ``lemonade_available`` at an *importer* module instead of its definition
  module — the production call sites use function-local imports, so an importer-level
  patch is a no-op and the consumer would still reach the network.
* Forgetting ``autouse=True`` — every assertion here would see the real objects.
* Exempting nothing, which would leave no tier that ever exercises the live wiring.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.compound import local_inference
from cohezion.compound import prompt_version_registry as pvr
from cohezion.compound import qa_gate
from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

from .conftest import _DEAD_LEMONADE_URL, _DEAD_SURREAL_URL


def test_lemonade_available_is_fused_at_its_definition_module() -> None:
    """The patch must land where the function is DEFINED, not where it is imported.

    Every production call site (``compound/__init__.py``, ``lemonade_world_model.py``,
    ``cohezion_state.py``) imports this name inside a function body, so definition-site
    patching is the only variant that reaches all of them.
    """
    assert isinstance(local_inference.lemonade_available, MagicMock)
    assert local_inference.lemonade_available(npu_port=13305) is False


def test_jepa_gate_consumer_sees_the_fuse() -> None:
    """CONSUMPTION check: the real production factory must fall back to no world model.

    This is the assertion that discriminates a definition-site patch from an
    importer-site one. With the service UP and the fuse mis-targeted,
    ``build_live_jepa_gate`` wires a live LLM-backed world model and this fails.
    (With the service DOWN it would pass either way — the test has full teeth only on
    a live box, which is exactly when the non-hermeticity bites.)
    """
    from cohezion.compound.lemonade_world_model import build_live_jepa_gate

    gate = build_live_jepa_gate()

    assert gate._world_model is None


def test_embed_bridge_reports_unavailable() -> None:
    """``JourneyTracker.__init__`` probes this on EVERY instantiation."""
    assert LemonadeEmbedBridge().is_available() is False


@pytest.mark.parametrize("module", [pvr, qa_gate])
def test_surreal_url_is_redirected_away_from_production(module) -> None:
    """``refine()``'s fixture bootstrap wrote rows into the PRODUCTION table.

    Because the bootstrap short-circuits when rows exist, that write made run N take a
    different branch than run N-1 of identical code — the specific defect that made a
    pass-to-pass baseline unobtainable.
    """
    assert module._SURREAL_URL == _DEAD_SURREAL_URL
    assert "8001" not in module._SURREAL_URL


def test_lemonade_chat_endpoint_is_redirected() -> None:
    """The 180s ``_fast_local_chat`` bound is the audit's mechanism C.

    ``_fast_local_chat`` posts to ``_FAST_CHAT_URL`` with NO ``lemonade_available``
    gate, so the fuse's ``lemonade_available`` patch does not stop it. Left live, a
    single ``refine()`` fixture bootstrap can block for three minutes.
    """
    assert pvr._FAST_CHAT_URL == _DEAD_LEMONADE_URL
    assert "13305" not in pvr._FAST_CHAT_URL
    assert "13305" not in pvr._EMBED_URL


def test_frontier_oracle_is_fused_off() -> None:
    """The real source of the multi-minute stalls.

    ``refine()`` -> ``_adversarial_review_gate`` runs a CLOUD cascade
    (Fable -> Opus -> ``agy``) through ``subprocess.run``, each leg bounded at 90s.
    Measured before this fuse: ``test_failed_bootstrap_leaves_gate_failopen`` alone took
    243.62s; the whole file took 246.60s and now takes 2.67s.

    No HTTP-level mock can catch this — it shells out to CLI binaries, so it is
    invisible to httpx/urllib patching.
    """
    from cohezion.inference import frontier_oracle

    with pytest.raises(RuntimeError, match="fused off"):
        frontier_oracle.frontier_complete_sync("ping")


@pytest.mark.integration
def test_integration_marked_tests_are_exempt_from_the_fuse() -> None:
    """The live tier must keep its teeth.

    Landing the fuse without an exempt tier would convert JG3-class wiring regressions
    into invisible ones. This asserts the exemption branch actually fires — it does not
    call the function, so no network request is made.
    """
    assert not isinstance(local_inference.lemonade_available, MagicMock)
    assert pvr._SURREAL_URL != _DEAD_SURREAL_URL
