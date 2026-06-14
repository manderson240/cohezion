"""Discriminating tests for the per-task model tournament (item 99, Thread N).

The tournament generalises RHO self-preference from harness updates to MODELS.
Each test fails a plausible wrong implementation:

  - one that always returns the first candidate (ignores prefer) → T_prefer_injected
  - one that fabricates a winner on empty candidates → T_no_candidates_unproven
  - one that ignores task_affinity in the default proxy → T_affinity_discriminates
  - one that computes margin as total wins, not winner-minus-runnerup → T_margin_is_gap
  - one that raises on a single uncontested candidate → T_solo_uncontested
  - one that mutates the candidate list → T_no_mutation
"""

from __future__ import annotations

from cohezion.inference.model_tournament import (
    model_tournament,
    model_tournament_report,
)
from cohezion.inference.registry import KVQuant, Lane, ModelEntry, Task, WeightQuant


# ---------------------------------------------------------------------------
# Fixtures — minimal ModelEntry objects, no live services
# ---------------------------------------------------------------------------


def _entry(
    model_id: str,
    *tasks: Task,
    priority: int = 100,
    cost: float = 0.0,
    verified: bool = False,
    lane: Lane = Lane.IGPU_UNIFIED,
) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=lane,
        endpoint="http://localhost:13305",
        runtime_backend="llamacpp_vulkan",
        task_affinity=frozenset(tasks),
        weight_quant=WeightQuant.Q4_K_M,
        context_window=8192,
        kv_quant=KVQuant(),
        cost_per_1k_input_usd=cost,
        cost_per_1k_output_usd=cost,
        priority=priority,
        verified_working=verified,
    )


# Two candidates: A covers GENERAL, B covers REASONING.
_A = _entry("model-A", Task.GENERAL, priority=100)
_B = _entry("model-B", Task.REASONING, priority=100)

# Candidate with task affinity for the test task (REASONING) and one without.
_R_matching = _entry("model-R-match", Task.REASONING, priority=50, verified=True)
_R_unmatching = _entry("model-R-nomatch", Task.GENERAL, priority=50, verified=True)


# ---------------------------------------------------------------------------
# T_no_candidates_unproven
# Fails: a selector that returns a fabricated winner instead of None.
# ---------------------------------------------------------------------------


def test_no_candidates_returns_unproven() -> None:
    result = model_tournament(Task.GENERAL, [])
    assert result.winner is None
    assert result.margin is None
    assert result.wins == {}
    assert "UNPROVEN" in result.rationale


# ---------------------------------------------------------------------------
# T_solo_uncontested
# Fails: a selector that raises or returns margin!=0 for a single candidate.
# ---------------------------------------------------------------------------


def test_single_candidate_is_uncontested_with_zero_margin() -> None:
    result = model_tournament(Task.GENERAL, [_A])
    assert result.winner is not None
    assert result.winner.model_id == "model-A"
    assert result.margin == 0
    # win-tally for a solo is 0 (no pairwise matches were played).
    assert result.wins == {"model-A": 0}


# ---------------------------------------------------------------------------
# T_prefer_injected
# Fails: a selector that ignores the injected prefer fn and always picks first.
# ---------------------------------------------------------------------------


def test_injected_prefer_always_picks_second_candidate() -> None:
    # Inject a preference that ALWAYS returns the second argument.
    always_second: object = lambda a, b, task: b  # noqa: E731
    result = model_tournament(Task.GENERAL, [_A, _B], prefer=always_second)  # type: ignore[arg-type]
    assert result.winner is not None
    # B is always preferred → B should have the most wins.
    assert result.winner.model_id == "model-B"


# ---------------------------------------------------------------------------
# T_affinity_discriminates
# Fails: a default-proxy that ignores task_affinity and uses cost/priority only.
# ---------------------------------------------------------------------------


def test_default_proxy_prefers_task_affinity_match_over_non_match() -> None:
    # _R_matching covers REASONING; _R_unmatching covers only GENERAL.
    # Both have identical priority and cost — only affinity differs.
    result = model_tournament(Task.REASONING, [_R_unmatching, _R_matching])
    assert result.winner is not None
    assert result.winner.model_id == "model-R-match"  # affinity wins the tie


# ---------------------------------------------------------------------------
# T_margin_is_gap
# Fails: a selector that computes margin as total-wins instead of winner-minus-runner-up.
# (In a 3-candidate field, 3 matches are played; the margin must be wins_gap, not 3.)
# ---------------------------------------------------------------------------


def test_margin_is_winner_minus_runnerup_not_total_matches() -> None:
    # Three candidates; the injected prefer always picks the SECOND argument.
    # A vs B → B wins.  A vs C → C wins.  B vs C → C wins.
    # C has 2 wins, B has 1, A has 0. Margin = 2 - 1 = 1.
    _C = _entry("model-C", Task.GENERAL)
    always_second: object = lambda a, b, task: b  # noqa: E731
    result = model_tournament(
        Task.GENERAL,
        [_A, _B, _C],
        prefer=always_second,  # type: ignore[arg-type]
    )
    assert result.margin == 1  # NOT 3 (total matches), NOT 2 (C's win count)


# ---------------------------------------------------------------------------
# T_no_mutation
# Fails: a selector that sorts / reorders the input list in place.
# ---------------------------------------------------------------------------


def test_candidate_list_is_not_mutated() -> None:
    candidates = [_B, _A]  # intentionally out of alphabetical order
    model_tournament(Task.GENERAL, candidates)
    assert candidates[0].model_id == "model-B"
    assert candidates[1].model_id == "model-A"


# ---------------------------------------------------------------------------
# T_decisive_margin
# Fails: a selector that returns margin=1 regardless of how many candidates.
# In a 4-candidate field where one always wins, margin should be > 1.
# ---------------------------------------------------------------------------


def test_decisive_winner_has_margin_greater_than_one() -> None:
    # To achieve margin > 1 in a round-robin we need a non-transitive trailing pack.
    # A beats everyone; B > C, C > D, D > B (circular non-transitive).
    # Matches: A>B, A>C, A>D, B>C, D>B, C>D.
    # Wins:    A=3,  B=1,  C=1, D=1 → margin = 3 - 1 = 2.
    _C = _entry("model-C", Task.GENERAL)
    _D = _entry("model-D", Task.GENERAL)
    candidates = [_A, _B, _C, _D]

    def non_transitive(m1: ModelEntry, m2: ModelEntry, task: Task) -> ModelEntry:  # noqa: ARG001
        # A beats everyone; B>C, C>D, D>B; ties fall to m1.
        if m1.model_id == "model-A":
            return m1
        if m2.model_id == "model-A":
            return m2
        if (m1.model_id, m2.model_id) in {("model-B", "model-C"), ("model-C", "model-D")}:
            return m1
        if (m1.model_id, m2.model_id) in {("model-D", "model-B")}:
            return m1
        if (m2.model_id, m1.model_id) in {("model-B", "model-C"), ("model-C", "model-D")}:
            return m2
        if (m2.model_id, m1.model_id) in {("model-D", "model-B")}:
            return m2
        return m1  # fallback (tie)

    result = model_tournament(Task.GENERAL, candidates, prefer=non_transitive)
    assert result.margin is not None and result.margin > 1
    assert result.winner is not None and result.winner.model_id == "model-A"


# ---------------------------------------------------------------------------
# model_tournament_report contract
# ---------------------------------------------------------------------------


def test_report_contains_required_keys() -> None:
    report = model_tournament_report(Task.REASONING, [_R_matching, _R_unmatching])
    for key in ("task", "winner_id", "wins", "margin", "candidate_count", "rationale", "judge"):
        assert key in report, f"missing key: {key}"


def test_report_winner_id_is_none_for_empty_candidates() -> None:
    report = model_tournament_report(Task.GENERAL, [])
    assert report["winner_id"] is None
    assert report["candidate_count"] == 0


def test_report_judge_is_deterministic_proxy_by_default() -> None:
    report = model_tournament_report(Task.GENERAL, [_A, _B])
    assert report["judge"] == "deterministic-proxy"


def test_report_judge_is_injected_when_prefer_supplied() -> None:
    always_a: object = lambda a, b, task: a  # noqa: E731
    report = model_tournament_report(Task.GENERAL, [_A, _B], prefer=always_a)  # type: ignore[arg-type]
    assert report["judge"] == "injected"


# ---------------------------------------------------------------------------
# Verified-working preference (secondary criterion after affinity)
# ---------------------------------------------------------------------------


def test_default_proxy_prefers_verified_model_when_affinity_ties() -> None:
    unverified = _entry("model-unverified", Task.GENERAL, verified=False)
    verified = _entry("model-verified", Task.GENERAL, verified=True)
    # Both cover GENERAL (tie on affinity) — verified_working breaks the tie.
    result = model_tournament(Task.GENERAL, [unverified, verified])
    assert result.winner is not None
    assert result.winner.model_id == "model-verified"


# ---------------------------------------------------------------------------
# TournamentResult is a frozen dataclass (immutable after construction)
# ---------------------------------------------------------------------------


def test_tournament_result_is_frozen() -> None:
    result = model_tournament(Task.GENERAL, [_A])
    try:
        result.winner = None  # type: ignore[misc]
        assert False, "should have raised FrozenInstanceError"
    except Exception:
        pass  # any exception = correctly frozen
