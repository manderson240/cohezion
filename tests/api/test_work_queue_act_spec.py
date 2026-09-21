"""A work-queue card can carry an ACT spec (oracle_test + edit scope) to the compound loop.

Additive contract: cards filed without an oracle keep their exact prior shape (no new
keys), so existing rows need no migration. The feeder forwards the spec only when set.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cohezion.compound.compound_feeder import _item_to_task


wqr = importlib.import_module("cohezion.api.work_queue_router")
SPEC = {
    "oracle_test": "tests/test_mod.py::test_v",
    "edit_file": "src/pkg/mod.py",
    "edit_targets": ["value"],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


def test_post_keeps_act_spec(client):
    resp = client.post("/api/work-queue", json={"title": "fix value", **SPEC})
    assert resp.status_code == 201, resp.text
    assert {k: resp.json()[k] for k in SPEC} == SPEC


def test_post_without_spec_adds_no_keys(client):
    item = client.post("/api/work-queue", json={"title": "plain"}).json()
    assert not set(SPEC) & set(item)


def test_patch_attaches_spec_to_existing_card(client):
    item = client.post("/api/work-queue", json={"title": "plain"}).json()
    patched = client.patch(f"/api/work-queue/{item['id']}", json=SPEC).json()
    assert {k: patched[k] for k in SPEC} == SPEC


def test_feeder_forwards_spec_only_when_present():
    with_spec = _item_to_task({"id": "a", "title": "t", **SPEC}, 1)
    assert {k: with_spec[k] for k in SPEC} == SPEC
    assert not set(SPEC) & set(_item_to_task({"id": "b", "title": "t"}, 2))
