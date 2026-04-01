#!/usr/bin/env python3
"""Validate and Verify All Claims

This script validates:
1. How many skills actually have results
2. Real token usage vs claimed
3. Which optimizations are validated vs simulated
4. Cross-skill learning execution status
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def count_actual_results():
    """Count actual result files in vault."""
    vault_paths = [
        Path("data/vault/research_squad"),
        Path("data/vault/multi_metric"),
        Path("data/vault/complete"),
        Path("data/vault/compound"),
    ]

    all_results = []
    for vault_path in vault_paths:
        if vault_path.exists():
            results = list(vault_path.glob("result_*.json"))
            all_results.extend(results)

    print("=" * 70)
    print("CLAIM VALIDATION: Actual Results")
    print("=" * 70)
    print(f"\nTotal result files found: {len(all_results)}")

    # Parse unique skills
    skills_optimized = set()
    total_tokens = 0

    for result_file in all_results:
        try:
            data = json.loads(result_file.read_text())
            skill = data.get("skill", "unknown")
            skills_optimized.add(skill)
            tokens = data.get("tokens_used", 0)
            total_tokens += tokens
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    print(f"Unique skills optimized: {len(skills_optimized)}")
    print(f"Skills: {sorted(skills_optimized)}")
    print(f"Total tokens used: {total_tokens:,}")
    print()

    return skills_optimized, total_tokens


def validate_phase2_claims():
    """Validate Phase 2 deployment claims."""
    print("=" * 70)
    print("CLAIM: Phase 2 - 8 skills, 75% success rate")
    print("=" * 70)

    report_path = Path("data/vault/research_squad/deployment_report_phase2.json")
    if not report_path.exists():
        print("❌ FAILED: No Phase 2 report found")
        return False

    data = json.loads(report_path.read_text())
    results = data.get("results", [])

    successful = sum(1 for r in results if r.get("status") == "success")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    total = len(results)

    print(f"Total skills: {total}")
    print(f"Successful: {successful}")
    print(f"Skipped: {skipped}")
    print(f"Success rate: {successful / total * 100:.0f}%")

    if successful == 6 and total == 8:
        print("✅ CLAIM VALIDATED: 6/8 optimized (75% success)")
        return True
    else:
        print(f"⚠️ PARTIAL: {successful}/{total} optimized")
        return False


def validate_token_efficiency():
    """Validate token efficiency claims."""
    print("\n" + "=" * 70)
    print("CLAIM: Token efficiency ~26-27%")
    print("=" * 70)

    vault_paths = [
        Path("data/vault/research_squad"),
        Path("data/vault/multi_metric"),
        Path("data/vault/complete"),
        Path("data/vault/compound"),
    ]

    total_tokens = 0
    total_budget = 0

    for vault_path in vault_paths:
        if vault_path.exists():
            for result_file in vault_path.glob("result_*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    tokens = data.get("tokens_used", 0)
                    total_tokens += tokens
                    total_budget += 8000  # Per skill budget
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

    if total_budget > 0:
        efficiency = total_tokens / total_budget
        print(f"Total tokens used: {total_tokens:,}")
        print(f"Total budget: {total_budget:,}")
        print(f"Efficiency: {efficiency * 100:.1f}%")

        if 0.25 <= efficiency <= 0.30:
            print("✅ CLAIM VALIDATED: Efficiency in 25-30% range")
            return True
        else:
            print(f"⚠️ PARTIAL: Efficiency {efficiency * 100:.1f}%")
            return False
    else:
        print("❌ FAILED: No token data found")
        return False


def validate_improvements():
    """Validate improvement claims."""
    print("\n" + "=" * 70)
    print("CLAIM: Improvements per skill")
    print("=" * 70)

    claimed_improvements = {
        "refactoring": 23.2,
        "debugging": 22.7,
        "documentation": 18.5,
        "testing": 13.5,
        "coding": 10.7,
        "review": 5.5,
    }

    # Load actual results
    report_path = Path("data/vault/research_squad/deployment_report_phase2.json")
    if report_path.exists():
        data = json.loads(report_path.read_text())
        results = data.get("results", [])

        print("\nSkill           Claimed    Actual    Status")
        print("-" * 50)

        for skill, claimed in claimed_improvements.items():
            actual_result = next(
                (r for r in results if r.get("skill") == skill and r.get("status") == "success"),
                None,
            )

            if actual_result:
                actual = actual_result.get("improvement_pct", 0)
                diff = abs(actual - claimed)
                status = "✅" if diff < 2.0 else "⚠️"
                print(f"{skill:15} {claimed:5.1f}%    {actual:5.1f}%   {status}")
            else:
                print(f"{skill:15} {claimed:5.1f}%    N/A       ❌")

    print()


def validate_cross_skill_learning():
    """Validate cross-skill learning claims."""
    print("=" * 70)
    print("CLAIM: Cross-skill learning (teachers → students)")
    print("=" * 70)

    # Check if any learning has been applied
    vault_paths = [
        Path("data/vault/compound"),
        Path("data/vault/complete"),
    ]

    learning_applied = 0
    for vault_path in vault_paths:
        if vault_path.exists():
            for result_file in vault_path.glob("result_*.json"):
                try:
                    data = json.loads(result_file.read_text())
                    if data.get("learning_applied"):
                        learning_applied += 1
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

    if learning_applied > 0:
        print(f"✅ CLAIM VALIDATED: {learning_applied} skills with learning applied")
        return True
    else:
        print("❌ FAILED: No cross-skill learning executed")
        print("   - Code exists in cross_skill_learning.py")
        print("   - No evidence of actual transfer")
        return False


def validate_alerting():
    """Validate alerting system claims."""
    print("\n" + "=" * 70)
    print("CLAIM: Production alerting system")
    print("=" * 70)

    report_paths = [
        Path("data/vault/complete/complete_report.json"),
        Path("data/vault/compound/compound_report.json"),
    ]

    total_alerts = 0
    for report_path in report_paths:
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text())
                alerts = data.get("alerts", [])
                total_alerts += len(alerts)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    if total_alerts > 0:
        print(f"✅ CLAIM VALIDATED: {total_alerts} alerts generated")
        return True
    else:
        print("⚠️ PARTIAL: Alerting code exists, 0 alerts triggered")
        print("   - System healthy, no degradation detected")
        return False


def validate_multi_metric():
    """Validate multi-metric optimization claims."""
    print("\n" + "=" * 70)
    print("CLAIM: Multi-metric optimization (coherence + success + time)")
    print("=" * 70)

    # Check multi_metric results
    mm_path = Path("data/vault/multi_metric")
    if mm_path.exists():
        results = list(mm_path.glob("result_*.json"))
        print(f"Multi-metric results: {len(results)}")

        if results:
            print("✅ CLAIM VALIDATED: Multi-metric results exist")
            # Show sample
            sample = json.loads(results[0].read_text())
            if "weighted_score" in sample:
                print(f"   - Weighted scoring: {sample['weighted_score']}")
            return True
        else:
            print("❌ FAILED: No multi-metric results")
            return False
    else:
        print("❌ FAILED: No multi-metric vault")
        return False


def main():
    """Run all validations."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE CLAIM VALIDATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    results = {}

    # Validate claims
    results["results_count"] = count_actual_results()
    results["phase2"] = validate_phase2_claims()
    validate_improvements()
    results["token_efficiency"] = validate_token_efficiency()
    results["multi_metric"] = validate_multi_metric()
    results["cross_skill"] = validate_cross_skill_learning()
    results["alerting"] = validate_alerting()

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v is True)
    partial = sum(1 for v in results.values() if v == "partial")
    failed = sum(1 for v in results.values() if v is False)

    print(f"✅ Validated: {passed}")
    print(f"⚠️  Partial: {partial}")
    print(f"❌ Failed: {failed}")
    print()

    if passed >= 4:
        print("OVERALL: Mostly validated, some claims need evidence")
        sys.exit(0)
    else:
        print("OVERALL: Significant gaps between claims and evidence")
        sys.exit(1)


if __name__ == "__main__":
    main()
