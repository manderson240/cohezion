#!/usr/bin/env python3
"""Dogfooding script for Proactive Hybrid Delegation & EVI Self-Healing framework.

Executes a live test suite across Tier 1 (Local), Tier 2 (Ollama Cloud), and Tier 3 (Premium API)
routing decisions, calculates EVI gating metrics, logs delegation traces, and exercises EVIHealer.
"""

import logging
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.inference.delegation_logger import DelegationLogger
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter
from cohezion.proactive.evi_healer import EVIHealer


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DogfoodHybrid")


def main() -> None:
    print("=========================================================")
    print("🚀 DOGFOODING: Proactive Hybrid Delegation & EVI Framework")
    print("=========================================================\n")

    # 1. Initialize Components
    logger.info("Initializing DelegationLogger, UnifiedHybridRouter, and EVIHealer...")
    delegation_logger = DelegationLogger()
    router = UnifiedHybridRouter(logger_instance=delegation_logger)
    healer = EVIHealer(router=router)

    # 2. Dogfood Routing Scenarios
    scenarios = [
        {
            "name": "Scenario 1: Routine Local Coding Task",
            "task_type": "coding",
            "task_importance": 0.4,
            "estimated_tier1_quality": 0.85,
            "target_quality_required": 0.85,
            "tier1_saturated": False,
            "context_tokens": 2048,
        },
        {
            "name": "Scenario 2: Heavy Math/Reasoning Task (Needs Escalation to Tier 2 Cloud)",
            "task_type": "reasoning",
            "task_importance": 0.85,
            "estimated_tier1_quality": 0.60,
            "target_quality_required": 0.95,
            "tier1_saturated": False,
            "context_tokens": 16384,
        },
        {
            "name": "Scenario 3: Tier 1 Hardware Saturated (Direct Escalation to Tier 2)",
            "task_type": "research",
            "task_importance": 0.70,
            "estimated_tier1_quality": 0.80,
            "target_quality_required": 0.85,
            "tier1_saturated": True,
            "context_tokens": 8192,
        },
        {
            "name": "Scenario 4: Frontier Architecture Task (>100k Context -> Tier 3 Premium API)",
            "task_type": "architecture",
            "task_importance": 0.95,
            "estimated_tier1_quality": 0.50,
            "target_quality_required": 0.98,
            "tier1_saturated": False,
            "context_tokens": 128000,
        },
    ]

    print("📊 Executing Hybrid Routing Decision Tree:")
    print("---------------------------------------------------------")
    for s in scenarios:
        res = router.route(
            task_type=s["task_type"],
            task_importance=s["task_importance"],
            estimated_tier1_quality=s["estimated_tier1_quality"],
            target_quality_required=s["target_quality_required"],
            tier1_saturated=s["tier1_saturated"],
            context_tokens=s["context_tokens"],
        )
        print(f"\n🔹 {s['name']}")
        print(
            f"   Task Type       : {s['task_type']} (Tokens: {s['context_tokens']}, Importance: {s['task_importance']})"
        )
        print(f"   Selected Tier   : Tier {res.selected_tier}")
        print(f"   Model Assigned  : {res.model_name}")
        print(f"   EVI Score       : {res.evi_score:.4f} (Gating threshold: > 0.75)")
        print(f"   Escalated       : {'YES' if res.escalated else 'NO'}")
        print(f"   Reason          : {res.reason}")

    # 3. Dogfood EVI Self-Healing System
    print("\n\n🩺 Executing Proactive EVI Self-Healing Diagnostic Suite:")
    print("---------------------------------------------------------")

    healing_candidates = [
        {
            "component": "npu_kv_cache",
            "issue_description": "NPU KV-Cache fragmentation at 42%",
            "remediation": "Compaction and cache page defragmentation",
            "quality_gap": 0.40,
            "issue_severity": 0.85,
            "remediation_cost": 0.30,
        },
        {
            "component": "telemetry_buffer",
            "issue_description": "Minor metric sampling latency spike (15ms)",
            "remediation": "Flush telemetry queue to disk",
            "quality_gap": 0.05,
            "issue_severity": 0.20,
            "remediation_cost": 0.60,
        },
    ]

    for cand in healing_candidates:
        action = healer.evaluate_healing_candidate(
            component=cand["component"],
            issue_description=cand["issue_description"],
            proposed_remediation=cand["remediation"],
            quality_gap=cand["quality_gap"],
            issue_severity=cand["issue_severity"],
            remediation_cost=cand["remediation_cost"],
        )
        status_str = "✅ APPROVED & DISPATCHED" if action.approved else "❌ REJECTED (EVI <= 0.75)"
        print(f"\n🔸 Component: {cand['component']}")
        print(f"   Issue      : {cand['issue_description']}")
        print(f"   Remediation: {cand['remediation']}")
        print(f"   EVI Score  : {action.evi_score:.4f}")
        print(f"   Status     : {status_str}")

    # 4. Verify Log Persistence
    print("\n\n📜 Verifying Delegation Telemetry Logs:")
    print("---------------------------------------------------------")
    recent_logs = delegation_logger.get_recent_events(limit=5)
    print(f"Found {len(recent_logs)} recent delegation events in persistent store:")
    for idx, log in enumerate(recent_logs, 1):
        print(
            f"   [{idx}] {log['task_name']} -> Tier {log['target_tier']} ({log['model_selected']}) | EVI: {log['evi_score']:.4f}"
        )

    print("\n✅ DOGFOODING COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
