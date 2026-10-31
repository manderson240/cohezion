"""Concierge degrades to keyword routing, visibly, when the text latent is unavailable."""

import logging

from cohezion.flume.canonical_latent import TextLatentUnavailable
from cohezion.governance import concierge as concierge_mod


def test_route_prompt_falls_back_to_keywords_and_warns(monkeypatch, caplog):
    def _boom(_text):
        raise TextLatentUnavailable("no weights")

    monkeypatch.setattr(concierge_mod, "FLUME_AVAILABLE", True)
    monkeypatch.setattr(concierge_mod, "encode_prompt", _boom, raising=False)
    c = concierge_mod.ConciergeAgent.__new__(concierge_mod.ConciergeAgent)
    c._history = []
    with caplog.at_level(logging.WARNING, logger=concierge_mod.logger.name):
        out = c.route_prompt("work on the genesis rendering", concierge_mod.SessionBriefing())
    assert out is not None
    assert any("semantic routing skipped" in r.message for r in caplog.records)
