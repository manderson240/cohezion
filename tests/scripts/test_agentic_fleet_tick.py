"""Unit test for the agentic fleet tick driver's pure model-pick logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_DRIVER = Path(__file__).resolve().parents[2] / "scripts" / "drivers" / "agentic_fleet_tick.py"
_spec = importlib.util.spec_from_file_location("agentic_fleet_tick", _DRIVER)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
pick_model = _mod.pick_model
parse_mode = _mod.parse_mode


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


class TestParseMode:
    """The CLI flag that routes to swarm_tick (roadmap's final ergonomics nicety)."""

    def test_swarm_flag_selects_swarm_mode_with_next_arg_as_intent(self):
        # DISCRIMINATING: --swarm must (a) switch mode to 'swarm' AND (b) take the FOLLOWING
        # token as the intent. An impl that ignores the flag returns ('fleet', '--swarm');
        # one that returns the flag token itself returns ('swarm', '--swarm'). Both fail this.
        assert parse_mode(["--swarm", "audit SurrealDB schema"]) == (
            "swarm",
            "audit SurrealDB schema",
        )

    def test_intent_alias_also_selects_swarm(self):
        assert parse_mode(["--intent", "wire data products"]) == ("swarm", "wire data products")

    def test_bare_positional_is_fleet_mode(self):
        # Preserves the original behavior: a positional prompt → fleet tier-distribution.
        assert parse_mode(["distribute this task"]) == ("fleet", "distribute this task")

    def test_no_args_defaults_to_fleet_with_default_prompt(self):
        mode, prompt = parse_mode([])
        assert mode == "fleet" and prompt == _mod._DEFAULT_PROMPT

    def test_bare_swarm_flag_falls_back_without_crashing(self):
        # A --swarm with no following intent must NOT IndexError; it stays in swarm mode and
        # uses the default prompt. (Kills a naive `rest[0]` impl.)
        mode, prompt = parse_mode(["--swarm"])
        assert mode == "swarm" and prompt == _mod._DEFAULT_PROMPT
