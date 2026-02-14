import { DecisionQualityScorer } from '../src/services/DecisionQualityScorer';
import { Decision, ReasoningChain, ReasoningStep } from '../src/types/Decision';

describe('DecisionQualityScorer', () => {
  let scorer: DecisionQualityScorer;

  beforeEach(() => {
    scorer = new DecisionQualityScorer();
  });

  describe('calculateScore', () => {
    it('should calculate perfect score (1.0) for excellent decision', () => {
      const decision: Decision = {
        id: 'test-1',
        title: 'Test Decision',
        chosen_option: 'Option A',
        rationale: 'Best choice',
        reasoning_type: 'research',
        confidence_score: 0.95,
        reasoning_chain: {
          id: 'chain-1',
          decision_id: 'test-1',
          steps: [
            { sequence: 1, content: 'Research phase', type: 'research', confidence: 0.95 },
            { sequence: 2, content: 'Pattern match', type: 'pattern', confidence: 0.9 },
            { sequence: 3, content: 'Consensus', type: 'convention', confidence: 0.85 },
          ],
          reasoning_type: 'research',
          confidence: 0.95,
          assumptions: ['Assumption 1', 'Assumption 2', 'Assumption 3'],
          timestamp: new Date().toISOString(),
        },
        alternatives_rejected: ['Option B', 'Option C', 'Option D', 'Option E'],
        status: 'active',
        timestamp: new Date().toISOString(),
      };

      const breakdown = scorer.calculateScore(decision, new Map(), 88);

      expect(breakdown.total).toBeGreaterThanOrEqual(0.8); // Should be very high
      expect(breakdown.confidence).toBeCloseTo(0.95 * 0.4, 2);
      expect(breakdown.alternatives).toBeCloseTo(0.2, 2); // 4/5 alternatives
      expect(breakdown.assumptions).toBeCloseTo(0.1, 2); // 3/3 assumptions
      expect(breakdown.diversity).toBeGreaterThan(0.18); // At least 3/5 types
    });

    it('should calculate low score for poor decision', () => {
      const decision: Decision = {
        id: 'test-2',
        title: 'Poor Decision',
        chosen_option: 'Option X',
        rationale: 'Guessed',
        reasoning_type: 'intuition',
        confidence_score: 0.2,
        reasoning_chain: {
          id: 'chain-2',
          decision_id: 'test-2',
          steps: [
            { sequence: 1, content: 'Quick decision', type: 'intuition', confidence: 0.2 },
          ],
          reasoning_type: 'intuition',
          confidence: 0.2,
          assumptions: [],
          timestamp: new Date().toISOString(),
        },
        alternatives_rejected: [],
        status: 'active',
        timestamp: new Date().toISOString(),
      };

      const breakdown = scorer.calculateScore(decision, new Map(), 88);

      expect(breakdown.total).toBeLessThan(0.3);
      expect(breakdown.confidence).toBeCloseTo(0.2 * 0.4, 2);
      expect(breakdown.alternatives).toBe(0);
      expect(breakdown.assumptions).toBe(0);
      expect(breakdown.diversity).toBeCloseTo(0.2 * 0.1, 2); // Only 1 type
    });

    it('should penalize decisions with contradictions', () => {
      const decision: Decision = {
        id: 'test-3',
        title: 'Contradicted Decision',
        chosen_option: 'Option Y',
        rationale: 'Chosen',
        reasoning_type: 'hybrid',
        confidence_score: 0.7,
        reasoning_chain: {
          id: 'chain-3',
          decision_id: 'test-3',
          steps: [
            { sequence: 1, content: 'Step 1', type: 'research', confidence: 0.7 },
          ],
          reasoning_type: 'hybrid',
          confidence: 0.7,
          assumptions: [],
          timestamp: new Date().toISOString(),
        },
        alternatives_rejected: ['Option Z'],
        status: 'active',
        timestamp: new Date().toISOString(),
      };

      const contradictions = new Map([
        ['test-3', 5], // 5 contradictions
      ]);

      const breakdown = scorer.calculateScore(decision, contradictions, 88);

      // Contradictions component should be reduced
      expect(breakdown.contradictions).toBeLessThan(0.2);
      expect(breakdown.total).toBeLessThan(0.6); // Overall score reduced by contradictions
    });

    it('should handle edge cases and clamp values', () => {
      const decision: Decision = {
        id: 'test-4',
        title: 'Edge Case Decision',
        chosen_option: 'Option',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 1.5, // Should be clamped to 1.0
        reasoning_chain: {
          id: 'chain-4',
          decision_id: 'test-4',
          steps: [],
          reasoning_type: 'hybrid',
          confidence: 1.5,
          assumptions: Array(10).fill('Assumption'), // Should cap at 3
          timestamp: new Date().toISOString(),
        },
        alternatives_rejected: Array(10).fill('Option'), // Should cap at 5
        status: 'active',
        timestamp: new Date().toISOString(),
      };

      const breakdown = scorer.calculateScore(decision, new Map(), 88);

      expect(breakdown.confidence).toBeCloseTo(0.4, 2); // Clamped to 1.0 * 0.4
      expect(breakdown.alternatives).toBeCloseTo(0.2, 2); // Clamped to 5/5
      expect(breakdown.assumptions).toBeCloseTo(0.1, 2); // Clamped to 3/3
      expect(breakdown.total).toBeLessThanOrEqual(1.0); // Final score clamped
    });
  });

  describe('scoreAllDecisions', () => {
    it('should score multiple decisions', () => {
      const decisions: Decision[] = [
        {
          id: 'dec-1',
          title: 'Decision 1',
          chosen_option: 'A',
          rationale: 'Best',
          reasoning_type: 'research',
          confidence_score: 0.9,
          reasoning_chain: {
            id: 'chain-1',
            decision_id: 'dec-1',
            steps: [],
            reasoning_type: 'research',
            confidence: 0.9,
            assumptions: [],
            timestamp: new Date().toISOString(),
          },
          alternatives_rejected: [],
          status: 'active',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'dec-2',
          title: 'Decision 2',
          chosen_option: 'B',
          rationale: 'Good',
          reasoning_type: 'hybrid',
          confidence_score: 0.5,
          reasoning_chain: {
            id: 'chain-2',
            decision_id: 'dec-2',
            steps: [],
            reasoning_type: 'hybrid',
            confidence: 0.5,
            assumptions: [],
            timestamp: new Date().toISOString(),
          },
          alternatives_rejected: [],
          status: 'active',
          timestamp: new Date().toISOString(),
        },
      ];

      const scored = scorer.scoreAllDecisions(decisions);

      expect(scored).toHaveLength(2);
      expect(scored[0].overall_score).toBeGreaterThan(scored[1].overall_score);
    });
  });

  describe('generateReport', () => {
    it('should generate valid markdown report', () => {
      const scoredDecisions = [
        {
          id: 'dec-1',
          title: 'High Quality',
          overall_score: 0.85,
          breakdown: {
            confidence: 0.36,
            alternatives: 0.18,
            assumptions: 0.08,
            contradictions: 0.18,
            diversity: 0.08,
            total: 0.85,
          },
        },
        {
          id: 'dec-2',
          title: 'Low Quality',
          overall_score: 0.25,
          breakdown: {
            confidence: 0.1,
            alternatives: 0,
            assumptions: 0,
            contradictions: 0.12,
            diversity: 0.03,
            total: 0.25,
          },
        },
      ];

      const report = scorer.generateReport(scoredDecisions);

      expect(report).toContain('Decision Quality Scoring Report');
      expect(report).toContain('High Quality');
      expect(report).toContain('Low Quality');
      expect(report).toContain('Top 10');
      expect(report).toContain('Bottom 10');
      expect(report).toContain('0.85');
      expect(report).toContain('0.25');
    });
  });
});
