from typing import Any


class KnowerAuditor:
    """
    The 'Knower' layer's validation tool.
    Audits reasoning stability and calculates confidence metrics.
    Implements Weighted Majority Voting based on Inference-Time Entropy (arXiv:2603.27844v1).
    """

    def __init__(self):
        self.stability_threshold = 0.95

    def audit_runs(
        self, run_results: list[int | None], reasoning_chains: list[str]
    ) -> dict[str, Any]:
        """
        Analyzes consistency between Run 1 and Run 2.
        """
        r1, r2 = run_results[0], run_results[1]

        # 1. Base Consistency
        is_consistent = (r1 == r2) and (r1 is not None)

        # 2. Stability Score (Internal confidence)
        stability_score = 1.0 if is_consistent else 0.0
        if r1 is None and r2 is None:
            stability_score = 0.0

        # 3. Reasoning Drift Analysis
        len_r1 = len(reasoning_chains[0])
        len_r2 = len(reasoning_chains[1])
        drift_ratio = abs(len_r1 - len_r2) / (max(len_r1, len_r2) + 1)

        if drift_ratio > 0.3:
            stability_score *= 0.8

        # 4. Entropy Calculation (Simplified approximation)
        # Higher drift or inconsistent answers increase entropy
        entropy = 0.0 if is_consistent else 0.5
        if r1 is None or r2 is None:
            entropy += 0.25

        # Weighted Confidence per AIMO-3 paper: w = 1 + 1 / (entropy + 0.1)
        weight = 1.0 + 1.0 / (entropy + 0.1)

        if r1 is None and r2 is None:
            final_answer = 0
        elif is_consistent:
            final_answer = r1
        else:
            final_answer = None

        return {
            "consistent": is_consistent,
            "stability_score": round(stability_score, 3),
            "drift_ratio": round(drift_ratio, 3),
            "entropy": round(entropy, 3),
            "weight": round(weight, 3),
            "final_answer": final_answer,
            "action": "COMMIT" if is_consistent else "TIE_BREAKER",
        }

    def resolve_tie(self, r1: int, r2: int, r3: int, reasoning_chains: list[str] = None) -> int:
        """
        Weighted Majority Vote tie-breaker.
        w = 1 + 1 / (entropy + 0.1)
        """
        # If no reasoning chains provided for entropy, use standard majority vote
        if not reasoning_chains or len(reasoning_chains) < 3:
            votes = [r1, r2, r3]
            counts = {v: votes.count(v) for v in set(votes)}
            return max(counts, key=counts.get)

        # Calculate weights based on approximate entropy (reasoning stability)
        weights = []
        for chain in reasoning_chains:
            # Entropy heuristic: variance in step length/density (simplified)
            # For this implementation, we use a constant base and penalize "yapping"
            # over 10k tokens as higher entropy/lower confidence
            ent = 0.1 + (max(0, len(chain) - 5000) / 20000.0)
            w = 1.0 + 1.0 / (ent + 0.1)
            weights.append(w)

        # Weighted vote
        vote_scores = {}
        for ans, w in zip([r1, r2, r3], weights):
            vote_scores[ans] = vote_scores.get(ans, 0.0) + w

        return max(vote_scores, key=vote_scores.get)


if __name__ == "__main__":
    auditor = KnowerAuditor()

    # Test 1: Consistent
    res1 = auditor.audit_runs([47, 47], ["Proof A is long...", "Proof B is long..."])
    print(f"Test 1 (Consistent): {res1}")

    # Test 2: Inconsistent
    res2 = auditor.audit_runs([47, 42], ["Proof A is long...", "Short proof."])
    print(f"Test 2 (Inconsistent): {res2}")
