# Track B: Confidence Scoring System - API Documentation

**Status**: [DRAFT - Under Development]
**Last Updated**: 2026-02-14
**Target Completion**: 2026-02-27

## Overview

The Confidence Scoring System provides a 5-factor weighted scoring algorithm for assessing decision confidence (0-100%) with full audit trails.

## Quick Start

```python
from src.scoring import ConfidenceScorer

scorer = ConfidenceScorer()
score = scorer.score_decision("decision_001", papers=["paper_001", "paper_002"])
print(f"Confidence: {score.value:.1%} ({score.reasoning})")
```

## Scoring Factors

The system combines 5 weighted factors:

1. **Evidence Quality** (30%): Strength and variety of supporting evidence
2. **Precedent Validation** (25%): How much similar decisions have succeeded
3. **Expert Agreement** (25%): Consensus among domain experts
4. **Recency** (15%): How current the supporting data is
5. **Completeness** (5%): Extent of information gathered

## Core Modules

### src.scoring.factors
Factor extraction and calculation.

### src.scoring.algorithms
Scoring algorithm implementation with weight aggregation.

### src.scoring.audit
Audit trail system for score reproducibility.

## API Reference

### ConfidenceScorer

```python
class ConfidenceScorer:
    """Calculate confidence scores for decisions."""

    def score_decision(decision_id: str, papers: list[str]) -> ConfidenceScore
    def score_paper(paper_id: str) -> float
    def get_factor_breakdown(score_id: str) -> FactorBreakdown
    def get_audit_trail(score_id: str) -> AuditTrail
```

### Data Models

- `ConfidenceScore`: Composite score with factors and audit trail
- `Factor`: Individual factor value and weight
- `AuditTrail`: Complete calculation history

## Performance Targets

- Scoring Latency: **< 100ms** per paper
- Papers Scored: **84+** in validation set
- Test Coverage: **30+ tests** (90%+ coverage)
- Score Distribution: **mean > 0.5** (median confidence)

## Development Progress

- [ ] Step 1: Factor extraction templates design
- [ ] Step 2: Scoring algorithm implementation
- [ ] Step 3: Audit trail system
- [ ] Step 4: Comprehensive testing
- [ ] Step 5: Documentation completion

## Related

- [Track A: GraphRAG](TRACK_A_GRAPHRAG_API.md)
- [Track C: Impact Analysis](TRACK_C_IMPACT_API.md)
- [Design Spec](../decisions/TRACK-B-DESIGN-SPEC-SCORING-2026-02-14.md)
