"""Unit tests for the NPU Gauntlet wiring module (no network, no NPU)."""

from __future__ import annotations

import json

import pytest

from cohezion.inference.gauntlet import BenchTask, _normalize_answer, _score_result
from cohezion.inference.npu_gauntlet import (
    CANARY_SUITE,
    leaderboard,
    load_npu,
    procedural_suite,
)


class TestProceduralSuite:
    def test_deterministic_per_seed(self):
        a = procedural_suite(seed=7)
        b = procedural_suite(seed=7)
        assert [t.prompt for t in a] == [t.prompt for t in b]
        assert [t.gold for t in a] == [t.gold for t in b]

    def test_different_seeds_differ(self):
        assert [t.prompt for t in procedural_suite(1)] != [t.prompt for t in procedural_suite(2)]

    def test_arithmetic_gold_is_consistent_with_prompt(self):
        t = next(t for t in procedural_suite(42) if t.name == "proc_arith")
        # Recover a,b,c,d from the templated prompt and recompute the gold.
        import re

        a, b = map(int, re.search(r"(\d+) crates with (\d+) widgets", t.prompt).groups())
        c = int(re.search(r"(\d+) loose widgets", t.prompt).group(1))
        d = int(re.search(r"then (\d+) widgets", t.prompt).group(1))
        assert t.gold == str(a * b + c - d)

    def test_all_tasks_exact_graded_with_gold(self):
        for t in procedural_suite(3):
            assert t.grader == "exact"
            assert t.gold != ""

    def test_json_gold_is_valid_json(self):
        t = next(t for t in procedural_suite(5) if t.name == "proc_json")
        assert isinstance(json.loads(t.gold), dict)

    def test_injection_probe_gold_is_the_code_not_the_bait(self):
        t = next(t for t in procedural_suite(11) if t.name == "proc_inject")
        assert t.gold.isdigit() and len(t.gold) == 4
        assert t.gold not in ("kumquat", "zephyr", "obelisk")
        # the bait word appears in the prompt, so obeying the injection fails exact grading
        assert any(b in t.prompt for b in ("kumquat", "zephyr", "obelisk"))

    def test_distractor_variant_gold_ignores_weight_clause(self):
        suite = procedural_suite(13)
        plain = next(t for t in suite if t.name == "proc_arith")
        distract = next(t for t in suite if t.name == "proc_arith_distract")
        assert distract.gold == plain.gold  # irrelevant clause must not change the answer
        assert "kg" in distract.prompt and "kg" not in plain.prompt

    def test_deterministic_tasks_pin_temperature_zero(self):
        for t in procedural_suite(9):
            if t.name not in ("proc_arith", "proc_arith_distract"):  # reasoning tasks inherit card sampling
                assert t.temperature == 0.0


class TestNormalizeAndGrade:
    def test_think_block_stripped_and_marker_wins(self):
        assert _normalize_answer("<think>3*4=12 no wait</think>Sure.\n#### 391") == "391"

    def test_numeric_commas(self):
        assert _normalize_answer("#### 1,234") == "1234"

    def test_json_canonicalized(self):
        assert _normalize_answer('{"site": "dune", "count": 7}') == _normalize_answer(
            '{"count":7,"site":"dune"}'
        )

    def test_casefold_and_punctuation(self):
        assert _normalize_answer("  Paris.") == "paris"

    def test_fenced_json_parses_to_canonical(self):
        # gemma-family models fence their JSON — must not fail exact grading
        fenced = 'Here you go:\n```json\n{"site": "dune", "count": 7}\n```'
        assert _normalize_answer(fenced) == _normalize_answer('{"count":7,"site":"dune"}')

    def test_pick_temp_arm_explores_then_exploits(self):
        import random

        from cohezion.inference.npu_gauntlet import pick_temp_arm

        rng = random.Random(1)
        # under-sampled arms are explored first, lesser-sampled arm preferred
        assert pick_temp_arm({}, rng) == "card"
        assert pick_temp_arm({"card": {"n": 3, "acc": 3.0}}, rng) == "temp0"
        # with evidence, the better arm dominates (temp0 clearly better here)
        stats = {"card": {"n": 20, "acc": 1.0}, "temp0": {"n": 20, "acc": 19.0}}
        picks = [pick_temp_arm(stats, random.Random(s)) for s in range(50)]
        assert picks.count("temp0") > 35  # exploited, modulo ε-exploration

    def test_exact_grader_scores_correct(self):
        t = BenchTask(name="x", role="router", prompt="p", expected_keywords=[], grader="exact", gold="paris")
        r = _score_result(t, ttft=0.1, tps=40.0, text="Paris.")
        assert r.quality_ratio == 1.0
        assert r.score == 40.0

    def test_exact_grader_scores_wrong(self):
        t = BenchTask(name="x", role="router", prompt="p", expected_keywords=[], grader="exact", gold="paris")
        r = _score_result(t, ttft=0.1, tps=40.0, text="London")
        assert r.quality_ratio == 0.0
        assert r.score == 0.0


class TestGuards:
    def test_flm_only_guard(self):
        with pytest.raises(ValueError, match="FLM"):
            load_npu("Gemma-4-26B-A4B-it-GGUF")

    def test_flm_size_estimate_parses_param_counts(self):
        from cohezion.inference.npu_gauntlet import _flm_size_gb

        assert _flm_size_gb("llama3.2-1b-FLM") == pytest.approx(0.7)
        assert _flm_size_gb("deepseek-r1-0528-8b-FLM") == pytest.approx(5.6)
        assert _flm_size_gb("lfm2.5-it-1.2b-FLM") == pytest.approx(0.84)
        assert _flm_size_gb("qwen3-4b-FLM") == pytest.approx(2.8)
        assert _flm_size_gb(None) == 0.0
        assert _flm_size_gb("mystery-FLM") == 6.0  # unparseable → conservative

    def test_swap_delta_gate_blocks_only_floor_breaches(self, monkeypatch):
        import cohezion.inference.npu_gauntlet as ng

        monkeypatch.setattr(ng, "npu_occupant", lambda: "deepseek-r1-0528-8b-FLM")
        # 18.9GB avail: swapping 8b -> 1b frees RAM (delta 0) — must NOT veto on RAM;
        # it proceeds to the HTTP load, which we stub to fail distinctly.
        monkeypatch.setattr(ng, "available_ram_gb", lambda: 18.9)
        monkeypatch.setattr(
            ng, "_http_json", lambda *a, **k: (_ for _ in ()).throw(OSError("net"))
        )
        with pytest.raises(OSError, match="net"):
            ng.load_npu("llama3.2-1b-FLM")
        # But an empty slot + big model + thin headroom must veto BEFORE any load.
        monkeypatch.setattr(ng, "npu_occupant", lambda: None)
        monkeypatch.setattr(ng, "available_ram_gb", lambda: 17.0)
        with pytest.raises(MemoryError, match="swap-delta"):
            ng.load_npu("deepseek-r1-0528-8b-FLM")

    def test_canary_suite_is_deterministic_and_graded(self):
        for t in CANARY_SUITE:
            assert t.temperature == 0.0
            assert t.grader == "exact"


class TestLeaderboard:
    def test_empty_results_dir(self, tmp_path, monkeypatch):
        import cohezion.inference.npu_gauntlet as ng

        monkeypatch.setattr(ng, "RUN_DIR", tmp_path)
        board = leaderboard()
        assert board["entries"] == []

    def test_aggregation(self, tmp_path, monkeypatch):
        import cohezion.inference.npu_gauntlet as ng

        monkeypatch.setattr(ng, "RUN_DIR", tmp_path)
        rows = [
            {"model": "m1", "role": "router", "quality_score": 1.0, "tps": 40.0},
            {"model": "m1", "role": "router", "quality_score": 0.0, "tps": 40.0},
            {"model": "m2", "role": "router", "quality_score": 1.0, "tps": 10.0},
        ]
        (tmp_path / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        board = leaderboard()
        by_model = {b["model"]: b for b in board["entries"]}
        assert by_model["m1"]["accuracy"] == 0.5
        assert by_model["m2"]["accuracy"] == 1.0
        assert by_model["m1"]["mean_tps"] == 40.0
        # accuracy ranks first: m2 (1.0) above m1 (0.5) despite lower TPS
        assert board["entries"][0]["model"] == "m2"
