"""Traceability pipeline for connecting PRDs to architecture and tests."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TraceabilityLink(BaseModel):
    """Links a requirement to its architectural component and test suite."""

    prd_req_id: str
    architecture_component: str
    test_filepath: str
    status: str = "pending"


class TraceabilityPipeline:
    """Ensures that all features pass TDD and architectural traceability before execution."""

    root_dir: Path

    def __init__(self, root_dir: str = "/home/mike-anderson/dev/cohezion") -> None:
        self.root_dir = Path(root_dir)
        self.links: dict[str, TraceabilityLink] = {}

    def register_requirement(self, link: TraceabilityLink) -> None:
        """Register a new PRD requirement for tracking."""
        self.links[link.prd_req_id] = link
        logger.info(f"Registered traceability link for {link.prd_req_id}")

    def verify_traceability(self, req_id: str) -> bool:
        """Verify that a requirement has a corresponding test file and architectural component."""
        if req_id not in self.links:
            logger.warning(f"Requirement {req_id} not found in traceability matrix.")
            return False

        link = self.links[req_id]

        test_path = self.root_dir / link.test_filepath
        if not test_path.exists():
            logger.error(f"Traceability failure: Missing test file {test_path} for req {req_id}")
            return False

        logger.debug(f"Traceability verified for {req_id}: Component {link.architecture_component}")
        return True
