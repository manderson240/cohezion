import {
  Decision,
  ReasoningChain,
  DecisionCascade,
  DecisionContradiction,
  ReasoningQueryResult,
  CascadeQueryResult,
  ContradictionQueryResult,
} from '../types/Decision';
import { Notice } from 'obsidian';

/**
 * SurrealDB Client for Phase 4 Decision Analysis
 *
 * Connects to SurrealDB via HTTP/REST API to query decision reasoning chains,
 * cascades, contradictions, and metadata.
 *
 * Uses LRU caching to minimize redundant queries and improve responsiveness.
 *
 * @example
 * const client = new SurrealDBClient('http://localhost:8000');
 * const reasoning = await client.queryReasoningForDecision('phase-2-track-a-complete');
 * console.log(reasoning.chains);
 */
export class SurrealDBClient {
  private baseUrl: string;
  private readonly cacheSize = 50;
  private queryCache: Map<string, { result: any; timestamp: number }> = new Map();
  private readonly cacheTTL = 5 * 60 * 1000; // 5 minutes

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Health check - verify SurrealDB is accessible
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch (error) {
      console.error('SurrealDB health check failed:', error);
      return false;
    }
  }

  /**
   * Execute a SurrealDB query
   * @param query SurrealQL query string
   * @returns Query result
   */
  private async executeQuery(query: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/sql`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Query failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('SurrealDB query error:', error);
      throw error;
    }
  }

  /**
   * Get or execute cached query
   */
  private async getCachedOrQuery(cacheKey: string, queryFn: () => Promise<any>): Promise<any> {
    // Check cache
    const cached = this.queryCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      console.debug(`Cache hit for ${cacheKey}`);
      return cached.result;
    }

    // Execute query
    const result = await queryFn();

    // Store in cache
    this.queryCache.set(cacheKey, { result, timestamp: Date.now() });

    // Enforce cache size limit (LRU)
    if (this.queryCache.size > this.cacheSize) {
      const firstKey = this.queryCache.keys().next().value;
      this.queryCache.delete(firstKey);
    }

    return result;
  }

  /**
   * Query reasoning chain for a decision
   * @param decisionId ID of the decision
   * @returns Reasoning chain and metadata
   */
  async queryReasoningForDecision(decisionId: string): Promise<ReasoningQueryResult | null> {
    const cacheKey = `reasoning:${decisionId}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        const query = `
          SELECT * FROM agent_reasoning
          WHERE decision_id = '${decisionId}'
          ORDER BY step_number ASC
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result) || result.length === 0) {
          console.warn(`No reasoning found for decision ${decisionId}`);
          return null;
        }

        // Transform result into ReasoningQueryResult
        const chains: ReasoningChain[] = result.map((row: any) => ({
          id: row.id || `chain-${decisionId}`,
          decision_id: decisionId,
          steps: row.steps || [],
          reasoning_type: row.reasoning_type || 'hybrid',
          confidence: row.confidence || 0.5,
          assumptions: row.assumptions || [],
          timestamp: row.timestamp || new Date().toISOString(),
        }));

        return {
          decision: { id: decisionId } as Decision,
          chains,
          high_confidence: chains.some(c => c.confidence > 0.8),
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        console.error(`Failed to query reasoning for ${decisionId}:`, error);
        return null;
      }
    });
  }

  /**
   * Analyze decision cascades (downstream impacts)
   * @param decisionId Source decision ID
   * @param depth Maximum cascade depth (1-5)
   * @returns Cascade analysis
   */
  async analyzeDecisionCascades(
    decisionId: string,
    depth: number = 3
  ): Promise<CascadeQueryResult | null> {
    const cacheKey = `cascades:${decisionId}:${depth}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        // Query direct cascades
        const query = `
          SELECT * FROM decision_cascades
          WHERE source_decision_id = '${decisionId}'
          LIMIT 100
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result)) {
          return null;
        }

        const cascades: DecisionCascade[] = result.map((row: any) => ({
          source_decision_id: decisionId,
          target_decision_id: row.target_decision_id,
          dependency_type: row.dependency_type,
          impact_level: row.impact_level,
          description: row.description,
        }));

        const criticalCount = cascades.filter(c => c.impact_level === 'critical').length;

        return {
          source_decision: { id: decisionId } as Decision,
          cascades,
          total_impacted: cascades.length,
          critical_impact_count: criticalCount,
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        console.error(`Failed to query cascades for ${decisionId}:`, error);
        return null;
      }
    });
  }

  /**
   * Detect contradictions between decision and lessons
   * @param decisionId Decision ID to check
   * @returns Contradictions found
   */
  async detectContradictions(decisionId: string): Promise<ContradictionQueryResult | null> {
    const cacheKey = `contradictions:${decisionId}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        const query = `
          SELECT * FROM decision_contradictions
          WHERE decision_id = '${decisionId}'
          ORDER BY severity DESC
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result)) {
          return null;
        }

        const contradictions: DecisionContradiction[] = result.map((row: any) => ({
          decision_id: decisionId,
          lesson_id: row.lesson_id,
          challenge_type: row.challenge_type,
          severity: row.severity,
          description: row.description,
        }));

        // Count by severity
        const severityCounts: Record<string, number> = {};
        contradictions.forEach(c => {
          severityCounts[c.severity] = (severityCounts[c.severity] || 0) + 1;
        });

        return {
          decision: { id: decisionId } as Decision,
          contradictions,
          severity_counts: severityCounts,
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        console.error(`Failed to query contradictions for ${decisionId}:`, error);
        return null;
      }
    });
  }

  /**
   * Fetch decision metadata
   * @param decisionId Decision ID
   * @returns Full decision details
   */
  async fetchDecisionMetadata(decisionId: string): Promise<Decision | null> {
    const cacheKey = `decision:${decisionId}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        const query = `
          SELECT * FROM decisions
          WHERE id = '${decisionId}'
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result) || result.length === 0) {
          return null;
        }

        const row = result[0];
        return {
          id: decisionId,
          title: row.title || '',
          chosen_option: row.chosen_option || '',
          rationale: row.rationale || '',
          reasoning_type: row.reasoning_type || 'hybrid',
          confidence_score: row.confidence_score || 0.5,
          reasoning_chain: {} as ReasoningChain,
          alternatives_rejected: row.alternatives_rejected || [],
          related_papers: row.related_papers || [],
          status: row.status || 'active',
          timestamp: row.timestamp || new Date().toISOString(),
          vault_path: row.vault_path,
        };
      } catch (error) {
        console.error(`Failed to fetch metadata for ${decisionId}:`, error);
        return null;
      }
    });
  }

  /**
   * Query high-confidence reasoning (>threshold)
   * @param threshold Minimum confidence (0.0-1.0)
   * @returns List of high-confidence decisions
   */
  async queryHighConfidenceReasoning(threshold: number = 0.8): Promise<Decision[]> {
    const cacheKey = `high-confidence:${threshold}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        const query = `
          SELECT * FROM decisions
          WHERE confidence_score >= ${threshold}
          ORDER BY confidence_score DESC
          LIMIT 50
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result)) {
          return [];
        }

        return result.map((row: any) => ({
          id: row.id,
          title: row.title || '',
          chosen_option: row.chosen_option || '',
          rationale: row.rationale || '',
          reasoning_type: row.reasoning_type || 'hybrid',
          confidence_score: row.confidence_score || 0.5,
          reasoning_chain: {} as ReasoningChain,
          status: row.status || 'active',
          timestamp: row.timestamp || new Date().toISOString(),
        }));
      } catch (error) {
        console.error('Failed to query high-confidence reasoning:', error);
        return [];
      }
    });
  }

  /**
   * Query decisions by reasoning type
   * @param type Reasoning type filter
   * @returns Matching decisions
   */
  async queryReasoningByType(
    type: 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid'
  ): Promise<Decision[]> {
    const cacheKey = `by-type:${type}`;

    return this.getCachedOrQuery(cacheKey, async () => {
      try {
        const query = `
          SELECT * FROM decisions
          WHERE reasoning_type = '${type}'
          ORDER BY confidence_score DESC
          LIMIT 50
        `;

        const result = await this.executeQuery(query);

        if (!result || !Array.isArray(result)) {
          return [];
        }

        return result.map((row: any) => ({
          id: row.id,
          title: row.title || '',
          chosen_option: row.chosen_option || '',
          rationale: row.rationale || '',
          reasoning_type: row.reasoning_type || 'hybrid',
          confidence_score: row.confidence_score || 0.5,
          reasoning_chain: {} as ReasoningChain,
          status: row.status || 'active',
          timestamp: row.timestamp || new Date().toISOString(),
        }));
      } catch (error) {
        console.error(`Failed to query by type ${type}:`, error);
        return [];
      }
    });
  }

  /**
   * Clear cache (useful after database updates)
   */
  clearCache(): void {
    this.queryCache.clear();
    console.log('SurrealDB query cache cleared');
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; ttl: number } {
    return {
      size: this.queryCache.size,
      ttl: this.cacheTTL,
    };
  }
}
