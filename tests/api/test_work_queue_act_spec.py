"""A work-queue card can carry an ACT spec (oracle_test + edit scope) to the compound loop.

Additive contract: cards filed without an oracle keep their exact prior shape (no new
keys), so existing rows need no migration. The feeder forwards the spec only when set.

Security finding M1 (2026-09-22): the ACT fields make the loop edit and commit code, and
any local process could POST/PATCH them. Now only a writer holding COHEZION_ACT_TOKEN
(X-Act-Token header) may set them, paths are validated server-side, and the feeder
forwards a spec only from cards the server flagged act_spec_trusted.
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


TOKEN = "t0ken-for-tests"
AUTH = {"X-Act-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("COHEZION_ACT_TOKEN", TOKEN)
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


def test_post_keeps_act_spec(client):
    resp = client.post("/api/work-queue", json={"title": "fix value", **SPEC}, headers=AUTH)
    assert resp.status_code == 201, resp.text
    assert resp.json()["act_spec_trusted"] is True
    assert {k: resp.json()[k] for k in SPEC} == SPEC


def test_post_without_spec_adds_no_keys(client):
    item = client.post("/api/work-queue", json={"title": "plain"}).json()
    assert not set(SPEC) & set(item)


def test_patch_attaches_spec_to_existing_card(client):
    item = client.post("/api/work-queue", json={"title": "plain"}).json()
    patched = client.patch(f"/api/work-queue/{item['id']}", json=SPEC, headers=AUTH).json()
    assert {k: patched[k] for k in SPEC} == SPEC


def test_feeder_forwards_spec_only_when_present():
    with_spec = _item_to_task({"id": "a", "title": "t", "act_spec_trusted": True, **SPEC}, 1)
    assert {k: with_spec[k] for k in SPEC} == SPEC
    assert not set(SPEC) & set(_item_to_task({"id": "b", "title": "t"}, 2))


# ---------------------------------------------------------------- M1 exploit tests
def test_post_act_spec_without_token_is_refused_and_not_stored(client):
    resp = client.post("/api/work-queue", json={"title": "fix value", **SPEC})
    assert resp.status_code == 403, resp.text
    assert client.get("/api/work-queue").json()["total"] == 0


def test_patch_act_spec_with_wrong_token_is_refused(client):
    item = client.post("/api/work-queue", json={"title": "plain"}).json()
    resp = client.patch(f"/api/work-queue/{item['id']}", json=SPEC, headers={"X-Act-Token": "nope"})
    assert resp.status_code == 403
    stored = client.get("/api/work-queue").json()["items"][0]
    assert not set(SPEC) & set(stored)


def test_unset_token_refuses_act_fields_even_with_empty_header(client, monkeypatch):
    monkeypatch.delenv("COHEZION_ACT_TOKEN")
    resp = client.post("/api/work-queue", json={"title": "x", **SPEC}, headers={"X-Act-Token": ""})
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "bad",
    [
        {"edit_file": "src/../cloud-vault-mcp/src/mcp_server/auth.py"},
        {"oracle_test": "/tmp/x_test.py"},
        {"edit_targets": ["value\nCo-Authored-By: x"]},
    ],
)
def test_trusted_writer_still_gets_paths_validated(client, bad):
    resp = client.post("/api/work-queue", json={"title": "x", **SPEC, **bad}, headers=AUTH)
    assert resp.status_code == 422, resp.text


def test_feeder_drops_spec_from_untrusted_card():
    task = _item_to_task({"id": "a", "title": "t", **SPEC}, 1)
    assert not set(SPEC) & set(task)
