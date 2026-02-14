import { Decision, ReasoningChain, DecisionContradiction } from '../types/Decision';

/**
 * Decision Quality Scoring Service
 *
 * Scores all decisions on a 0-1 quality scale based on:
 * - Confidence (40%)
 * - Alternatives considered (20%, capped at 5)
 * - Explicit assumptions (10%, capped at 3)
 * - Freedom from contradictions (20%)
 * - Reasoning diversity (10%, counts distinct types)
 *
 * Formula:
 * QualityScore = (
 *   (Confidence × 0.4) +
 *   (AlternativesRejectedCount / 5 × 0.2) +
 *   (AssumptionCount / 3 × 0.1) +
 *   (1 - ContradictionCount / (TotalDecisions × 0.2) × 0.2) +
 *   (ReasoningDiversity × 0.1)
 * ) / 5
 */
export interface QualityScoreBreakdown {
  confidence: number;
  alternatives: number;
  assumptions: number;
  contradictions: number;
  diversity: number;
  total: number;
}

export interface ScoredDecision {
  id: string;
  title: string;
  overall_score: number;
  breakdown: QualityScoreBreakdown;
}

export class DecisionQualityScorer {
  /**
   * Score all decisions
   * @param decisions List of decision objects
   * @param contradictionMap Map of decision_id -> contradictions count
   * @returns Scored decisions with breakdowns
   */
  scoreAllDecisions(
    decisions: Decision[],
    contradictionMap: Map<string, number> = new Map()
  ): ScoredDecision[] {
    const totalDecisions = decisions.length;

    return decisions.map(decision => {
      const breakdown = this.calculateScore(decision, contradictionMap, totalDecisions);
      return {
        id: decision.id,
        title: decision.title,
        overall_score: breakdown.total,
        breakdown,
      };
    });
  }

  /**
   * Calculate quality score for a single decision
   * @param decision The decision to score
   * @param contradictionMap Map of decision_id -> contradictions count
   * @param totalDecisions Total number of decisions (for contradiction normalization)
   * @returns Quality breakdown (0-1 per component, total is 0-1)
   */
  calculateScore(
    decision: Decision,
    contradictionMap: Map<string, number> = new Map(),
    totalDecisions: number = 88
  ): QualityScoreBreakdown {
    // 1. Confidence component (0.4 weight)
    const confidenceScore = Math.min(1.0, Math.max(0.0, decision.confidence_score || 0.5));
    const confidenceComponent = confidenceScore * 0.4;

    // 2. Alternatives component (0.2 weight, capped at 5)
    const alternativesCount = (decision.alternatives_rejected || []).length;
    const alternativesComponent = Math.min(1.0, alternativesCount / 5) * 0.2;

    // 3. Assumptions component (0.1 weight, capped at 3)
    const assumptionsCount = this.countAssumptions(decision);
    const assumptionsComponent = Math.min(1.0, assumptionsCount / 3) * 0.1;

    // 4. Contradictions component (0.2 weight)
    // Lower contradictions = higher score
    const contradictionsCount = contradictionMap.get(decision.id) || 0;
    const maxContradictions = totalDecisions * 0.2; // Normalize by 20% of total decisions
    const contradictionsScore = Math.max(0.0, 1.0 - contradictionsCount / maxContradictions);
    const contradictionsComponent = contradictionsScore * 0.2;

    // 5. Reasoning diversity component (0.1 weight)
    const diversityScore = this.calculateReasoningDiversity(decision);
    const diversityComponent = diversityScore * 0.1;

    // Sum all components (already weighted)
    const total = Math.min(1.0, Math.max(0.0,
      confidenceComponent +
      alternativesComponent +
      assumptionsComponent +
      contradictionsComponent +
      diversityComponent
    ));

    return {
      confidence: confidenceComponent,
      alternatives: alternativesComponent,
      assumptions: assumptionsComponent,
      contradictions: contradictionsComponent,
      diversity: diversityComponent,
      total,
    };
  }

  /**
   * Count assumptions in a decision's reasoning chain
   * @param decision Decision to analyze
   * @returns Number of distinct assumptions
   */
  private countAssumptions(decision: Decision): number {
    if (!decision.reasoning_chain || !decision.reasoning_chain.assumptions) {
      return 0;
    }
    return decision.reasoning_chain.assumptions.length;
  }

  /**
   * Calculate reasoning diversity score (0-1)
   * Diversity = distinct_reasoning_types / 5
   * If decision uses all 5 types, diversity = 1.0
   * If only 1 type, diversity = 0.2
   * @param decision Decision to analyze
   * @returns Diversity score (0-1)
   */
  private calculateReasoningDiversity(decision: Decision): number {
    const reasoningTypes = new Set<string>();

    // Get type from decision level
    if (decision.reasoning_type) {
      reasoningTypes.add(decision.reasoning_type);
    }

    // Get types from reasoning chain steps
    if (decision.reasoning_chain && decision.reasoning_chain.steps) {
      decision.reasoning_chain.steps.forEach(step => {
        if (step.type) {
          reasoningTypes.add(step.type);
        }
      });
    }

    // Calculate diversity: (count of distinct types) / 5
    const distinctCount = reasoningTypes.size;
    return Math.min(1.0, distinctCount / 5);
  }

  /**
   * Generate a human-readable quality report
   * @param scoredDecisions All scored decisions
   * @returns Formatted report string
   */
  generateReport(scoredDecisions: ScoredDecision[]): string {
    // Sort by score
    const sorted = [...scoredDecisions].sort((a, b) => b.overall_score - a.overall_score);

    // Top 10
    const top10 = sorted.slice(0, 10);
    const bottom10 = sorted.slice(-10).reverse();

    let report = '';
    report += '# Decision Quality Scoring Report\n\n';
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Total Decisions Scored: ${scoredDecisions.length}\n`;
    report += `Average Quality Score: ${(
      scoredDecisions.reduce((sum, d) => sum + d.overall_score, 0) / scoredDecisions.length
    ).toFixed(3)}\n\n`;

    report += '## Score Distribution\n\n';
    report += this.generateDistribution(scoredDecisions) + '\n\n';

    report += '## Top 10 Highest Quality Decisions\n\n';
    report += top10.map((d, i) =>
      this.formatDecisionRow(i + 1, d)
    ).join('\n');

    report += '\n\n## Bottom 10 Lowest Quality Decisions (Review Candidates)\n\n';
    report += bottom10.map((d, i) =>
      this.formatDecisionRow(i + 1, d)
    ).join('\n');

    report += '\n\n## Detailed Breakdown\n\n';
    report += 'All decisions scored:\n\n';
    report += sorted.map((d, i) =>
      `${i + 1}. **${d.title}** (${d.id})\n   Score: ${d.overall_score.toFixed(3)}`
    ).join('\n');

    return report;
  }

  /**
   * Generate score distribution summary
   */
  private generateDistribution(scoredDecisions: ScoredDecision[]): string {
    const ranges = [
      { min: 0.9, label: '0.9-1.0 (Excellent)' },
      { min: 0.7, label: '0.7-0.9 (Good)' },
      { min: 0.5, label: '0.5-0.7 (Fair)' },
      { min: 0.3, label: '0.3-0.5 (Poor)' },
      { min: 0.0, label: '0.0-0.3 (Very Poor)' },
    ];

    let dist = '';
    ranges.forEach(range => {
      const count = scoredDecisions.filter(d =>
        d.overall_score >= range.min && d.overall_score < (range.min + 0.2)
      ).length;
      const pct = ((count / scoredDecisions.length) * 100).toFixed(1);
      dist += `- ${range.label}: ${count} decisions (${pct}%)\n`;
    });

    return dist;
  }

  /**
   * Format a decision row for reporting
   */
  private formatDecisionRow(rank: number, decision: ScoredDecision): string {
    return `${rank}. **${decision.title}** (${decision.id})
   Overall Score: ${decision.overall_score.toFixed(3)}
   - Confidence: ${decision.breakdown.confidence.toFixed(3)}
   - Alternatives: ${decision.breakdown.alternatives.toFixed(3)}
   - Assumptions: ${decision.breakdown.assumptions.toFixed(3)}
   - Contradictions: ${decision.breakdown.contradictions.toFixed(3)}
   - Diversity: ${decision.breakdown.diversity.toFixed(3)}`;
  }
}
