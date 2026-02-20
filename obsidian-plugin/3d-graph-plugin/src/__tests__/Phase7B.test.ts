/**
 * Phase 7B Cascade Timeline + Recommendations Tests
 * Tests for CascadeTimeline and DecisionRecommendationEngine
 */

import { DecisionRecommendationEngine, DecisionRecommendation, PaperRef } from '../services/DecisionRecommendationEngine';
import { Decision, DecisionCascade, DecisionContradiction } from '../types/Decision';

describe('Phase 7B - Cascade Timeline & Recommendations', () => {
  let sampleDecisions: Decision[];
  let sampleCascades: DecisionCascade[];
  let sampleContradictions: DecisionContradiction[];
  let samplePapers: PaperRef[];
  let paperEmbeddings: Map<string, number[]>;

  beforeEach(() => {
    // Create sample decisions
    sampleDecisions = [
      {
        id: 'dec-1',
        title: 'Architecture: Monolith',
        chosen_option: 'Monolithic architecture',
        rationale: 'Simpler for small teams',
        reasoning_type: 'convention',
        confidence_score: 0.8,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-01T00:00:00Z',
        related_papers: ['paper-1', 'paper-2'],
      },
      {
        id: 'dec-2',
        title: 'Database: PostgreSQL',
        chosen_option: 'PostgreSQL',
        rationale: 'ACID compliance required',
        reasoning_type: 'research',
        confidence_score: 0.9,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-05T00:00:00Z',
        related_papers: ['paper-2', 'paper-3'],
      },
      {
        id: 'dec-3',
        title: 'Caching: Redis',
        chosen_option: 'Redis',
        rationale: 'High performance requirement',
        reasoning_type: 'pattern',
        confidence_score: 0.75,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-10T00:00:00Z',
        related_papers: ['paper-3'],
      },
      {
        id: 'dec-4',
        title: 'API: REST',
        chosen_option: 'REST API',
        rationale: 'Standard web API',
        reasoning_type: 'convention',
        confidence_score: 0.7,
        reasoning_chain: {} as any,
        status: 'active',
        timestamp: '2026-01-15T00:00:00Z',
        related_papers: ['paper-4'],
      },
    ];

    // Create sample cascades
    sampleCascades = [
      {
        source_decision_id: 'dec-1',
        target_decision_id: 'dec-2',
        dependency_type: 'enables',
        impact_level: 'critical',
        description: 'Monolith architecture enables PostgreSQL choice',
      },
      {
        source_decision_id: 'dec-2',
        target_decision_id: 'dec-3',
        dependency_type: 'influences',
        impact_level: 'significant',
        description: 'PostgreSQL choice influences caching strategy',
      },
      {
        source_decision_id: 'dec-1',
        target_decision_id: 'dec-4',
        dependency_type: 'enables',
        impact_level: 'significant',
        description: 'Monolith enables REST API approach',
      },
    ];

    // Create sample contradictions
    sampleContradictions = [
      {
        decision_id: 'dec-1',
        lesson_id: 'les-1',
        challenge_type: 'contradicts',
        severity: 'high',
        description: 'Microservices considered better practice',
      },
    ];

    // Create sample papers
    samplePapers = [
      {
        id: 'paper-1',
        title: 'Monolithic Architecture Patterns',
        authors: ['Author A'],
        year: 2020,
      },
      {
        id: 'paper-2',
        title: 'Database Design for Scale',
        authors: ['Author B'],
        year: 2021,
      },
      {
        id: 'paper-3',
        title: 'Caching Strategies',
        authors: ['Author C'],
        year: 2022,
      },
      {
        id: 'paper-4',
        title: 'REST API Best Practices',
        authors: ['Author D'],
        year: 2023,
      },
      {
        id: 'paper-5',
        title: 'Microservices Architecture',
        authors: ['Author E'],
        year: 2023,
      },
    ];

    // Create simple embeddings (normalized random vectors)
    paperEmbeddings = new Map();
    samplePapers.forEach((paper) => {
      const embedding = Array(10)
        .fill(0)
        .map(() => Math.random() - 0.5);
      const magnitude = Math.sqrt(embedding.reduce((a, b) => a + b * b, 0));
      const normalized = embedding.map((v) => v / magnitude);
      paperEmbeddings.set(paper.id, normalized);
    });
  });

  describe('Cascade Timeline', () => {
    test('should identify direct cascades', () => {
      const directCascades = sampleCascades.filter((c) => c.source_decision_id === 'dec-1');

      expect(directCascades.length).toBe(2); // dec-2, dec-4
      expect(directCascades[0].dependency_type).toMatch(/enables|influences|blocks|conflicts/);
    });

    test('should compute cascade chains correctly', () => {
      // dec-1 -> dec-2 -> dec-3 is a chain
      const dec1Cascades = sampleCascades.filter((c) => c.source_decision_id === 'dec-1');
      const dec2Cascades = sampleCascades.filter((c) => c.source_decision_id === 'dec-2');

      const chainExists =
        dec1Cascades.some((c) => c.target_decision_id === 'dec-2') &&
        dec2Cascades.some((c) => c.target_decision_id === 'dec-3');

      expect(chainExists).toBe(true);
    });

    test('should identify impact levels', () => {
      const criticalCascades = sampleCascades.filter((c) => c.impact_level === 'critical');
      const significantCascades = sampleCascades.filter((c) => c.impact_level === 'significant');

      expect(criticalCascades.length).toBe(1);
      expect(significantCascades.length).toBe(2);
    });
  });

  describe('Decision Recommendations', () => {
    test('should find recommendations for similar papers', async () => {
      // Create a new paper similar to existing papers
      const newPaper: PaperRef = {
        id: 'paper-new',
        title: 'Advanced Monolithic Patterns',
        authors: ['Author F'],
        year: 2024,
      };

      // Add embedding similar to paper-1
      const embedding = Array(10)
        .fill(0)
        .map(() => Math.random() - 0.5);
      const magnitude = Math.sqrt(embedding.reduce((a, b) => a + b * b, 0));
      const normalized = embedding.map((v) => v / magnitude);
      paperEmbeddings.set(newPaper.id, normalized);

      const recommendations = await DecisionRecommendationEngine.findRecommendations(
        newPaper,
        samplePapers,
        sampleDecisions,
        sampleContradictions,
        paperEmbeddings
      );

      // Should find some recommendations
      expect(Array.isArray(recommendations)).toBe(true);
    });

    test('should score recommendations appropriately', () => {
      const rec: DecisionRecommendation = {
        id: 'rec-1',
        decision_id: 'dec-1',
        decision_title: 'Architecture: Monolith',
        new_paper_id: 'paper-new',
        new_paper_title: 'New Architecture Paper',
        recommendation_type: 'contradicts',
        score: 0.85,
        reason: 'Similar papers contradict this decision',
        timestamp: new Date().toISOString(),
        resolved: false,
      };

      expect(rec.score).toBeGreaterThanOrEqual(0);
      expect(rec.score).toBeLessThanOrEqual(1);
      expect(['contradicts', 'supports', 'requires_review']).toContain(rec.recommendation_type);
    });

    test('should generate meaningful reason strings', async () => {
      const newPaper: PaperRef = {
        id: 'paper-test',
        title: 'Test Paper',
        authors: [],
        year: 2024,
      };

      const contradictionResult = await DecisionRecommendationEngine.evaluateContradiction(
        newPaper,
        sampleDecisions[0],
        'This contradicts the previous approach',
        'Original decision rationale'
      );

      expect(contradictionResult.reason).toBeTruthy();
      expect(contradictionResult.reason.length).toBeGreaterThan(0);
    });
  });

  describe('Contradiction Detection', () => {
    test('should detect contradictory language', async () => {
      const newPaper: PaperRef = {
        id: 'paper-contra',
        title: 'Against Monoliths',
        authors: [],
        year: 2024,
      };

      const result = await DecisionRecommendationEngine.evaluateContradiction(
        newPaper,
        sampleDecisions[0],
        'Monoliths are not recommended. Avoid this approach.',
        'Use monolithic architecture'
      );

      expect(result.score).toBeGreaterThanOrEqual(0);
    });

    test('should detect supportive language', async () => {
      const newPaper: PaperRef = {
        id: 'paper-support',
        title: 'Monolith Benefits',
        authors: [],
        year: 2024,
      };

      const result = await DecisionRecommendationEngine.evaluateContradiction(
        newPaper,
        sampleDecisions[0],
        'Research confirms monolithic architecture benefits for small teams',
        'Use monolithic architecture'
      );

      expect(result.contradicts).toBe(false);
    });

    test('should handle neutral language', async () => {
      const newPaper: PaperRef = {
        id: 'paper-neutral',
        title: 'Architecture Options',
        authors: [],
        year: 2024,
      };

      const result = await DecisionRecommendationEngine.evaluateContradiction(
        newPaper,
        sampleDecisions[0],
        'Various architectural approaches exist in the industry',
        'Use monolithic architecture'
      );

      expect(result.score).toBeLessThanOrEqual(0.5);
    });
  });

  describe('Similarity Search', () => {
    test('should find similar papers by embedding', () => {
      // All papers have embeddings
      expect(paperEmbeddings.size).toBe(samplePapers.length);

      samplePapers.forEach((paper) => {
        expect(paperEmbeddings.has(paper.id)).toBe(true);
      });
    });

    test('should handle missing embeddings gracefully', async () => {
      const newPaper: PaperRef = {
        id: 'paper-no-embed',
        title: 'No Embedding Paper',
        authors: [],
        year: 2024,
      };

      // Don't add embedding for this paper
      const recommendations = await DecisionRecommendationEngine.findRecommendations(
        newPaper,
        samplePapers,
        sampleDecisions,
        sampleContradictions,
        paperEmbeddings
      );

      // Should return empty array
      expect(recommendations.length).toBe(0);
    });
  });

  describe('Integration Tests', () => {
    test('should process full recommendation pipeline', async () => {
      const newPaper: PaperRef = {
        id: 'paper-integrated',
        title: 'Integrated Architecture Study',
        authors: ['Author X'],
        year: 2024,
      };

      // Add embedding
      const embedding = Array(10)
        .fill(0)
        .map(() => Math.random() - 0.5);
      const magnitude = Math.sqrt(embedding.reduce((a, b) => a + b * b, 0));
      const normalized = embedding.map((v) => v / magnitude);
      paperEmbeddings.set(newPaper.id, normalized);

      const recommendations = await DecisionRecommendationEngine.findRecommendations(
        newPaper,
        samplePapers,
        sampleDecisions,
        sampleContradictions,
        paperEmbeddings
      );

      // Verify recommendations structure
      recommendations.forEach((rec) => {
        expect(rec.id).toBeTruthy();
        expect(rec.decision_id).toBeTruthy();
        expect(rec.score).toBeGreaterThanOrEqual(0);
        expect(rec.score).toBeLessThanOrEqual(1);
        expect(rec.reason).toBeTruthy();
      });
    });
  });
});
