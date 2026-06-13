# Autoresearch: Nemotron Accuracy Improvement

## Objective
Improve Nemotron multi-domain accuracy beyond 72.0% overall.
Focus on bit_manip (50.1%) — the largest remaining gap.
equations are near-ceiling (5.7%), deprioritized.

## Metrics
- **Primary**: overall_accuracy (%, higher is better)
- **Secondary**: bit_manip_accuracy (50.1% → target >75%)
- **Baseline** (exp_analysis_v73): 72.0% overall, bit_manip=50.1%, equations=5.7%

## Current Breakdown (as of exp_analysis_v73, 3000-row eval)
| Type | Accuracy | Status |
|------|----------|--------|
| numeral | 100% | ceiling |
| encryption | 100% | ceiling |
| gravity | 86.7% | near ceiling |
| unit_conv | 87.1% | near ceiling |
| bit_manip | 50.1% | **ACTIVE FRONTIER** |
| equations | 5.7% | near ceiling (complex patterns) |

## Failed Approaches
- exp_EE: majority-vote char mapping for equations → 7.9%→1.3% (regression, reverted)
- exp_BB: operator-semantics for equations → 5.0%→4.9% (regression)

## Next Experiments (Frontier — bit_manip focus)
1. **Bitwise pattern analysis** — detect AND/OR/XOR/NOT/shift operations from examples
   - Look for: output has same bits as input with mask applied, or shift by K positions
2. **Binary representation** — convert to binary, detect operation, convert back
   - bit_manip problems often need: "input & 0xF0 → output", "input XOR key → output"
3. **Exhaustive small-integer search** — for numeric pairs, try all bit ops systematically

## Constraints
- Experiments should be measured on the existing eval dataset (not generate new)
- Winner threshold: overall_accuracy improvement ≥ 0.5pp OR bit_manip_accuracy ≥ 70%
- Log to autoresearch.jsonl with winner: true/false and metrics dict
- OOM-safe: no large model loading
