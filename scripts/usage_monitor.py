#!/usr/bin/env python3
"""Read-only inference-usage monitor — local-vs-cloud tokens, cloud $ (est.), budget.

Reads the durable usage corpus written by ``cohezion.inference.usage_log.record_usage``
(the single dispatch chokepoint in ``compound.local_inference``) and prints an aggregated
report. The headline KPI is ``local share`` — the fraction of tokens served by free AMD
silicon (NPU/iGPU/CPU); the higher it is, the less you spend on cloud.

The cloud-$ figure is an ESTIMATE (pricing table × ~4-char/token estimate), not a billed
actual — the orchestrator's direct tiers do not surface real API usage. Treat it as a
budget-direction signal, not an invoice.

Usage
-----
    uv run python scripts/usage_monitor.py                 # all-time summary
    uv run python scripts/usage_monitor.py --since 2026-06-09   # since an ISO date
    uv run python scripts/usage_monitor.py --budget 20     # against a $20/mo cap
    uv run python scripts/usage_monitor.py --source live --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cohezion.inference.usage_log import (
    DEFAULT_LOG,
    format_report,
    read_usage,
    summarize_usage,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", type=Path, default=DEFAULT_LOG,
                        help=f"usage log path (default: {DEFAULT_LOG})")
    parser.add_argument("--since", default=None,
                        help="ISO timestamp/date lower bound, e.g. 2026-06-09")
    parser.add_argument("--source", default=None,
                        help="filter by source tag (e.g. live, replay)")
    parser.add_argument("--budget", type=float, default=None,
                        help="cloud budget in USD to report remaining against")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit the summary as JSON instead of a text report")
    args = parser.parse_args(argv)

    records = read_usage(since=args.since, source=args.source, path=args.path)
    summary = summarize_usage(records)

    if not records:
        print(f"No usage records at {args.path}"
              + (f" (since {args.since})" if args.since else "")
              + ".\nThe corpus fills as compound-loop dispatches run through the chokepoint.")
        return 0

    if args.as_json:
        out = {
            "local_tokens": summary.local_tokens,
            "cloud_input_tokens": summary.cloud_input_tokens,
            "cloud_output_tokens": summary.cloud_output_tokens,
            "cloud_cost_usd_est": round(summary.cloud_cost_usd, 6),
            "local_energy_usd_est": round(summary.local_energy_usd, 6),
            "total_cost_usd_est": round(summary.total_cost_usd, 6),
            "local_fraction": round(summary.local_fraction, 4),
            "n_records": summary.n_records,
            "n_cached": summary.n_cached,
            "by_model": summary.by_model,
        }
        if args.budget is not None:
            out["budget_usd"] = args.budget
            out["budget_remaining_usd"] = round(args.budget - summary.cloud_cost_usd, 6)
        print(json.dumps(out, indent=2))
    else:
        print(format_report(summary, budget_usd=args.budget))

    return 0


if __name__ == "__main__":
    sys.exit(main())
