# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Hallucination Resolver Logic for Cohezion.
Grounds agent claims against live system diagnostics and the Hallucination Tracker.
"""

import os
import re
from pathlib import Path
from typing import Any

from cohezion.reliability.residency_awareness import ResidencyAnchorBase


class HallucinationResolver:
    def __init__(
        self,
        tracker_path: str = "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/HALLUCINATION_TRACKER.md",
    ):
        self.tracker_path = Path(tracker_path)
        self.ground_truth = ResidencyAnchorBase.get_anchors()

    def resolve_claims(self, text: str) -> dict[str, Any]:
        """Verify text against ground truth and known hallucinations."""
        issues = []
        corrections = {}

        # 1. Check for Hardware Hallucinations (e.g. Framework 16 vs Ryzen AI Max)
        if "Framework 16" in text and "AMD RYZEN AI MAX+" not in self.ground_truth.get("cpu", ""):
            # This is a bit of a nuance: if the user CALLS it a Framework 16, it might be fine,
            # but if the agent CLAIMS specs optimized for it without checking, it's a flag.
            pass

        if (
            "NVIDIA" in text or "H100" in text or "A100" in text
        ) and "AMD" in self.ground_truth.get("gpu", ""):
            issues.append("Claimed NVIDIA hardware on an AMD system.")
            corrections["gpu"] = self.ground_truth["gpu"]

        # 2. Check for path hallucinations
        path_matches = re.findall(r"(/[a-zA-Z0-9_\-\./]+)", text)
        for path in path_matches:
            if (
                "/home/" in path
                and not path.startswith(self.ground_truth["project_root"])
                and "mike-anderson" in path
            ) and not os.path.exists(path):
                issues.append(f"Referenced non-existent absolute path: {path}")

        return {
            "is_hallucinating": len(issues) > 0,
            "issues": issues,
            "corrections": corrections,
            "ground_truth": self.ground_truth,
        }

    def get_truth_anchors(self) -> str:
        """Generate a concise 'Truth Anchor' block for context injection."""
        gt = self.ground_truth
        return f"""
[TRUTH ANCHORS]
- System: {gt["os"]} on {gt["cpu"]}
- GPU: {gt["gpu"]}
- RAM: {gt["ram_gb"]} GB
- Project Root: {gt["project_root"]}
- Verification: Hardware vitals checked via sysfs/lscpu.
""".strip()


if __name__ == "__main__":
    resolver = HallucinationResolver()
    print(resolver.get_truth_anchors())
