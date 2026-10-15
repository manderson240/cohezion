"""Tests for SurrealDB 3.3.0 Kaggle Graph Engineering Engine & Recursive Learning Linkage.

Verifies:
1. Active competition nodes strictly conform to rules (Mandate 8: no expired/pokemon comps).
2. Physical & mathematical invariant nodes and AutoHarness deterministic policies.
3. Multi-hop GraphRAG traversal:
   competition -> has_invariant -> invariant <- enforces_invariant <- autoharness_policy
4. End-to-end score provenance trace:
   kaggle_score <- yielded_score <- submission_record <- generated_submission <- kaggle_kernel
5. Cross-competition knowledge transfer queries.
6. RecursiveLearningEngine automatic graph linkage on new learning cycles.
"""

from __future__ import annotations

import pytest

from cohezion.agi.recursive_learning import RecursiveLearningEngine
from cohezion.knowledge_graph.kaggle_graph_engine import KaggleGraphEngine


@pytest.fixture(scope="module")
def graph_engine() -> KaggleGraphEngine:
    engine = KaggleGraphEngine()
    # Ensure graph is seeded and edges wired
    engine.seed_active_competitions()
    engine.seed_first_principles_invariants()
    engine.seed_autoharness_policies()
    engine.seed_kernels_and_scores()
    engine.build_graph_relations()
    return engine


def test_active_competitions_mandate_filter(graph_engine: KaggleGraphEngine):
    """Verify active competitions exist and no pokemon/expired competitions exist (Mandate 8)."""
    res = graph_engine.execute(
        "SELECT slug, title, status FROM kaggle_competition WHERE status = 'active';"
    )
    assert res[0]["status"] == "OK"
    comps = res[0]["result"]
    slugs = [c["slug"] for c in comps]

    assert "arc-prize-2026-arc-agi-2" in slugs
    assert "arc-prize-2026-arc-agi-3" in slugs
    assert "rsna-knee-abnormality-detection" in slugs
    assert "biohub-cell-tracking-during-development" in slugs
    assert "enveda-CASMI26-molecule-id-mass-spectra" in slugs
    assert "gemma-4-developer-agent" in slugs

    # Strict Mandate 8 rule verification
    for c in comps:
        assert "pokemon" not in c.get("slug", "").lower()
        if c.get("title"):
            assert "pokemon" not in c["title"].lower()



def test_invariants_and_autoharness_policies(graph_engine: KaggleGraphEngine):
    """Verify first-principles invariants and zero-cost verifier policies."""
    res = graph_engine.execute("SELECT id, code, domain FROM kaggle_invariant;")
    assert res[0]["status"] == "OK"
    invariants = {inv["id"]: inv for inv in res[0]["result"]}

    assert "kaggle_invariant:inv_d4_dihedral" in invariants
    assert "kaggle_invariant:inv_non_overlapping_tta" in invariants
    assert "kaggle_invariant:inv_stem_adaptive_threshold" in invariants
    assert "kaggle_invariant:inv_precursor_isobar" in invariants
    assert "kaggle_invariant:inv_copula_rank" in invariants

    res_p = graph_engine.execute("SELECT id, name, zero_cost_latency FROM autoharness_policy;")
    assert res_p[0]["status"] == "OK"
    policies = {p["id"]: p for p in res_p[0]["result"]}

    assert "autoharness_policy:policy_arc_d4_verifier" in policies
    assert "autoharness_policy:policy_rsna_time_budget" in policies
    assert "autoharness_policy:policy_biohub_edge_guard" in policies
    assert "autoharness_policy:policy_ast_callable_anchor" in policies


def test_multi_hop_competition_lineage(graph_engine: KaggleGraphEngine):
    """Verify multi-hop GraphRAG traversal for ARC-AGI-2."""
    lineage = graph_engine.get_competition_lineage("arc-prize-2026-arc-agi-2")
    assert lineage is not None
    assert lineage["slug"] == "arc-prize-2026-arc-agi-2"
    assert lineage["current_best_score"] == 30.14

    # Traversal 1: competition -> has_invariant
    invariants = lineage.get("invariants", [])
    inv_codes = [inv["code"] for inv in invariants if inv]
    assert "D4_DIHEDRAL_INVARIANCE" in inv_codes

    # Traversal 2: competition -> has_invariant <- enforces_invariant <- autoharness_policy
    policies = lineage.get("governing_policies", [])
    pol_ids = [p["id"] for p in policies if p]
    assert "autoharness_policy:policy_arc_d4_verifier" in pol_ids

    # Traversal 3: competition <- targets_competition <- kaggle_kernel
    kernels = lineage.get("dispatched_kernels", [])
    kernel_ids = [k["id"] for k in kernels if k]
    assert "kaggle_kernel:arc_quad_l4" in kernel_ids

    # Traversal 4: competition <- targets <- kernel -> generated_submission -> submission_record
    submissions = lineage.get("generated_submissions", [])
    sub_ids = [s["id"] for s in submissions if s]
    assert "submission_record:arc_quad_v1" in sub_ids

    # Traversal 5: competition <- targets <- kernel -> submission -> yielded_score -> kaggle_score
    scores = lineage.get("yielded_scores", [])
    score_vals = [s["value"] for s in scores if s]
    assert 30.14 in score_vals


def test_end_to_end_score_provenance(graph_engine: KaggleGraphEngine):
    """Verify reverse GraphRAG score provenance trace for RSNA Knee SOTA score."""
    prov = graph_engine.get_score_provenance("rsna_sota")
    assert prov is not None
    assert prov["id"] == "kaggle_score:rsna_sota"
    assert prov["value"] == 0.955
    assert prov["metric"] == "ROC-AUC"

    # Provenance back to submission
    submissions = prov.get("submission", [])
    assert any(s["id"] == "submission_record:rsna_v14" for s in submissions if s)

    # Provenance back to kernel
    kernels = prov.get("kernel", [])
    assert any(k["id"] == "kaggle_kernel:rsna_knee_ensemble" for k in kernels if k)

    # Provenance to policy & invariant
    policies = prov.get("policies", [])
    assert any(p["id"] == "autoharness_policy:policy_rsna_time_budget" for p in policies if p)

    invariants = prov.get("invariants", [])
    assert any(inv["id"] == "kaggle_invariant:inv_non_overlapping_tta" for inv in invariants if inv)

    # Provenance to target competition
    comps = prov.get("competition", [])
    assert any(c["slug"] == "rsna-knee-abnormality-detection" for c in comps if c)


def test_cross_competition_transfers(graph_engine: KaggleGraphEngine):
    """Verify cross-competition transfer query identifies multi-target learnings."""
    transfers = graph_engine.get_cross_competition_transfers()
    assert len(transfers) >= 1
    for t in transfers:
        assert "id" in t
        assert "title" in t
        assert len(t.get("targeted_competitions", [])) >= 2


@pytest.mark.asyncio
async def test_recursive_learning_cycle_links_graph(graph_engine: KaggleGraphEngine):
    """Verify RecursiveLearningEngine automatically links newly minted learning to Kaggle graph."""
    engine = RecursiveLearningEngine()
    test_summary = "First-principles verification of topological dihedral symmetry on ARC-AGI-2"
    result = await engine.execute_recursive_learning_cycle(
        trajectory_summary=test_summary,
        target_competition="arc-prize-2026-arc-agi-2",
        transfers_to=["arc-prize-2026-arc-agi-3"],
    )

    assert result.surreal_persisted is True
    assert result.zkfv_verified is True

    # Verify edge was formed in SurrealDB
    check_surql = f"""
    SELECT
        ->applies_to->kaggle_competition.slug AS targets,
        ->transfers_to->kaggle_competition.slug AS transfers
    FROM learning:`{result.cycle_id}`;
    """
    res = graph_engine.execute(check_surql)
    assert res[0]["status"] == "OK"
    hits = res[0]["result"]
    assert len(hits) == 1
    assert "arc-prize-2026-arc-agi-2" in hits[0]["targets"]
    assert "arc-prize-2026-arc-agi-3" in hits[0]["transfers"]
