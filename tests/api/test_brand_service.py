"""Tests for the Brand API service."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    from cohezion.api.services.brand import brand_router

    app = FastAPI()
    app.include_router(brand_router, prefix="/api/brand")
    return TestClient(app)


class TestBrandThemeEndpoint:
    def test_get_theme_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/brand/theme")
        assert resp.status_code == 200

    def test_theme_has_colors(self, client: TestClient) -> None:
        data = client.get("/api/brand/theme").json()
        assert "colors" in data
        assert data["colors"]["nexus_green"] == "#00FF00"
        assert data["colors"]["matte_black"] == "#0A0A0A"
        assert data["colors"]["earth_blue"] == "#0077BE"

    def test_theme_has_identity(self, client: TestClient) -> None:
        data = client.get("/api/brand/theme").json()
        assert "identity" in data
        assert data["identity"]["name"] == "COHEZION"
        assert data["identity"]["tagline"] == "The Nexus of Coherence"

    def test_theme_has_hiho_palette(self, client: TestClient) -> None:
        """HIHO palette maps coherence zones to colors for the CSS bridge."""
        data = client.get("/api/brand/theme").json()
        assert "hiho_palette" in data
        palette = data["hiho_palette"]
        assert "critical_low" in palette
        assert "warning" in palette
        assert "stable" in palette
        assert "critical_high" in palette
