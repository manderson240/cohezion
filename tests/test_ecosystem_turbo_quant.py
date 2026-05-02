import pytest

from cohezion.swarm.providers.lemonade_provider import LemonadeProvider
from cohezion.swarm.providers.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_lemonade_provider_turbo_quant_flag():
    """
    RED PHASE: Verify LemonadeProvider can accept and handle turbo_quant flag.
    Currently expected to FAIL or ignore the flag.
    """
    provider = LemonadeProvider()
    # Mocking or actual check depending on how much we want to test live
    # For now, we test the interface/acceptance of the parameter
    response = await provider.generate(
        prompt="Test", model="Gemma-4-E2B", turbo_quant={"enabled": True, "precision": "3.5-bit"}
    )
    # If the provider doesn't support it yet, it might raise TypeError
    # or just return a standard result without performance tags.
    assert "turbo_quant" in response.metadata, "Response metadata missing turbo_quant tag"


@pytest.mark.asyncio
async def test_ollama_provider_turbo_quant_fallback():
    """
    RED PHASE: Verify OllamaProvider can handle turbo_quant fallback.
    """
    provider = OllamaProvider()
    response = await provider.generate(
        prompt="Test", model="phi4-mini", turbo_quant={"enabled": True}
    )
    assert response.success is True
