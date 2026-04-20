import asyncio
from pathlib import Path
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem,
    ReviewPerspective,
)


async def run_review():
    project_root = Path.cwd()
    system = AdversarialReviewSystem(project_root)

    session_id = "arc_prize_2026_init"
    print(f"Running adversarial review for session: {session_id}")

    # Review from specific perspectives relevant to ARC
    perspectives = [
        ReviewPerspective.SECURITY,
        ReviewPerspective.PERFORMANCE,
        ReviewPerspective.MAINTAINABILITY,
        ReviewPerspective.INNOVATION,
    ]

    session = await system.run_full_adversarial_review(session_id, perspectives=perspectives)

    print("\n--- Review Findings ---")
    for finding in session.findings:
        print(f"[{finding.perspective.value.upper()}] {finding.title} ({finding.severity})")
        print(f"  Description: {finding.description}")
        print(f"  Suggestion: {finding.suggestions[0]}")

    print("\n--- Conflict Analysis ---")
    if not session.conflicts:
        print("No conflicts detected between perspectives.")
    else:
        for f1, f2 in session.conflicts:
            print(f"Conflict: {f1.perspective.value} vs {f2.perspective.value}")

    print("\n--- Insights ---")
    for insight in session.insights:
        print(f"- {insight}")

    print(f"\nOverall System Score: {session.overall_score:.2f}")


if __name__ == "__main__":
    asyncio.run(run_review())
