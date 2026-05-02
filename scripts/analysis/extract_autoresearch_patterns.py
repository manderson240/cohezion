#!/usr/bin/env python3
"""Extract patterns from autoresearch results for skill refinement.

Analyzes autoresearch.jsonl to identify:
- Successful optimization patterns
- Failed approaches to avoid
- Performance characteristics
- Improvement opportunities

Charter: Idempotent analysis, transparent reporting, artifact persistence.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def load_autoresearch_data(path: Path) -> list[dict[str, Any]]:
    """Load autoresearch results."""
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data


def analyze_patterns(data: list[dict]) -> dict[str, Any]:
    """Extract patterns from autoresearch data."""
    results = {
        "sessions": set(),
        "total_experiments": 0,
        "kept": [],
        "discarded": [],
        "crashed": [],
        "improvements": [],
        "techniques": defaultdict(lambda: {"kept": 0, "discarded": 0, "total_ms": 0.0}),
    }

    for entry in data:
        if entry.get("type") == "config":
            results["sessions"].add(entry.get("name", "unknown"))
            continue

        results["total_experiments"] += 1
        status = entry.get("status", "unknown")

        if status == "keep":
            results["kept"].append(entry)
        elif status == "discard":
            results["discarded"].append(entry)
        elif status == "crash":
            results["crashed"].append(entry)

        # Extract technique from description
        desc = entry.get("description", "").lower()

        # Categorize by technique
        if "parallel" in desc or "asyncio" in desc:
            results["techniques"]["parallel_execution"][status] += 1
        if "batch" in desc or "buffer" in desc:
            results["techniques"]["batching"][status] += 1
        if "cache" in desc:
            results["techniques"]["caching"][status] += 1
        if "slim" in desc or "lightweight" in desc or "tuple" in desc:
            results["techniques"]["object_optimization"][status] += 1
        if "defer" in desc or "lazy" in desc:
            results["techniques"]["deferred_execution"][status] += 1

        # Track metrics
        metric = entry.get("metric", 0)
        if metric > 0:
            results["techniques"]["overall"]["total_ms"] += metric * 1000

    return results


def generate_report(results: dict) -> str:
    """Generate markdown report."""
    report = "# Autoresearch Pattern Analysis\n\n"
    report += f"**Sessions**: {len(results['sessions'])}\n\n"
    report += f"**Total Experiments**: {results['total_experiments']}\n\n"

    # Summary
    kept = len(results["kept"])
    discarded = len(results["discarded"])
    crashed = len(results["crashed"])

    report += "## Outcomes\n\n"
    report += f"- **Kept**: {kept} ({kept / results['total_experiments'] * 100:.1f}%)\n"
    report += (
        f"- **Discarded**: {discarded} ({discarded / results['total_experiments'] * 100:.1f}%)\n"
    )
    report += f"- **Crashed**: {crashed} ({crashed / results['total_experiments'] * 100:.1f}%)\n\n"

    # Technique analysis
    report += "## Technique Effectiveness\n\n"
    for technique, stats in sorted(results["techniques"].items()):
        if technique == "overall":
            continue
        total = stats["kept"] + stats["discarded"]
        if total == 0:
            continue
        success_rate = stats["kept"] / total * 100
        report += f"### {technique.replace('_', ' ').title()}\n"
        report += f"- Success rate: {success_rate:.1f}% ({stats['kept']}/{total})\n"
        report += f"- Kept: {stats['kept']}, Discarded: {stats['discarded']}\n\n"

    # Top winners
    report += "## Winning Optimizations\n\n"
    for entry in sorted(results["kept"], key=lambda x: x.get("metric", 0))[:5]:
        run = entry.get("run", "?")
        metric = entry.get("metric", 0)
        desc = entry.get("description", "No description")
        commit = entry.get("commit", "unknown")[:8]
        report += f"- **Run {run}** ({commit}): {metric:.4f}s - {desc}\n"

    # Lessons from failures
    report += "\n## Failed Approaches (Avoid These)\n\n"
    for entry in results["discarded"][:5]:
        run = entry.get("run", "?")
        desc = entry.get("description", "No description")
        asi = entry.get("asi", {})
        rollback = asi.get("rollback_reason", "No reason given")
        report += f"- **Run {run}**: {desc}\n"
        report += f"  - Why: {rollback}\n"

    return report


def main():
    """CLI entry point."""
    autoresearch_path = Path("autoresearch.jsonl")
    if not autoresearch_path.exists():
        print(f"No autoresearch.jsonl found at {autoresearch_path}")
        sys.exit(1)

    data = load_autoresearch_data(autoresearch_path)
    results = analyze_patterns(data)
    report = generate_report(results)

    # Save report
    output_path = Path("docs/analysis/autoresearch_patterns.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"Report saved to {output_path}")
    print(report)


if __name__ == "__main__":
    main()
