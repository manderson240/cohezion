"""Hermetic tests for the BAML bridge (no live network).

Mocks the generated client (_b.RecommendNextStep) so the tier-routing and
typed-output contract are verified without touching Lemonade/Ollama. The
registry construction itself is real — it proves the baml_py ClientRegistry
API shape stays compatible.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.baml import client_router


def test_registry_local_tier_points_at_lemonade() -> None:
    cr = client_router.build_registry("local")
    assert cr is not None  # real ClientRegistry built without error


def test_registry_unknown_tier_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown BAML tier"):
        client_router.build_registry("nonexistent")


def test_recommend_next_step_returns_typed_model() -> None:
    fake = MagicMock(spec=["action", "rationale", "risk_level"])
    fake.action = "add test"
    fake.rationale = "kills survivors"
    fake.risk_level = "low"
    with patch.object(client_router, "_b") as mock_b, patch.object(
        client_router, "build_registry", return_value=MagicMock()
    ) as mock_reg:
        mock_b.RecommendNextStep.return_value = fake
        out = client_router.recommend_next_step("ctx", "cand")
    assert out.action == "add test"
    assert out.risk_level == "low"
    assert mock_b.RecommendNextStep.called
    assert mock_reg.called


def test_recommend_next_step_async_returns_typed_model() -> None:
    from unittest.mock import AsyncMock

    fake = MagicMock(spec=["action", "rationale", "risk_level"])
    fake.action = "ship it"
    fake.rationale = "verified"
    fake.risk_level = "medium"
    with patch.object(client_router, "_b") as mock_b:
        mock_b.RecommendNextStep = AsyncMock(return_value=fake)
        val = asyncio.run(client_router.recommend_next_step_async("ctx", "cand"))
    assert val.action == "ship it"
    assert val.risk_level == "medium"


def test_tier_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COHEZION_BAML_TIER", "cloud")
    assert client_router._tier() == "cloud"
    monkeypatch.setenv("COHEZION_BAML_TIER", "local")
    assert client_router._tier() == "local"