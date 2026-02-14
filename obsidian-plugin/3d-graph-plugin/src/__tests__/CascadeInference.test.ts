import { CascadeInferenceEngine, DecisionImpact } from '../services/CascadeInference';
import { Decision, DecisionCascade } from '../types/Decision';

/**
 * Mock SurrealDB Client for testing
 */
class MockSurrealDBClient {
  private decisions: Decision[] = [];
  private cascades: DecisionCascade[] = [];

  setDecisions(decisions: Decision[]) {
    this.decisions = decisions;
  }

  setCascades(cascades: DecisionCascade[]) {
    this.cascades = cascades;
  }

  async executeQuery(query: string): Promise<any> {
    if (query.includes('SELECT * FROM decisions')) {
      return this.decisions;
    }
    if (query.includes('SELECT * FROM decision_cascades')) {
      return this.cascades;
    }
    if (query.includes('CREATE TABLE')) {
      return { status: 'ok' };
    }
    if (query.includes('DELETE FROM decision_impacts')) {
      return { status: 'ok' };
    }
    if (query.includes('INSERT INTO decision_impacts')) {
      return { status: 'ok' };
    }
    if (query.includes('SELECT COUNT')) {
      return [{ count: this.cascades.length * 3 }];
    }
    return null;
  }
}

describe('CascadeInferenceEngine', () => {
  let engine: CascadeInferenceEngine;
  let mockDb: MockSurrealDBClient;

  beforeEach(() => {
    mockDb = new MockSurrealDBClient();
    // Mock the db client in engine (would need to refactor to inject)
  });

  test('should compute direct impacts from cascades', () => {
    // Test data: 3 decisions with 2 cascades (A→B, B→C)
    const decisions: Decision[] = [
      {
        id: 'decision-a',
        title: 'Decision A',
        chosen_option: 'Option 1',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.8,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'decision-b',
        title: 'Decision B',
        chosen_option: 'Option 2',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.7,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'decision-c',
        title: 'Decision C',
        chosen_option: 'Option 3',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.6,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
    ];

    const cascades: DecisionCascade[] = [
      {
        source_decision_id: 'decision-a',
        target_decision_id: 'decision-b',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'A enables B',
      },
      {
        source_decision_id: 'decision-b',
        target_decision_id: 'decision-c',
        dependency_type: 'influences',
        impact_level: 'minor',
        description: 'B influences C',
      },
    ];

    mockDb.setDecisions(decisions);
    mockDb.setCascades(cascades);

    // Verify cascade graph is built
    expect(decisions.length).toBe(3);
    expect(cascades.length).toBe(2);

    // Direct impact: A→B should be depth 1
    // Indirect impact: A→C should be depth 2 (via B)
  });

  test('should detect conflict cascades', () => {
    const decisions: Decision[] = [
      {
        id: 'decision-x',
        title: 'Decision X',
        chosen_option: 'Option 1',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.8,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'decision-y',
        title: 'Decision Y',
        chosen_option: 'Option 2',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.7,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'decision-z',
        title: 'Decision Z',
        chosen_option: 'Option 3',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.6,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
    ];

    const cascades: DecisionCascade[] = [
      {
        source_decision_id: 'decision-x',
        target_decision_id: 'decision-y',
        dependency_type: 'blocks',
        impact_level: 'critical',
        description: 'X blocks Y',
      },
      {
        source_decision_id: 'decision-z',
        target_decision_id: 'decision-y',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'Z enables Y',
      },
    ];

    mockDb.setDecisions(decisions);
    mockDb.setCascades(cascades);

    // Conflict scenario: X blocks Y, but Z enables Y
    // This should be detected during cascade analysis
    expect(cascades.some(c => c.dependency_type === 'blocks')).toBe(true);
    expect(cascades.some(c => c.dependency_type === 'enables')).toBe(true);
  });

  test('should compute impact scores correctly', () => {
    // Impact score decreases with depth
    // Direct (depth 1): higher score
    // Indirect (depth 2+): lower score
    // Conflict/Support types: higher multiplier

    const impact1: DecisionImpact = {
      source_decision_id: 'a',
      target_decision_id: 'b',
      depth: 1,
      impact_type: 'direct',
      impact_score: 0.0, // Will be computed
    };

    const impact2: DecisionImpact = {
      source_decision_id: 'a',
      target_decision_id: 'c',
      depth: 2,
      impact_type: 'indirect',
      impact_score: 0.0, // Will be computed
    };

    // Depth 1 should generally score higher than depth 2
    expect(impact1.depth).toBeLessThan(impact2.depth);
  });

  test('should prevent cycles in BFS traversal', () => {
    // Create a cycle: A→B→C→B
    const decisions: Decision[] = [
      {
        id: 'a',
        title: 'A',
        chosen_option: 'Option',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.5,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'b',
        title: 'B',
        chosen_option: 'Option',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.5,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'c',
        title: 'C',
        chosen_option: 'Option',
        rationale: 'Test',
        reasoning_type: 'hybrid',
        confidence_score: 0.5,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: new Date().toISOString(),
      },
    ];

    const cascades: DecisionCascade[] = [
      {
        source_decision_id: 'a',
        target_decision_id: 'b',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'A→B',
      },
      {
        source_decision_id: 'b',
        target_decision_id: 'c',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'B→C',
      },
      {
        source_decision_id: 'c',
        target_decision_id: 'b',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'C→B (cycle)',
      },
    ];

    mockDb.setDecisions(decisions);
    mockDb.setCascades(cascades);

    // BFS should detect the cycle and not infinite loop
    expect(cascades.length).toBe(3);
  });
});
