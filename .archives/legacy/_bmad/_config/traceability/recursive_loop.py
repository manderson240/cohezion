#!/usr/bin/env python3
"""
Recursive Self-Improvement Loop for Traceability Engine

Enables continuous compound engineering via:
1. Self-trace mode (engine traces itself)
2. Adversarial review (multi-agent party mode)
3. TDD validation (tests verify improvements)
4. Recursive iteration (snapshots compared)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from traceability_engine import TraceabilityEngine


def run_traceability_engine(self_trace: bool = False) -> dict:
    """Run the traceability engine and return stats."""
    args = ["uv", "run", "python", "_bmad/_config/traceability/traceability_engine.py"]
    if self_trace:
        args.append("--self-trace")

    result = subprocess.run(
        args, capture_output=True, text=True, cwd="/home/mike-anderson/dev/cohezion"
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def compare_snapshots(prev_snapshot: Path, curr_snapshot: Path) -> dict:
    """Compare two snapshots to detect changes."""
    prev_data = {}
    curr_data = {}

    with open(prev_snapshot, "r") as f:
        for line in f:
            if "," in line:
                key, val = line.strip().split(",", 1)
                prev_data[key] = val

    with open(curr_snapshot, "r") as f:
        for line in f:
            if "," in line:
                key, val = line.strip().split(",", 1)
                curr_data[key] = val

    changes = {}
    for key in prev_data:
        if key in curr_data and prev_data[key] != curr_data[key]:
            changes[key] = {"prev": prev_data[key], "curr": curr_data[key]}

    return changes


def run_tests() -> dict:
    """Run the test suite."""
    result = subprocess.run(
        ["uv", "run", "pytest", "_bmad/_config/traceability/tests/", "-v"],
        capture_output=True,
        text=True,
        cwd="/home/mike-anderson/dev/cohezion",
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def run_party_mode_review() -> dict:
    """Trigger party-mode adversarial review workflow."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "_bmad/_config/traceability/workflows/run_party_review.py",
        ],
        capture_output=True,
        text=True,
        cwd="/home/mike-anderson/dev/cohezion",
        timeout=600,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def find_latest_snapshot(output_dir: Path) -> Path:
    """Find the most recent snapshot."""
    snapshot_dir = output_dir / "snapshots"
    if not snapshot_dir.exists():
        return None

    snapshots = sorted(snapshot_dir.glob("traceability_*.csv"), reverse=True)
    return snapshots[0] if snapshots else None


def main():
    """Main recursive loop entry point."""
    print("🔄 BMAD Traceability Recursive Self-Improvement Loop")
    print("=" * 60)

    project_root = Path("/home/mike-anderson/dev/cohezion")
    output_dir = project_root / "_bmad" / "_config" / "traceability"

    # Find previous snapshot
    prev_snapshot = find_latest_snapshot(output_dir)
    if prev_snapshot:
        print(f"📊 Found previous snapshot: {prev_snapshot.name}")
    else:
        print("📊 No previous snapshot found (first run)")

    # Run traceability engine with self-trace
    print("\n🔍 Running traceability engine with self-trace...")
    result = run_traceability_engine(self_trace=True)
    print(result["stdout"])

    if result["returncode"] != 0:
        print(f"❌ Engine failed: {result['stderr']}")
        sys.exit(1)

    # Find new snapshot
    curr_snapshot = find_latest_snapshot(output_dir)
    if not curr_snapshot:
        print("❌ No snapshot generated")
        sys.exit(1)

    print(f"💾 New snapshot: {curr_snapshot.name}")

    # Compare snapshots
    if prev_snapshot and prev_snapshot != curr_snapshot:
        print("\n📈 Comparing snapshots...")
        changes = compare_snapshots(prev_snapshot, curr_snapshot)
        if changes:
            print("🔄 Changes detected:")
            for key, change in changes.items():
                print(f"  {key}: {change['prev']} → {change['curr']}")
        else:
            print("✓ No changes from previous run")

    # Run tests
    print("\n🧪 Running test suite...")
    test_result = run_tests()
    if test_result["returncode"] == 0:
        print("✅ All tests passed")
    else:
        print("❌ Tests failed:")
        print(test_result["stderr"])
        sys.exit(1)

    # Check for gaps
    engine = TraceabilityEngine(project_root)
    engine.run_full_extraction(self_trace=True)

    gaps = []
    if len(engine.invocations) < 20:
        gaps.append("Low invocation count (expected 20+)")
    if not engine.matrix_workflow_chain:
        gaps.append("Empty workflow chain matrix")
    if len(engine.matrix_workflow_task) < len(engine.tasks):
        gaps.append("Missing task invocations")

    if gaps:
        print("\n⚠️  Gaps detected:")
        for gap in gaps:
            print(f"  - {gap}")

        # Auto-trigger party-mode adversarial review when gaps found
        print("\n🎉 Triggering party-mode adversarial review...")
        party_result = run_party_mode_review()
        if party_result["returncode"] == 0:
            print("✅ Party-mode review completed")
            print("   Findings saved to: MULTI_AGENT_REVIEW_FINDINGS.md")
        else:
            print(f"⚠️  Party-mode review failed: {party_result['stderr']}")
    else:
        print("\n✅ No critical gaps detected")

    print("\n🎯 Recursive loop complete!")
    print("   Next iteration: Run engine again or review new findings")


if __name__ == "__main__":
    main()
