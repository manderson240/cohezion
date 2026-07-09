#!/usr/bin/env python3
"""Compound engineering analytics CLI.

Usage:
    uv run python scripts/compound_analytics_cli.py status
    uv run python scripts/compound_analytics_cli.py retire
    uv run python scripts/compound_analytics_cli.py recommend [--n N]
    uv run python scripts/compound_analytics_cli.py health

Commands:
    status      Show session status with HIHO balance and experiment table
    retire      Show retirement candidates
    recommend   Show next experiment recommendations
    health      Run health checks on all compound components
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def cmd_status(args):
    from cohezion.compound.experiment_analytics import get_analytics_report
    from cohezion.compound.loop_visualizer import render_session_summary, render_experiment_table

    report = get_analytics_report(n=2000)
    top = report["top_experiments"]
    mean_delta = sum(e["mean_metric"] for e in top) / max(len(top), 1)

    print(
        render_session_summary(
            n_experiments=report["n_records"],
            hiho_balance=report["hiho_balance"],
            mean_delta=mean_delta,
            keep_rate=report["hiho_balance"],
            retirement_candidates=report["retirement_candidates"],
        )
    )
    print()
    print(
        render_experiment_table(
            report["per_experiment"],
            retirement_candidates=report["retirement_candidates"],
        )
    )


def cmd_retire(args):
    from cohezion.compound.experiment_analytics import get_analytics_report

    report = get_analytics_report(n=3000)
    candidates = report["retirement_candidates"]

    if not candidates:
        print("No retirement candidates found (all experiments still variable).")
        return

    print(f"Retirement candidates ({len(candidates)}):")
    for exp in candidates:
        stats = report["per_experiment"].get(exp, {})
        print(
            f"  {exp}: n={stats.get('total', 0)} cv={stats.get('cv', 0):.4f} mean={stats.get('mean_metric', 0):.4f}"
        )


def cmd_recommend(args):
    from cohezion.compound.experiment_recommender import get_session_recommendation_summary

    summary = get_session_recommendation_summary()
    print(f"HIHO Balance: {summary['hiho_balance']:.3f} (mode: {summary['mode'].upper()})")
    print(f"Retiring: {summary['retirement_candidates'][:5]}")
    print(f"\nRecommended next experiments (n={len(summary['recommendations'])}):")
    for rec in summary["recommendations"][: args.n]:
        replaces = f" → replaces {rec['replaces']}" if rec.get("replaces") else ""
        print(f"  [{rec['mode'].upper()}] {rec['experiment_name']}{replaces}")
        print(f"    {rec['hypothesis'][:80]}")


def cmd_health(args):
    from cohezion.compound.health_monitor import get_health_report

    report = get_health_report()
    status = "✓ HEALTHY" if report["healthy"] else "✗ UNHEALTHY"
    print(f"Compound Engineering Health: {status}")
    print()
    for check, result in report["checks"].items():
        ok = "✓" if result.get("ok") else "✗"
        error = f" — {result.get('error', '')}" if not result.get("ok") else ""
        print(f"  {ok} {check}{error}")


def main():
    parser = argparse.ArgumentParser(description="Compound engineering analytics CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show session status")
    sub.add_parser("retire", help="Show retirement candidates")
    rec_parser = sub.add_parser("recommend", help="Show recommendations")
    rec_parser.add_argument("--n", type=int, default=5, help="Number of recommendations")
    sub.add_parser("health", help="Health check")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "retire":
        cmd_retire(args)
    elif args.command == "recommend":
        cmd_recommend(args)
    elif args.command == "health":
        cmd_health(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
