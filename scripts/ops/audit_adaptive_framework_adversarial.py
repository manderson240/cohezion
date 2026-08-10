"""Local Multiperspective Adversarial Audit for AdaptiveFrameworkOptimizer.

Evaluates AdaptiveFrameworkOptimizer using 3 local model perspectives
(Qwen3-Coder-30B, deepseek-r1-8b, qwen3.6-moe-35b) to deduct self-congratulatory score inflation
and calculate deflated realistic adversarial scores.
"""

from __future__ import annotations

import logging
import time

from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.verification.local_adversarial_auditor import LocalAdversarialAuditor


logger = logging.getLogger("adversarial_audit_adaptive")


def run_adaptive_framework_adversarial_audit() -> None:
    print("\n" + "🛡️" * 35)
    print("⚔️ LOCAL MULTIPERSPECTIVE ADVERSARIAL REVIEW: ADAPTIVE FRAMEWORK")
    print("   Evaluating via 3 Local Models (Qwen3-Coder, DeepSeek-R1, Qwen3.6-MoE)")
    print("🛡️" * 35 + "\n")

    t0 = time.monotonic()
    auditor = LocalAdversarialAuditor()

    target_name = "adaptive_framework_optimizer"
    raw_claim = 0.95
    description = (
        "AdaptiveFrameworkOptimizer dynamically tuning context windows, "
        "hardware load factors, and EVI thresholds"
    )

    print(f"🔍 Audit Target: {target_name.upper()}")
    print(f"  • Description     : {description}")
    print(f"  • Raw Score Claim : {raw_claim:.2f} / 1.00")

    # Run 3 local model perspectives
    audit_res = auditor.audit_artifact_claims(target_name, raw_claim, description)

    duration_s = time.monotonic() - t0

    models_used = [p.model_used for p in audit_res.perspectives]

    print("\n📊 LOCAL ADVERSARIAL AUDIT METRICS:")
    print("-" * 75)
    print(f"  • Raw Claimed Score   : {audit_res.raw_claimed_score:.2f} / 1.00")
    print(f"  • Deflated Real Score : {audit_res.deflated_adversarial_score:.2f} / 1.00")
    print(f"  • Inflation Penalty   : -{audit_res.total_penalty:.2f}")
    print(f"  • Models Evaluated    : 3 Local Perspectives ({', '.join(models_used)})")
    print("-" * 75)

    print("\n📌 ADVERSARIAL MODEL PERSPECTIVES & CRITIQUES:")
    for p in audit_res.perspectives:
        print(f"   ⚠️ [{p.reviewer_role} - {p.model_used}]: Penalty -{p.inflation_penalty:.2f}")
        print(f"      Criticism: {p.criticism}")
        print(f"      Action   : {p.recommended_action}\n")

    # Persist Adversarial Audit Card
    persist_item(
        {
            "id": f"adversarial_audit_adaptive_{int(time.time())}",
            "title": f"[Local Adversarial Audit] {target_name}: Deflated {audit_res.deflated_adversarial_score:.2f} (Penalty: -{audit_res.total_penalty:.2f})",
            "status": "completed",
            "priority": "critical",
            "source": "audit_adaptive_framework_adversarial",
            "category": "adversarial_review",
            "notes": (
                f"Raw Claim: {raw_claim:.2f} | "
                f"Deflated Real Score: {audit_res.deflated_adversarial_score:.2f} | "
                f"Inflation Penalty: -{audit_res.total_penalty:.2f} | "
                f"3 Local Model Perspectives: Verified"
            ),
        }
    )

    print("\n" + "=" * 75)
    print("🎉 LOCAL MULTIPERSPECTIVE ADVERSARIAL REVIEW COMPLETE!")
    print(f"  • Total Audit Time     : {duration_s:.2f} seconds")
    print("  • Inflation Penalty   : APPLIED & DEFLATED TO REALITY ✅")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_adaptive_framework_adversarial_audit()
