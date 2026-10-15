"""Kaggle Graph Engineering Engine for SurrealDB v3.3.0.

Provides graph-relational provenance and GraphRAG multi-hop retrieval connecting:
- Active Kaggle Competitions (Targets)
- Physical, Mathematical & Topological Invariants
- AutoHarness Deterministic Verification Policies
- Kaggle Kernels, Submissions & Leaderboard Scores
- Tri-temporal Recursive Learnings (with HNSW vector search)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.request
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("KaggleGraphEngine")

SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")


class KaggleGraphEngine:
    """SurrealDB 3.3.0 Native Graph Engine for Kaggle Recursive Learning."""

    def __init__(
        self,
        url: str = SURREAL_URL,
        ns: str = SURREAL_NS,
        db: str = SURREAL_DB,
        user: str = SURREAL_USER,
        password: str = SURREAL_PASS,
    ) -> None:
        self.url = url
        self.ns = ns
        self.db = db
        auth_bytes = f"{user}:{password}".encode("ascii")
        self._auth = base64.b64encode(auth_bytes).decode("ascii")

    def execute(self, surql: str) -> list[dict[str, Any]]:
        """Execute raw SurrealQL statements against SurrealDB endpoint."""
        req = urllib.request.Request(  # noqa: S310
            self.url,
            data=surql.encode("utf-8"),
            headers={
                "Authorization": f"Basic {self._auth}",
                "surreal-ns": self.ns,
                "surreal-db": self.db,
                "Accept": "application/json",
                "Content-Type": "text/plain",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:  # noqa: S310
                if resp.status != 200:
                    raise RuntimeError(f"SurrealDB HTTP {resp.status}: {resp.read().decode('utf-8')}")
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            logger.error("SurrealDB query failed (%s): %s", exc.code, err_body)
            raise RuntimeError(f"SurrealDB query error: {err_body}") from exc

    def seed_active_competitions(self) -> dict[str, Any]:
        """Seed canonical active Kaggle competitions using slug IDs."""
        competitions = [
            {
                "slug": "arc-prize-2026-arc-agi-2",
                "title": "ARC Prize 2026: ARC-AGI-2 Track",
                "prize_pool": "$700,000 USD",
                "deadline": "2026-11-02",
                "metric": "Exact Grid Match",
                "current_best_score": 30.14,
                "target_score": 85.0,
                "status": "active",
            },
            {
                "slug": "arc-prize-2026-arc-agi-3",
                "title": "ARC Prize 2026: ARC-AGI-3 Track",
                "prize_pool": "$850,000 USD",
                "deadline": "2026-11-02",
                "metric": "Dynamic Multi-Step Interactive Grid",
                "current_best_score": 0.15,
                "target_score": 50.0,
                "status": "active",
            },
            {
                "slug": "rsna-knee-abnormality-detection",
                "title": "RSNA Knee Abnormality Detection",
                "prize_pool": "$77,000 USD",
                "deadline": "2026-10-22",
                "metric": "Multi-Label ROC-AUC",
                "current_best_score": 0.955,
                "target_score": 0.965,
                "status": "active",
            },
            {
                "slug": "biohub-cell-tracking-during-development",
                "title": "Biohub Cell Tracking During Development",
                "prize_pool": "Prestige / Top 5",
                "deadline": "2026-10-30",
                "metric": "TRA / SEG Tracking Score",
                "current_best_score": 0.94486,
                "target_score": 0.966,
                "status": "active",
            },
            {
                "slug": "enveda-CASMI26-molecule-id-mass-spectra",
                "title": "Enveda CASMI26 Molecule ID Mass Spectra",
                "prize_pool": "$50,000 USD",
                "deadline": "2026-12-14",
                "metric": "Cosine Similarity / Formula Match",
                "current_best_score": 0.417,
                "target_score": 0.550,
                "status": "active",
            },
            {
                "slug": "gemma-4-developer-agent",
                "title": "Google - The Gemma 4 Developer Agent",
                "prize_pool": "$65,000 USD",
                "deadline": "2026-12-02",
                "metric": "SWE-Bench / Agentic Patch Acceptance",
                "current_best_score": 0.15,
                "target_score": 0.40,
                "status": "active",
            },
        ]

        stmts = []
        for c in competitions:
            slug = c["slug"]
            stmts.append(f"UPSERT kaggle_competition:`{slug}` CONTENT {json.dumps(c)};")
        res = self.execute("\n".join(stmts))
        return {"status": "OK", "competitions_seeded": len(res)}

    def seed_first_principles_invariants(self) -> dict[str, Any]:
        """Seed foundational physical, mathematical & code invariants."""
        invariants = [
            {
                "id": "kaggle_invariant:inv_d4_dihedral",
                "code": "D4_DIHEDRAL_INVARIANCE",
                "title": "D4 Dihedral Group & Color Permutation Symmetry",
                "domain": "discrete_geometry",
                "description": "Grid task transformations commute under 8 rotations/reflections and color-preserving permutations.",
                "formal_rule": "forall g in D4: Task(g(grid)) == g(Task(grid))",
            },
            {
                "id": "kaggle_invariant:inv_non_overlapping_tta",
                "code": "RSNA_NON_OVERLAPPING_TTA",
                "title": "Non-Overlapping Spatial TTA Windowing",
                "domain": "medical_imaging",
                "description": "Restricts multi-view knee slice evaluation to two disjoint spatial windows, accelerating inference by 8.5x and preventing timeout.",
                "formal_rule": "WindowA intersect WindowB == empty_set and Time(Inference) <= 3200s",
            },
            {
                "id": "kaggle_invariant:inv_stem_adaptive_threshold",
                "code": "BIOHUB_STEM_ADAPTIVE_THRESHOLD",
                "title": "Stem-Adaptive Contrast Gated Association",
                "domain": "biological_kinematics",
                "description": "Dynamic 0.945 detection gating for faint stems (e.g. 6bba) recovering 32 lost tracking edges.",
                "formal_rule": "Threshold(stem) = (0.945 if contrast(stem) < tau else 0.965)",
            },
            {
                "id": "kaggle_invariant:inv_precursor_isobar",
                "code": "CASMI_PRECURSOR_ISOBAR",
                "title": "Precursor Isobar Flat-Top Filtering",
                "domain": "mass_spectrometry",
                "description": "Prevents precursor mass noise from collapsing isotopic rank matrices in MS2 spectra.",
                "formal_rule": "delta_mz <= 5ppm implies IsobarClass(p1) == IsobarClass(p2)",
            },
            {
                "id": "kaggle_invariant:inv_copula_rank",
                "code": "COPULA_RANK_ALIGNMENT",
                "title": "Copula Rank Invariant Var(R)=1/12",
                "domain": "ensemble_statistics",
                "description": "Uniform marginal probability transformations eliminate variance dominance when blending heteroscedastic model outputs.",
                "formal_rule": "Var(UniformRank(p)) == 1/12",
            },
            {
                "id": "kaggle_invariant:inv_monotonic_attempt",
                "code": "MONOTONIC_ATTEMPT_2",
                "title": "Monotonic Attempt-2 DSL Injection",
                "domain": "algorithmic_search",
                "description": "Guarantees non-negative expected score improvement when injecting search programs into duplicate attempts.",
                "formal_rule": "Delta E[Score] >= 0 for K=2",
            },
            {
                "id": "kaggle_invariant:inv_ast_callable_last",
                "code": "AST_CALLABLE_LAST_ANCHOR",
                "title": "Lexical AST Callable Anchor",
                "domain": "code_governance",
                "description": "Ensures 'def agent(obs, config)' is the lexically trailing function in submission scripts.",
                "formal_rule": "get_last_callable(AST(main.py)).name == 'agent'",
            },
        ]

        stmts = [
            f"UPSERT {inv['id']} CONTENT {json.dumps({k: v for k, v in inv.items() if k != 'id'})};"
            for inv in invariants
        ]
        res = self.execute("\n".join(stmts))
        return {"status": "OK", "invariants_seeded": len(res)}

    def seed_autoharness_policies(self) -> dict[str, Any]:
        """Seed AutoHarness deterministic verifier policies."""
        policies = [
            {
                "id": "autoharness_policy:policy_ast_callable_anchor",
                "name": "AutoHarness: AST Callable Lexical Anchor",
                "description": "Deterministic AST parser verifying agent() callable order prior to Kaggle notebook dispatch.",
                "ast_rule": "ast.FunctionDef[-1].name == 'agent'",
                "zero_cost_latency": 0.12,
            },
            {
                "id": "autoharness_policy:policy_rsna_time_budget",
                "name": "AutoHarness: RSNA Inference Time Budget Guard",
                "description": "Asserts non-overlapping TTA and bounds model ensemble execution to under 3600s.",
                "ast_rule": "TTA_OVERLAP == False and len(ENSEMBLE) <= 5",
                "zero_cost_latency": 0.08,
            },
            {
                "id": "autoharness_policy:policy_biohub_edge_guard",
                "name": "AutoHarness: Biohub Hungarian Mitosis Guard",
                "description": "Enforces bipartite matching invariants and adaptive detection threshold limits.",
                "ast_rule": "0.940 <= BIOHUB_ADAPTIVE_LOW_THRESHOLD <= 0.950",
                "zero_cost_latency": 0.15,
            },
            {
                "id": "autoharness_policy:policy_arc_d4_verifier",
                "name": "AutoHarness: ARC D4 Invariant Verifier",
                "description": "Bytecode verifier testing candidate solution grids against D4 dihedral symmetries.",
                "ast_rule": "verify_d4_group_actions(grid_in, grid_out)",
                "zero_cost_latency": 0.28,
            },
        ]

        stmts = [
            f"UPSERT {p['id']} CONTENT {json.dumps({k: v for k, v in p.items() if k != 'id'})};"
            for p in policies
        ]
        res = self.execute("\n".join(stmts))
        return {"status": "OK", "policies_seeded": len(res)}

    def seed_kernels_and_scores(self) -> dict[str, Any]:
        """Seed active dispatched Kaggle kernels and verified scores."""
        kernels = [
            {
                "id": "kaggle_kernel:arc_quad_l4",
                "kernel_slug": "manderson240/arc-agi-2-fork-lb33-89-20260903",
                "competition": "arc-prize-2026-arc-agi-2",
                "hardware": "NvidiaL4x4 (4x 24GB L4 GPU, 96GB VRAM)",
                "last_status": "COMPLETE",
            },
            {
                "id": "kaggle_kernel:rsna_knee_ensemble",
                "kernel_slug": "manderson240/cohezion-rsna-knee-sota-ensemble",
                "competition": "rsna-knee-abnormality-detection",
                "hardware": "Kaggle Dual-T4 / L4",
                "last_status": "COMPLETE",
            },
            {
                "id": "kaggle_kernel:biohub_v6",
                "kernel_slug": "manderson240/cohezion-biohub-v6",
                "competition": "biohub-cell-tracking-during-development",
                "hardware": "Kaggle GPU L4",
                "last_status": "COMPLETE",
            },
            {
                "id": "kaggle_kernel:casmi26_sota",
                "kernel_slug": "manderson240/cohezion-casmi26-sota",
                "competition": "enveda-CASMI26-molecule-id-mass-spectra",
                "hardware": "Kaggle High-RAM CPU",
                "last_status": "COMPLETE",
            },
        ]

        scores = [
            {
                "id": "kaggle_score:arc2_sota",
                "value": 30.14,
                "metric": "Exact Grid Match",
                "score_type": "public_leaderboard",
            },
            {
                "id": "kaggle_score:rsna_sota",
                "value": 0.955,
                "metric": "ROC-AUC",
                "score_type": "public_leaderboard",
            },
            {
                "id": "kaggle_score:biohub_sota",
                "value": 0.94486,
                "metric": "TRA/SEG Score",
                "score_type": "public_leaderboard",
            },
            {
                "id": "kaggle_score:casmi_sota",
                "value": 0.417,
                "metric": "Formula Match Cosine",
                "score_type": "public_leaderboard",
            },
        ]

        stmts = [
            f"UPSERT {k['id']} CONTENT {json.dumps({key: val for key, val in k.items() if key != 'id'})};"
            for k in kernels
        ] + [
            f"UPSERT {s['id']} CONTENT {json.dumps({key: val for key, val in s.items() if key != 'id'})};"
            for s in scores
        ]
        res = self.execute("\n".join(stmts))
        return {"status": "OK", "records_seeded": len(res)}

    def relate_if_not_exists(
        self,
        in_id: str,
        edge_table: str,
        out_id: str,
        content: dict[str, Any] | None = None,
    ) -> Any:
        """Create a graph relation only if an identical (in, out) edge does not already exist."""
        content_str = f" CONTENT {json.dumps(content)}" if content else ""
        surql = f"""
        IF ! (SELECT VALUE id FROM {edge_table} WHERE in = {in_id} AND out = {out_id})[0] THEN
            RELATE {in_id}->{edge_table}->{out_id}{content_str};
        END;
        """
        return self.execute(surql)

    def build_graph_relations(self) -> dict[str, Any]:
        """Construct multi-hop graph edges via idempotent conditional SurrealQL RELATE blocks."""
        # Ensure submission records exist for all active kernels
        sub_records = [
            {
                "id": "submission_record:arc_quad_v1",
                "competition": "arc-prize-2026-arc-agi-2",
                "status": "COMPLETE",
                "score": 30.14,
                "kernel_slug": "manderson240/arc-agi-2-fork-lb33-89-20260903",
            },
            {
                "id": "submission_record:casmi_v1",
                "competition": "enveda-CASMI26-molecule-id-mass-spectra",
                "status": "COMPLETE",
                "score": 0.417,
                "kernel_slug": "manderson240/cohezion-casmi26-sota",
            },
        ]
        sub_stmts = [
            f"UPSERT {sr['id']} CONTENT {json.dumps({k: v for k, v in sr.items() if k != 'id'})};"
            for sr in sub_records
        ]
        self.execute("\n".join(sub_stmts))

        edges: list[tuple[str, str, str, dict[str, Any] | None]] = [
            # 1. Competition -> HAS_INVARIANT -> Invariant
            ("kaggle_competition:`arc-prize-2026-arc-agi-2`", "has_invariant", "kaggle_invariant:inv_d4_dihedral", None),
            ("kaggle_competition:`arc-prize-2026-arc-agi-2`", "has_invariant", "kaggle_invariant:inv_monotonic_attempt", None),
            ("kaggle_competition:`arc-prize-2026-arc-agi-3`", "has_invariant", "kaggle_invariant:inv_d4_dihedral", None),
            ("kaggle_competition:`rsna-knee-abnormality-detection`", "has_invariant", "kaggle_invariant:inv_non_overlapping_tta", None),
            ("kaggle_competition:`rsna-knee-abnormality-detection`", "has_invariant", "kaggle_invariant:inv_copula_rank", None),
            ("kaggle_competition:`biohub-cell-tracking-during-development`", "has_invariant", "kaggle_invariant:inv_stem_adaptive_threshold", None),
            ("kaggle_competition:`enveda-CASMI26-molecule-id-mass-spectra`", "has_invariant", "kaggle_invariant:inv_precursor_isobar", None),

            # 2. AutoHarness Policy -> ENFORCES -> Invariant
            ("autoharness_policy:policy_arc_d4_verifier", "enforces_invariant", "kaggle_invariant:inv_d4_dihedral", None),
            ("autoharness_policy:policy_rsna_time_budget", "enforces_invariant", "kaggle_invariant:inv_non_overlapping_tta", None),
            ("autoharness_policy:policy_biohub_edge_guard", "enforces_invariant", "kaggle_invariant:inv_stem_adaptive_threshold", None),
            ("autoharness_policy:policy_ast_callable_anchor", "enforces_invariant", "kaggle_invariant:inv_ast_callable_last", None),

            # 3. Kernel -> EMBEDS_POLICY -> Policy
            ("kaggle_kernel:arc_quad_l4", "embeds_policy", "autoharness_policy:policy_arc_d4_verifier", None),
            ("kaggle_kernel:rsna_knee_ensemble", "embeds_policy", "autoharness_policy:policy_rsna_time_budget", None),
            ("kaggle_kernel:biohub_v6", "embeds_policy", "autoharness_policy:policy_biohub_edge_guard", None),

            # 4. Kernel -> TARGETS -> Competition
            ("kaggle_kernel:arc_quad_l4", "targets_competition", "kaggle_competition:`arc-prize-2026-arc-agi-2`", None),
            ("kaggle_kernel:rsna_knee_ensemble", "targets_competition", "kaggle_competition:`rsna-knee-abnormality-detection`", None),
            ("kaggle_kernel:biohub_v6", "targets_competition", "kaggle_competition:`biohub-cell-tracking-during-development`", None),
            ("kaggle_kernel:casmi26_sota", "targets_competition", "kaggle_competition:`enveda-CASMI26-molecule-id-mass-spectra`", None),

            # 5. Kernel -> GENERATED_SUBMISSION -> Submission Record
            ("kaggle_kernel:arc_quad_l4", "generated_submission", "submission_record:arc_quad_v1", None),
            ("kaggle_kernel:rsna_knee_ensemble", "generated_submission", "submission_record:rsna_v14", None),
            ("kaggle_kernel:biohub_v6", "generated_submission", "submission_record:biohub_v18", None),
            ("kaggle_kernel:casmi26_sota", "generated_submission", "submission_record:casmi_v1", None),

            # 6. Submission Record -> YIELDED_SCORE -> Kaggle Score
            ("submission_record:arc_quad_v1", "yielded_score", "kaggle_score:arc2_sota", {"verified": True}),
            ("submission_record:rsna_v14", "yielded_score", "kaggle_score:rsna_sota", {"verified": True}),
            ("submission_record:biohub_v18", "yielded_score", "kaggle_score:biohub_sota", {"verified": True}),
            ("submission_record:casmi_v1", "yielded_score", "kaggle_score:casmi_sota", {"verified": True}),

            # 7. Learning -> APPLIES_TO -> Competition
            ("learning:l441", "applies_to", "kaggle_competition:`biohub-cell-tracking-during-development`", {"confidence": 0.95}),
            ("learning:l442", "applies_to", "kaggle_competition:`arc-prize-2026-arc-agi-2`", {"confidence": 0.98}),
            ("learning:l442", "applies_to", "kaggle_competition:`rsna-knee-abnormality-detection`", {"confidence": 0.92}),
            ("learning:l443", "applies_to", "kaggle_competition:`rsna-knee-abnormality-detection`", {"confidence": 0.90}),
            ("learning:l444", "applies_to", "kaggle_competition:`rsna-knee-abnormality-detection`", {"confidence": 0.94}),
            ("learning:l444", "applies_to", "kaggle_competition:`biohub-cell-tracking-during-development`", {"confidence": 0.91}),
            ("learning:l446", "applies_to", "kaggle_competition:`arc-prize-2026-arc-agi-2`", {"confidence": 0.96}),
            ("learning:l446", "applies_to", "kaggle_competition:`rsna-knee-abnormality-detection`", {"confidence": 0.93}),
            ("learning:l446", "applies_to", "kaggle_competition:`biohub-cell-tracking-during-development`", {"confidence": 0.95}),

            # 8. Cross-competition Knowledge Transfer (TRANSFERS_TO)
            ("learning:l442", "transfers_to", "kaggle_competition:`rsna-knee-abnormality-detection`", {"transfer_mechanism": "hidden_test_governance"}),
            ("learning:l444", "transfers_to", "kaggle_competition:`biohub-cell-tracking-during-development`", {"transfer_mechanism": "bipartite_goal_loop"}),
            ("learning:l446", "transfers_to", "kaggle_competition:`arc-prize-2026-arc-agi-3`", {"transfer_mechanism": "ast_anchor_and_timeout_guard"}),
        ]

        blocks = []
        for in_id, edge, out_id, content in edges:
            content_str = f" CONTENT {json.dumps(content)}" if content else ""
            block = f"""IF ! (SELECT VALUE id FROM {edge} WHERE in = {in_id} AND out = {out_id})[0] THEN
                RELATE {in_id}->{edge}->{out_id}{content_str};
            END;"""
            blocks.append(block)

        res = self.execute("\n".join(blocks))
        return {"status": "OK", "relations_processed": len(edges), "execution_batches": len(res)}

    def link_learning_to_competition(
        self,
        learning_id: str,
        competition_slug: str,
        transfers_to: list[str] | None = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Link a tri-temporal learning node to a competition and optional transfer targets."""
        lid = f"learning:{learning_id}" if not learning_id.startswith("learning:") else learning_id
        comp_ref = f"kaggle_competition:`{competition_slug}`"

        self.relate_if_not_exists(lid, "applies_to", comp_ref, {"confidence": confidence})

        if transfers_to:
            for target in transfers_to:
                target_ref = f"kaggle_competition:`{target}`"
                self.relate_if_not_exists(
                    lid,
                    "transfers_to",
                    target_ref,
                    {"transfer_mechanism": "cross_domain_invariant"},
                )

        return {
            "status": "OK",
            "learning": lid,
            "target": competition_slug,
            "transfers": transfers_to or [],
        }

    def get_score_provenance(self, score_id: str) -> dict[str, Any]:
        """Trace score provenance back through submission records, dispatched kernels, policies, and invariants."""
        target_id = score_id if score_id.startswith("kaggle_score:") else f"kaggle_score:{score_id}"
        surql = f"""
        SELECT
            id,
            value,
            metric,
            score_type,
            <-yielded_score<-submission_record.* AS submission,
            <-yielded_score<-submission_record<-generated_submission<-kaggle_kernel.* AS kernel,
            <-yielded_score<-submission_record<-generated_submission<-kaggle_kernel->embeds_policy->autoharness_policy.* AS policies,
            <-yielded_score<-submission_record<-generated_submission<-kaggle_kernel->embeds_policy->autoharness_policy->enforces_invariant->kaggle_invariant.* AS invariants,
            <-yielded_score<-submission_record<-generated_submission<-kaggle_kernel->targets_competition->kaggle_competition.* AS competition
        FROM {target_id};
        """
        res = self.execute(surql)
        hits = res[0].get("result", []) if res else []
        return hits[0] if hits else {}

    def get_competition_lineage(self, slug: str) -> dict[str, Any]:
        """Perform a multi-hop GraphRAG query tracing invariants, policies, kernels, submissions, scores, and learnings."""
        surql = f"""
        SELECT
            id,
            slug,
            title,
            current_best_score,
            metric,
            ->has_invariant->kaggle_invariant.* AS invariants,
            ->has_invariant->kaggle_invariant<-enforces_invariant<-autoharness_policy.* AS governing_policies,
            <-targets_competition<-kaggle_kernel.* AS dispatched_kernels,
            <-targets_competition<-kaggle_kernel->generated_submission->submission_record.* AS generated_submissions,
            <-targets_competition<-kaggle_kernel->generated_submission->submission_record->yielded_score->kaggle_score.* AS yielded_scores,
            <-applies_to<-learning.{{id, title, tags, transaction_time}} AS associated_learnings,
            <-transfers_to<-learning.{{id, title, tags, transaction_time}} AS incoming_transfers
        FROM kaggle_competition:`{slug}`;
        """
        res = self.execute(surql)
        hits = res[0].get("result", []) if res else []
        return hits[0] if hits else {}

    def get_cross_competition_transfers(self) -> list[dict[str, Any]]:
        """Query learnings that bridge across two or more competitions."""
        surql = """
        SELECT
            id,
            title,
            ->applies_to->kaggle_competition.title AS targeted_competitions,
            ->transfers_to->kaggle_competition.title AS transferred_competitions
        FROM learning
        WHERE count(->applies_to->kaggle_competition) >= 2
        LIMIT 10;
        """
        res = self.execute(surql)
        return res[0].get("result", []) if res else []


def main() -> None:
    """Run full seed and graph construction."""
    engine = KaggleGraphEngine()
    logger.info("1. Seeding Kaggle competitions...")
    engine.seed_active_competitions()

    logger.info("2. Seeding First-Principles invariants...")
    engine.seed_first_principles_invariants()

    logger.info("3. Seeding AutoHarness policies...")
    engine.seed_autoharness_policies()

    logger.info("4. Seeding Kernels and Scores...")
    engine.seed_kernels_and_scores()

    logger.info("5. Linking graph edges (RELATE)...")
    engine.build_graph_relations()

    logger.info("6. Verifying ARC-AGI-2 lineage traversal...")
    lineage = engine.get_competition_lineage("arc-prize-2026-arc-agi-2")
    logger.info("ARC Lineage: %s", json.dumps(lineage, indent=2))

    logger.info("7. Verifying cross-competition transfers...")
    transfers = engine.get_cross_competition_transfers()
    logger.info("Transfers found: %d", len(transfers))
    for t in transfers:
        logger.info("  %s: %s -> %s", t["id"], t["title"], t.get("targeted_competitions"))


if __name__ == "__main__":
    main()
