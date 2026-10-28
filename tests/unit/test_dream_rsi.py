"""Unit tests for the Dream-RSI discovery-replay evaluator (dream_rsi.py).

Grounded in arXiv:2609.14858 (Zheng et al., 2026): fixtures reproduce the
paper's replay semantics (off-policy counterfactual evaluation over recorded
history, Eq. 1 replay objective, offline policy selection) with fully
synthetic records — no live SurrealDB, no models, offline.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from cohezion.agi.dream_rsi import (
    DEFAULT_CONTEXT_KEYS,
    DiscoveryRecord,
    DiscoveryTree,
    PolicyRefinement,
    PolicyScore,
    candidate_from_context,
    load_from_surrealdb,
    load_from_vault_retros,
    refine_policy,
    replay_dream,
    replay_objective,
)


# --------------------------------------------------------------------------
# Synthetic history: 4 NPU-context records + 2 iGPU-context records
# --------------------------------------------------------------------------


def _rec(
    rid: str,
    model: str = "m1",
    tier: str = "npu",
    task: str = "codegen",
    action: str | None = "npu_first",
    score: float | None = 0.5,
    cost: float | None = 2.0,
    evi: float = 0.9,
) -> DiscoveryRecord:
    return DiscoveryRecord(
        id=rid,
        timestamp=f"2026-09-15T00:00:{sum(ord(c) for c in rid) % 60:02d}",
        policy_context={"model": model, "tier": tier, "task": task, "evi": evi},
        action=action,
        outcome_metrics={"score": score} if score is not None else {},
        cost=cost,
        source_table="delegation_log",
        succeeded=None,
    )


@pytest.fixture
def history() -> tuple[DiscoveryRecord, ...]:
    return (
        _rec("1", action="npu_first", score=0.8, cost=2.0),
        _rec("2", action="npu_first", score=0.0, cost=2.0),
        _rec("3", action="igpu_first", score=0.9, cost=1.0),
        _rec("4", action="igpu_first", score=0.7, cost=1.0),
        _rec("5", action="cloud_escalate", score=None, cost=None),
        _rec("5b", action="cloud_escalate", score=None, cost=None),
    )


@pytest.fixture
def tree(history: tuple[DiscoveryRecord, ...]) -> DiscoveryTree:
    return DiscoveryTree.from_records(history)


# --------------------------------------------------------------------------
# Loader with synthetic records
# --------------------------------------------------------------------------


class TestDiscoveryTreeLoader:
    def test_from_records_dedupes_and_orders_deterministically(self):
        a = _rec("1")
        b = _rec("2")
        dup = _rec("1")
        tree = DiscoveryTree.from_records([b, a, dup])
        assert [r.id for r in tree.records] == ["1", "2"]
        assert len(tree) == 2

    def test_record_defaults_and_source_provenance(self):
        rec = DiscoveryRecord(id="x", timestamp="2026-09-15T10:00:00+00:00")
        assert rec.action is None
        assert rec.policy_context == {}
        assert rec.source_table == "manual"

    def test_load_from_surrealdb_all_tables_down_fail_open(self):
        """Source-level mock of urllib, kanban_bridge-style; no live DB.

        Every table erroring must produce an empty record list and captured
        errors — fail-open like kanban_bridge, never a raise.
        """
        with patch_urlopen(_raise_boom):
            records, errors = load_from_surrealdb(
                tables=("delegation_log", "experiment_run", "learning")
            )

        # Fail-open: every table down -> no records, errors captured, no raise.
        assert records == []
        assert len(errors) == 3
        assert all("boom" in e for e in errors)

    def test_load_from_surrealdb_success_path(self):
        """One healthy table parses into a record; erroring tables are captured."""
        payload = {
            "result": [  # delegation_log
                {
                    "id": "delegation_log:abc",
                    "timestamp": 1787773683.93,
                    "model": "deepseek-v4-pro:cloud",
                    "tier": "tier2",
                    "evi": 0.88,
                    "action": "npu_first",
                    "cost": 1.5,
                    "metrics": {"score": 0.91},
                },
            ]
        }

        class FakeResponse:
            def __init__(self, payload: dict) -> None:
                self._buf = BytesIO(json.dumps(payload).encode())

            def read(self) -> bytes:
                return self._buf.read()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

        with patch_urlopen(lambda req, timeout: FakeResponse(payload)):
            records, errors = load_from_surrealdb(tables=("delegation_log",))

        assert errors == []
        assert len(records) == 1
        rec = records[0]
        assert rec.id == "delegation_log:abc"
        assert rec.source_table == "delegation_log"
        assert rec.action == "npu_first"
        assert rec.cost == 1.5
        assert rec.policy_context["tier"] == "tier2"
        assert rec.outcome_metrics["score"] == 0.91
        assert rec.succeeded is None
        assert rec.timestamp.startswith("20")  # epoch normalized to ISO

    def test_load_from_vault_retros_synthetic_dir(self, tmp_path: Path):
        (tmp_path / "2026-07-10-consolidation-final.md").write_text(
            "# Consolidation Final\n\nLessons learned.\n", encoding="utf-8"
        )
        (tmp_path / "2026-08-15-notes.md").write_text(
            "---\ndate: 2026-08-16\n---\n\n# CI Repair\n", encoding="utf-8"
        )
        (tmp_path / "not-a-retro.txt").write_text("ignored\n", encoding="utf-8")
        records = load_from_vault_retros(tmp_path)
        by_id = {r.id: r for r in records}
        assert set(by_id) == {"2026-07-10-consolidation-final", "2026-08-15-notes"}
        retro = by_id["2026-07-10-consolidation-final"]
        assert retro.source_table == "vault_retro"
        assert retro.action == "Consolidation Final"
        assert retro.timestamp == "2026-07-10"
        assert by_id["2026-08-15-notes"].timestamp == "2026-08-16"  # frontmatter wins
        assert all(r.cost is None and r.outcome_metrics == {} for r in records)

    def test_load_from_vault_retros_missing_dir_fail_closed_empty(self, tmp_path: Path):
        assert load_from_vault_retros(tmp_path / "nope") == []


def patch_urlopen(fn):
    """Source-level patch: cohezion.agi.dream_rsi.urlopen (repo mock pattern)."""
    import unittest.mock

    return unittest.mock.patch("cohezion.agi.dream_rsi.urllib.request.urlopen", fn)


def _raise_boom(req, timeout):
    raise OSError("boom")


# --------------------------------------------------------------------------
# Counterfactual replay (dreaming)
# --------------------------------------------------------------------------


class TestReplayDream:
    def test_known_better_policy_scores_positive_gain(self, history, tree):
        """The paper's core claim: history alone reveals the better policy.

        iGPU-first realized branches average 0.8 vs NPU-first's 0.4, at half
        the cost, so an iGPU-first policy must strictly dominate on both axes.
        """
        igpu = candidate_from_context({}, "igpu_first")
        npu = candidate_from_context({}, "npu_first")
        score_igpu = replay_dream(history, igpu, policy_name="igpu_first")
        score_npu = replay_dream(history, npu, policy_name="npu_first")
        # Scored points: records 1-4 (5/5b carry no outcome). Agreement books
        # 0.0; disagreement scores against the counterfactual branch pool:
        #   igpu dream: agrees on 3,4 (0,0); disagrees on 1,2 -> igpu pool
        #     mean 0.8 vs realized npu 0.8/0.0 -> gains 0.0, +0.8
        #   => mean (0.0+0.8+0.0+0.0)/4 = 0.2
        #   npu dream: agrees on 1,2 (0,0); disagrees on 3,4 -> npu pool mean
        #     0.4 vs realized igpu 0.9/0.7 -> gains -0.5, -0.3
        #   => mean (-0.5-0.3)/4 = -0.2
        assert score_igpu.counterfactual_gain_estimate == pytest.approx(0.2)
        assert score_npu.counterfactual_gain_estimate == pytest.approx(-0.2)
        gain_igpu = score_igpu.counterfactual_gain_estimate
        gain_npu = score_npu.counterfactual_gain_estimate
        assert gain_igpu is not None and gain_npu is not None
        assert gain_igpu > gain_npu
        # Cost: agreements book 0.0; igpu dream disagrees on 1,2 vs igpu pool
        # mean 1.0 vs realized 2.0 -> (-1.0 + -1.0)/4 = -0.5. npu dream
        # disagrees on 3,4 vs npu pool 2.0 vs realized igpu 1.0 ->
        # (+1.0 + 1.0)/4 = +0.5.
        assert score_igpu.cost_delta == pytest.approx(-0.5)
        assert score_npu.cost_delta == pytest.approx(0.5)
        # Full applicability (constant policy matches all 6 contexts)
        assert score_igpu.coverage == pytest.approx(1.0)
        assert score_npu.coverage == pytest.approx(1.0)
        assert score_igpu.n_decision_points == len(tree)

    def test_agreement_rate_and_zero_gain_for_incumbent(self, history):
        """A policy that always agrees books zero counterfactual gain."""
        incumbent = candidate_from_context({}, "npu_first")
        # NPU policy agrees on records 1-2 (npu_first realized) and disagrees
        # on 3, 4 (igpu_first realized) and 5, 5b (cloud_escalate realized).
        score = replay_dream(history, incumbent, policy_name="npu_first")
        assert score.agreement_rate == pytest.approx(2 / 6)
        # Agreed points contribute exactly 0.0; disagreement on 3,4 scores the
        # npu pool mean 0.4 vs realized igpu outcomes (0.9, 0.7):
        # (-0.5 + -0.3)/4 = -0.2.
        assert score.counterfactual_gain_estimate == pytest.approx(-0.2)

    def test_unknown_context_fail_closed_no_gain(self):
        """Unknown policy context -> no applicable points -> coverage 0, None gain."""
        stranger = DiscoveryRecord(
            id="s1",
            timestamp="2026-09-15T12:00:00+00:00",
            policy_context={"model": "unknown-model", "tier": "unknown"},
            action="quantum_route",
            outcome_metrics={"score": 1.0},
            cost=0.1,
        )
        scoped = candidate_from_context({"tier": "npu"}, "npu_first", otherwise=None)
        score = replay_dream([stranger], scoped)
        assert score.coverage == 0.0
        assert score.counterfactual_gain_estimate is None
        assert score.agreement_rate is None
        assert score.cost_delta is None
        assert score.n_applicable == 0
        assert score.n_scored == 0

    def test_empty_history_fail_closed(self):
        score = replay_dream([], candidate_from_context({}, "x"))
        assert score.coverage == 0.0
        assert score.counterfactual_gain_estimate is None
        assert score.agreement_rate is None
        assert score.n_decision_points == 0

    def test_policy_exception_contained_not_raised(self, history):
        def broken_policy(record: DiscoveryRecord) -> str | None:
            raise RuntimeError("policy bug")

        score = replay_dream(history, broken_policy, policy_name="broken")
        assert score.coverage == 0.0
        assert score.counterfactual_gain_estimate is None
        assert score.agreement_rate is None

    def test_policy_returning_none_is_not_applicable(self, history):
        def abstainer(record: DiscoveryRecord) -> str | None:
            return None

        score = replay_dream(history, abstainer, policy_name="abstain")
        assert score.coverage == 0.0
        assert score.agreement_rate is None
        assert score.n_applicable == 0

    def test_unrecorded_counterfactual_branch_yields_none(self):
        """Only one recorded action in context -> counterfactual branch unknown."""
        rec = _rec("1", action="npu_first", score=0.8, cost=2.0)
        dream_of_other = candidate_from_context({}, "igpu_first")
        score = replay_dream([rec], dream_of_other)
        # No igpu branch was ever recorded in this context: unestimable.
        assert score.counterfactual_gain_estimate is None
        assert score.cost_delta is None
        # But the policy WAS applicable and DID disagree -> agreement 0.0, not None.
        assert score.coverage == pytest.approx(1.0)
        assert score.agreement_rate == pytest.approx(0.0)

    def test_context_keys_scope_counterfactual_pools(self, history):
        """Pool per task context: an unrelated task's branches must not leak in."""
        scoped = candidate_from_context({}, "igpu_first")
        score = replay_dream(history, scoped, policy_name="igpu", context_keys=("tier", "task"))
        assert score.counterfactual_gain_estimate == pytest.approx(0.2)
        # Cross-task contamination check: same policy over a foreign-task record
        foreign = _rec("f1", task="kaggle", action="npu_first", score=0.1, cost=5.0)
        score_fx = replay_dream(
            [*history, foreign], scoped, policy_name="igpu", context_keys=("tier", "task")
        )
        # Foreign task has NO igpu branch -> contributes no gain, only coverage.
        assert score_fx.counterfactual_gain_estimate == pytest.approx(0.2)

    def test_succeeded_flag_used_as_outcome_fallback(self):
        recs = (
            DiscoveryRecord(
                id="a",
                timestamp="t1",
                policy_context={"tier": "npu", "task": "t"},
                action="act_a",
                succeeded=True,
            ),
            DiscoveryRecord(
                id="b",
                timestamp="t2",
                policy_context={"tier": "npu", "task": "t"},
                action="act_b",
                succeeded=False,
            ),
        )
        pick_b = candidate_from_context({}, "act_b")
        score = replay_dream(recs, pick_b)
        # cf outcome from act_b pool = 0.0; record a: realized 1.0 -> -1.0;
        # record b: agreement -> 0.0. Mean over 2 scored = -0.5.
        assert score.counterfactual_gain_estimate == pytest.approx(-0.5)

    def test_default_context_keys_are_model_tier_task(self):
        assert DEFAULT_CONTEXT_KEYS == ("model", "tier", "task")


# --------------------------------------------------------------------------
# Replay objective (paper Eq. 1)
# --------------------------------------------------------------------------


class TestReplayObjective:
    def test_eq1_quality_minus_beta1_n_plus_parallelism_bonus(self, tree):
        # outcomes 0.8, 0.0, 0.9, 0.7 -> max 0.9, N=4
        v = replay_objective(tree, beta1=0.1, beta2=0.05, n_rounds=2)
        assert v == pytest.approx(0.9 - 0.1 * 4 + 0.05 * 4 / 2)

    def test_eq1_sequential_default_k_equals_n(self, tree):
        v = replay_objective(tree, beta1=0.1, beta2=0.05)
        assert v == pytest.approx(0.9 - 0.4 + 0.05)

    def test_eq1_empty_or_outcomeless_history_returns_none(self):
        assert replay_objective([]) is None
        outcomeless = DiscoveryRecord(id="z", timestamp="t", policy_context={})
        assert replay_objective([outcomeless]) is None


# --------------------------------------------------------------------------
# Policy refinement (offline selection) — determinism + fail-closed
# --------------------------------------------------------------------------


class TestRefinePolicy:
    def test_winner_is_known_better_policy(self, history):
        candidates = {
            "npu_first": candidate_from_context({}, "npu_first"),
            "igpu_first": candidate_from_context({}, "igpu_first"),
        }
        refinement = refine_policy(history, candidates)
        assert refinement is not None
        assert refinement.winner_name == "igpu_first"
        assert refinement.rationale.startswith("Selected 'igpu_first'")
        assert refinement.history_size == len(history)
        assert "off-policy replay" in refinement.rationale

    def test_ranking_determinism_and_tiebreak_order(self, history):
        candidates = {
            "b_second": candidate_from_context({}, "npu_first"),
            "a_first": candidate_from_context({}, "npu_first"),
            "igpu": candidate_from_context({}, "igpu_first"),
        }
        refinement = refine_policy(history, candidates)
        assert refinement is not None
        names = [s.policy_name for s in refinement.scores]
        assert names == ["igpu", "a_first", "b_second"]  # gain desc, then name asc
        # Rerun: identical result (no stochasticity anywhere in the pipeline)
        again = refine_policy(history, candidates)
        assert again is not None and again.winner_name == refinement.winner_name
        assert [s.policy_name for s in again.scores] == names

    def test_empty_history_returns_none(self):
        assert refine_policy([], {"x": candidate_from_context({}, "x")}) is None

    def test_no_candidates_returns_none(self, history):
        assert refine_policy(history, {}) is None

    def test_no_applicable_candidate_returns_none(self, history):
        sleepy = candidate_from_context({"tier": "tpu"}, "tpu_route", otherwise=None)
        assert refine_policy(history, {"sleepy": sleepy}) is None

    def test_refinement_scores_sorted_best_first(self, history):
        candidates = {
            "npu": candidate_from_context({}, "npu_first"),
            "igpu": candidate_from_context({}, "igpu_first"),
        }
        refinement = refine_policy(history, candidates)
        assert refinement is not None
        gains = [s.counterfactual_gain_estimate for s in refinement.scores]
        assert all(g is not None for g in gains)
        float_gains = [g for g in gains if g is not None]
        assert float_gains == sorted(float_gains, reverse=True)
        assert isinstance(refinement, PolicyRefinement)
        assert all(isinstance(s, PolicyScore) for s in refinement.scores)


# --------------------------------------------------------------------------
# Policy builder
# --------------------------------------------------------------------------


class TestCandidateFromContext:
    def test_match_and_fallback_semantics(self, history):
        npu_only = candidate_from_context({"tier": "npu"}, "npu_first", otherwise="igpu_first")
        assert npu_only(history[0]) == "npu_first"
        assert (
            npu_only(  # iGPU-context record falls to 'otherwise'
                DiscoveryRecord(
                    id="9",
                    timestamp="t",
                    policy_context={"tier": "igpu", "model": "m", "task": "c"},
                    action="igpu_first",
                    outcome_metrics={"score": 0.5},
                    cost=1.0,
                )
            )
            == "igpu_first"
        )

    def test_missing_context_key_is_non_matching(self):
        policy = candidate_from_context({"evi": 0.9}, "go", otherwise=None)
        record = DiscoveryRecord(id="r", timestamp="t", policy_context={"model": "m"})
        assert policy(record) is None  # fail-closed applicability
        assert policy(DiscoveryRecord(id="r2", timestamp="t", policy_context={"evi": 0.9})) == "go"
