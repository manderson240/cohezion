"""Tests for scripts/sync_lemonade_kv_quant.py.

The script closes the loop between the registry's declarative kv_quant config
and Lemonade's actual persisted recipe_options. Tests here cover:
  1. The pure `expected_llamacpp_args` formatter.
  2. The `already_in_sync` idempotency decision across shapes.
  3. The `_is_llamacpp_kv_quant_candidate` filter.
  4. `plan_and_apply` in dry-run against a stubbed HTTP fetcher.

Network + subprocess are mocked; these run in <1s offline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# Script lives under scripts/, not src/ — add to path so the test can import it.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import sync_lemonade_kv_quant as sk  # noqa: E402


def test_expected_llamacpp_args_composes_cache_type_flags() -> None:
    assert sk.expected_llamacpp_args("q8_0") == "--cache-type-k q8_0 --cache-type-v q8_0"
    assert sk.expected_llamacpp_args("bf16") == "--cache-type-k bf16 --cache-type-v bf16"


def test_already_in_sync_true_when_both_cache_flags_present() -> None:
    current = {"llamacpp_args": "--cache-type-k q8_0 --cache-type-v q8_0 --ctx-size 8192"}
    assert sk.already_in_sync(current, "--cache-type-k q8_0 --cache-type-v q8_0") is True


def test_already_in_sync_false_when_only_one_flag_present() -> None:
    current = {"llamacpp_args": "--cache-type-k q8_0 --ctx-size 8192"}
    assert sk.already_in_sync(current, "--cache-type-k q8_0 --cache-type-v q8_0") is False


def test_already_in_sync_false_on_missing_options() -> None:
    assert sk.already_in_sync(None, "--cache-type-k q8_0 --cache-type-v q8_0") is False
    assert sk.already_in_sync({}, "--cache-type-k q8_0 --cache-type-v q8_0") is False
    assert sk.already_in_sync({"other_key": "value"}, "--cache-type-k q8_0") is False


def test_is_llamacpp_kv_quant_candidate_filters_correctly() -> None:
    """Only iGPU lanes with non-default kv_quant AND llama.cpp runtime flag qualify."""
    from cohezion.inference.registry import FleetRegistry, Lane

    registry = FleetRegistry()
    candidates = [m for m in registry.models.values() if sk._is_llamacpp_kv_quant_candidate(m)]
    # Exactly the two iGPU Gemma models after the 2026-04-21 kv8 pivot.
    assert {m.model_id for m in candidates} == {
        "Gemma-4-E4B-it-GGUF",
        "Gemma-4-26B-A4B-it-GGUF",
    }
    # None of the CPU/NPU/cloud lanes should qualify (they have no llama.cpp flag
    # or are not iGPU).
    for m in registry.models.values():
        if m.lane not in {Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED}:
            assert not sk._is_llamacpp_kv_quant_candidate(m), (
                f"{m.model_id} on {m.lane} was incorrectly classified as a candidate"
            )


def test_plan_and_apply_dry_run_invokes_no_subprocess() -> None:
    """In dry-run, the script must NEVER spawn `lemonade load`. Stub HTTP to force
    the 'needs-sync' branch, mock subprocess to detect any accidental invocation."""
    from cohezion.inference.registry import FleetRegistry

    registry = FleetRegistry()
    # Make fetch_recipe_options return an empty dict for every model -> needs sync.
    with (
        patch.object(sk, "fetch_recipe_options", return_value={}) as mock_fetch,
        patch.object(sk, "apply_sync") as mock_apply,
    ):
        in_sync, planned, applied = sk.plan_and_apply(
            registry, "http://fake", dry_run=True, verbose=False
        )
    assert mock_apply.call_count == 0, "dry-run must not invoke apply_sync"
    assert planned == 2, "both iGPU Gemma models should need sync (post-kv8 pivot)"
    assert applied == 0
    assert in_sync == 0
    # fetch was called once per candidate.
    assert mock_fetch.call_count == 2


def test_plan_and_apply_skips_models_already_in_sync() -> None:
    """When Lemonade's recipe_options already match, the model should be skipped."""
    from cohezion.inference.registry import FleetRegistry

    registry = FleetRegistry()
    in_sync_options = {"llamacpp_args": "--cache-type-k q8_0 --cache-type-v q8_0"}
    with (
        patch.object(sk, "fetch_recipe_options", return_value=in_sync_options),
        patch.object(sk, "apply_sync") as mock_apply,
    ):
        in_sync, planned, applied = sk.plan_and_apply(
            registry, "http://fake", dry_run=False, verbose=False
        )
    assert in_sync == 2
    assert planned == 0
    assert applied == 0
    assert mock_apply.call_count == 0, "models already in-sync must not trigger apply"


def test_plan_and_apply_target_model_isolates_one_entry() -> None:
    """--model <id> must limit the scan to that single entry."""
    from cohezion.inference.registry import FleetRegistry

    registry = FleetRegistry()
    with patch.object(sk, "fetch_recipe_options", return_value={}):
        _, planned, applied = sk.plan_and_apply(
            registry,
            "http://fake",
            dry_run=True,
            target_model_id="Gemma-4-E4B-it-GGUF",
        )
    assert planned == 1
    assert applied == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
