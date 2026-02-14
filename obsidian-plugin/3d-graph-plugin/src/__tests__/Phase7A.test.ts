/**
 * Phase 7A Health Dashboard Tests
 * Tests for DashboardMetricsComputer and DecisionHealthDashboard
 */

import { DashboardMetricsComputer } from '../data/DashboardMetricsComputer';
import { Decision, DecisionContradiction } from '../types/Decision';

describe('Phase 7A - Health Dashboard', () => {
  let sampleDecisions: Decision[];
  let sampleContradictions: DecisionContradiction[];
  let sampleImpacts: any[];

  beforeEach(() => {
    // Create sample decisions
    sampleDecisions = [
      {
        id: 'dec-1',
        title: 'Use TypeScript for plugin',
        chosen_option: 'TypeScript',
        rationale: 'Type safety for Obsidian plugin',
        reasoning_type: 'research',
        confidence_score: 0.9,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-01T00:00:00Z',
      },
      {
        id: 'dec-2',
        title: 'Implement SurrealDB integration',
        chosen_option: 'SurrealDB',
        rationale: 'Graph database for decision relationships',
        reasoning_type: 'pattern',
        confidence_score: 0.85,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-02T00:00:00Z',
      },
      {
        id: 'dec-3',
        title: 'Use Chart.js for visualizations',
        chosen_option: 'Chart.js',
        rationale: 'Lightweight charting library',
        reasoning_type: 'convention',
        confidence_score: 0.7,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-03T00:00:00Z',
      },
      {
        id: 'dec-4',
        title: 'Hybrid reasoning approach',
        chosen_option: 'Mix of research and intuition',
        rationale: 'Best of both worlds',
        reasoning_type: 'hybrid',
        confidence_score: 0.75,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-04T00:00:00Z',
      },
      {
        id: 'dec-5',
        title: 'Low confidence decision',
        chosen_option: 'Option A',
        rationale: 'Uncertain choice',
        reasoning_type: 'intuition',
        confidence_score: 0.3,
        reasoning_chain: {} as any,
        status: 'revisited',
        timestamp: '2026-01-05T00:00:00Z',
      },
    ];

    sampleContradictions = [
      {
        decision_id: 'dec-1',
        lesson_id: 'les-1',
        challenge_type: 'contradicts',
        severity: 'high',
        description: 'TypeScript has overhead',
      },
      {
        decision_id: 'dec-2',
        lesson_id: 'les-2',
        challenge_type: 'requires_review',
        severity: 'medium',
        description: 'Consider alternatives',
      },
    ];

    sampleImpacts = [
      {
        source_decision_id: 'dec-1',
        target_decision_id: 'dec-2',
        impact_level: 'critical',
        depth: 1,
      },
      {
        source_decision_id: 'dec-2',
        target_decision_id: 'dec-3',
        impact_level: 'significant',
        depth: 1,
      },
      {
        source_decision_id: 'dec-3',
        target_decision_id: 'dec-4',
        impact_level: 'minor',
        depth: 1,
      },
    ];
  });

  describe('Confidence Distribution', () => {
    test('should group decisions by confidence ranges', () => {
      const histogram = DashboardMetricsComputer.computeConfidenceDistribution(sampleDecisions);

      expect(histogram.labels).toEqual(['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']);
      expect(histogram.data.length).toBe(5);
      expect(histogram.data[0]).toBe(0); // 0.0-0.2: none
      expect(histogram.data[1]).toBe(1); // 0.2-0.4: dec-5 (0.3)
      expect(histogram.data[2]).toBe(0); // 0.4-0.6: none
      expect(histogram.data[3]).toBe(2); // 0.6-0.8: dec-3 (0.7), dec-4 (0.75)
      expect(histogram.data[4]).toBe(2); // 0.8-1.0: dec-1 (0.9), dec-2 (0.85)
    });

    test('should return empty data for empty decisions', () => {
      const histogram = DashboardMetricsComputer.computeConfidenceDistribution([]);

      expect(histogram.data).toEqual([0, 0, 0, 0, 0]);
    });
  });

  describe('Reasoning Type Breakdown', () => {
    test('should count reasoning types correctly', () => {
      const pie = DashboardMetricsComputer.computeReasoningBreakdown(sampleDecisions);

      expect(pie.labels).toEqual(['research', 'pattern', 'intuition', 'convention', 'hybrid']);
      expect(pie.data).toEqual([1, 1, 1, 1, 1]); // One of each
      expect(pie.backgroundColor).toHaveLength(5);
    });

    test('should handle missing reasoning_type', () => {
      const decisions = [
        {
          ...sampleDecisions[0],
          reasoning_type: undefined,
        } as any,
      ];

      const pie = DashboardMetricsComputer.computeReasoningBreakdown(decisions);

      expect(pie.data[4]).toBe(1); // Should default to hybrid
    });
  });

  describe('Contradiction Rate Trend', () => {
    test('should compute contradiction percentages over time', () => {
      const trend = DashboardMetricsComputer.computeContradictionTrend(
        sampleDecisions,
        sampleContradictions
      );

      expect(trend.labels.length).toBeGreaterThan(0);
      expect(trend.datasets.length).toBe(1);
      expect(trend.datasets[0].label).toBe('Contradiction Rate (%)');
    });

    test('should handle no contradictions', () => {
      const trend = DashboardMetricsComputer.computeContradictionTrend(sampleDecisions, []);

      expect(trend.datasets[0].data).toEqual(expect.arrayContaining([0]));
    });
  });

  describe('Quality Score Ranking', () => {
    test('should rank decisions by quality score', () => {
      const decisionsWithScores = sampleDecisions.map((d) => ({
        ...d,
        quality_score: Math.random(),
      }));

      const ranking = DashboardMetricsComputer.computeQualityRanking(decisionsWithScores);

      expect(ranking.top.length).toBeLessThanOrEqual(10);
      expect(ranking.bottom.length).toBeLessThanOrEqual(10);

      // Top should be sorted descending
      for (let i = 1; i < ranking.top.length; i++) {
        expect(ranking.top[i].qualityScore).toBeLessThanOrEqual(ranking.top[i - 1].qualityScore);
      }
    });

    test('should handle fewer than 10 decisions', () => {
      const ranking = DashboardMetricsComputer.computeQualityRanking(
        sampleDecisions.slice(0, 3)
      );

      expect(ranking.top.length).toBeLessThanOrEqual(3);
      expect(ranking.bottom.length).toBeLessThanOrEqual(3);
    });
  });

  describe('Impact Distribution', () => {
    test('should compute impact level distribution', () => {
      const donut = DashboardMetricsComputer.computeImpactDistribution(sampleImpacts);

      expect(donut.labels).toEqual(['Critical', 'Significant', 'Minor']);
      expect(donut.data[0]).toBe(1); // critical
      expect(donut.data[1]).toBe(1); // significant
      expect(donut.data[2]).toBe(1); // minor
    });

    test('should handle empty impacts', () => {
      const donut = DashboardMetricsComputer.computeImpactDistribution([]);

      expect(donut.data).toEqual([0, 0, 0]);
    });
  });

  describe('Decision Velocity', () => {
    test('should group decisions by week', () => {
      const velocity = DashboardMetricsComputer.computeDecisionVelocity(sampleDecisions);

      expect(velocity.labels.length).toBeGreaterThan(0);
      expect(velocity.datasets[0].label).toBe('Decisions Created');
      expect(velocity.datasets[0].data.length).toBe(velocity.labels.length);
    });

    test('should handle empty decisions', () => {
      const velocity = DashboardMetricsComputer.computeDecisionVelocity([]);

      expect(velocity.labels.length).toBe(0);
      expect(velocity.datasets[0].data.length).toBe(0);
    });
  });

  describe('Integration Tests', () => {
    test('should process full dashboard metrics pipeline', () => {
      const confidence = DashboardMetricsComputer.computeConfidenceDistribution(sampleDecisions);
      const reasoning = DashboardMetricsComputer.computeReasoningBreakdown(sampleDecisions);
      const contradiction = DashboardMetricsComputer.computeContradictionTrend(
        sampleDecisions,
        sampleContradictions
      );
      const quality = DashboardMetricsComputer.computeQualityRanking(sampleDecisions);
      const impact = DashboardMetricsComputer.computeImpactDistribution(sampleImpacts);
      const velocity = DashboardMetricsComputer.computeDecisionVelocity(sampleDecisions);

      // All metrics should produce valid output
      expect(confidence.data.reduce((a, b) => a + b, 0)).toBe(sampleDecisions.length);
      expect(reasoning.data.reduce((a, b) => a + b, 0)).toBe(sampleDecisions.length);
      expect(quality.top.length).toBeGreaterThan(0);
      expect(impact.data.reduce((a, b) => a + b, 0)).toBe(sampleImpacts.length);
      expect(velocity.datasets[0].data.length).toBeGreaterThan(0);
    });
  });
});
