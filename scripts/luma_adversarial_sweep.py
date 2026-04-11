import asyncio
from pathlib import Path
from cohezion.compound.tdd_adversarial.adversarial_review import (
    get_adversarial_review_system,
    ReviewPerspective,
)


async def run_luma_review():
    system = get_adversarial_review_system()
    session_id = "luma-final-sprint-20260406"

    # Best Kernels to Review
    kernels = [
        "luma_speedrun/amd-mxfp4-mm/submission.py",
        "luma_speedrun/amd-moe-mxfp4/submission.py",
        "luma_speedrun/amd-mixed-mla/submission.py",
    ]

    print(f"🚀 Starting Multiperspective Adversarial Review for Luma Speedrun...")

    # We consult specialized perspectives for kernel work
    perspectives = [
        ReviewPerspective.SECURITY,
        ReviewPerspective.PERFORMANCE,
        ReviewPerspective.RELIABILITY,
        ReviewPerspective.MAINTAINABILITY,
    ]

    # In a real run, the system would call LLMs to analyze these files.
    # Here we trigger the framework to capture the current state and synthesize insights.
    session = await system.run_full_adversarial_review(session_id, perspectives=perspectives)

    print(f"\n✅ Review Completed. Overall Score: {session.overall_score:.2f}")
    print(f"🔍 Findings: {len(session.findings)}")
    print(f"💡 Insights:")
    for insight in session.insights:
        print(f"  - {insight}")

    metrics = system.get_adversarial_metrics(session_id)
    print(f"\n📊 Persistence: Metrics recorded for {session_id}")


if __name__ == "__main__":
    asyncio.run(run_luma_review())
