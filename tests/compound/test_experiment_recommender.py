"""Tests for experiment recommendation engine."""

import json

from cohezion.compound.experiment_recommender import (
    get_session_recommendation_summary,
    recommend_next_experiments,
)


def _make_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records))


class TestExperimentRecommender:
    def test_recommend_returns_n_experiments(self, tmp_path):
        f = tmp_path / "test.jsonl"
        records = [
            {"metric": 0.15, "status": "keep", "asi": {"experiment": "E63"}} for _ in range(5)
        ]
        _make_jsonl(f, records)
        recs = recommend_next_experiments(n=3, jsonl_path=f)
        assert len(recs) == 3

    def test_recommendation_has_required_fields(self, tmp_path):
        f = tmp_path / "test.jsonl"
        _make_jsonl(f, [{"metric": 0.1, "status": "keep", "asi": {"experiment": "E1"}}])
        recs = recommend_next_experiments(n=2, jsonl_path=f)
        for rec in recs:
            assert "experiment_name" in rec, f"Missing experiment_name: {rec}"
            assert "hypothesis" in rec
            assert "mode" in rec
            assert "priority" in rec

    def test_mode_is_exploit_or_explore(self, tmp_path):
        f = tmp_path / "test.jsonl"
        _make_jsonl(f, [{"metric": 0.8, "status": "keep", "asi": {"experiment": "E1"}}])
        recs = recommend_next_experiments(n=2, jsonl_path=f)
        for rec in recs:
            assert rec["mode"] in ("exploit", "explore")

    def test_retired_experiments_appear_in_replaces(self, tmp_path):
        f = tmp_path / "test.jsonl"
        # E50 with constant 0.125 for 15 runs → retirement candidate
        records = [
            {"metric": 0.125, "status": "keep", "asi": {"experiment": "E50"}} for _ in range(15)
        ]
        _make_jsonl(f, records)
        recs = recommend_next_experiments(n=1, jsonl_path=f)
        replaces = [r.get("replaces") for r in recs]
        assert any(r == "E50" for r in replaces), f"E50 not in replaces: {replaces}"

    def test_summary_structure(self, tmp_path):
        f = tmp_path / "test.jsonl"
        _make_jsonl(f, [{"metric": 0.1, "status": "keep", "asi": {"experiment": "E1"}}])
        # Use a patched jsonl path - can't easily test without patching
        # Just verify the structure from a live call with tiny dataset
        import unittest.mock as mock

        with mock.patch("cohezion.compound.experiment_analytics.JSONL_PATH", f):
            summary = get_session_recommendation_summary()
        assert "hiho_balance" in summary
        assert "recommendations" in summary
        assert "mode" in summary
