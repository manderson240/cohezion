"""Research-card honesty gates at the work-queue's single writer.

Live evidence (2026-09-21): vault kanban/e7087d5f9008.md reached APPLY/actioned with no
probe, quoted a phrase ("choice tokens") absent from its source, and 321 arXiv papers
were carded twice (arxiv.org + HF papers). Each test below fails on the pre-fix router.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cohezion.api import card_honesty as ch


wqr = importlib.import_module("cohezion.api.work_queue_router")

# Verbatim from the live e7087d5f9008 card: source description and the model's note.
_SOURCE = (
    "AI agents spend a ridiculous amount of compute generating text nobody actually "
    "needs. The decisions an agent makes along the"
)
_FABRICATED_NOTE = (
    "The paper introduces discrete non-verbal “choice tokens” or action heads "
    "that let an agent emit categorical decisions directly."
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


def _post(client, **fields):
    body = {"type": "research", "title": "t", "relevance": "APPLY", **fields}
    resp = client.post("/api/work-queue", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestProbeGate:
    def test_unprobed_research_apply_is_capped_at_monitor(self, client):
        item = _post(client, url="https://example.com/a")
        assert item["relevance"] == "MONITOR"
        assert item["relevance_claimed"] == "APPLY"

    def test_probed_research_apply_survives(self, client):
        item = _post(client, url="https://example.com/b", probe_ref="research/probe.md")
        assert item["relevance"] == "APPLY"

    def test_patch_cannot_promote_unprobed_card_to_apply(self, client):
        item = _post(client, url="https://example.com/c", relevance="MONITOR")
        patched = client.patch(f"/api/work-queue/{item['id']}", json={"relevance": "APPLY"})
        assert patched.json()["relevance"] == "MONITOR"

    def test_internal_improvement_items_are_out_of_scope(self, client):
        item = _post(client, type="improvement", url="https://example.com/d")
        assert item["relevance"] == "APPLY"

    def test_bare_actioned_patch_is_refused(self, client):
        item = _post(client, url="https://example.com/e")
        resp = client.patch(f"/api/work-queue/{item['id']}", json={"status": "actioned"})
        assert resp.status_code == 422, resp.text

    def test_actioner_patch_with_route_is_accepted(self, client):
        # Same body WorkQueueAPI.mark_actioned sends: the legitimate consumer still works.
        item = _post(client, url="https://example.com/f")
        resp = client.patch(
            f"/api/work-queue/{item['id']}",
            json={"status": "actioned", "action_route": "implement"},
        )
        assert resp.status_code == 200 and resp.json()["status"] == "actioned"


class TestDedupe:
    @pytest.mark.parametrize(
        "second_url",
        [
            "https://huggingface.co/papers/2609.19169",
            "https://arxiv.org/abs/2609.19169v3",
            "http://arxiv.org/pdf/2609.19169v1",
        ],
    )
    def test_same_arxiv_paper_is_carded_once(self, client, second_url):
        first = _post(client, url="https://arxiv.org/abs/2609.19169")
        second = _post(client, url=second_url)
        assert second["id"] == first["id"] and second["deduplicated"] is True
        assert client.get("/api/work-queue").json()["total"] == 1

    def test_different_papers_are_not_merged(self, client):
        _post(client, url="https://arxiv.org/abs/2609.19169")
        _post(client, url="https://arxiv.org/abs/2609.19170")
        assert client.get("/api/work-queue").json()["total"] == 2

    def test_canonical_id_strips_version(self):
        assert ch.canonical_paper_id("https://arxiv.org/abs/2501.00001v2") == "arxiv:2501.00001"
        assert ch.canonical_paper_id("https://thenewstack.io/kev") == ""


class TestSummaryFaithfulness:
    def test_fabricated_quote_is_marked_unfaithful(self, client):
        item = _post(client, description=_SOURCE)
        patched = client.patch(
            f"/api/work-queue/{item['id']}", json={"notes": _FABRICATED_NOTE}
        ).json()
        assert patched["quote_check"] == "fail"
        assert patched["notes"].startswith(ch.UNFAITHFUL_LABEL)

    def test_verbatim_quote_passes_and_prose_is_labelled_unverified(self, client):
        note = 'It says "generating text nobody actually needs" and proposes a fix.'
        item = _post(client, description=_SOURCE, notes=note)
        assert item["quote_check"] == "pass"
        assert item["notes"].startswith(ch.UNVERIFIED_LABEL)

    def test_unquoted_summary_is_labelled_unverified(self):
        text, check = ch.label_summary("A paraphrase with no quotes.", _SOURCE)
        assert check == "none" and text.startswith(ch.UNVERIFIED_LABEL)

    def test_labelling_is_idempotent(self):
        once, _ = ch.label_summary(_FABRICATED_NOTE, _SOURCE)
        twice, _ = ch.label_summary(once, _SOURCE)
        assert once == twice
