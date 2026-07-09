"""Fire-and-forget CLI: record a git commit in the plan traceability graph.

Usage::

    uv run python -m cohezion.traceability.record_commit <commit_hash> <message> <plan_slug> [step ...]

Called by the git post-commit hook. Must never block or raise.
"""

from __future__ import annotations

import asyncio
import logging
import sys


logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) < 4:
        print(
            f"Usage: {sys.argv[0]} <commit_hash> <message> <plan_slug> [step ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    commit_hash = sys.argv[1]
    message = sys.argv[2]
    plan_slug = sys.argv[3]
    task_steps = sys.argv[4:]

    try:
        from cohezion.traceability.plan_graph import PlanGraph

        asyncio.run(PlanGraph().record_commit(commit_hash, message, task_steps, plan_slug))
    except Exception as exc:
        logger.debug("record_commit silenced: %s", exc)


if __name__ == "__main__":
    main()
