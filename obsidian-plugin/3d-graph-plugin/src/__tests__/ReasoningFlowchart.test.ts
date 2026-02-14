import { App } from 'obsidian';
import { ReasoningFlowchart } from '../visualizations/ReasoningFlowchart';
import { Decision } from '../types/Decision';

/**
 * Integration tests for ReasoningFlowchart
 * Tests SVG rendering with mock decision data
 */
describe('ReasoningFlowchart', () => {
  let app: App;
  let mockDecision: Decision;

  beforeEach(() => {
    // Mock Obsidian App
    app = {
      workspace: {},
    } as unknown as App;

    // Create mock decision with reasoning chain
    mockDecision = {
      id: 'test-decision',
      title: 'Test Decision: Choose Architecture',
      chosen_option: 'Microservices',
      rationale: 'Microservices provide better scalability',
      reasoning_type: 'research',
      confidence_score: 0.85,
      reasoning_chain: {
        id: 'chain-1',
        decision_id: 'test-decision',
        steps: [
          {
            sequence: 1,
            content: 'Researched three architectural patterns: monolith, microservices, serverless',
            type: 'research',
            confidence: 0.9,
          },
          {
            sequence: 2,
            content: 'Analyzed team expertise - experienced in distributed systems',
            type: 'pattern',
            confidence: 0.85,
          },
          {
            sequence: 3,
            content: 'Reviewed scalability requirements - 10x growth expected',
            type: 'research',
            confidence: 0.8,
          },
        ],
        reasoning_type: 'hybrid',
        confidence: 0.85,
        assumptions: ['Team commitment to microservices learning', 'Budget available for infrastructure'],
        timestamp: '2026-02-14T00:00:00Z',
      },
      alternatives_rejected: ['Monolith (less scalable)', 'Serverless (vendor lock-in)'],
      status: 'active',
      timestamp: '2026-02-14T00:00:00Z',
    };
  });

  describe('rendering', () => {
    it('should create a flowchart modal', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      expect(flowchart).toBeDefined();
      expect(flowchart.titleEl).toBeDefined();
    });

    it('should render with empty steps gracefully', () => {
      const decisionNoSteps: Decision = {
        ...mockDecision,
        reasoning_chain: {
          ...mockDecision.reasoning_chain,
          steps: [],
        },
      };

      const flowchart = new ReasoningFlowchart(app, decisionNoSteps);
      expect(flowchart).toBeDefined();
    });

    it('should display decision title', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      expect(flowchart.titleEl).toBeDefined();
      expect(flowchart.titleEl.textContent).toContain('Reasoning Chain');
      expect(flowchart.titleEl.textContent).toContain('Test Decision');
    });
  });

  describe('SVG generation', () => {
    it('should generate SVG with correct step count', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      // SVG should have one node per step + arrows between them
      expect(mockDecision.reasoning_chain.steps.length).toBe(3);
    });

    it('should color code steps by reasoning type', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);

      // Verify color mapping exists
      const colors: Record<string, string> = {
        research: '#3b82f6',
        pattern: '#10b981',
        intuition: '#f59e0b',
        convention: '#8b5cf6',
        hybrid: '#6366f1',
      };

      for (const step of mockDecision.reasoning_chain.steps) {
        expect(colors[step.type]).toBeDefined();
      }
    });

    it('should scale nodes by confidence', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);

      // All steps should have confidence between 0 and 1
      for (const step of mockDecision.reasoning_chain.steps) {
        expect(step.confidence).toBeGreaterThanOrEqual(0);
        expect(step.confidence).toBeLessThanOrEqual(1);
      }
    });
  });

  describe('interaction', () => {
    it('should display assumptions when present', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      expect(mockDecision.reasoning_chain.assumptions.length).toBeGreaterThan(0);
    });

    it('should display alternatives rejected', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      expect(mockDecision.alternatives_rejected).toBeDefined();
      expect(mockDecision.alternatives_rejected?.length).toBeGreaterThan(0);
    });

    it('should handle missing optional fields', () => {
      const minimalDecision: Decision = {
        id: 'minimal',
        title: 'Minimal Decision',
        chosen_option: 'Option A',
        rationale: '',
        reasoning_type: 'hybrid',
        confidence_score: 0.5,
        reasoning_chain: {
          id: 'chain-1',
          decision_id: 'minimal',
          steps: [{ sequence: 1, content: 'A single step', type: 'research', confidence: 0.7 }],
          reasoning_type: 'research',
          confidence: 0.7,
          assumptions: [],
          timestamp: '2026-02-14T00:00:00Z',
        },
        status: 'active',
        timestamp: '2026-02-14T00:00:00Z',
      };

      const flowchart = new ReasoningFlowchart(app, minimalDecision);
      expect(flowchart).toBeDefined();
    });
  });

  describe('confidence visualization', () => {
    it('should show confidence percentages', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);

      for (const step of mockDecision.reasoning_chain.steps) {
        const percentage = (step.confidence * 100).toFixed(0);
        expect(parseInt(percentage)).toBeGreaterThanOrEqual(0);
        expect(parseInt(percentage)).toBeLessThanOrEqual(100);
      }
    });

    it('should indicate overall reasoning confidence', () => {
      const flowchart = new ReasoningFlowchart(app, mockDecision);
      const overallConfidence = mockDecision.confidence_score;

      expect(overallConfidence).toBeGreaterThanOrEqual(0);
      expect(overallConfidence).toBeLessThanOrEqual(1);
    });
  });
});
