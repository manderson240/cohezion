import json
import os

import numpy as np
from arc_axiomatic import ARCAxiomaticProjector


class ARCManifoldTransfer:
    """
    Implements Cross-Game Transfer for ARC via the 12D Axiomatic Manifold.
    Learns 'Rule Embeddings' and stores them in a latent library.
    """

    def __init__(self, library_path="research/challenges/arc_prize_2026/rule_library.json"):
        self.library_path = library_path
        self.rule_library = self._load_library()
        self.projector = ARCAxiomaticProjector()

    def _load_library(self):
        if os.path.exists(self.library_path):
            with open(self.library_path) as f:
                return json.load(f)
        return {}

    def save_rule(self, task_id, axioms_delta, program_summary):
        """
        Stores a transformation rule as a displacement vector in the 12D manifold.
        """
        self.rule_library[task_id] = {
            "axioms_delta": axioms_delta.tolist(),
            "program": program_summary,
        }
        with open(self.library_path, "w") as f:
            json.dump(self.rule_library, f, indent=2)
        print(f"  Saved rule for {task_id} to Manifold Library.")

    def find_similar_rule(self, current_axioms_delta):
        """
        Finds the most similar rule in the library based on 12D manifold distance.
        """
        if not self.rule_library:
            return None

        best_match = None
        min_dist = float("inf")

        for task_id, data in self.rule_library.items():
            lib_delta = np.array(data["axioms_delta"])
            dist = np.linalg.norm(current_axioms_delta - lib_delta)
            if dist < min_dist:
                min_dist = dist
                best_match = data["program"]

        # Return match if within a certain manifold radius
        if min_dist < 5.0:
            return best_match
        return None


if __name__ == "__main__":
    transfer = ARCManifoldTransfer()
    # Mock a learned rule: "Rotation90"
    mock_delta = np.random.randn(12)
    transfer.save_rule("mock_task_1", mock_delta, "rotate90")

    # Try to find it
    query_delta = mock_delta + 0.1  # Slight perturbation
    match = transfer.find_similar_rule(query_delta)
    print(f"Manifold Query Result: {match}")
