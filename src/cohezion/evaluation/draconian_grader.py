"""
Draconian Adversarial Grading System
=====================================
True consensus, not majority vote.
Edge cases matter. No compromise on quality.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import numpy as np

class VoteType(Enum):
    STRONG_APPROVE = 2
    APPROVE = 1
    ABSTAIN = 0
    REJECT = -1
    STRONG_REJECT = -2

@dataclass
class Critique:
    """A model's critique of a proposal."""
    model: str
    vote: VoteType
    reasoning: str
    edge_cases_identified: List[str]
    severity: float  # 0-1, how critical are the issues

@dataclass
class GradingResult:
    """Result of draconian grading."""
    passed: bool
    consensus_score: float  # 0-1, must be ≥0.95 for TRUE consensus
    edge_case_coverage: float  # 0-1, must be ≥0.90
    critiques: List[Critique]
    failed_reason: Optional[str]

class DraconianGrader:
    """
    DRACONIAN grading system.
    
    Rules:
    1. TRUE CONSENSUS required (≥95% agreement)
    2. No single STRONG_REJECT allowed
    3. All edge cases must be addressed
    4. Efficacy + Completeness + Forward-looking ALL must pass
    5. Any critical flaw = instant fail
    """
    
    def __init__(self, min_consensus=0.95, min_edge_coverage=0.90):
        self.min_consensus = min_consensus
        self.min_edge_coverage = min_edge_coverage
    
    def grade(
        self, 
        proposal: str, 
        judges: List[str],
        efficacy_score: float,
        completeness_score: float,
        forward_looking_score: float
    ) -> GradingResult:
        """
        Grade proposal with DRACONIAN standards.
        
        Measurements (user specified):
        - Efficacy: Does it actually work?
        - Completeness: Is everything covered?
        - Forward-looking: Does it enable future work?
        """
        
        # Collect critiques from all judges
        critiques = self._collect_critiques(proposal, judges)
        
        # Check for instant-fail conditions
        for critique in critiques:
            if critique.vote == VoteType.STRONG_REJECT:
                return GradingResult(
                    passed=False,
                    consensus_score=0.0,
                    edge_case_coverage=0.0,
                    critiques=critiques,
                    failed_reason=f"{critique.model} STRONG_REJECT: {critique.reasoning}"
                )
            
            if critique.severity > 0.8:  # Critical flaw
                return GradingResult(
                    passed=False,
                    consensus_score=0.0,
                    edge_case_coverage=0.0,
                    critiques=critiques,
                    failed_reason=f"Critical flaw from {critique.model}: {critique.reasoning}"
                )
        
        # Calculate consensus (votes weighted by conviction)
        vote_scores = [c.vote.value for c in critiques]
        consensus_score = (sum(vote_scores) + len(judges) * 2) / (len(judges) * 4)
        
        # Edge case coverage
        all_edge_cases = set()
        for c in critiques:
            all_edge_cases.update(c.edge_cases_identified)
        
        covered_cases = len([ec for ec in all_edge_cases if self._is_addressed(ec, proposal)])
        edge_case_coverage = covered_cases / max(len(all_edge_cases), 1)
        
        # Check core metrics
        if efficacy_score < 0.90:
            return GradingResult(
                passed=False,
                consensus_score=consensus_score,
                edge_case_coverage=edge_case_coverage,
                critiques=critiques,
                failed_reason=f"Efficacy too low: {efficacy_score:.2f} < 0.90"
            )
        
        if completeness_score < 0.90:
            return GradingResult(
                passed=False,
                consensus_score=consensus_score,
                edge_case_coverage=edge_case_coverage,
                critiques=critiques,
                failed_reason=f"Completeness too low: {completeness_score:.2f} < 0.90"
            )
        
        if forward_looking_score < 0.85:
            return GradingResult(
                passed=False,
                consensus_score=consensus_score,
                edge_case_coverage=edge_case_coverage,
                critiques=critiques,
                failed_reason=f"Forward-looking too low: {forward_looking_score:.2f} < 0.85"
            )
        
        # Check TRUE consensus
        if consensus_score < self.min_consensus:
            return GradingResult(
                passed=False,
                consensus_score=consensus_score,
                edge_case_coverage=edge_case_coverage,
                critiques=critiques,
                failed_reason=f"No true consensus: {consensus_score:.2f} < {self.min_consensus}"
            )
        
        # Check edge case coverage
        if edge_case_coverage < self.min_edge_coverage:
            return GradingResult(
                passed=False,
                consensus_score=consensus_score,
                edge_case_coverage=edge_case_coverage,
                critiques=critiques,
                failed_reason=f"Insufficient edge case coverage: {edge_case_coverage:.2f} < {self.min_edge_coverage}"
            )
        
        # PASSED all draconian checks
        return GradingResult(
            passed=True,
            consensus_score=consensus_score,
            edge_case_coverage=edge_case_coverage,
            critiques=critiques,
            failed_reason=None
        )
    
    def _collect_critiques(self, proposal: str, judges: List[str]) -> List[Critique]:
        """Collect critiques from all judge models."""
        critiques = []
        
        for judge in judges:
            # In real implementation, call Ollama here
            # For now, simulate
            critique = Critique(
                model=judge,
                vote=VoteType.APPROVE,  # Would come from actual model
                reasoning=f"Analysis from {judge}",
                edge_cases_identified=[f"edge_{judge}_1", f"edge_{judge}_2"],
                severity=np.random.uniform(0, 0.7)
            )
            critiques.append(critique)
        
        return critiques
    
    def _is_addressed(self, edge_case: str, proposal: str) -> bool:
        """Check if edge case is addressed in proposal."""
        # In real implementation, use semantic search or LLM check
        return edge_case.lower() in proposal.lower()

if __name__ == "__main__":
    grader = DraconianGrader()
    
    # Test proposal
    test_proposal = "Implement HIHO detection with threshold 0.5"
    judges = ["deepseek-r1:70b", "qwen3-coder:32b", "phi-4-mini", "gemma-3n:2b"]
    
    result = grader.grade(
        proposal=test_proposal,
        judges=judges,
        efficacy_score=0.92,
        completeness_score=0.91,
        forward_looking_score=0.87
    )
    
    print(f"DRACONIAN GRADING RESULT:")
    print(f"  Passed: {result.passed}")
    print(f"  Consensus: {result.consensus_score:.3f}")
    print(f"  Edge Coverage: {result.edge_case_coverage:.3f}")
    if result.failed_reason:
        print(f"  FAILED: {result.failed_reason}")
