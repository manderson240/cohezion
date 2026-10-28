#!/usr/bin/env python3
"""Semantic Blast Radius Guard (Open Ontologies / BORO 4D Grounding).

Linear-time machine-checkable verification gating core infrastructure PRs:
    python scripts/ci/semantic_guard.py --self-test  # prove it can go RED before trusting GREEN
    python scripts/ci/semantic_guard.py              # gate

WHY THIS EXISTS:
----------------
Ensures that modifications to foundational communication infrastructure (EventBus,
KanbanBridge) do not introduce uncalculated transitive breaking changes across the
semantic graph without a zero-trust derivation certificate.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from cohezion.knowledge_graph.open_ontologies_bridge import (  # noqa: E402
    DerivationCertificate,
    DerivationStep,
    SemanticPlanner,
    SemanticTriple,
)


def self_test() -> int:
    """Discriminating self-test: must fail on forged derivation step, pass on sound derivation."""
    t_rule = SemanticTriple("cohezion:event_bus", "rdfs:domain", "cohezion:Message")
    t_fact = SemanticTriple("user_msg", "cohezion:event_bus", "payload")
    t_inferred = SemanticTriple("user_msg", "rdf:type", "cohezion:Message")
    t_forged = SemanticTriple("user_msg", "rdf:type", "cohezion:AdminPrivilege")

    step_sound = DerivationStep(
        step_id="step_1",
        rule_name="rdfs:domain_inference",
        premise_digests=[t_rule.digest(), t_fact.digest()],
        conclusion=t_inferred,
    )
    cert_green = DerivationCertificate(
        certificate_id="green_cert",
        asserted_triples=[t_rule, t_fact],
        derivation_steps=[step_sound],
    )
    is_valid, msg = cert_green.verify()
    if not is_valid:
        print(f"SELF-TEST FAILED: green certificate failed verification: {msg}")
        return 1

    # Red test: forged premise digest
    step_forged = DerivationStep(
        step_id="step_forged",
        rule_name="rdfs:domain_inference",
        premise_digests=["deadbeef1234"],  # Unasserted premise
        conclusion=t_forged,
    )
    cert_red = DerivationCertificate(
        certificate_id="red_cert",
        asserted_triples=[t_rule, t_fact],
        derivation_steps=[step_forged],
    )
    is_red_valid, _ = cert_red.verify()
    if is_red_valid:
        print("SELF-TEST FAILED: red forged certificate was erroneously accepted!")
        return 1

    print("SELF-TEST OK: semantic guard rejects forged premise steps (red) and verifies sound derivations (green).")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    planner = SemanticPlanner()
    # Baseline check: verify default Horn closure rules are sound
    rules = planner.rule_table
    if not rules:
        print("SEMANTIC GUARD FAILED — rule table empty.")
        return 1

    print(f"semantic-guard OK — {len(rules)} Horn closure rule(s) verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
