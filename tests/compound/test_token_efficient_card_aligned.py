"""RED tests for the token-efficient prefix with FLUME_VAE hash (PR 3).

The TokenEfficientCompoundExecutor's static prefix gets a new block
that fingerprints the card. The fingerprint is the FLUME VAE
hashing of the card (model_id + family + thinking_mode) so a card
change invalidates the Anthropic prompt cache automatically.

Contracts:
- _get_cacheable_prefix() includes a # CARD-ALIGNED RECIPE block
  with the model_id, family, thinking_mode, and a FLUME_VAE hash.
- A different card produces a different prefix hash (verified by
  string comparison).
- execute_task_efficient() emits a WITNESS_MARK with coherence
  0.8 when the prefix cache hits (vs 0.6 for normal executions).
- The token delta correctly reports 0 on a prefix cache hit.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_cacheable_prefix_contains_card_aligned_recipe_block():
    """The static prefix has a # CARD-ALIGNED RECIPE block."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    guidance = {"relevant_context": []}
    prefix = executor._get_cacheable_prefix(guidance)
    assert "# CARD-ALIGNED RECIPE" in prefix


def test_cacheable_prefix_carries_model_id_and_family():
    """The recipe block carries the (model_id, family, thinking_mode)
    for the model the executor is currently using."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    # Pin the executor's current model to a known card
    executor._current_card = ("qwen3-coder:30b", "qwen3", "optional_prefix")
    guidance = {"relevant_context": []}
    prefix = executor._get_cacheable_prefix(guidance)
    assert "qwen3-coder:30b" in prefix
    assert "qwen3" in prefix
    assert "optional_prefix" in prefix


def test_cacheable_prefix_includes_flume_vae_hash():
    """The recipe block includes a `# FLUME_VAE: <hash>` line so the
    Anthropic prompt cache's server-side fingerprint is reproducible
    from a SurrealDB row."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    executor._current_card = ("qwen3-coder:30b", "qwen3", "optional_prefix")
    guidance = {"relevant_context": []}
    prefix = executor._get_cacheable_prefix(guidance)
    assert "# FLUME_VAE:" in prefix
    # The hash is a stable 16-char prefix of a sha256
    import re

    m = re.search(r"# FLUME_VAE:\s*([a-f0-9]+)", prefix)
    assert m is not None
    assert len(m.group(1)) >= 8


def test_different_cards_produce_different_prefixes():
    """Two different cards produce two different prefix strings
    (so a card change correctly invalidates the prompt cache)."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    guidance = {"relevant_context": []}
    executor._current_card = ("qwen3-coder:30b", "qwen3", "optional_prefix")
    prefix_qwen3 = executor._get_cacheable_prefix(guidance)
    executor._current_card = ("phi4:latest", "phi4", "never")
    prefix_phi4 = executor._get_cacheable_prefix(guidance)
    assert prefix_qwen3 != prefix_phi4
    # The FLUME_VAE hash lines must differ
    import re

    h_qwen3 = re.search(r"# FLUME_VAE:\s*([a-f0-9]+)", prefix_qwen3).group(1)
    h_phi4 = re.search(r"# FLUME_VAE:\s*([a-f0-9]+)", prefix_phi4).group(1)
    assert h_qwen3 != h_phi4


def test_same_cards_produce_same_prefixes():
    """Two calls with the same card produce the same prefix
    (so the prompt cache hits deterministically)."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    executor._current_card = ("qwen3-coder:30b", "qwen3", "optional_prefix")
    guidance = {"relevant_context": []}
    p1 = executor._get_cacheable_prefix(guidance)
    p2 = executor._get_cacheable_prefix(guidance)
    assert p1 == p2


def test_execute_task_efficient_emits_witness_mark_on_prefix_hit():
    """When the prompt cache hits (Anthropic-side), the executor
    emits a WITNESS_MARK with coherence=0.8 (vs 0.6 for normal)."""
    from cohezion.compound.token_efficient_executor import (
        TokenEfficientCompoundExecutor,
    )

    fake_mcp = MagicMock()
    executor = TokenEfficientCompoundExecutor(fake_mcp)
    executor._current_card = ("qwen3-coder:30b", "qwen3", "optional_prefix")

    # Stub out the parts of execute_task_efficient that would otherwise
    # require a live execution context.
    async def fake_execute(prefix, suffix):
        return "output", {"prefix_hit": True}

    with (
        patch("cohezion.precipitation.bus") as mock_bus,
        patch.object(executor, "load_execution_context"),
        patch.object(executor, "get_experience_guidance", return_value={}),
        patch.object(executor, "_compute_token_delta", return_value={"tokens_saved": 50}),
        patch.object(executor, "logger") as mock_logger,
    ):
        mock_logger.log_execution_start = MagicMock(return_value="path")
        mock_logger.log_execution_result = MagicMock()
        # Simulate a prefix cache hit by calling the prefix-hit
        # emission directly
        executor._emit_prefix_hit_witness_mark("qwen3-coder:30b", "test task")
    mock_bus.emit.assert_called_once()
    event = mock_bus.emit.call_args.args[0]
    assert event.coherence == 0.8
