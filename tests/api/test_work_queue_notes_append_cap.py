"""notes_append is length-capped (security review minor, 2026-09-22).

THE DEFECT: PATCH notes_append had no cap. Each append rewrites the whole queue file under
the lock, so one caller could grow every later read-modify-write without bound.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


wqr = importlib.import_module("cohezion.api.work_queue_router")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(wqr, "WORK_QUEUE_FILE", tmp_path / "work-queue.json")
    monkeypatch.setattr(wqr, "_persist", lambda _item: None)
    app = FastAPI()
    app.include_router(wqr.router)
    return TestClient(app)


def test_oversized_notes_append_is_rejected_and_not_stored(client):
    item = client.post("/api/work-queue", json={"title": "t"}).json()
    resp = client.patch(f"/api/work-queue/{item['id']}", json={"notes_append": "x" * 100_000})
    assert resp.status_code == 422
    assert client.get("/api/work-queue").json()["items"][0]["notes"] == ""


def test_normal_notes_append_still_works(client):
    item = client.post("/api/work-queue", json={"title": "t"}).json()
    resp = client.patch(f"/api/work-queue/{item['id']}", json={"notes_append": "reason"})
    assert resp.status_code == 200 and resp.json()["notes"] == "reason"
