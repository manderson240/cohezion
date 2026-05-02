from typing import Any


class KnowerAuditor:
    """
    The 'Knower' layer's validation tool.
    Audits reasoning stability and calculates confidence metrics.
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
        # Factors: Consistency, reasoning length variance, token density
        stability_score = 1.0 if is_consistent else 0.0
        if r1 is None and r2 is None:
            stability_score = 0.0

        # 3. Reasoning Drift Analysis
        # Check if the reasoning chains are significantly different in length
        len_r1 = len(reasoning_chains[0])
        len_r2 = len(reasoning_chains[1])
        drift_ratio = abs(len_r1 - len_r2) / (max(len_r1, len_r2) + 1)

        if drift_ratio > 0.3:
            stability_score *= 0.8  # Penalize for erratic reasoning length

        # 4. Final Answer: None if inconsistent (triggers tie-breaker)
        # Special case: both None returns 0 (graceful degradation)
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
            "final_answer": final_answer,
            "action": "COMMIT" if is_consistent else "TIE_BREAKER",
        }

    def resolve_tie(self, r1: int, r2: int, r3: int) -> int:
        """
        Majority vote tie-breaker.
        """
        votes = [r1, r2, r3]
        counts = {v: votes.count(v) for v in set(votes)}
        return max(counts, key=counts.get)


if __name__ == "__main__":
    auditor = KnowerAuditor()

    # Test 1: Consistent
    res1 = auditor.audit_runs([47, 47], ["Proof A is long...", "Proof B is long..."])
    print(f"Test 1 (Consistent): {res1}")

    # Test 2: Inconsistent
    res2 = auditor.audit_runs([47, 42], ["Proof A is long...", "Short proof."])
    print(f"Test 2 (Inconsistent): {res2}")
