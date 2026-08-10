"""Sync Preexisting Conditions & Technical Debt to Agentic Kanban.

Parses discovered codebase TODOs, tech debt items, and pre-existing conditions
and persists them as structured Kanban cards in SurrealDB & Obsidian Vault.
"""

from __future__ import annotations

import logging

from cohezion.core.event_bus import EventBus
from cohezion.data_mesh.kanban_bridge import persist_item


logger = logging.getLogger("kanban_sync")


PREEXISTING_CONDITIONS = [
    {
        "id": "tech_debt_streaming_api_skill_wire",
        "title": "api/streaming.py: Wire skill execution to TokenEfficientClient",
        "priority": "medium",
        "category": "tech_debt",
        "notes": "Line 75 in api/streaming.py contains an un-wired skill execution TODO placeholder.",
    },
    {
        "id": "tech_debt_orborous_global_metrics",
        "title": "research/orborous.py: Wire to real GlobalMetricsAggregator",
        "priority": "medium",
        "category": "tech_debt",
        "notes": "Line 117 in research/orborous.py uses hardcoded values instead of GlobalMetricsAggregator.",
    },
    {
        "id": "tech_debt_admin_surreal_cursor_pagination",
        "title": "core/persistence/admin.py: Implement cursor pagination for >1M records",
        "priority": "low",
        "category": "performance",
        "notes": "Line 74 in admin.py needs pagination for large query results.",
    },
    {
        "id": "tech_debt_pickle_security_validation",
        "title": "experiment_e70_tdd_adversarial.py: Validate pickle security",
        "priority": "high",
        "category": "security",
        "notes": "Line 598 in experiment_e70_tdd_adversarial.py: Security Predator finding regarding pickle safety.",
    },
    {
        "id": "tech_debt_jepa_hyperparameter_guidance",
        "title": "skills/JEPA_WORLD_MODEL_PRIME.md: Document hyperparameter guidance for SIGReg",
        "priority": "low",
        "category": "documentation",
        "notes": "Line 23 in JEPA_WORLD_MODEL_PRIME.md needs SIGReg hyperparameter docs.",
    },
]


def sync_preexisting_conditions_to_kanban() -> None:
    print("\n" + "=" * 70)
    print("📌 AGENTIC KANBAN BRIDGE: SYNCING PREEXISTING CONDITIONS & TECH DEBT")
    print("=" * 70)

    EventBus()

    for item in PREEXISTING_CONDITIONS:
        persist_item(
            {
                "id": item["id"],
                "title": f"[Kanban Sync] {item['title']}",
                "status": "backlog",
                "priority": item["priority"],
                "source": "preexisting_condition_audit",
                "category": item["category"],
                "notes": item["notes"],
            }
        )
        print(f"  • Persisted Kanban Item: [{item['priority'].upper()}] {item['title']}")

    print("\n" + "=" * 70)
    print("🎉 ALL PREEXISTING CONDITIONS SYNCED TO SURREALDB & OBSIDIAN VAULT!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sync_preexisting_conditions_to_kanban()
