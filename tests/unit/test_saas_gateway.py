"""Unit tests for SaaS Gateway commercial endpoints."""

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app

client = TestClient(app)


def test_saas_pricing_tiers():
    """Verify SaaS pricing tiers structure and SLA guarantees."""
    resp = client.get("/v1/saas/tiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "tiers" in data
    assert len(data["tiers"]) == 3
    tiers = {t["id"]: t for t in data["tiers"]}
    assert "starter" in tiers
    assert "pro" in tiers
    assert "enterprise" in tiers
    assert tiers["starter"]["price_usd_monthly"] == 49
    assert tiers["pro"]["price_usd_monthly"] == 149
    assert tiers["enterprise"]["price_usd_monthly"] == 499


def test_code_audit_auth_rejection():
    """Verify unauthorized requests are rejected."""
    resp = client.post("/v1/audit/code", json={"code": "print('hi')"})
    assert resp.status_code in (401, 403)


def test_code_audit_vulnerable_code():
    """Verify dangerous code is flagged with non-zero risk score."""
    resp = client.post(
        "/v1/audit/code",
        headers={"Authorization": "Bearer czn_live_master_2026"},
        json={"code": "def run(x):\n    return eval(x)"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "flagged"
    assert data["risk_score"] > 0.0
    assert data["autoharness_verified"] is False
    assert len(data["violations"]) > 0


def test_code_audit_clean_code():
    """Verify clean code passes verification with zero violations."""
    resp = client.post(
        "/v1/audit/code",
        headers={"Authorization": "Bearer czn_live_master_2026"},
        json={"code": "def add(a: int, b: int) -> int:\n    return a + b"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "passed"
    assert data["risk_score"] == 0.0
    assert data["autoharness_verified"] is True
    assert len(data["violations"]) == 0
    assert "zkfv_polynomial_root" in data
