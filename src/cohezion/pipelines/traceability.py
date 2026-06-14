from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TraceabilityLink:
    prd_req_id: str
    architecture_component: str
    test_filepath: str
    status: str = "pending"


class TraceabilityPipeline:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)
        self.links: dict[str, TraceabilityLink] = {}

    def register_requirement(self, link: TraceabilityLink) -> None:
        self.links[link.prd_req_id] = link

    def verify_traceability(self, req_id: str) -> bool:
        if req_id not in self.links:
            return False
        link = self.links[req_id]
        return (self.root_dir / link.test_filepath).exists()
