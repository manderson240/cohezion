"""Unit tests for the KST knowledge-structure probe (src/cohezion/agi/kst_eval.py).

Grounded in arXiv:2609.05245 (Cui, Do & Sachan, EMNLP 2026 Findings): fixtures
reproduce the paper's definitions (strict Eq. 1 prerequisite induction, Eq. 2-7
metrics) and its headline quantitative anchors where a closed form exists.
"""

from __future__ import annotations

import dataclasses

import pytest

from cohezion.agi.kst_eval import (
    KSTKnowledgeStructureProbe,
    derive_prerequisite_graph,
    knowledge_overlap_coefficient,
    koc_normalized,
    pairwise_koc_norm_matrix,
    prerequisite_satisfaction,
    prerequisite_scaffold_advantage,
    psr_distribution,
    psr_macro,
    psr_micro,
    psr_one_rate,
    reflexive_transitive_closure,
    scaffolding_gain,
)


# --------------------------------------------------------------------------
# Fixtures mirroring the paper's pipeline: concepts -> Eq. 1 question prereqs
# --------------------------------------------------------------------------

CONCEPT_PREREQS = {
    # addition/multiplication chain ("3+3 before 3x3" example, paper §3.3.1)
    "addition": [],
    "multiplication": ["addition"],
    "linear_equation": ["addition"],
    "quadratic": ["linear_equation"],  # quadratics presuppose linear equations
}

QUESTION_CONCEPTS = {
    "q_add": {"addition"},
    "q_mul": {"multiplication"},
    "q_lin": {"linear_equation"},
    "q_quad": {"quadratic"},
    "q_both": {"addition", "multiplication"},
}


@pytest.fixture
def graph() -> dict[str, frozenset[str]]:
    return derive_prerequisite_graph(QUESTION_CONCEPTS, CONCEPT_PREREQS)


# --------------------------------------------------------------------------
# Concept closure and Eq. 1 prerequisite induction
# --------------------------------------------------------------------------


class TestClosureAndGraph:
    def test_closure_is_reflexive_and_transitive(self):
        cl = reflexive_transitive_closure(CONCEPT_PREREQS)
        assert cl["addition"] == frozenset({"addition"})
        assert cl["quadratic"] == frozenset({"addition", "linear_equation", "quadratic"})

    def test_closure_rejects_self_loop(self):
        with pytest.raises(ValueError, match="itself"):
            reflexive_transitive_closure({"a": ["a"]})

    def test_closure_rejects_cycle(self):
        with pytest.raises(ValueError, match="cycle"):
            reflexive_transitive_closure({"a": ["b"], "b": ["a"]})

    def test_closure_rejects_longer_cycle(self):
        with pytest.raises(ValueError, match="cycle"):
            reflexive_transitive_closure({"a": ["b"], "b": ["c"], "c": ["a"]})

    def test_strict_eq1_all_concepts_must_be_dominated(self, graph):
        # Eq. 1: q_i is a prerequisite of q_j iff EVERY concept of q_i is
        # dominated by SOME concept of q_j. Verified by hand against the
        # paper's definition: addition ⪯ multiplication makes q_add a
        # prerequisite of q_mul, q_lin, q_quad and q_both; the q_both question
        # (needs both addition and multiplication) is itself a prerequisite of
        # q_mul because its concept set is dominated term-by-term.
        assert "q_add" in graph["q_mul"]
        assert "q_add" in graph["q_lin"]
        assert "q_add" in graph["q_quad"]
        assert "q_lin" in graph["q_quad"]  # transitive through the graph
        assert "q_both" in graph["q_mul"]
        # no cycles at question level
        assert "q_quad" not in graph["q_add"]

    def test_weak_any_pair_rule_is_not_used(self):
        # Under the rejected weak rule, q_lin {linear_equation} would be a
        # prerequisite of q_mul {multiplication} via the shared ancestor
        # addition. The strict rule (Eq. 1) requires linear_equation itself to
        # be dominated by multiplication's concept set — it is not.
        g = derive_prerequisite_graph(
            {"q_lin": {"linear_equation"}, "q_mul": {"multiplication"}},
            CONCEPT_PREREQS,
        )
        assert "q_lin" not in g["q_mul"]
        # q_mul is not a prerequisite of q_lin either: C(q_mul) =
        # {multiplication} is dominated (multiplication ⪯ linear_equation is
        # false; only their shared ancestor addition is), so strictness cuts
        # both ways here.
        assert "q_mul" not in g["q_lin"]

    def test_unreachable_concepts_are_not_prerequisites(self, graph):
        # q_lin does not require q_mul: linear_equation's closure contains
        # addition but not multiplication.
        assert "q_mul" not in graph["q_lin"]

    def test_conceptless_question_fails_closed(self):
        with pytest.raises(ValueError, match="no concepts"):
            derive_prerequisite_graph({"q_bad": set()}, CONCEPT_PREREQS)

    def test_unknown_concept_fails_closed(self):
        with pytest.raises(ValueError, match="unknown concepts"):
            derive_prerequisite_graph({"q": {"nonexistent"}}, CONCEPT_PREREQS)


# --------------------------------------------------------------------------
# NB1: PSR (Eqs. 2-4) and the Table 2 anchors
# --------------------------------------------------------------------------


class TestPrerequisiteSatisfaction:
    def test_perfect_state_scores_one(self, graph):
        k = ["q_add", "q_mul", "q_lin", "q_quad"]
        assert prerequisite_satisfaction("q_quad", k, graph) == 1.0

    def test_partial_state_is_fraction_of_prereqs_mastered(self, graph):
        # Pre(q_both) = {q_add, q_mul}; K = {q_add, q_both} -> PSR 0.5
        k = ["q_add", "q_both"]
        assert prerequisite_satisfaction("q_both", k, graph) == pytest.approx(0.5)

    def test_transitive_prereqs_enter_pre(self, graph):
        # Pre(q_quad) = {q_add, q_lin} under Eq. 1 on this fixture: q_lin's
        # concept dominates quadratic's single concept; q_mul's multiplication
        # is not dominated by linear_equation.
        assert graph["q_quad"] == frozenset({"q_add", "q_lin"})

    def test_prerequisite_free_question_is_vacuously_one(self, graph):
        assert prerequisite_satisfaction("q_add", ["q_add"], graph) == 1.0

    def test_psr_only_defined_on_correct_answers(self, graph):
        with pytest.raises(ValueError, match="correctly-answered"):
            prerequisite_satisfaction("q_quad", ["q_add"], graph)

    def test_unknown_question_raises(self, graph):
        with pytest.raises(ValueError, match="unknown question"):
            prerequisite_satisfaction("q_ghost", ["q_ghost", "q_add"], graph)

    def test_duplicates_do_not_inflate(self, graph):
        k = ["q_add", "q_add", "q_lin"]
        assert prerequisite_satisfaction("q_lin", k, graph) == 1.0


class TestPSRAggregates:
    def test_macro_is_unweighted_mean(self, graph):
        # q_lin correct with q_add but not q_both -> PSR(q_lin)=0.5
        # (Pre(q_lin) = {q_add}); q_add correct, no prereqs -> PSR 1.0
        k = ["q_add", "q_lin", "q_both"]
        # PSR(q_lin) = 1.0 (Pre = {q_add} ⊆ K); PSR(q_both) = |{q_add,q_mul}∩K|/2 = 1/2
        assert psr_macro(k, graph) == pytest.approx((1.0 + 1.0 + 0.5) / 3)

    def test_micro_weights_by_prereq_count(self, graph):
        k = ["q_add", "q_lin", "q_both"]
        # hits: q_add 0/0 + q_lin 1/1 + q_both 1/2; totals 0 + 1 + 2 = 3
        assert psr_micro(k, graph) == pytest.approx(2 / 3)

    def test_micro_and_macro_diverge_when_prereq_counts_differ(self, graph):
        k = ["q_add", "q_lin", "q_both"]
        assert psr_macro(k, graph) != psr_micro(k, graph)

    def test_empty_state_scores_one(self, graph):
        assert psr_macro(set(), graph) == 1.0
        assert psr_micro(set(), graph) == 1.0
        assert psr_one_rate(set(), graph) == 1.0

    def test_human_anchor_not_reproduced_by_random_state(self, graph):
        # Humans at 0.796 accuracy score PSR ≈ 0.94. The probe must separate
        # accuracy from structural coherence: a HIGHER-accuracy state that
        # answers advanced questions without their prerequisites scores far
        # lower on every PSR view, exactly the paper's LLM pattern (Table 2:
        # Qwen2.5-32B beats human accuracy 0.849 vs 0.796 yet loses on PSR).
        coherent = ["q_add", "q_lin", "q_both", "q_mul", "q_quad"]  # acc 1.0, PSR 1.0
        lucky = ["q_mul", "q_both", "q_lin"]  # answered q_mul with zero prereq grounding
        assert psr_one_rate(coherent, graph) == pytest.approx(1.0)
        assert psr_one_rate(lucky, graph) == pytest.approx(0.0)
        assert psr_macro(lucky, graph) < psr_macro(coherent, graph)
        assert psr_micro(lucky, graph) < psr_micro(coherent, graph)

    def test_hard_violation_scores_zero(self, graph):
        # Correct q_mul with none of its prerequisites in K: PSR = 0.0.
        # This is the "3×3 correct while 3+3 fails" pattern from paper §3.3.1.
        assert psr_micro(["q_mul"], graph) == pytest.approx(0.0)
        assert psr_one_rate(["q_mul"], graph) == pytest.approx(0.0)


class TestPSROneRateAndDistribution:
    def test_psr_one_rate_counts_fully_grounded_answers(self, graph):
        # Pre(q_lin)={q_add} ⊆ K -> PSR 1.0; Pre(q_both)={q_add,q_mul} has
        # q_mul ∉ K -> PSR 0.5; q_add vacuously 1.0 → 2 of 3 fully grounded.
        k = ["q_add", "q_lin", "q_both"]
        assert psr_one_rate(k, graph) == pytest.approx(2 / 3)

    def test_distribution_buckets_sum_to_one(self, graph):
        k = ["q_add", "q_lin", "q_both"]
        dist = psr_distribution(k, graph)
        assert sum(dist) == pytest.approx(1.0)
        assert len(dist) == 6

    def test_distribution_places_partial_psr_in_correct_bucket(self, graph):
        # K = {q_add, q_both}: PSR(q_add)=1.0 -> bucket {=1.0};
        # PSR(q_both)=0.5 -> bucket [0.4, 0.6)
        dist = psr_distribution(["q_add", "q_both"], graph)
        assert dist[2] == pytest.approx(0.5)
        assert dist[5] == pytest.approx(0.5)

    def test_distribution_perfect_state_lands_in_eq_one_bucket(self, graph):
        dist = psr_distribution(["q_add", "q_lin", "q_both", "q_mul"], graph)
        assert dist[5] == pytest.approx(1.0)

    def test_empty_distribution_is_zero(self, graph):
        assert psr_distribution(set(), graph) == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------
# NB2: Scaffolding (Eq. 5)
# --------------------------------------------------------------------------


class TestScaffolding:
    def test_sg_matches_eq5(self):
        # |Q| = 100, baseline 50 correct, scaffolded 55 -> +0.05
        assert scaffolding_gain(
            {f"q{i}" for i in range(50)}, {f"q{i}" for i in range(55)}, 100
        ) == pytest.approx(0.05)

    def test_sg_negative_when_context_hurts(self):
        # Paper: Qwen2.5-7B prerequisite context SG = -0.56
        assert scaffolding_gain(
            {f"q{i}" for i in range(70)}, {f"q{i}" for i in range(14)}, 100
        ) == pytest.approx(-0.56)

    def test_deduplicates_input(self):
        assert scaffolding_gain(["a", "a"], ["a", "a", "b"], 10) == pytest.approx(0.1)

    def test_nonpositive_n_raises(self):
        with pytest.raises(ValueError):
            scaffolding_gain([], [], 0)

    def test_paper_finding_prereq_below_alternative(self):
        # Qwen3-80B: prereq SG +0.50 vs same-skill/similarity higher
        adv = prerequisite_scaffold_advantage(0.50, [0.70, 0.80, 0.10])
        assert adv < 0  # pattern-matching explains gains better than prereqs

    def test_kst_coherent_model_has_positive_advantage(self):
        assert prerequisite_scaffold_advantage(0.9, [0.2, 0.4]) > 0

    def test_advantage_requires_alternatives(self):
        with pytest.raises(ValueError):
            prerequisite_scaffold_advantage(0.5, [])


# --------------------------------------------------------------------------
# NB3: Subsumption (Eqs. 6-7)
# --------------------------------------------------------------------------


class TestSubsumption:
    def test_koc_full_subsumption_is_one(self):
        assert knowledge_overlap_coefficient(["a", "b"], ["a", "b", "c", "d"]) == 1.0

    def test_koc_is_symmetric(self):
        assert knowledge_overlap_coefficient(
            ["a", "b"], ["a", "b", "c"]
        ) == knowledge_overlap_coefficient(["a", "b", "c"], ["a", "b"])

    def test_koc_partial_overlap(self):
        # |∩|=1, min(|K|=2) -> 0.5
        assert knowledge_overlap_coefficient(["a", "x"], ["a", "b", "c"]) == pytest.approx(0.5)

    def test_koc_empty_states(self):
        assert knowledge_overlap_coefficient([], []) == 1.0
        assert knowledge_overlap_coefficient([], ["a"]) == 0.0

    def test_koc_norm_removes_chance_overlap(self):
        # Two independent random states over |Q|=100: sizes 10 and 20 with
        # seed 42 give |∩| = 4 -> raw KOC 0.4, chance p_max = 0.2 -> 0.25.
        # (The paper's point: raw KOC 0.4 looks like structure but is exactly
        # what chance predicts for a stronger learner at accuracy 0.2.)
        import random

        rng = random.Random(42)
        k1 = {f"q{i}" for i in rng.sample(range(100), 10)}
        k2 = {f"q{i}" for i in rng.sample(range(100), 20)}
        assert len(k1 & k2) == 4  # fixture is reproducible, not luck
        assert koc_normalized(k1, k2, 100) == pytest.approx(0.25)

    def test_koc_norm_perfect_subsumption_is_one(self):
        assert koc_normalized(["a", "b"], ["a", "b", "c", "d"], 4) == pytest.approx(1.0)

    def test_koc_norm_below_chance_is_negative(self):
        # disjoint states of equal size 10/100: KOC=0, p_max=0.1 -> (0-0.1)/0.9
        k1 = [f"a{i}" for i in range(10)]
        k2 = [f"b{i}" for i in range(10)]
        assert koc_normalized(k1, k2, 100) == pytest.approx(-0.1 / 0.9)

    def test_koc_norm_degenerate_perfect_stronger_learner(self):
        # p_max = 1 -> literal KOC returned unchanged (|∩|=1, min=1)
        assert koc_normalized(["a"], ["a", "b"], 2) == pytest.approx(1.0)
        # disjoint singletons: KOC 0 with p_max 0.5 -> (0 - 0.5)/(1 - 0.5) = -1
        assert koc_normalized(["a"], ["b"], 2) == pytest.approx(-1.0)

    def test_koc_norm_validates_question_count(self):
        with pytest.raises(ValueError):
            koc_normalized(["a"], [], 0)
        with pytest.raises(ValueError):
            koc_normalized(["a", "b", "c"], [], 2)

    def test_paper_anchor_closed_pair_overlap_is_low(self):
        # GPT-4.1-mini vs Claude: KOC_norm = 0.38 on a |Q|=4118 domain. Two
        # independently-sampled high-accuracy states score near chance
        # (~0.03, measured), while nested human-style states (weak mastery is
        # a subset of strong mastery) score 1.0. The probe must reproduce
        # that ordering — the paper's central NB3 contrast.
        import random

        def bernoulli(base: float, n: int, seed: int) -> set[str]:
            rng = random.Random(seed)
            return {f"q{i}" for i in range(n) if rng.random() < base}

        def nested(low_acc: float, high_acc: float, n: int, seed: int) -> tuple[set[str], set[str]]:
            # human-style: a question mastered by the weak group is almost
            # always mastered by the strong group (KST closure).
            rng = random.Random(seed)
            low: set[str] = set()
            high: set[str] = set()
            for i in range(n):
                strong = rng.random() < high_acc
                if strong or rng.random() < low_acc:
                    low.add(f"q{i}")
                if strong:
                    high.add(f"q{i}")
            return low, high

        s1, s2 = bernoulli(0.85, 4118, 1), bernoulli(0.84, 4118, 2)
        closed_pair = koc_normalized(s1, s2, 4118)
        low, high = nested(0.5, 0.89, 4118, 4)
        human_like = koc_normalized(low, high, 4118)
        assert closed_pair < 0.1, closed_pair  # ≈ chance for independent states
        assert human_like == pytest.approx(1.0)
        assert closed_pair < human_like

    def test_pairwise_matrix_is_symmetric_and_complete(self):
        learners = {
            "strong": ["a", "b", "c"],
            "weak": ["a"],
            "other": ["d"],
        }
        m = pairwise_koc_norm_matrix(learners, 4)
        assert set(m) == {
            ("other", "strong"),
            ("other", "weak"),
            ("strong", "weak"),
            ("strong", "other"),
            ("weak", "other"),
            ("weak", "strong"),
        }
        assert m[("strong", "weak")] == m[("weak", "strong")]
        assert m[("strong", "weak")] == pytest.approx(1.0)  # full subsumption
        assert m[("other", "weak")] == pytest.approx(-1 / 3)  # disjoint 1/3 states


# --------------------------------------------------------------------------
# Composite probe
# --------------------------------------------------------------------------


class TestKSTKnowledgeStructureProbe:
    def test_evaluate_matches_standalone_metrics(self, graph):
        probe = KSTKnowledgeStructureProbe(QUESTION_CONCEPTS, CONCEPT_PREREQS)
        assert probe.prereq_graph == graph
        k = ["q_add", "q_mul", "q_lin", "q_both"]
        report = probe.evaluate(k)
        assert report.accuracy == pytest.approx(4 / 5)  # |Q| = 5 in the fixture
        assert report.psr_micro == pytest.approx(psr_micro(k, graph))
        assert report.psr_macro == pytest.approx(psr_macro(k, graph))
        assert report.psr_one_rate == pytest.approx(psr_one_rate(k, graph))
        assert report.psr_distribution == psr_distribution(k, graph)
        assert report.n_correct == 4
        assert report.n_questions == 5

    def test_accuracy_divorced_from_structure(self):
        # Paper Table 2: Qwen2.5-32B beats human accuracy (0.849 vs 0.796)
        # while losing on every PSR view. Model both with the same probe.
        concepts = {f"c{i}": ([] if i == 0 else [f"c{i - 1}"]) for i in range(10)}
        qconcepts = {f"q{i}": {f"c{i}"} for i in range(10)}
        probe = KSTKnowledgeStructureProbe(qconcepts, concepts)
        human = ["q0", "q1", "q2", "q3", "q4", "q5"]  # acc .6, coherent
        llm = ["q0", "q1", "q2", "q4", "q6", "q8", "q9"]  # acc .7, holes
        h, m = probe.evaluate(human), probe.evaluate(llm)
        assert m.accuracy > h.accuracy
        assert m.psr_one_rate < h.psr_one_rate
        assert m.psr_micro < h.psr_micro

    def test_evaluate_rejects_unknown_questions(self):
        probe = KSTKnowledgeStructureProbe(QUESTION_CONCEPTS, CONCEPT_PREREQS)
        with pytest.raises(ValueError, match="unknown questions"):
            probe.evaluate(["q_ghost"])

    def test_evaluate_rejects_oversized_state(self):
        probe = KSTKnowledgeStructureProbe(QUESTION_CONCEPTS, CONCEPT_PREREQS)
        with pytest.raises(ValueError, match="unknown questions"):
            probe.evaluate([*list(QUESTION_CONCEPTS), "extra"], n_questions=2)
        with pytest.raises(ValueError, match="larger than"):
            # all questions valid but the declared |Q| is smaller
            probe.evaluate(list(QUESTION_CONCEPTS), n_questions=2)

    def test_subsumption_uses_graph_question_count(self):
        probe = KSTKnowledgeStructureProbe(QUESTION_CONCEPTS, CONCEPT_PREREQS)
        assert probe.subsumption(["q_add"], ["q_add", "q_mul"]) == pytest.approx(1.0)

    def test_probe_is_frozen(self):
        probe = KSTKnowledgeStructureProbe(QUESTION_CONCEPTS, CONCEPT_PREREQS)
        with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
            probe.question_concepts = {}  # type: ignore[misc]
