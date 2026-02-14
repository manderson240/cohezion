#!/usr/bin/env ts-node
/**
 * Decision Quality Scorer Validation Script
 *
 * Tests the DecisionQualityScorer logic with synthetic data
 * before running against the actual 88 decisions
 */

import { DecisionQualityScorer } from '../services/DecisionQualityScorer';
import { Decision } from '../types/Decision';

function createTestDecision(id: string, title: string, overrides: any = {}): Decision {
  return {
    id,
    title,
    chosen_option: 'Option A',
    rationale: 'Test rationale',
    reasoning_type: 'hybrid',
    confidence_score: 0.7,
    reasoning_chain: {
      id: `chain-${id}`,
      decision_id: id,
      steps: [
        { sequence: 1, content: 'Step 1', type: 'research', confidence: 0.8 },
      ],
      reasoning_type: 'hybrid',
      confidence: 0.7,
      assumptions: [],
      timestamp: new Date().toISOString(),
    },
    alternatives_rejected: [],
    status: 'active',
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

function validate(condition: boolean, message: string) {
  if (condition) {
    console.log(`  ✓ ${message}`);
  } else {
    console.error(`  ✗ ${message}`);
    process.exit(1);
  }
}

async function main() {
  console.log('🧪 Decision Quality Scorer Validation\n');

  const scorer = new DecisionQualityScorer();

  // Test 1: Excellent decision scores high
  console.log('Test 1: Excellent Decision');
  const excellent = createTestDecision('test-1', 'Excellent Decision', {
    confidence_score: 0.95,
    alternatives_rejected: ['B', 'C', 'D', 'E', 'F'],
    reasoning_chain: {
      id: 'chain-1',
      decision_id: 'test-1',
      steps: [
        { sequence: 1, content: 'Research', type: 'research', confidence: 0.95 },
        { sequence: 2, content: 'Patterns', type: 'pattern', confidence: 0.9 },
        { sequence: 3, content: 'Conventions', type: 'convention', confidence: 0.85 },
        { sequence: 4, content: 'Intuition', type: 'intuition', confidence: 0.8 },
      ],
      reasoning_type: 'research',
      confidence: 0.95,
      assumptions: ['A1', 'A2', 'A3'],
      timestamp: new Date().toISOString(),
    },
  });

  const excellentScore = scorer.calculateScore(excellent, new Map(), 88);
  console.log(`  Score: ${excellentScore.total.toFixed(3)}`);
  validate(excellentScore.total > 0.75, 'Score > 0.75 for excellent decision');
  validate(excellentScore.confidence > 0.35, 'Confidence component > 0.35');
  validate(excellentScore.alternatives > 0.15, 'Alternatives component > 0.15');
  validate(excellentScore.assumptions > 0.08, 'Assumptions component > 0.08');
  validate(excellentScore.diversity > 0.12, 'Diversity component > 0.12');

  // Test 2: Poor decision scores low
  console.log('\nTest 2: Poor Decision');
  const poor = createTestDecision('test-2', 'Poor Decision', {
    confidence_score: 0.2,
    alternatives_rejected: [],
    reasoning_chain: {
      id: 'chain-2',
      decision_id: 'test-2',
      steps: [
        { sequence: 1, content: 'Quick guess', type: 'intuition', confidence: 0.2 },
      ],
      reasoning_type: 'intuition',
      confidence: 0.2,
      assumptions: [],
      timestamp: new Date().toISOString(),
    },
  });

  const poorScore = scorer.calculateScore(poor, new Map(), 88);
  console.log(`  Score: ${poorScore.total.toFixed(3)}`);
  validate(poorScore.total < 0.3, 'Score < 0.3 for poor decision');
  validate(poorScore.alternatives === 0, 'No alternatives = 0 component');

  // Test 3: Contradictions reduce score
  console.log('\nTest 3: Contradictions Impact');
  const contradiction = createTestDecision('test-3', 'Contradicted Decision', {
    confidence_score: 0.8,
  });

  const noContradictions = scorer.calculateScore(contradiction, new Map(), 88);
  const withContradictions = scorer.calculateScore(
    contradiction,
    new Map([['test-3', 10]]),
    88
  );

  console.log(`  Without contradictions: ${noContradictions.total.toFixed(3)}`);
  console.log(`  With 10 contradictions: ${withContradictions.total.toFixed(3)}`);
  validate(
    noContradictions.contradictions > withContradictions.contradictions,
    'Contradictions reduce score'
  );

  // Test 4: Score clamps to 0-1
  console.log('\nTest 4: Score Clamping');
  const extreme = createTestDecision('test-4', 'Extreme Values', {
    confidence_score: 1.5,
    alternatives_rejected: Array(10).fill('X'),
    reasoning_chain: {
      id: 'chain-4',
      decision_id: 'test-4',
      steps: Array(20).fill({
        sequence: 1,
        content: 'X',
        type: 'research' as const,
        confidence: 1.5,
      }),
      reasoning_type: 'research',
      confidence: 1.5,
      assumptions: Array(10).fill('A'),
      timestamp: new Date().toISOString(),
    },
  });

  const clampedScore = scorer.calculateScore(extreme, new Map(), 88);
  console.log(`  Score: ${clampedScore.total.toFixed(3)}`);
  validate(clampedScore.total >= 0.0, 'Score >= 0.0');
  validate(clampedScore.total <= 1.0, 'Score <= 1.0');
  validate(clampedScore.confidence <= 0.4, 'Confidence clamped to <= 0.4');
  validate(clampedScore.alternatives <= 0.2, 'Alternatives clamped to <= 0.2');

  // Test 5: Report generation
  console.log('\nTest 5: Report Generation');
  const testDecisions = [excellent, poor, contradiction];
  const scored = scorer.scoreAllDecisions(testDecisions);
  const report = scorer.generateReport(scored);

  validate(report.includes('Decision Quality Scoring Report'), 'Report has title');
  validate(report.includes('Top 10'), 'Report includes Top 10');
  validate(report.includes('Bottom 10'), 'Report includes Bottom 10');
  validate(scored.length === 3, 'Correct number of scored decisions');

  // Test 6: Reasoning diversity
  console.log('\nTest 6: Reasoning Diversity');
  const fullDiversity = createTestDecision('test-6a', 'Full Diversity', {
    reasoning_chain: {
      id: 'chain-6a',
      decision_id: 'test-6a',
      steps: [
        { sequence: 1, content: 'R', type: 'research', confidence: 0.8 },
        { sequence: 2, content: 'P', type: 'pattern', confidence: 0.8 },
        { sequence: 3, content: 'I', type: 'intuition', confidence: 0.8 },
        { sequence: 4, content: 'C', type: 'convention', confidence: 0.8 },
        { sequence: 5, content: 'H', type: 'hybrid', confidence: 0.8 },
      ],
      reasoning_type: 'hybrid',
      confidence: 0.8,
      assumptions: [],
      timestamp: new Date().toISOString(),
    },
  });

  const fullDiversityScore = scorer.calculateScore(fullDiversity, new Map(), 88);
  console.log(`  Full diversity (5/5): ${fullDiversityScore.diversity.toFixed(3)}`);
  validate(fullDiversityScore.diversity > 0.09, 'Full diversity = 0.1 weight');

  const singleType = createTestDecision('test-6b', 'Single Type', {
    reasoning_chain: {
      id: 'chain-6b',
      decision_id: 'test-6b',
      steps: [
        { sequence: 1, content: 'R', type: 'research', confidence: 0.8 },
        { sequence: 2, content: 'R2', type: 'research', confidence: 0.8 },
      ],
      reasoning_type: 'research',
      confidence: 0.8,
      assumptions: [],
      timestamp: new Date().toISOString(),
    },
  });

  const singleTypeScore = scorer.calculateScore(singleType, new Map(), 88);
  console.log(`  Single type (1/5): ${singleTypeScore.diversity.toFixed(3)}`);
  validate(singleTypeScore.diversity < fullDiversityScore.diversity, 'Single type < full diversity');

  console.log('\n✅ All validation tests passed!');
  console.log('DecisionQualityScorer is ready for production.\n');
}

main().catch(err => {
  console.error('❌ Validation failed:', err);
  process.exit(1);
});
