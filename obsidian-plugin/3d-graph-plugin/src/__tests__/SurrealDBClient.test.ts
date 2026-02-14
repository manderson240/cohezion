import { SurrealDBClient } from '../services/SurrealDBClient';

/**
 * Unit tests for SurrealDBClient
 * Tests query methods with mock data
 */
describe('SurrealDBClient', () => {
  let client: SurrealDBClient;

  beforeEach(() => {
    // Mock fetch for tests
    global.fetch = jest.fn();
    client = new SurrealDBClient('http://localhost:8000');
  });

  afterEach(() => {
    jest.clearAllMocks();
    client.clearCache();
  });

  describe('health', () => {
    it('should return true when SurrealDB is accessible', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
      });

      const result = await client.health();
      expect(result).toBe(true);
    });

    it('should return false when SurrealDB is not accessible', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Connection failed'));

      const result = await client.health();
      expect(result).toBe(false);
    });
  });

  describe('queryReasoningForDecision', () => {
    it('should return reasoning chain for a decision', async () => {
      const mockData = [
        {
          id: 'chain-1',
          decision_id: 'test-decision',
          steps: [
            { sequence: 1, content: 'Step 1', type: 'research', confidence: 0.9 },
            { sequence: 2, content: 'Step 2', type: 'pattern', confidence: 0.8 },
          ],
          reasoning_type: 'hybrid',
          confidence: 0.85,
          assumptions: ['Assumption 1'],
          timestamp: '2026-02-14T00:00:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.queryReasoningForDecision('test-decision');

      expect(result).not.toBeNull();
      expect(result?.chains).toHaveLength(1);
      expect(result?.chains[0].steps).toHaveLength(2);
      expect(result?.high_confidence).toBe(true);
    });

    it('should use cache for repeated queries', async () => {
      const mockData = [
        {
          id: 'chain-1',
          decision_id: 'test-decision',
          steps: [],
          reasoning_type: 'research',
          confidence: 0.9,
          assumptions: [],
          timestamp: '2026-02-14T00:00:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      // First call
      await client.queryReasoningForDecision('test-decision');
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second call should use cache
      await client.queryReasoningForDecision('test-decision');
      expect(global.fetch).toHaveBeenCalledTimes(1); // Still 1, from cache
    });

    it('should return null when no reasoning found', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const result = await client.queryReasoningForDecision('nonexistent');
      expect(result).toBeNull();
    });
  });

  describe('analyzeDecisionCascades', () => {
    it('should return cascades for a decision', async () => {
      const mockData = [
        {
          target_decision_id: 'decision-2',
          dependency_type: 'enables',
          impact_level: 'critical',
          description: 'Enables downstream decision',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.analyzeDecisionCascades('decision-1', 3);

      expect(result).not.toBeNull();
      expect(result?.cascades).toHaveLength(1);
      expect(result?.critical_impact_count).toBe(1);
    });
  });

  describe('detectContradictions', () => {
    it('should return contradictions for a decision', async () => {
      const mockData = [
        {
          lesson_id: 'lesson-1',
          challenge_type: 'contradicts',
          severity: 'high',
          description: 'This lesson contradicts the decision',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.detectContradictions('decision-1');

      expect(result).not.toBeNull();
      expect(result?.contradictions).toHaveLength(1);
      expect(result?.severity_counts['high']).toBe(1);
    });
  });

  describe('caching', () => {
    it('should enforce cache size limit', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      // Add more than cacheSize items
      for (let i = 0; i < 60; i++) {
        await client.queryReasoningForDecision(`decision-${i}`);
      }

      const stats = client.getCacheStats();
      expect(stats.size).toBeLessThanOrEqual(50);
    });

    it('should return cache statistics', () => {
      const stats = client.getCacheStats();
      expect(stats).toHaveProperty('size');
      expect(stats).toHaveProperty('ttl');
      expect(stats.ttl).toBe(5 * 60 * 1000); // 5 minutes
    });
  });

  describe('queryHighConfidenceReasoning', () => {
    it('should return decisions above confidence threshold', async () => {
      const mockData = [
        {
          id: 'decision-1',
          title: 'High confidence decision',
          confidence_score: 0.9,
          reasoning_type: 'research',
          status: 'active',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.queryHighConfidenceReasoning(0.8);

      expect(result).toHaveLength(1);
      expect(result[0].confidence_score).toBeGreaterThanOrEqual(0.8);
    });
  });

  describe('queryReasoningByType', () => {
    it('should return decisions of specified reasoning type', async () => {
      const mockData = [
        {
          id: 'research-decision-1',
          title: 'Research-based decision',
          reasoning_type: 'research',
          confidence_score: 0.85,
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.queryReasoningByType('research');

      expect(result).toHaveLength(1);
      expect(result[0].reasoning_type).toBe('research');
    });
  });
});
