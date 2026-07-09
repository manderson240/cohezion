"""Fire-and-forget CLI: emit a file-touch event to the plan traceability graph.

Usage::

    uv run python -m cohezion.traceability.record_touch <plan_slug> <step_number> <file_path>

Called by the spec-implement workflow after each Edit/Write. Must never block
or raise -- tracing failures are silently swallowed.
"""

from __future__ import annotations

import asyncio
import logging
import sys


logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) < 4:
        print(
            f"Usage: {sys.argv[0]} <plan_slug> <step_number> <file_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    plan_slug, step_number, file_path = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        from cohezion.traceability.plan_graph import PlanGraph

        asyncio.run(PlanGraph().record_file_touch(plan_slug, step_number, file_path))
    except Exception as exc:
        logger.debug("record_touch silenced: %s", exc)


if __name__ == "__main__":
    main()
