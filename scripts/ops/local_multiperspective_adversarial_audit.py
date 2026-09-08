"""Local Multiperspective Adversarial Audit Script.

Executes 3 unsparing local perspective reviews over all recent 3D assets,
music tracks, and policy modules to eliminate score inflation and enforce empirical rigor.
"""

from __future__ import annotations

import logging

from cohezion.verification.local_adversarial_auditor import LocalAdversarialAuditor


def run_local_multiperspective_audit() -> None:
    print("\n" + "=" * 70)
    print("⚔️ LOCAL MULTIPERSPECTIVE ADVERSARIAL AUDIT: DEFLATING INFLATED SCORES")
    print("=" * 70)

    auditor = LocalAdversarialAuditor()

    audit_targets = [
        ("trellis_3d_refined_mesh", 0.93, "TRELLIS 3D GLTF asset refined pass quality claim"),
        ("ace_step_refined_audio", 0.93, "ACE-Step 30s synthwave music track refined score claim"),
        (
            "autoharness_policy_verifiers",
            0.95,
            "AutoHarness AST bytecode policy verification score claim",
        ),
        (
            "poincare_manifold_tracker",
            0.90,
            "Poincaré 2048D trajectory drift isolation score claim",
        ),
    ]

    deflated_reports = []

    for artifact_id, claimed_score, summary in audit_targets:
        print(f"\n🔍 Auditing Artifact: {artifact_id.upper()}")
        print(f"  • Claimed Raw Score : {claimed_score:.2f} / 1.00")
        print(f"  • Claimed Summary   : {summary}")

        report = auditor.audit_artifact_claims(artifact_id, claimed_score, summary)
        deflated_reports.append(report)

        status_str = "⚠️ INFLATION PENALIZED" if report.inflation_detected else "✅ VERIFIED"
        print(
            f"  • Deflated Score   : {report.deflated_adversarial_score:.2f} / 1.00 ({status_str})"
        )
        print(f"  • Total Penalty    : -{report.total_penalty:.2f}")

        for p in report.perspectives:
            pass_icon = "❌" if not p.pass_verification else "✅"
            print(
                f"    - {pass_icon} [{p.reviewer_role} via {p.model_used}]: {p.criticism[:80]}..."
            )

    print("\n" + "=" * 70)
    print("🎉 UNSPARING LOCAL ADVERSARIAL AUDIT COMPLETE!")
    print("=" * 70)
    print(f"  • Total Artifacts Audited : {len(deflated_reports)}")
    print(
        f"  • Average Score Deflation  : -{sum(r.total_penalty for r in deflated_reports) / len(deflated_reports):.2f}"
    )
    print("  • Empirical Ground-Truth Cards Written to SurrealDB & Obsidian Vault")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_local_multiperspective_audit()
