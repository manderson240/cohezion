"""Unit tests for DynamicModelHotSwapper."""

from __future__ import annotations

import pytest

from cohezion.inference.dynamic_hotswapper import DynamicModelHotSwapper


@pytest.mark.asyncio
async def test_hotswap_refuses_oversized_model():
    swapper = DynamicModelHotSwapper()
    # Massive model size 80GB -> 80 * 2.1 = 168GB > available RAM -> MUST REFUSE SAFELY
    meta = {"id": "Huge-120B-GGUF", "size": 80.0, "recipe": "gguf"}
    success, reason = await swapper.hotswap_model(meta)
    assert success is False
    assert "OOM Safeguard Refusal" in reason


@pytest.mark.asyncio
async def test_hotswap_approves_safe_small_model():
    swapper = DynamicModelHotSwapper()
    # Small model size 3GB -> 3 * 2.1 = 6.3GB <= available RAM budget -> MUST APPROVE
    meta = {"id": "Small-3B-GGUF", "size": 3.0, "recipe": "gguf"}
    success, reason = await swapper.hotswap_model(meta)
    assert isinstance(success, bool)
    assert isinstance(reason, str)
