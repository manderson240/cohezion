#!/usr/bin/env python3
"""
Daily Platform Health Digest - Example Usage

Demonstrates Charter-aligned health monitoring:
- Layer 1: Health data collection (repository, tests, dependencies)
- Layer 2: Charter scoring (50% HIHO + 25% metrics + 25% trend)
- Layer 3: EDL routing for critical issues

Usage:
    uv run python scripts/examples/daily_health_digest_example.py
"""

import asyncio

from cohezion.platform.daily_health_digest import get_daily_health_digest


async def main():
    """Generate and display daily health digest."""

    print("=" * 70)
    print("DAILY PLATFORM HEALTH DIGEST - EXAMPLE")
    print("=" * 70)
    print("\nGenerating health digest...\n")

    # Get digest instance
    digest = get_daily_health_digest()

    try:
        # Generate complete health assessment
        result = await digest.generate_digest()

        # Display formatted digest
        print(digest.format_digest_terminal(result))

        # If critical issues detected, route through EDL
        if result.requires_edl_review:
            print("\n⚠️  Critical issues detected. Routing through Expert Domain Lattice...\n")
            await digest.route_critical_issues_to_edl(result)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Overall Health Score: {result.overall_health_score:.3f} / 1.0")
        print(f"Status: {result.overall_status.value.upper()}")
        print(f"HIHO Stable: {'✅ Yes' if result.hiho_stable else '⚠️  No'}")
        print(f"Trend (7 days): {result.trend_7d:+.3f}")
        print(f"Recommendations: {len(result.recommendations)}")

        if result.overall_status.value == "healthy":
            print("\n✅ All systems healthy! No actions required.")
        elif result.overall_status.value == "warning":
            print("\n⚠️  Some issues detected. Review recommendations.")
        else:  # critical
            print("\n❌ CRITICAL issues detected! Immediate action required.")

    except Exception as e:
        print(f"\n❌ Error generating digest: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
