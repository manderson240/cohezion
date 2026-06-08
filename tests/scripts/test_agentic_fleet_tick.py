"""Unit test for the agentic fleet tick driver's pure model-pick logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_DRIVER = Path(__file__).resolve().parents[2] / "scripts" / "drivers" / "agentic_fleet_tick.py"
_spec = importlib.util.spec_from_file_location("agentic_fleet_tick", _DRIVER)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
pick_model = _mod.pick_model


class TestPickModel:
    def test_prefers_match_over_first_resident(self):
        # DISCRIMINATING: Granite preferred even though the 1B is listed first.
        # A "return first resident" impl would wrongly pick the 1B.
        loaded = ["llama3.2-1b-FLM", "Granite-4.1-8B-GGUF"]
        assert pick_model(loaded, ["Granite", "8B"]) == "Granite-4.1-8B-GGUF"

    def test_npu_prefers_flm(self):
        loaded = ["llama3.2-1b-FLM", "nomic-embed-text-v2-moe-GGUF"]
        assert pick_model(loaded, ["FLM", "llama3.2-1b"]) == "llama3.2-1b-FLM"

    def test_skips_embeddings(self):
        # Only an embedding model resident → no chat model → None.
        assert pick_model(["nomic-embed-text-v2-moe-GGUF"], ["FLM"]) is None

    def test_empty_tier_returns_none(self):
        assert pick_model([], ["Granite"]) is None

    def test_fallback_to_any_resident_when_no_pref_match(self):
        assert pick_model(["Qwen3-8B-GGUF"], ["Granite"]) == "Qwen3-8B-GGUF"
