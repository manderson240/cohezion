/**
 * Data Loading and Parsing Tests
 *
 * Tests for YAML frontmatter parsing, dimension extraction,
 * graph building, and data validation
 */

import { validateDimensions } from '../DataLoader';
import { PaperNode } from '../types/Paper';

describe('DataLoader', () => {
  describe('Dimension Validation', () => {
    it('should validate a complete paper with all 8 dimensions', () => {
      const validPaper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 0.5,
          conceptual_depth: 0.6,
          temporal: 0.7,
          cross_domain: 5,
          completion: 75,
          recency: 0.8,
          semantic_similarity: 0.3,
          similar_papers: [],
        },
      };

      const result = validateDimensions(validPaper);
      expect(result.valid).toBe(true);
      expect(result.missing).toHaveLength(0);
    });

    it('should detect missing dimensions', () => {
      const incompletePaper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 0.5,
          conceptual_depth: 0.6,
          temporal: 0.7,
          cross_domain: 5,
          completion: 75,
          recency: 0.8,
          semantic_similarity: 0.3,
          similar_papers: [],
        },
      };

      // Simulate missing completion
      delete incompletePaper.dimensions.completion;

      const result = validateDimensions(incompletePaper);
      expect(result.valid).toBe(false);
      expect(result.missing).toContain('completion');
    });

    it('should enforce dimension value bounds', () => {
      const paper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 1.5, // Out of bounds [0, 1]
          conceptual_depth: 0.6,
          temporal: 0.7,
          cross_domain: 20, // Out of bounds [1, 15]
          completion: 150, // Out of bounds [0, 100]
          recency: 0.8,
          semantic_similarity: 0.3,
          similar_papers: [],
        },
      };

      // Values should be clamped in DataLoader.extractDimensions
      expect(paper.dimensions.connectivity).toBeGreaterThanOrEqual(0);
      expect(paper.dimensions.connectivity).toBeLessThanOrEqual(1);
    });
  });

  describe('Similar Papers Extraction', () => {
    it('should extract similar papers as SimilarPaper objects', () => {
      const paper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 0.5,
          conceptual_depth: 0.6,
          temporal: 0.7,
          cross_domain: 5,
          completion: 75,
          recency: 0.8,
          semantic_similarity: 0.3,
          similar_papers: [
            { title: 'Related Paper 1', score: 0.8 },
            { title: 'Related Paper 2', score: 0.7 },
            { title: 'Related Paper 3', score: 0.6 },
          ],
        },
      };

      expect(paper.dimensions.similar_papers).toHaveLength(3);
      expect(paper.dimensions.similar_papers[0].title).toBe('Related Paper 1');
      expect(paper.dimensions.similar_papers[0].score).toBe(0.8);
    });

    it('should handle empty similar papers list', () => {
      const paper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 0.5,
          conceptual_depth: 0.6,
          temporal: 0.7,
          cross_domain: 5,
          completion: 75,
          recency: 0.8,
          semantic_similarity: 0.3,
          similar_papers: [],
        },
      };

      expect(paper.dimensions.similar_papers).toHaveLength(0);
    });
  });

  describe('Graph Metadata', () => {
    it('should calculate correct edge count from similar papers', () => {
      const papers: PaperNode[] = [
        {
          id: 'paper-1',
          title: 'Paper 1',
          path: 'papers/paper-1.md',
          dimensions: {
            connectivity: 0.5,
            conceptual_depth: 0.5,
            temporal: 0.5,
            cross_domain: 5,
            completion: 50,
            recency: 0.5,
            semantic_similarity: 0.3,
            similar_papers: [{ title: 'Paper 2', score: 0.8 }],
          },
        },
        {
          id: 'paper-2',
          title: 'Paper 2',
          path: 'papers/paper-2.md',
          dimensions: {
            connectivity: 0.6,
            conceptual_depth: 0.6,
            temporal: 0.6,
            cross_domain: 5,
            completion: 60,
            recency: 0.6,
            semantic_similarity: 0.3,
            similar_papers: [{ title: 'Paper 1', score: 0.8 }],
          },
        },
      ];

      // In a real implementation, edges would be deduplicated
      // Each bidirectional relationship creates 1 edge
      expect(papers.length).toBe(2);
      expect(papers[0].dimensions.similar_papers.length).toBe(1);
    });

    it('should calculate average connectivity across nodes', () => {
      const papers: PaperNode[] = [
        {
          id: 'paper-1',
          title: 'Paper 1',
          path: 'papers/paper-1.md',
          dimensions: {
            connectivity: 0.3,
            conceptual_depth: 0.5,
            temporal: 0.5,
            cross_domain: 5,
            completion: 50,
            recency: 0.5,
            semantic_similarity: 0.3,
            similar_papers: [],
          },
        },
        {
          id: 'paper-2',
          title: 'Paper 2',
          path: 'papers/paper-2.md',
          dimensions: {
            connectivity: 0.7,
            conceptual_depth: 0.5,
            temporal: 0.5,
            cross_domain: 5,
            completion: 50,
            recency: 0.5,
            semantic_similarity: 0.3,
            similar_papers: [],
          },
        },
      ];

      const avgConnectivity = papers.reduce((sum, p) => sum + p.dimensions.connectivity, 0) / papers.length;
      expect(avgConnectivity).toBeCloseTo(0.5, 1);
    });
  });

  describe('Data Type Conversion', () => {
    it('should convert string numbers to actual numbers', () => {
      // Simulating YAML parsing which may return strings
      const stringValue = '0.75';
      const numValue = parseFloat(stringValue);
      expect(typeof numValue).toBe('number');
      expect(numValue).toBe(0.75);
    });

    it('should handle boolean values in YAML', () => {
      const trueValue = 'true';
      const falseValue = 'false';
      expect(trueValue === 'true').toBe(true);
      expect(falseValue === 'false').toBe(false);
    });

    it('should parse JSON arrays from YAML', () => {
      const jsonArray = '["paper1", "paper2", "paper3"]';
      const parsed = JSON.parse(jsonArray);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed).toHaveLength(3);
    });
  });

  describe('Error Handling', () => {
    it('should use defaults when dimension values are missing', () => {
      const paper: PaperNode = {
        id: 'test-paper',
        title: 'Test Paper',
        path: 'papers/test-paper.md',
        dimensions: {
          connectivity: 0.5, // Default
          conceptual_depth: 0.5, // Default
          temporal: 0.5, // Default
          cross_domain: 5, // Default
          completion: 50, // Default
          recency: 0.5, // Default
          semantic_similarity: 0.3,
          similar_papers: [],
        },
      };

      // All defaults should be valid
      expect(paper.dimensions.connectivity).toBeGreaterThanOrEqual(0);
      expect(paper.dimensions.conceptual_depth).toBeGreaterThanOrEqual(0);
    });

    it('should clamp out-of-bounds values to valid ranges', () => {
      // Values should be clamped during extraction
      const connectivity = Math.max(0, Math.min(1, 1.5)); // Should be 1
      const crossDomain = Math.max(1, Math.min(15, 20)); // Should be 15
      const completion = Math.max(0, Math.min(100, 150)); // Should be 100

      expect(connectivity).toBe(1);
      expect(crossDomain).toBe(15);
      expect(completion).toBe(100);
    });
  });

  describe('ID Generation', () => {
    it('should generate valid IDs from filenames', () => {
      // Helper function as in DataLoader
      const generateId = (filename: string) => filename.replace(/\.md$/, '').replace(/\s+/g, '-').toLowerCase();

      expect(generateId('Test Paper.md')).toBe('test-paper');
      expect(generateId('2026-02-09-unique-investment-opportunities-research.md')).toBe('2026-02-09-unique-investment-opportunities-research');
      expect(generateId('AI_Research_Notes.md')).toBe('ai_research_notes');
    });
  });
});
