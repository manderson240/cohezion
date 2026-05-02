import numpy as np

from cohezion.swarm.topological_router import TopologicalRegime, TopologicalRouter


class ARCEvolutionarySteer:
    """
    Uses Topological Data Analysis (TDA) to steer the evolutionary program search.
    Detects when the search is stuck in local minima (loops) and triggers a PIVOT.
    """

    def __init__(self, search_session_id="arc_search"):
        self.router = TopologicalRouter(min_trajectory_length=5)
        self.session_id = search_session_id

    def record_candidate(self, fitness, latent_rule_vector):
        """
        Records a candidate program's fitness and its latent representation.
        """
        # We use (1 - fitness) as a proxy for distance in the manifold
        self.router.record_trajectory_point(self.session_id, latent_rule_vector)

    def get_steering_directive(self):
        """
        Returns a directive for the genetic algorithm: EXPLORE, EXPLOIT, or PIVOT.
        """
        topo = self.router.analyze_agent(self.session_id)

        if topo.regime == TopologicalRegime.PIVOT:
            print("  [TDA] Loop detected in search space. Triggering PIVOT (Mass Mutation).")
            return "PIVOT"
        elif topo.regime == TopologicalRegime.EXPLORE:
            return "EXPLORE"
        else:
            return "EXPLOIT"


if __name__ == "__main__":
    steer = ARCEvolutionarySteer()
    # Simulate a loop in search space (stagnant latents)
    latent = np.random.randn(256)
    for _ in range(10):
        steer.record_candidate(0.1, latent + 0.01 * np.random.randn(256))

    directive = steer.get_steering_directive()
    print(f"Steering Directive: {directive}")
