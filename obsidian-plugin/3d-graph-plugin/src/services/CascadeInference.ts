import { Decision, DecisionCascade } from '../types/Decision';
import { SurrealDBClient } from './SurrealDBClient';

/**
 * Impact information for a decision-to-decision relationship
 */
export interface DecisionImpact {
  source_decision_id: string;
  target_decision_id: string;
  depth: number; // 1-5: distance in cascade graph
  impact_type: 'direct' | 'indirect' | 'conflict' | 'support';
  impact_score: number; // 0-1: strength of relationship
}

/**
 * BFS traversal queue item
 */
interface QueueItem {
  decision_id: string;
  depth: number;
  path: string[]; // Track path for cycle detection
  impact_type: 'direct' | 'indirect' | 'conflict' | 'support';
}

/**
 * Cascade Inference Engine
 *
 * Computes 2nd/3rd order effects of decisions on each other using BFS traversal.
 * Discovers indirect impacts, conflict chains, and support cascades.
 *
 * Algorithm:
 * 1. Load all decisions and cascades from SurrealDB
 * 2. For each decision, run BFS to depth=5
 * 3. Track impact type: direct, indirect, conflict, support
 * 4. Compute impact_score based on path strength and depth
 * 5. Store results in decision_impacts table
 *
 * @example
 * const engine = new CascadeInferenceEngine();
 * const impacts = await engine.computeImpacts();
 * console.log(`Computed ${impacts.length} impact relationships`);
 */
export class CascadeInferenceEngine {
  private db: SurrealDBClient;
  private maxDepth = 5;
  private decisionMap: Map<string, Decision> = new Map();
  private cascadeMap: Map<string, DecisionCascade[]> = new Map();

  constructor(dbUrl: string = 'http://localhost:8000') {
    this.db = new SurrealDBClient(dbUrl);
  }

  /**
   * Main entry point: compute all cascade impacts
   * @returns List of impact relationships computed
   */
  async computeImpacts(): Promise<DecisionImpact[]> {
    console.log('Starting cascade impact computation...');
    const startTime = Date.now();

    try {
      // Load all decisions and cascades
      console.log('Loading decisions and cascades from SurrealDB...');
      await this.loadDecisionsAndCascades();

      const decisionIds = Array.from(this.decisionMap.keys());
      console.log(`Loaded ${decisionIds.length} decisions and ${this.cascadeMap.size} cascade edges`);

      // Compute impacts for each decision
      const allImpacts: DecisionImpact[] = [];
      for (const decisionId of decisionIds) {
        const impacts = await this.bfsTraverse(decisionId);
        allImpacts.push(...impacts);
        console.log(
          `  ${decisionId}: found ${impacts.length} downstream impacts (${impacts.filter(i => i.depth === 1).length} direct)`
        );
      }

      // Remove duplicates (same source-target pair with best score)
      const deduped = this.deduplicateImpacts(allImpacts);
      console.log(
        `Deduped: ${allImpacts.length} impacts → ${deduped.length} unique relationships`
      );

      // Store in SurrealDB
      const storedCount = await this.storeInSurrealDB(deduped);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(
        `Cascade inference complete: ${storedCount} impacts stored in ${elapsed}s`
      );

      return deduped;
    } catch (error) {
      console.error('Cascade inference failed:', error);
      throw error;
    }
  }

  /**
   * Load all decisions and cascades from SurrealDB
   * @throws Error with detailed setup instructions if tables are missing or SurrealDB unavailable
   */
  private async loadDecisionsAndCascades(): Promise<void> {
    try {
      // Check if SurrealDB is healthy
      const isHealthy = await this.checkSurrealDBHealth();
      if (!isHealthy) {
        throw new Error(
          'SurrealDB is unavailable. Cannot load decisions.\n' +
          'Setup required:\n' +
          '1. Ensure SurrealDB is running on http://localhost:8000\n' +
          '2. Run: npm run setup:surrealdb\n' +
          '3. See docs/SURREALDB_SETUP.md for details'
        );
      }

      // Load decisions
      const decisionsQuery = `SELECT * FROM decisions LIMIT 500`;
      const decisionsResult = await (this.db as any).executeQuery(decisionsQuery);

      if (!decisionsResult || !Array.isArray(decisionsResult)) {
        throw new Error(
          'decisions table not found or returned invalid data.\n' +
          'Setup required:\n' +
          '1. Run: npx ts-node scripts/surrealdb-migrations.sql\n' +
          '2. Run: npx ts-node scripts/populate-test-data.ts\n' +
          '3. See docs/SURREALDB_SETUP.md for details'
        );
      }

      if (decisionsResult.length === 0) {
        console.warn('⚠️  Warning: No decisions found in table. Check data population.');
      }

      decisionsResult.forEach((row: any) => {
        this.decisionMap.set(row.id, {
          id: row.id,
          title: row.title || '',
          chosen_option: row.chosen_option || '',
          rationale: row.rationale || '',
          reasoning_type: row.reasoning_type || 'hybrid',
          confidence_score: row.confidence_score || 0.5,
          reasoning_chain: {} as any,
          status: row.status || 'active',
          timestamp: row.timestamp || new Date().toISOString(),
        });
      });

      console.log(`✓ Loaded ${this.decisionMap.size} decisions from SurrealDB`);

      // Load cascades
      const cascadesQuery = `SELECT * FROM decision_cascades LIMIT 1000`;
      const cascadesResult = await (this.db as any).executeQuery(cascadesQuery);

      if (!cascadesResult || !Array.isArray(cascadesResult)) {
        throw new Error(
          'decision_cascades table not found or returned invalid data.\n' +
          'Setup required:\n' +
          '1. Run: npx ts-node scripts/populate-test-data.ts\n' +
          '2. See docs/SURREALDB_SETUP.md for details'
        );
      }

      if (cascadesResult.length === 0) {
        console.warn('⚠️  Warning: No cascades found in table. Check cascade computation.');
      }

      cascadesResult.forEach((row: any) => {
        const sourceId = row.source_decision_id;
        if (!this.cascadeMap.has(sourceId)) {
          this.cascadeMap.set(sourceId, []);
        }
        this.cascadeMap.get(sourceId)!.push({
          source_decision_id: sourceId,
          target_decision_id: row.target_decision_id,
          dependency_type: row.dependency_type,
          impact_level: row.impact_level,
          description: row.description || '',
        });
      });

      console.log(`✓ Loaded ${cascadesResult.length} cascades from SurrealDB`);

    } catch (error) {
      throw new Error(
        `SurrealDB setup incomplete. ${(error as Error).message}\n\n` +
        `Steps to fix:\n` +
        `1. Ensure SurrealDB is running: surreal start\n` +
        `2. Run schema migration: npx ts-node scripts/surrealdb-migrations.sql\n` +
        `3. Run data population: npx ts-node scripts/populate-test-data.ts\n` +
        `4. Verify setup: surreal query "SELECT COUNT(*) FROM decisions;"\n` +
        `See docs/SURREALDB_SETUP.md for complete setup instructions`
      );
    }
  }

  /**
   * Check if SurrealDB is healthy and accessible
   */
  private async checkSurrealDBHealth(): Promise<boolean> {
    try {
      const response = await fetch('http://localhost:8000/health', {
        method: 'GET',
        timeout: 5000,
      } as any);
      return response.status === 200;
    } catch (err) {
      console.warn('SurrealDB health check failed:', (err as Error).message);
      return false;
    }
  }

  /**
   * BFS traversal from a source decision
   * Computes all downstream impacts up to maxDepth
   */
  private async bfsTraverse(sourceDecisionId: string): Promise<DecisionImpact[]> {
    const impacts: DecisionImpact[] = [];
    const visited: Set<string> = new Set();
    const queue: QueueItem[] = [];

    // Start with direct cascades
    const directCascades = this.cascadeMap.get(sourceDecisionId) || [];
    for (const cascade of directCascades) {
      queue.push({
        decision_id: cascade.target_decision_id,
        depth: 1,
        path: [sourceDecisionId, cascade.target_decision_id],
        impact_type: this.classifyImpactType(cascade.dependency_type, 1),
      });
    }

    // BFS traversal
    while (queue.length > 0) {
      const item = queue.shift()!;

      // Cycle detection: skip if already visited at same or lower depth
      const visitKey = `${item.decision_id}@${item.depth}`;
      if (visited.has(visitKey)) {
        continue;
      }
      visited.add(visitKey);

      // Record impact
      const impact: DecisionImpact = {
        source_decision_id: sourceDecisionId,
        target_decision_id: item.decision_id,
        depth: item.depth,
        impact_type: item.impact_type,
        impact_score: this.computeImpactScore(item),
      };
      impacts.push(impact);

      // Continue BFS if depth < maxDepth
      if (item.depth < this.maxDepth) {
        const nextCascades = this.cascadeMap.get(item.decision_id) || [];
        for (const cascade of nextCascades) {
          // Avoid paths that contain cycles
          if (!item.path.includes(cascade.target_decision_id)) {
            queue.push({
              decision_id: cascade.target_decision_id,
              depth: item.depth + 1,
              path: [...item.path, cascade.target_decision_id],
              impact_type: this.classifyImpactType(cascade.dependency_type, item.depth + 1),
            });
          }
        }
      }
    }

    return impacts;
  }

  /**
   * Classify impact type based on dependency and depth
   */
  private classifyImpactType(
    dependencyType: string,
    depth: number
  ): 'direct' | 'indirect' | 'conflict' | 'support' {
    if (depth === 1) {
      return 'direct';
    }

    if (dependencyType === 'conflicts' || dependencyType === 'blocks') {
      return 'conflict';
    }

    if (dependencyType === 'enables' || dependencyType === 'influences') {
      return 'support';
    }

    return 'indirect';
  }

  /**
   * Compute impact score (0-1) based on path depth and dependency strength
   */
  private computeImpactScore(item: QueueItem): number {
    // Deeper paths have lower scores (discount future)
    const depthDiscount = 1 / (1 + item.depth * 0.2);

    // Conflict/support types have higher base scores
    const typeBonus = item.impact_type === 'conflict' || item.impact_type === 'support' ? 0.2 : 0;

    return Math.min(1, 0.8 * depthDiscount + typeBonus);
  }

  /**
   * Deduplicate impacts: keep best score for each source-target pair
   */
  private deduplicateImpacts(impacts: DecisionImpact[]): DecisionImpact[] {
    const map = new Map<string, DecisionImpact>();

    for (const impact of impacts) {
      const key = `${impact.source_decision_id}→${impact.target_decision_id}`;
      const existing = map.get(key);

      if (!existing || impact.impact_score > existing.impact_score) {
        map.set(key, impact);
      }
    }

    return Array.from(map.values());
  }

  /**
   * Store impacts in SurrealDB
   */
  private async storeInSurrealDB(impacts: DecisionImpact[]): Promise<number> {
    try {
      // First, ensure table exists
      const createTableQuery = `
        CREATE TABLE IF NOT EXISTS decision_impacts {
          source_decision_id: string,
          target_decision_id: string,
          depth: number,
          impact_type: string,
          impact_score: number
        }
      `;
      await (this.db as any).executeQuery(createTableQuery);
      console.log('decision_impacts table created/verified');

      // Clear existing impacts (fresh computation)
      const clearQuery = `DELETE FROM decision_impacts`;
      await (this.db as any).executeQuery(clearQuery);

      // Insert in batches to avoid memory issues
      const batchSize = 100;
      let inserted = 0;

      for (let i = 0; i < impacts.length; i += batchSize) {
        const batch = impacts.slice(i, Math.min(i + batchSize, impacts.length));

        const insertQueries = batch
          .map(
            impact =>
              `INSERT INTO decision_impacts (source_decision_id, target_decision_id, depth, impact_type, impact_score)
               VALUES ('${impact.source_decision_id}', '${impact.target_decision_id}', ${impact.depth}, '${impact.impact_type}', ${impact.impact_score});`
          )
          .join('\n');

        await (this.db as any).executeQuery(insertQueries);
        inserted += batch.length;
        console.log(`  Inserted ${inserted}/${impacts.length} impacts...`);
      }

      // Verify insertion
      const countQuery = `SELECT COUNT(*) as count FROM decision_impacts`;
      const countResult = await (this.db as any).executeQuery(countQuery);
      const count = countResult?.[0]?.count || 0;
      console.log(`Verified: ${count} impacts in decision_impacts table`);

      return inserted;
    } catch (error) {
      console.error('Failed to store impacts in SurrealDB:', error);
      throw error;
    }
  }

  /**
   * Verify a few BFS chains manually (for testing)
   */
  async verifyCascadeChains(sampleSize: number = 3): Promise<void> {
    console.log(`\nVerifying ${sampleSize} cascade chains...`);

    const decisionIds = Array.from(this.decisionMap.keys()).slice(0, sampleSize);

    for (const decisionId of decisionIds) {
      const cascades = this.cascadeMap.get(decisionId) || [];
      console.log(`\n  ${decisionId}:`);
      console.log(`    Direct impacts: ${cascades.length}`);

      for (const cascade of cascades.slice(0, 2)) {
        const secondOrder = this.cascadeMap.get(cascade.target_decision_id) || [];
        console.log(
          `    └→ ${cascade.target_decision_id} (${cascade.dependency_type}) → ${secondOrder.length} further impacts`
        );

        for (const second of secondOrder.slice(0, 1)) {
          console.log(
            `       └→ ${second.target_decision_id} (${second.dependency_type})`
          );
        }
      }
    }
  }
}
