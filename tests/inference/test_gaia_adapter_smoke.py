"""Structural smoke tests for amd-gaia 0.21.1 integration.

Validates that:
  - The installed gaia.llm.lemonade_client module is importable.
  - build_gaia_llm_tier() returns a GaiaAgentTier (factory wiring).
  - _GaiaLLMClientShim.prompt() calls chat_completions (not the text-completions
    sibling or any other method) with the correct kwargs.

All LemonadeClient instances are mocked — no real Lemonade endpoints are hit.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cohezion.inference.gaia_adapter import GaiaAgentTier, _GaiaLLMClientShim, build_gaia_llm_tier


# ── Test 1: importability ─────────────────────────────────────────────────────


def test_gaia_importable() -> None:
    """gaia.llm.lemonade_client.LemonadeClient must be importable after install."""
    # No mock — this is an install-check; we want the real import to succeed.
    from gaia.llm.lemonade_client import LemonadeClient

    assert LemonadeClient is not None


# ── Test 2: build_gaia_llm_tier factory ──────────────────────────────────────


def test_build_gaia_llm_tier_returns_gaia_agent_tier() -> None:
    """build_gaia_llm_tier() wraps a mocked LemonadeClient in a GaiaAgentTier."""
    # Patch at the module level where LemonadeClient lives so the function-local
    # import picks up the mock (same target proven by test_build_llm_tier_defaults_to_fleet_router).
    with patch("gaia.llm.lemonade_client.LemonadeClient") as MockClient:
        MockClient.return_value = MagicMock()
        tier = build_gaia_llm_tier("Granite-4.1-8B-GGUF")

    assert isinstance(tier, GaiaAgentTier)
    assert tier.label == "gaia-llm:Granite-4.1-8B-GGUF"
    # Factory must point at the fleet router, not a raw model port
    init_kwargs = MockClient.call_args.kwargs
    assert "13305" in init_kwargs.get("base_url", ""), (
        f"Expected router :13305 in base_url, got: {init_kwargs}"
    )


# ── Test 3: shim calls the correct method (discriminating) ───────────────────


def test_shim_prompt_calls_correct_method() -> None:
    """_GaiaLLMClientShim.prompt() must call chat_completions, NOT completions.

    Discriminating test: the most plausible wrong implementation calls
    client.completions() (the text-completion sibling). We assert:
      - chat_completions is called exactly once
      - completions is NOT called
      - model, messages, max_tokens, and temperature are forwarded correctly
    """
    mock_client = MagicMock()
    mock_client.chat_completions.return_value = {
        "choices": [{"message": {"content": "Berlin"}, "finish_reason": "stop"}]
    }

    shim = _GaiaLLMClientShim(
        mock_client,
        "Granite-4.1-8B-GGUF",
        max_tokens=64,
        temperature=0.1,
    )
    result = shim.prompt("capital of Germany?")

    # Must use chat_completions, not the text-completion sibling
    mock_client.chat_completions.assert_called_once()
    mock_client.completions.assert_not_called()

    # Verify the response content is extracted correctly
    assert result == "Berlin"

    # Verify kwargs forwarded to chat_completions
    call_kwargs = mock_client.chat_completions.call_args.kwargs
    assert call_kwargs["model"] == "Granite-4.1-8B-GGUF"
    assert call_kwargs["messages"] == [{"role": "user", "content": "capital of Germany?"}]
    assert call_kwargs["max_tokens"] == 64
    assert call_kwargs["temperature"] == 0.1
    # 0.21.1 OOM safety: auto_download must be False (fleet already running)
    assert call_kwargs.get("auto_download") is False, (
        "auto_download must be False to prevent OOM-dangerous model downloads via :13305 (N3)"
    )
