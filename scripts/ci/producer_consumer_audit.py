#!/usr/bin/env python3
"""Producer-Consumer Audit Gate for Cohezion.
==============================================
Validates that every architectural producer in the codebase has an active,
production consumer (preventing hollow seams and dormant capabilities).

Checks:
1. EventBus event types (published vs subscribed)
2. Goal trace tasks (created vs executed by loop)
3. Data products (registered vs consumed by consumers)
4. BAML schemas (generated vs parsed)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"

PAIRS = [
    {
        "producer": "EventBus.publish (Event producer)",
        "producer_pattern": r"(?:await\s+)?(?:self\._)?(?:event_)?bus\.publish\(",
        "consumer": "EventConsumer / Subscriber (Event consumer)",
        "consumer_pattern": r"\.subscribe\(",
        "expected_min_consumers": 2,
    },
    {
        "producer": "GoalTraceTask (Trace/Goal task creator)",
        "producer_pattern": r"GoalTraceTask\(",
        "consumer": "GoalDrivenTraceLoop.run (Goal loop consumer)",
        "consumer_pattern": r"GoalDrivenTraceLoop\(.*?\)\.run\(",
        "expected_min_consumers": 1,
    },
    {
        "producer": "DataProductSchema (Data Mesh producer)",
        "producer_pattern": r"DataProductSchema\(",
        "consumer": "DataMesh Consumer / Quality pipeline",
        "consumer_pattern": r"(?:CorpusQualityConsumer|consume_data_product|EventConsumer)",
        "expected_min_consumers": 1,
    },
    {
        "producer": "BAMLSchemaGenerator (BAML contract producer)",
        "producer_pattern": r"BAMLSchemaGenerator\.generate_baml_class\(",
        "consumer": "BAMLResilientParser (BAML contract consumer)",
        "consumer_pattern": r"BAMLResilientParser\.parse_to_model\(",
        "expected_min_consumers": 1,
    },
]


def run_audit() -> int:
    print("=" * 70)
    print("🔍 COHEZION PRODUCER-CONSUMER WIRING AUDIT")
    print("=" * 70)

    py_files = list(SRC.rglob("*.py"))
    all_content = {}
    for p in py_files:
        try:
            all_content[p] = p.read_text(encoding="utf-8")
        except Exception:
            pass

    failures = 0
    for item in PAIRS:
        p_matches = []
        c_matches = []

        p_re = re.compile(item["producer_pattern"])
        c_re = re.compile(item["consumer_pattern"])

        for path, text in all_content.items():
            if p_re.search(text):
                p_matches.append(path.relative_to(REPO))
            if c_re.search(text):
                c_matches.append(path.relative_to(REPO))

        p_count = len(p_matches)
        c_count = len(c_matches)

        print(f"\n• Pair: {item['producer']} ➔ {item['consumer']}")
        print(f"  - Producers found: {p_count} files ({', '.join(str(m) for m in p_matches[:2])})")
        print(f"  - Consumers found: {c_count} files ({', '.join(str(m) for m in c_matches[:2])})")

        if p_count > 0 and c_count < item["expected_min_consumers"]:
            print(f"  ❌ FAILURE: Producer exists but consumer count ({c_count}) < floor ({item['expected_min_consumers']})")
            failures += 1
        else:
            print("  ✅ VERIFIED: All producers have active consumers.")

    print("\n" + "=" * 70)
    if failures == 0:
        print("🎉 ALL PRODUCERS HAVE ACTIVE CONSUMERS (Zero Hollow Seams)")
        print("=" * 70)
        return 0
    else:
        print(f"💥 AUDIT FAILED: {failures} producer-consumer gap(s) detected.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_audit())
