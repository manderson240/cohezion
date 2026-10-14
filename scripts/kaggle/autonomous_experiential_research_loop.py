#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

from cohezion.competitions.scientific_digital_twins import KaggleDigitalTwinsCouncil
from cohezion.flume.manifold_audit import FlumeManifoldAuditor
from scripts.kaggle.bleeding_edge_research_engine import BleedingEdgeResearchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("experiential_research_loop")


class AutonomousExperientialResearcher:
    """Manages continuous experiential learning, research, and simulation between submissions."""

    def __init__(self) -> None:
        self.research_engine = BleedingEdgeResearchEngine()
        self.digital_twins = KaggleDigitalTwinsCouncil()
        self.flume_auditor = FlumeManifoldAuditor()
        self.cycle_count = 0

    def run_experiential_cycle(self) -> dict[str, Any]:
        """Runs a complete research, simulation, and experiential distillation cycle."""
        self.cycle_count += 1
        logger.info("=== Experiential Recursive Learning Cycle #%d ===", self.cycle_count)

        cycle_results: dict[str, Any] = {
            "cycle": self.cycle_count,
            "timestamp": time.time(),
            "research_sprints": [],
            "manifold_audits": [],
            "twins_status": [],
        }

        # 1. Scientific Digital Twins Review
        twins_portfolio = self.digital_twins.get_portfolio_status()
        cycle_results["twins_status"] = twins_portfolio
        logger.info("🏛 Digital Twins Evaluated: %d competitions", len(twins_portfolio))

        # 2. In-between Submission Research Sprint (Zero-GPU, Cloud Ollama / Headless Claude)
        sprint_res = self.research_engine.step(summary={}, time_budget=35)
        cycle_results["research_sprints"].append({
            "topic": sprint_res.topic.value if hasattr(sprint_res.topic, "value") else str(sprint_res.topic),
            "success": sprint_res.success,
            "summary": sprint_res.summary[:180] if sprint_res.summary else "None",
            "invariants": sprint_res.invariants_found,
            "ast_verified": sprint_res.ast_verified,
        })
        logger.info(
            "🔬 Research Sprint [%s]: Success=%s (Invariants: %d)",
            sprint_res.topic,
            sprint_res.success,
            len(sprint_res.invariants_found),
        )

        # 3. FLUME Manifold Audit on Active Hypotheses
        audit_cases = [
            ("arc-prize-2026-arc-agi-2", "Quad-L4 LoRA + Non-destructive Attempt-2 DSL", 33.89, 31.81),
            ("enveda-CASMI26-molecule-id-mass-spectra", "Verbatim Fusion Fork + Tautomer Canonicalization", 0.421, 0.420),
            ("rsna-knee-abnormality-detection", "Kolmogorov Monotonicity Projection + Copula Rank Alignment", 0.943, 0.942),
            ("arc-prize-2026-arc-agi-3", "CPU Go-Explore 64-bit Zobrist Anti-Cycle BFS", 0.35, 0.24),
        ]

        for comp, hyp, pred, base in audit_cases:
            report = self.flume_auditor.audit_competition_step(comp, hyp, pred, base)
            cycle_results["manifold_audits"].append(report.to_dict())

        logger.info("🌀 FLUME Manifold Audits completed: %d cases audited", len(audit_cases))

        # 4. Deposit Experiential Learning into SurrealDB & Obsidian Vault
        learning_record = {
            "source": "autonomous_experiential_research_loop",
            "cycle": self.cycle_count,
            "timestamp": time.time(),
            "research_topic": str(sprint_res.topic),
            "invariants_synthesized": sprint_res.invariants_found,
            "flume_audits": cycle_results["manifold_audits"],
            "recommendations": [t["recommendation"] for t in twins_portfolio],
        }

        from scripts.kaggle.bleeding_edge_research_engine import (
            persist_to_obsidian_vault,
            persist_to_surrealdb,
        )
        persist_to_surrealdb(f"experiential_cycle_{self.cycle_count}", learning_record)
        persist_to_obsidian_vault(
            f"experiential_cycle_{self.cycle_count}.md",
            f"# Experiential Learning Cycle #{self.cycle_count}\n\n```json\n{json.dumps(learning_record, indent=2)}\n```\n",
        )
        logger.info("💾 Experiential deposit completed to SurrealDB `learning` and Obsidian Vault.")

        return cycle_results


def main():
    parser = argparse.ArgumentParser(description="Autonomous Experiential Recursive Research Loop")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--interval", type=int, default=600, help="Interval in seconds between research cycles (default 600s/10m)")
    args = parser.parse_args()

    engine = AutonomousExperientialResearcher()

    if args.once:
        res = engine.run_experiential_cycle()
        print(json.dumps(res, indent=2))
        return

    logger.info("Starting Autonomous Experiential Research Loop (Interval: %ds)...", args.interval)
    while True:
        try:
            engine.run_experiential_cycle()
        except Exception as e:
            logger.error("Error in experiential research cycle: %s", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
