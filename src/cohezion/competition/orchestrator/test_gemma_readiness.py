"""Test Gemma hackathon agent with actual submission artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.gemma_hackathon_agent import GemmaHackathonAgent
from model_dispatcher import ModelDispatcher


def main():
    dispatcher = ModelDispatcher()
    agent = GemmaHackathonAgent(dispatcher)

    # Our actual Gemma hackathon artifacts
    artifacts = [
        "README.md",
        "kernel.py",
        "kaggle_submission.py",
        "app.py",
        "dashboard.py",
        "training_loop.py",
        "BLOG_POST.md",
        "PROJECT_WRITEUP.md",
        "VIDEO_SCRIPT.md",
    ]
    missing_human = ["registration", "video", "cover_image"]

    result = agent.run_task(
        {
            "action": "check_requirements",
            "artifacts": artifacts,
            "missing_human": missing_human,
        }
    )

    if result.get("status") == "error" or "error" in result:
        print(f"ERROR: {result}")
        return

    parsed = result.get("result", {})
    readiness = parsed.get("readiness_pct", 0)
    ai_pct = parsed.get("ai_completeness_pct", 0)
    human_pct = parsed.get("human_completeness_pct", 0)

    print(f"\nReadiness: {readiness}%")
    print(f"AI completeness: {ai_pct}%")
    print(f"Human completeness: {human_pct}%")
    print(f"Missing critical: {parsed.get('missing_critical', [])}")
    print(f"Next actions: {parsed.get('next_actions', [])}")
    print(f"\nMETRIC submission_readiness_pct={readiness}")


if __name__ == "__main__":
    main()
