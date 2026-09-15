"""KST-grounded knowledge-structure probe (arXiv:2609.05245).

Implements, as deterministic zero-cost analysis over question-level response
patterns, the Knowledge Space Theory (KST) evaluation framework of:

    Peng Cui, Heejin Do, Mrinmaya Sachan.
    "Do LLMs Exhibit Coherent Knowledge Structures in Mathematical Reasoning?
    A Perspective from Knowledge Space Theory."
    EMNLP 2026 Findings. https://arxiv.org/abs/2609.05245 (v1, 2026-09-04).

The paper operationalizes KST (Doignon & Falmagne, 1985/2012) at the question
level: concepts ``C`` carry expert prerequisite relations; question ``q`` is a
prerequisite of question ``q'`` iff *every* concept of ``q`` is dominated by
some concept of ``q'`` (Eq. 1, deliberately strict). A learner's knowledge
state ``K`` is the set of questions answered correctly, and three normative
behaviors (NB1-NB3) are scored with:

* PSR       — Prerequisite Satisfaction Ratio per correct question (Eq. 2),
              aggregated macro (Eq. 3) and micro (Eq. 4), plus the fraction of
              correct answers with PSR = 1 (full KST closure).
* SG        — Scaffolding Gain: accuracy delta from in-context prerequisite
              exemplars vs. the no-context baseline (Eq. 5, NB2).
* KOC       — Knowledge Overlap Coefficient ``|K1 ∩ K2| / min(|K1|, |K2|)``
              (Eq. 6) and its chance-corrected normalization (Eq. 7, NB3).

Headline empirical anchors (XES3G5M, 4,118 questions, 18,066 students, 8 LLMs):
human learners hit micro/macro PSR 0.936/0.942 at only 0.796 accuracy with
72.7% of correct answers at PSR = 1.0, while the strongest LLM (Qwen3-Next-80B)
reaches 48.16% despite 0.925 accuracy; prerequisite context yields no
systematic scaffolding advantage (SG = -0.56 .. +0.70, below same-skill and
similarity retrieval); closed-source models overlap each other at KOC_norm =
0.38. Accuracy and LLM-as-judge trajectory scores miss all of this: they are
local per-item measures, whereas PSR/KOC are global cross-question consistency
checks (paper Appendix C shows Relevance 4.76 -> 4.86 -> 4.93 rising while
PSR=1 rates move 20.81% -> 27.32% -> 25.44%, i.e. non-monotonic).

This module is pure stdlib, side-effect free and fail-closed: ill-formed
concept graphs (cycles, concept-less questions) raise ValueError instead of
silently producing misleading structure.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field


__all__ = [
    "KSTKnowledgeStructureProbe",
    "KnowledgeStructureReport",
    "derive_prerequisite_graph",
    "knowledge_overlap_coefficient",
    "koc_normalized",
    "pairwise_koc_norm_matrix",
    "prerequisite_satisfaction",
    "prerequisite_scaffold_advantage",
    "psr_distribution",
    "psr_macro",
    "psr_micro",
    "psr_one_rate",
    "reflexive_transitive_closure",
    "scaffolding_gain",
]


# --------------------------------------------------------------------------
# Concept-level primitives (paper §3.1-3.2)
# --------------------------------------------------------------------------


def reflexive_transitive_closure(
    concept_prereqs: Mapping[str, Iterable[str]],
) -> dict[str, frozenset[str]]:
    """Return the reflexive-transitive closure of a concept prerequisite DAG.

    ``concept_prereqs[c]`` lists concepts that must be mastered before ``c``.
    The returned mapping maps every concept to its prerequisite-or-equal set
    (``c ⪯ c`` included, per the reflexive partial order in paper §3.1).

    Raises:
        ValueError: if the prerequisite edges form a directed cycle — a
            prerequisite relation must be a strict partial order; cycles mean
            the upstream standard (or its LLM extraction) is malformed, and
            scoring against it would be meaningless.
    """
    edges = {c: set(ps) for c, ps in concept_prereqs.items()}
    for c, ps in edges.items():
        for p in ps:
            if p == c:
                raise ValueError(f"concept {c!r} lists itself as a prerequisite")
            edges.setdefault(p, set())

    state: dict[str, int] = {}  # 0=visiting, 1=done
    closure: dict[str, frozenset[str]] = {}

    def visit(node: str, stack: set[str]) -> frozenset[str]:
        mark = state.get(node)
        if mark == 1:
            return closure[node]
        if node in stack:
            raise ValueError(f"prerequisite cycle detected involving {node!r}")
        stack.add(node)
        acc = {node}
        for pre in edges.get(node, ()):  # direct prerequisites
            acc |= visit(pre, stack)
        stack.discard(node)
        state[node] = 1
        closure[node] = frozenset(acc)
        return closure[node]

    for concept in edges:
        visit(concept, set())
    return closure


def derive_prerequisite_graph(
    question_concepts: Mapping[str, Iterable[str]],
    concept_prereqs: Mapping[str, Iterable[str]],
) -> dict[str, frozenset[str]]:
    """Induce question-level prerequisites from concept dependencies (Eq. 1).

    Paper definition (strict form, intentionally conservative): question
    ``q_i`` is a prerequisite of question ``q_j`` iff

        ∀ c_a ∈ C(q_i), ∃ c_b ∈ C(q_j) such that c_a ⪯ c_b

    i.e. every concept of ``q_i`` is dominated by *some* concept of ``q_j``
    (equality counts, so shared concepts participate). The weaker "any single
    concept pair" alternative is deliberately NOT implemented — the paper
    rejects it as too noisy (§3.2, "Deriving question dependencies").

    Args:
        question_concepts: question id -> concepts required by the question.
        concept_prereqs: concept -> direct prerequisite concepts.

    Returns:
        Mapping question id -> frozenset of prerequisite question ids.

    Raises:
        ValueError: if any question has an empty concept set. The paper
            *discards* concept-less questions (Appendix B: annotation recall
            gaps remove them); vacuous-truth semantics would otherwise make
            every question a prerequisite of such targets, so we fail closed
            and require the caller to filter them first.
    """
    closure = reflexive_transitive_closure(concept_prereqs)
    concepts = {q: frozenset(cs) for q, cs in question_concepts.items()}
    for q, cs in concepts.items():
        if not cs:
            raise ValueError(f"question {q!r} has no concepts; discard it (paper App. B)")
        unknown = cs - closure.keys()
        if unknown:
            raise ValueError(f"question {q!r} references unknown concepts: {sorted(unknown)}")

    ids = sorted(concepts)
    graph: dict[str, frozenset[str]] = {}
    for j in ids:
        target_concepts = concepts[j]
        prereqs = [
            i
            for i in ids
            if i != j
            and all(any(ca in closure[cb] for cb in target_concepts) for ca in concepts[i])
        ]
        graph[j] = frozenset(prereqs)
    return graph


# --------------------------------------------------------------------------
# NB1 — Prerequisite Satisfaction (paper §3.3.1, Eqs. 2-4)
# --------------------------------------------------------------------------


def prerequisite_satisfaction(
    question: str,
    correct: Iterable[str],
    prereq_graph: Mapping[str, Iterable[str]],
) -> float:
    """Per-question PSR (Eq. 2): ``|Pre(q) ∩ K| / |Pre(q)|`` for ``q ∈ K``.

    Only correctly-answered questions are scored (the paper computes PSR on
    ``q ∈ K_l`` exclusively). A correct question with no prerequisites is
    vacuously coherent and scores 1.0. PSR > 1 is impossible; a correct target
    question absent from ``prereq_graph`` is a lookup error.

    Raises:
        ValueError: if ``question`` was not answered correctly, or is unknown.
    """
    k = frozenset(correct)
    if question not in k:
        raise ValueError(f"PSR is defined only for correctly-answered questions ({question!r} ∉ K)")
    if question not in prereq_graph:
        raise ValueError(f"unknown question {question!r}: not in the prerequisite graph")
    pre = frozenset(prereq_graph[question])
    if not pre:
        return 1.0
    return len(pre & k) / len(pre)


def psr_macro(correct: Iterable[str], prereq_graph: Mapping[str, Iterable[str]]) -> float:
    """Macro-aggregated PSR (Eq. 3): unweighted mean of per-question PSR.

    All-vacuous states (every correct question prerequisite-free) score 1.0:
    no constraint can be violated.
    """
    per_q = [prerequisite_satisfaction(q, correct, prereq_graph) for q in sorted(set(correct))]
    if not per_q:
        return 1.0
    return sum(per_q) / len(per_q)


def psr_micro(correct: Iterable[str], prereq_graph: Mapping[str, Iterable[str]]) -> float:
    """Micro-aggregated PSR (Eq. 4): prerequisite-count-weighted mean.

    ``Σ|Pre(q) ∩ K| / Σ|Pre(q)|`` over correct ``q``; zero-prerequisite
    questions contribute to neither term. All-vacuous inputs score 1.0.
    """
    k = frozenset(correct)
    hit = 0
    total = 0
    for q in k:
        if q not in prereq_graph:
            raise ValueError(f"unknown question {q!r}: not in the prerequisite graph")
        pre = frozenset(prereq_graph[q])
        hit += len(pre & k)
        total += len(pre)
    if total == 0:
        return 1.0
    return hit / total


def psr_one_rate(correct: Iterable[str], prereq_graph: Mapping[str, Iterable[str]]) -> float:
    """Fraction of correct answers with PSR = 1.0 (full KST closure, NB1).

    This is the paper's headline gap metric: 72.7% for humans (81.6% on the
    verified subset) vs. at most 48.16% for any evaluated LLM (55.7% verified).
    Zero-prerequisite correct answers count as 1.0 (vacuously coherent).
    """
    per_q = [prerequisite_satisfaction(q, correct, prereq_graph) for q in sorted(set(correct))]
    if not per_q:
        return 1.0
    return sum(1 for v in per_q if v == 1.0) / len(per_q)


def psr_distribution(
    correct: Iterable[str],
    prereq_graph: Mapping[str, Iterable[str]],
) -> tuple[float, ...]:
    """Table-2 question-level PSR histogram over correct answers.

    Buckets: [0,0.2), [0.2,0.4), [0.4,0.6), [0.6,0.8), [0.8,1.0), {=1.0}.
    Returns six fractions summing to 1.0 (0.0 for an empty knowledge state).
    """
    edges = (0.2, 0.4, 0.6, 0.8)  # first bucket [0,0.2) is the implicit fallthrough
    buckets = [0.0] * 6
    per_q = [prerequisite_satisfaction(q, correct, prereq_graph) for q in sorted(set(correct))]
    if not per_q:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    n = len(per_q)
    for v in per_q:
        idx = 5
        for i, e in enumerate(edges):
            if v < e:
                idx = i
                break
        buckets[idx] += 1 / n
    return tuple(buckets)


# --------------------------------------------------------------------------
# NB2 — Scaffolding effect (paper §3.3.1, Eq. 5)
# --------------------------------------------------------------------------


def scaffolding_gain(
    baseline_correct: Iterable[str],
    scaffolded_correct: Iterable[str],
    n_questions: int,
) -> float:
    """Scaffolding Gain (Eq. 5): ``(|K^+pre| − |K|) / |Q|``.

    Positive means prerequisite-grounded in-context exemplars improved accuracy
    over the no-context baseline. NB2 predicts a *systematic advantage* of
    prerequisite exemplars over same-skill / similarity / random exemplars; the
    paper found the opposite (prerequisite SG ranged -0.56 .. +0.70 and never
    dominated), which ``prerequisite_scaffold_advantage`` encodes directly.
    """
    if n_questions <= 0:
        raise ValueError("n_questions must be positive")
    delta = len(set(scaffolded_correct)) - len(set(baseline_correct))
    return delta / n_questions


def prerequisite_scaffold_advantage(
    sg_prerequisite: float,
    sg_alternatives: Sequence[float],
) -> float:
    """NB2 coherence score: prerequisite SG minus the best alternative SG.

    ``> 0`` — prerequisite knowledge scaffolds better than any surface-similar
    alternative (KST-coherent). ``<= 0`` — gains are explained by contextual
    pattern matching at least as well as by prerequisite structure, the
    paper's Finding on NB2.
    """
    if not sg_alternatives:
        raise ValueError("sg_alternatives must contain at least one baseline strategy")
    return sg_prerequisite - max(sg_alternatives)


# --------------------------------------------------------------------------
# NB3 — Knowledge subsumption across learners (paper §3.3.2, Eqs. 6-7)
# --------------------------------------------------------------------------


def knowledge_overlap_coefficient(k1: Iterable[str], k2: Iterable[str]) -> float:
    """KOC (Eq. 6): ``|K1 ∩ K2| / min(|K1|, |K2|)`` ∈ [0, 1].

    1.0 = the smaller knowledge state is fully subsumed by the larger. Two
    empty states score 1.0 (trivially nested); one empty state scores 0.0.
    Raw KOC is inflated by chance overlap (expected value = the stronger
    learner's accuracy); prefer :func:`koc_normalized` for comparisons.
    """
    s1, s2 = frozenset(k1), frozenset(k2)
    denom = min(len(s1), len(s2))
    if denom == 0:
        return 1.0 if len(s1) == len(s2) else 0.0
    return len(s1 & s2) / denom


def koc_normalized(
    k1: Iterable[str],
    k2: Iterable[str],
    n_questions: int,
) -> float:
    """Chance-corrected KOC (Eq. 7): ``(KOC − p_max) / (1 − p_max)``.

    ``p_max = max(|K1|, |K2|) / |Q|`` is the expected chance overlap between
    random knowledge states. 0 = chance-level overlap, > 0 = systematic
    subsumption beyond chance, 1 = perfect subsumption. Below-chance overlap
    scores negative (anti-aligned states) and is left unclamped. When the
    stronger learner is perfect (``p_max = 1``) chance overlap equals 1.0 and
    the literal subsumption value is returned unchanged (degenerate regime).

    Raises:
        ValueError: if ``n_questions`` is not positive or a state exceeds it.
    """
    if n_questions <= 0:
        raise ValueError("n_questions must be positive")
    s1, s2 = frozenset(k1), frozenset(k2)
    if len(s1) > n_questions or len(s2) > n_questions:
        raise ValueError("knowledge state larger than the question set")
    p_max = max(len(s1), len(s2)) / n_questions
    if p_max >= 1.0:
        return knowledge_overlap_coefficient(s1, s2)
    raw = knowledge_overlap_coefficient(s1, s2)
    return (raw - p_max) / (1.0 - p_max)


def pairwise_koc_norm_matrix(
    learners: Mapping[str, Iterable[str]],
    n_questions: int,
) -> dict[tuple[str, str], float]:
    """All-pairs KOC_norm (Eq. 7) for NB3 cohort analysis (paper Figure 4).

    Human learner groups score near-perfect mutual subsumption; the paper's
    LLM panel does not (closed-source pair GPT-4.1-mini / Claude Sonnet 4.6:
    0.38), so low values here flag incoherent, fragmented knowledge growth.
    """
    names = sorted(learners)
    states = {name: frozenset(learners[name]) for name in names}
    matrix: dict[tuple[str, str], float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            v = koc_normalized(states[a], states[b], n_questions)
            matrix[(a, b)] = v
            matrix[(b, a)] = v
    return matrix


# --------------------------------------------------------------------------
# Composite probe
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowledgeStructureReport:
    """NB1/NB2-style structural metrics for one learner's knowledge state."""

    accuracy: float
    psr_macro: float
    psr_micro: float
    psr_one_rate: float
    psr_distribution: tuple[float, ...]
    n_correct: int
    n_questions: int


@dataclass(frozen=True, slots=True)
class KSTKnowledgeStructureProbe:
    """Bundle a question prerequisite graph with the NB1/NB3 metric battery.

    Construct from concept annotations plus an expert concept-dependency
    standard (paper §3.2: NYS Mathematics Learning Standards — 480 concepts,
    148 clusters, 63 domains; LLM-annotated in two stages, clusters first).
    Then :meth:`evaluate` scores any response pattern exactly as the paper
    scores its eight LLMs and 18,066 human learners.
    """

    question_concepts: Mapping[str, Iterable[str]]
    concept_prereqs: Mapping[str, Iterable[str]]
    # Computed in __post_init__ (slot must be declared for frozen+slots dataclasses).
    _prereq_graph: dict[str, frozenset[str]] | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        graph = derive_prerequisite_graph(self.question_concepts, self.concept_prereqs)
        object.__setattr__(self, "_prereq_graph", graph)

    @property
    def prereq_graph(self) -> dict[str, frozenset[str]]:
        """Induced question-level prerequisite graph (Eq. 1)."""
        # mypy narrowing; graph is always built in __post_init__.
        graph = self._prereq_graph
        if graph is None:  # pragma: no cover - impossible post __post_init__
            raise ValueError("prerequisite graph not initialised")
        return graph

    def evaluate(
        self,
        correct: Iterable[str],
        n_questions: int | None = None,
    ) -> KnowledgeStructureReport:
        """Score a knowledge state (NB1 metrics; accuracy if |Q| supplied).

        ``n_questions`` defaults to the number of questions in the graph, which
        matches the paper's practice of evaluating over the full question set.
        """
        graph = self.prereq_graph
        k = frozenset(correct)
        unknown = k - graph.keys()
        if unknown:
            raise ValueError(f"knowledge state references unknown questions: {sorted(unknown)}")
        total = n_questions if n_questions is not None else len(graph)
        if n_questions is not None and len(k) > n_questions:
            raise ValueError("knowledge state larger than the question set")
        return KnowledgeStructureReport(
            accuracy=len(k) / total if total else 0.0,
            psr_macro=psr_macro(k, graph),
            psr_micro=psr_micro(k, graph),
            psr_one_rate=psr_one_rate(k, graph),
            psr_distribution=psr_distribution(k, graph),
            n_correct=len(k),
            n_questions=total,
        )

    def subsumption(self, k1: Iterable[str], k2: Iterable[str]) -> float:
        """Chance-corrected KOC between two knowledge states over this probe's Q."""
        return koc_normalized(k1, k2, len(self.prereq_graph))
