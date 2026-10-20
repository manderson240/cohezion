"""The actioner must never overwrite a card's analysis notes.

Regression guard for a live data-loss defect: ``WorkQueueAPI.mark_actioned`` PATCHed
``notes`` with a 50-character status string ("actioned via <route> route ..."), so
actioning a card destroyed the research analysis stored there. Measured on the running
queue: **764 of 6,110 cards** had their notes replaced, including four whose multi-
kilobyte findings were authored the same day.

Why the existing suite missed it: ``tests/unit/test_actioner_engine.py`` uses a fake
``mark_actioned(item_id, note)`` that records the call and returns a stub. A test double
standing in for the mutation path cannot reveal what that path does to stored state -- the
suite stayed green while the bug shipped.

These tests therefore target the SEAM that broke: the PATCH body the caller emits, and
that body applied by the REAL router handler.
"""

from __future__ import annotations

import importlib
import json

import pytest

from cohezion.actioner.engine import WorkQueueAPI


# NOT `from cohezion.api import work_queue_router` -- the package __init__ re-exports the
# APIRouter OBJECT under that name, which shadows the module and yields an APIRouter here.
wq = importlib.import_module("cohezion.api.work_queue_router")


ANALYSIS = "REAL ANALYSIS: " + ("finding " * 200)  # stands in for a research digest


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the real router at a temp store so nothing touches ~/.cohezion."""
    path = tmp_path / "work-queue.json"
    path.write_text(json.dumps({"items": [], "version": 1}))
    monkeypatch.setattr(wq, "WORK_QUEUE_FILE", path)
    monkeypatch.setattr(wq, "_persist", lambda item: None)  # no SurrealDB/Obsidian in unit tests
    return path


def _capture_patch_body(monkeypatch) -> dict:
    """Run mark_actioned and return the PATCH body it emits, without any network."""
    sent: dict = {}

    def fake_request(self, method, path, body=None):
        sent.update({"method": method, "path": path, "body": body})
        return {}

    monkeypatch.setattr(WorkQueueAPI, "_request", fake_request)
    WorkQueueAPI(base_url="http://localhost:8080").mark_actioned("card-1", route="experiment")
    return sent


class TestActionerDoesNotClobberNotes:
    def test_mark_actioned_patch_body_omits_notes(self, monkeypatch):
        """DISCRIMINATING: fails on the old code, which sent notes=<status string>.

        This is the invariant at the source. Even if the router changes, a caller that
        puts bookkeeping into a content field is the defect.
        """
        sent = _capture_patch_body(monkeypatch)
        body = sent["body"]

        assert "notes" not in body, f"mark_actioned must not write the content field; body={body!r}"
        assert body["status"] == "actioned"
        assert body["action_route"] == "experiment", "the route must still be recorded somewhere"

    def test_real_router_preserves_analysis_when_that_body_is_applied(self, store, monkeypatch):
        """DISCRIMINATING end-to-end: the emitted body, applied by the REAL handler.

        Composes the two halves across the seam that actually failed -- no fake stands in
        for either side. Under the old body this leaves ~50 chars where the analysis was.
        """
        created = wq.create_item(
            wq.WorkItemCreate(type="research", title="card under test", notes=ANALYSIS)
        )
        # control: the store round-trips content at all (research notes gain an additive
        # "[model summary, unverified]" label from card_honesty; the content is intact)
        assert created["notes"].endswith(ANALYSIS)

        body = _capture_patch_body(monkeypatch)["body"]
        patched = wq.patch_item(created["id"], wq.WorkItemPatch(**body))

        assert patched["notes"] == created["notes"], "actioning a card destroyed its analysis"
        assert patched["status"] == "actioned"
        assert patched["action_route"] == "experiment"

    def test_notes_are_still_writable_when_explicitly_patched(self, store):
        """The fix must not make notes read-only -- triage legitimately writes them.

        Without this, 'never touch notes' could be satisfied by breaking the field, which
        would pass the two tests above for entirely the wrong reason.
        """
        created = wq.create_item(wq.WorkItemCreate(type="research", title="t", notes="old"))
        patched = wq.patch_item(created["id"], wq.WorkItemPatch(notes="deliberately updated"))
        assert patched["notes"].endswith("deliberately updated")


def _apply_triage_call(store, monkeypatch, call) -> dict:
    """Create a card with ANALYSIS, run a triage client call, apply its body via the real router."""
    # probe_ref licenses APPLY under card honesty (fix/research-card-honesty), so the
    # mark_reviewed(relevance="APPLY") assertion below tests notes preservation only.
    created = wq.create_item(
        wq.WorkItemCreate(type="research", title="t", notes=ANALYSIS, probe_ref="probe/test")
    )
    sent: dict = {}

    def fake_request(self, method, path, body=None):
        sent.update(body or {})
        return {}

    monkeypatch.setattr(WorkQueueAPI, "_request", fake_request)
    call(WorkQueueAPI(base_url="http://localhost:8080"), created["id"])
    assert "notes" not in sent, f"triage must not overwrite the content field; body={sent!r}"
    return wq.patch_item(created["id"], wq.WorkItemPatch(**sent))


class TestTriageDoesNotClobberNotes:
    """Same defect class as mark_actioned: mark_rejected/mark_reviewed PATCHed notes=<reason>."""

    def test_mark_rejected_keeps_analysis_and_records_reason(self, store, monkeypatch):
        patched = _apply_triage_call(
            store, monkeypatch, lambda api, i: api.mark_rejected(i, note="rejected by guardrail: X")
        )
        assert ANALYSIS in patched["notes"], "rejecting a card destroyed its analysis"
        assert "rejected by guardrail: X" in patched["notes"]
        assert patched["status"] == "rejected"

    def test_mark_reviewed_keeps_analysis_and_records_reason(self, store, monkeypatch):
        patched = _apply_triage_call(
            store,
            monkeypatch,
            lambda api, i: api.mark_reviewed(i, relevance="APPLY", note="triage: applies to X"),
        )
        assert ANALYSIS in patched["notes"], "reviewing a card destroyed its analysis"
        assert "triage: applies to X" in patched["notes"]
        assert patched["status"] == "reviewed"
        assert patched["relevance"] == "APPLY"

    def test_notes_append_on_empty_notes_has_no_leading_separator(self, store):
        created = wq.create_item(wq.WorkItemCreate(type="research", title="t"))
        patched = wq.patch_item(created["id"], wq.WorkItemPatch(notes_append="reason"))
        assert patched["notes"] == "reason"
