"""work-queue POST must honour a caller-supplied priority (ticket 99569e2433f1).

The datamesh EventConsumer publishes events carrying a priority, but every
work item was created at the hardcoded default — blocking findings (priority 2)
were indistinguishable from routine ones in triage.

Client-side fix alone was insufficient: WorkItemCreate had no ``priority`` field,
so Pydantic silently dropped it and ``create_item`` hardcoded 1. Caught by an
un-mocked probe against the live API, not by mocked unit tests.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# `cohezion.api.work_queue_router` as an attribute resolves to the exported
# APIRouter object, which shadows the module — import the module explicitly.
wqr = importlib.import_module("cohezion.api.work_queue_router")


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Isolated queue file so tests never touch ~/.cohezion/work-queue.json."""
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


def test_post_honours_supplied_priority(client):
    """DISCRIMINATING: priority=2 must survive creation.

    The plausible-wrong impl (hardcoded `"priority": 1`, or a model without the
    field) returns 1 here and fails.
    """
    resp = client.post(
        "/api/work-queue",
        json={"title": "blocking finding", "type": "improvement", "priority": 2},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["priority"] == 2, f"priority dropped on create: {resp.json()}"


def test_post_without_priority_defaults_to_one(client):
    """Backward compat: existing callers that omit priority are unaffected."""
    resp = client.post("/api/work-queue", json={"title": "routine item"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["priority"] == 1


def test_posted_priority_is_readable_from_the_list(client):
    """The stored value — not just the response echo — must carry the priority."""
    item_id = client.post("/api/work-queue", json={"title": "blocking", "priority": 2}).json()["id"]
    listed = client.get("/api/work-queue").json()
    items = listed if isinstance(listed, list) else listed.get("items", [])
    stored = next(i for i in items if i["id"] == item_id)
    assert stored["priority"] == 2
