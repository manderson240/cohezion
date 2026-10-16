"""Unit tests for First-Principles Systems Engineering V-Model Rigor Engine."""

from __future__ import annotations

from cohezion.compound.first_principles_vmodel_engine import (
    FirstPrinciplesDomain,
    FirstPrinciplesMath,
    build_first_principles_vmodel_compound_graph,
    run_first_principles_audit,
)
from cohezion.compound.vmodel_compound_graph_system import VModelLevel


class TestFirstPrinciplesMathInvariants:
    """Rigorous mathematical invariant unit tests."""

    def test_rsna_kolmogorov_monotonicity_satisfied(self) -> None:
        p_overall = 0.95
        p_findings = [0.10, 0.45, 0.90, 0.32, 0.88]
        res = FirstPrinciplesMath.verify_kolmogorov_monotonicity(p_overall, p_findings)
        assert res.verified is True
        assert res.domain == FirstPrinciplesDomain.RSNA_KNEE
        assert res.margin >= 0.0
        assert len(res.certificate) == 64

    def test_rsna_kolmogorov_monotonicity_violated(self) -> None:
        p_overall = 0.70
        p_findings = [0.10, 0.95, 0.30]
        res = FirstPrinciplesMath.verify_kolmogorov_monotonicity(p_overall, p_findings)
        assert res.verified is False
        assert res.margin < 0.0
        assert res.diagnostics["violations_count"] == 1

    def test_rsna_bilateral_joint_symmetry(self) -> None:
        left = [0.5, 0.2, 0.8]
        right = [0.52, 0.19, 0.79]
        res = FirstPrinciplesMath.verify_bilateral_joint_symmetry(
            left, right, max_normal_divergence=0.20
        )
        assert res.verified is True
        assert res.margin >= 0.0

    def test_casmi26_adduct_mass_defect_h_plus(self) -> None:
        # MW = 310.22966 -> [M+H]+ = 311.236936
        mw = 310.22966
        obs_mz = mw + FirstPrinciplesMath.PROTON_MASS + 0.0001
        res = FirstPrinciplesMath.verify_adduct_mass_defect(
            obs_mz, "[M+H]+", mw, tolerance_ppm=15.0
        )
        assert res.verified is True
        assert res.diagnostics["ppm"] < 15.0

    def test_casmi26_adduct_mass_defect_na_plus(self) -> None:
        # MW = 310.22966 -> [M+Na]+ = 333.218878
        mw = 310.22966
        obs_mz = mw + FirstPrinciplesMath.SODIUM_MASS + 0.0002
        res = FirstPrinciplesMath.verify_adduct_mass_defect(
            obs_mz, "[M+Na]+", mw, tolerance_ppm=15.0
        )
        assert res.verified is True
        assert res.diagnostics["ppm"] < 15.0

    def test_casmi26_neutral_loss_parsimony(self) -> None:
        precursor = 400.0
        # Fragment with loss of CO2 (43.989829 Da)
        fragment = precursor - 43.989829 + 0.001
        res = FirstPrinciplesMath.verify_neutral_loss_parsimony(
            precursor, fragment, tolerance_da=0.015
        )
        assert res.verified is True
        assert res.diagnostics["matched_neutral_loss"] == "CO2"

    def test_arc_d4_group_actions(self) -> None:
        grid = [
            [1, 2],
            [3, 4],
        ]
        actions = FirstPrinciplesMath.compute_d4_group_actions(grid)
        assert len(actions) == 8
        assert actions["identity"] == grid
        assert actions["rot180"] == [[4, 3], [2, 1]]
        assert actions["flip_horizontal"] == [[2, 1], [4, 3]]
        assert actions["flip_vertical"] == [[3, 4], [1, 2]]

    def test_arc_euler_characteristic(self) -> None:
        # Planar unit square with 1 face, 4 edges, 4 vertices -> chi = 4 - 4 + 1 = 1
        res = FirstPrinciplesMath.verify_euler_characteristic_preservation(
            v=4, e=4, f=1, expected_genus=0
        )
        assert res.verified is True
        assert res.diagnostics["euler_characteristic"] == 1

    def test_splitmix64_zobrist_fingerprint(self) -> None:
        tokens_a = [1, 2, 3, 4, 5]
        tokens_b = [1, 2, 3, 4, 6]
        hash_a1 = FirstPrinciplesMath.splitmix64_zobrist_fingerprint(tokens_a)
        hash_a2 = FirstPrinciplesMath.splitmix64_zobrist_fingerprint(tokens_a)
        hash_b = FirstPrinciplesMath.splitmix64_zobrist_fingerprint(tokens_b)

        assert hash_a1 == hash_a2  # Deterministic
        assert hash_a1 != hash_b  # Collision resistant

    def test_sinkhorn_wasserstein_divergence(self) -> None:
        dist_p = [0.25, 0.25, 0.25, 0.25]
        dist_q = [0.24, 0.26, 0.25, 0.25]
        dist = FirstPrinciplesMath.sinkhorn_wasserstein_divergence(dist_p, dist_q)
        assert dist >= 0.0
        assert dist < 0.05


class TestFirstPrinciplesVModelCompoundGraph:
    """Systems Engineering V-Model Rigor tests."""

    def test_vmodel_graph_structure_and_levels(self) -> None:
        graph = build_first_principles_vmodel_compound_graph()
        assert len(graph.goals) == 12
        assert len(graph.loops) == 4
        assert len(graph.proofs) == 8

        sys_goals = [g for g in graph.goals.values() if g.vmodel_level == VModelLevel.SYSTEM]
        sub_goals = [g for g in graph.goals.values() if g.vmodel_level == VModelLevel.SUBSYSTEM]
        assert len(sys_goals) == 4
        assert len(sub_goals) == 8

    def test_vmodel_graph_kahn_acyclicity(self) -> None:
        graph = build_first_principles_vmodel_compound_graph()
        is_dag, order = graph.verify_acyclicity()
        assert is_dag is True
        assert len(order) == len(graph.goals) + len(graph.loops) + len(graph.proofs)

    def test_vmodel_100_percent_vtm_traceability(self) -> None:
        graph = build_first_principles_vmodel_compound_graph()
        vtm = graph.get_verification_traceability_matrix()
        assert len(vtm) == 12
        verified_count = sum(1 for item in vtm if item["is_verified"])
        assert verified_count == 12

    def test_run_first_principles_audit_all_pass(self) -> None:
        report = run_first_principles_audit()
        assert report["status"] == "VERIFIED_FIRST_PRINCIPLES"
        for name, passed in report["invariants"].items():
            assert passed is True, f"Invariant {name} failed in audit"
        assert report["vmodel_rigor"]["vtm_coverage_percentage"] == 100.0
        assert report["vmodel_rigor"]["is_dag"] is True
