/**
 * Knowledge Gap Explorer - Phase 4 Universe Simulation
 *
 * Allows users to simulate adding hypothetical papers to explore how they would
 * impact the knowledge graph. Uses Ollama embeddings to predict clustering position
 * and calculate impact metrics.
 *
 * Architecture:
 * 1. User enters title + abstract in modal
 * 2. Generate 768-dim embedding vector (Ollama nomic-embed-text)
 * 3. Compute cosine similarity to existing 84 papers
 * 4. Predict clustering position (k-nearest neighbors)
 * 5. Render ghost node in 3D graph (translucent sphere, dashed lines)
 * 6. Calculate impact metrics (cross-domain connections, orphan connections, density)
 * 7. Allow multiple what-if scenarios (add multiple hypothetical papers)
 */

import { Notice } from 'obsidian';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Hypothetical paper input
 */
interface HypotheticalPaper {
  title: string;
  abstract: string;
  tags?: string[]; // Optional domain tags
}

/**
 * Ghost node representing hypothetical paper in graph
 */
interface GhostNode {
  id: string;
  label: string;
  title: string;
  abstract: string;
  embedding: number[]; // 768-dim vector
  predicted_position: { x: number; y: number; z: number };
  nearest_neighbors: Array<{
    node_id: string;
    similarity: number;
    label: string;
  }>;
  predicted_tags: string[]; // Inferred domain tags
  confidence: number; // 0.0-1.0 (prediction confidence)
}

/**
 * Impact metrics for hypothetical paper
 */
interface ImpactMetrics {
  cross_domain_connections_added: number; // New connections across domains
  orphaned_papers_connected: number; // Previously orphaned papers now connected
  knowledge_density_improvement: number; // Delta in graph density (0.0-1.0)
  cluster_bridging_score: number; // 0.0-1.0 (how well it bridges disconnected clusters)
  new_research_directions: string[]; // Suggested research directions opened up
}

/**
 * Gap exploration scenario (multiple hypothetical papers)
 */
interface GapScenario {
  scenario_name: string;
  hypothetical_papers: GhostNode[];
  combined_impact: ImpactMetrics;
  comparison_to_baseline: {
    connectivity_delta: number;
    density_delta: number;
    cluster_count_delta: number;
  };
}

/**
 * Validation result (comparing prediction to known papers)
 */
interface ValidationResult {
  test_paper_id: string;
  actual_neighbors: string[];
  predicted_neighbors: string[];
  accuracy: number; // 0.0-1.0 (% of correct predictions)
  mean_similarity_error: number; // Average error in similarity scores
}

// ============================================================================
// OLLAMA CLIENT (Reuse from DecisionForkSimulator)
// ============================================================================

/**
 * Ollama local LLM client for embeddings
 */
class OllamaClient {
  private baseUrl: string;
  private embeddingModel: string;

  constructor(
    baseUrl: string = 'http://localhost:11434',
    embeddingModel: string = 'nomic-embed-text'
  ) {
    this.baseUrl = baseUrl;
    this.embeddingModel = embeddingModel;
  }

  /**
   * Generate embeddings for text
   */
  async embed(text: string): Promise<number[]> {
    const response = await fetch(`${this.baseUrl}/api/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.embeddingModel,
        prompt: text,
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama embed failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data.embedding;
  }

  /**
   * Compute cosine similarity between two embeddings
   */
  cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error('Embeddings must have same dimension');
    }

    const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
    const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
    const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));

    return dotProduct / (magnitudeA * magnitudeB);
  }
}

// ============================================================================
// GRAPH ANALYZER
// ============================================================================

/**
 * Analyze existing graph structure to compute baselines
 */
class GraphAnalyzer {
  private graphData: any; // From .obsidian/3d-graph-data.json

  constructor(graphData: any) {
    this.graphData = graphData;
  }

  /**
   * Compute graph density (actual edges / possible edges)
   */
  computeDensity(): number {
    const nodeCount = this.graphData.nodes.length;
    const edgeCount = this.graphData.edges.length;
    const possibleEdges = (nodeCount * (nodeCount - 1)) / 2;

    return edgeCount / possibleEdges;
  }

  /**
   * Identify orphaned papers (no connections)
   */
  identifyOrphanedPapers(): string[] {
    const connectedNodes = new Set<string>();

    for (const edge of this.graphData.edges) {
      connectedNodes.add(edge.source);
      connectedNodes.add(edge.target);
    }

    const orphans: string[] = [];
    for (const node of this.graphData.nodes) {
      if (!connectedNodes.has(node.id)) {
        orphans.push(node.id);
      }
    }

    return orphans;
  }

  /**
   * Compute cross-domain connections (edges between different domain tags)
   */
  computeCrossDomainConnections(): number {
    let crossDomainCount = 0;

    for (const edge of this.graphData.edges) {
      const sourceNode = this.graphData.nodes.find((n: any) => n.id === edge.source);
      const targetNode = this.graphData.nodes.find((n: any) => n.id === edge.target);

      if (!sourceNode || !targetNode) continue;

      const sourceTags = new Set(sourceNode.tags || []);
      const targetTags = new Set(targetNode.tags || []);

      // Check if tags are disjoint (no overlap)
      const overlap = [...sourceTags].some((tag) => targetTags.has(tag));
      if (!overlap && sourceTags.size > 0 && targetTags.size > 0) {
        crossDomainCount++;
      }
    }

    return crossDomainCount;
  }

  /**
   * Identify disconnected clusters using DFS
   */
  identifyDisconnectedClusters(): Array<string[]> {
    const adjacencyList = new Map<string, string[]>();

    // Build adjacency list
    for (const node of this.graphData.nodes) {
      adjacencyList.set(node.id, []);
    }

    for (const edge of this.graphData.edges) {
      adjacencyList.get(edge.source)?.push(edge.target);
      adjacencyList.get(edge.target)?.push(edge.source);
    }

    // DFS to find connected components
    const visited = new Set<string>();
    const clusters: Array<string[]> = [];

    const dfs = (nodeId: string, cluster: string[]) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      cluster.push(nodeId);

      const neighbors = adjacencyList.get(nodeId) || [];
      for (const neighbor of neighbors) {
        dfs(neighbor, cluster);
      }
    };

    for (const node of this.graphData.nodes) {
      if (!visited.has(node.id)) {
        const cluster: string[] = [];
        dfs(node.id, cluster);
        clusters.push(cluster);
      }
    }

    return clusters;
  }
}

// ============================================================================
// KNOWLEDGE GAP EXPLORER
// ============================================================================

/**
 * Main gap explorer class
 */
export class KnowledgeGapExplorer {
  private ollamaClient: OllamaClient;
  private graphAnalyzer: GraphAnalyzer;
  private graphData: any;
  private embeddingCache: Map<string, number[]>; // Node ID -> embedding

  constructor(graphData: any) {
    this.ollamaClient = new OllamaClient();
    this.graphAnalyzer = new GraphAnalyzer(graphData);
    this.graphData = graphData;
    this.embeddingCache = new Map();
  }

  /**
   * Explore impact of adding hypothetical paper
   */
  async explorePaper(hypothetical: HypotheticalPaper): Promise<{
    ghost_node: GhostNode;
    impact: ImpactMetrics;
  }> {
    new Notice('Analyzing hypothetical paper...', 3000);

    try {
      // 1. Generate embedding
      const embedding = await this.ollamaClient.embed(
        `${hypothetical.title}\n\n${hypothetical.abstract}`
      );

      // 2. Find k-nearest neighbors (k=5)
      const neighbors = await this.findNearestNeighbors(embedding, 5);

      // 3. Predict position (average of nearest neighbors)
      const predictedPosition = this.computeAveragePosition(neighbors);

      // 4. Infer tags from neighbors
      const predictedTags = this.inferTags(neighbors);

      // 5. Create ghost node
      const ghostNode: GhostNode = {
        id: `ghost-${Date.now()}`,
        label: hypothetical.title,
        title: hypothetical.title,
        abstract: hypothetical.abstract,
        embedding,
        predicted_position: predictedPosition,
        nearest_neighbors: neighbors.map((n) => ({
          node_id: n.node.id,
          similarity: n.similarity,
          label: n.node.label,
        })),
        predicted_tags: predictedTags,
        confidence: neighbors[0]?.similarity || 0.5,
      };

      // 6. Calculate impact metrics
      const impact = await this.calculateImpact(ghostNode, neighbors);

      new Notice(`Impact: +${impact.cross_domain_connections_added} cross-domain connections`, 5000);

      return { ghost_node: ghostNode, impact };
    } catch (error) {
      new Notice(`Exploration failed: ${error.message}`, 5000);
      throw error;
    }
  }

  /**
   * Find k nearest neighbors using embeddings
   */
  private async findNearestNeighbors(
    embedding: number[],
    k: number
  ): Promise<Array<{ node: any; similarity: number }>> {
    const similarities: Array<{ node: any; similarity: number }> = [];

    for (const node of this.graphData.nodes) {
      // Check cache first
      let nodeEmbedding = this.embeddingCache.get(node.id);

      if (!nodeEmbedding) {
        // Generate embedding for node
        const text = `${node.label}\n${node.description || ''}`;
        nodeEmbedding = await this.ollamaClient.embed(text);
        this.embeddingCache.set(node.id, nodeEmbedding);
      }

      // Compute similarity
      const similarity = this.ollamaClient.cosineSimilarity(embedding, nodeEmbedding);
      similarities.push({ node, similarity });
    }

    // Sort by similarity (descending) and take top k
    similarities.sort((a, b) => b.similarity - a.similarity);
    return similarities.slice(0, k);
  }

  /**
   * Compute average position of neighbors
   */
  private computeAveragePosition(neighbors: Array<{ node: any; similarity: number }>): {
    x: number;
    y: number;
    z: number;
  } {
    if (neighbors.length === 0) {
      return { x: 0, y: 0, z: 0 }; // Default to origin
    }

    let sumX = 0,
      sumY = 0,
      sumZ = 0;

    for (const { node } of neighbors) {
      sumX += node.x || 0;
      sumY += node.y || 0;
      sumZ += node.z || 0;
    }

    return {
      x: sumX / neighbors.length,
      y: sumY / neighbors.length,
      z: sumZ / neighbors.length,
    };
  }

  /**
   * Infer tags from nearest neighbors (majority vote)
   */
  private inferTags(neighbors: Array<{ node: any; similarity: number }>): string[] {
    const tagCounts = new Map<string, number>();

    for (const { node, similarity } of neighbors) {
      const tags = node.tags || [];
      for (const tag of tags) {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + similarity);
      }
    }

    // Sort by weighted count (descending) and take top 3
    const sortedTags = Array.from(tagCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([tag]) => tag);

    return sortedTags;
  }

  /**
   * Calculate impact metrics
   */
  private async calculateImpact(
    ghostNode: GhostNode,
    neighbors: Array<{ node: any; similarity: number }>
  ): Promise<ImpactMetrics> {
    // Baseline metrics
    const baselineDensity = this.graphAnalyzer.computeDensity();
    const baselineOrphans = this.graphAnalyzer.identifyOrphanedPapers();
    const baselineCrossDomain = this.graphAnalyzer.computeCrossDomainConnections();
    const baselineClusters = this.graphAnalyzer.identifyDisconnectedClusters();

    // Simulate adding ghost node
    const potentialConnections = neighbors.filter((n) => n.similarity > 0.7).length;

    // Cross-domain connections
    const ghostTags = new Set(ghostNode.predicted_tags);
    let crossDomainAdded = 0;
    for (const { node } of neighbors) {
      const nodeTags = new Set(node.tags || []);
      const overlap = [...ghostTags].some((tag) => nodeTags.has(tag));
      if (!overlap && ghostTags.size > 0 && nodeTags.size > 0) {
        crossDomainAdded++;
      }
    }

    // Orphan connections (neighbors that are orphaned)
    const orphansConnected = neighbors.filter((n) => baselineOrphans.includes(n.node.id)).length;

    // Density improvement
    const newDensity =
      (this.graphData.edges.length + potentialConnections) /
      ((this.graphData.nodes.length + 1) * this.graphData.nodes.length / 2);
    const densityImprovement = newDensity - baselineDensity;

    // Cluster bridging (does it connect multiple clusters?)
    const neighborClusters = new Set<number>();
    for (const { node } of neighbors) {
      const clusterIndex = baselineClusters.findIndex((cluster) => cluster.includes(node.id));
      if (clusterIndex !== -1) {
        neighborClusters.add(clusterIndex);
      }
    }
    const clusterBridgingScore = Math.min(1.0, neighborClusters.size / 3); // Normalize to 0-1

    // New research directions (infer from tag combinations)
    const newDirections = this.inferResearchDirections(ghostNode, neighbors);

    return {
      cross_domain_connections_added: crossDomainAdded,
      orphaned_papers_connected: orphansConnected,
      knowledge_density_improvement: densityImprovement,
      cluster_bridging_score: clusterBridgingScore,
      new_research_directions: newDirections,
    };
  }

  /**
   * Infer new research directions from ghost node and neighbors
   */
  private inferResearchDirections(
    ghostNode: GhostNode,
    neighbors: Array<{ node: any; similarity: number }>
  ): string[] {
    const directions: string[] = [];

    // Combine ghost tags with neighbor tags
    const allTags = new Set<string>(ghostNode.predicted_tags);
    for (const { node } of neighbors) {
      for (const tag of node.tags || []) {
        allTags.add(tag);
      }
    }

    // Generate combinations (simplified: just list unique tag pairs)
    const tagsArray = Array.from(allTags);
    for (let i = 0; i < tagsArray.length - 1; i++) {
      for (let j = i + 1; j < tagsArray.length; j++) {
        directions.push(`${tagsArray[i]} + ${tagsArray[j]}`);
      }
    }

    return directions.slice(0, 5); // Return top 5
  }

  /**
   * Explore multiple scenarios (add multiple hypothetical papers)
   */
  async exploreScenario(
    scenarioName: string,
    hypotheticals: HypotheticalPaper[]
  ): Promise<GapScenario> {
    const ghostNodes: GhostNode[] = [];
    const impacts: ImpactMetrics[] = [];

    for (const hypothetical of hypotheticals) {
      const result = await this.explorePaper(hypothetical);
      ghostNodes.push(result.ghost_node);
      impacts.push(result.impact);
    }

    // Combine impacts
    const combinedImpact: ImpactMetrics = {
      cross_domain_connections_added: impacts.reduce(
        (sum, i) => sum + i.cross_domain_connections_added,
        0
      ),
      orphaned_papers_connected: impacts.reduce((sum, i) => sum + i.orphaned_papers_connected, 0),
      knowledge_density_improvement: impacts.reduce(
        (sum, i) => sum + i.knowledge_density_improvement,
        0
      ),
      cluster_bridging_score: impacts.reduce((sum, i) => sum + i.cluster_bridging_score, 0) / impacts.length,
      new_research_directions: Array.from(
        new Set(impacts.flatMap((i) => i.new_research_directions))
      ),
    };

    // Baseline comparison
    const baselineDensity = this.graphAnalyzer.computeDensity();
    const baselineClusters = this.graphAnalyzer.identifyDisconnectedClusters();

    return {
      scenario_name: scenarioName,
      hypothetical_papers: ghostNodes,
      combined_impact: combinedImpact,
      comparison_to_baseline: {
        connectivity_delta: combinedImpact.cross_domain_connections_added,
        density_delta: combinedImpact.knowledge_density_improvement,
        cluster_count_delta: -ghostNodes.filter((n) => n.confidence > 0.7).length, // Negative = fewer clusters
      },
    };
  }

  /**
   * Validate prediction accuracy against known papers
   *
   * Test method: Remove a known paper from graph, predict its neighbors, compare to actual
   */
  async validatePrediction(test_paper_id: string): Promise<ValidationResult> {
    // Find test paper
    const testPaper = this.graphData.nodes.find((n: any) => n.id === test_paper_id);
    if (!testPaper) {
      throw new Error(`Paper ${test_paper_id} not found`);
    }

    // Get actual neighbors (from edges)
    const actualNeighbors: string[] = [];
    for (const edge of this.graphData.edges) {
      if (edge.source === test_paper_id) {
        actualNeighbors.push(edge.target);
      } else if (edge.target === test_paper_id) {
        actualNeighbors.push(edge.source);
      }
    }

    // Temporarily remove test paper from graph
    const originalNodes = [...this.graphData.nodes];
    const originalEdges = [...this.graphData.edges];
    this.graphData.nodes = this.graphData.nodes.filter((n: any) => n.id !== test_paper_id);
    this.graphData.edges = this.graphData.edges.filter(
      (e: any) => e.source !== test_paper_id && e.target !== test_paper_id
    );

    // Generate embedding for test paper
    const embedding = await this.ollamaClient.embed(
      `${testPaper.label}\n${testPaper.description || ''}`
    );

    // Predict neighbors
    const predictedNeighborsData = await this.findNearestNeighbors(embedding, actualNeighbors.length);
    const predictedNeighbors = predictedNeighborsData.map((n) => n.node.id);

    // Restore graph
    this.graphData.nodes = originalNodes;
    this.graphData.edges = originalEdges;

    // Compute accuracy (% of correct predictions)
    const correctPredictions = predictedNeighbors.filter((id) => actualNeighbors.includes(id)).length;
    const accuracy = correctPredictions / actualNeighbors.length;

    // Compute mean similarity error
    const similarityErrors: number[] = [];
    for (let i = 0; i < predictedNeighbors.length; i++) {
      const predicted = predictedNeighborsData[i].similarity;
      const actual = actualNeighbors.includes(predictedNeighbors[i]) ? 1.0 : 0.0;
      similarityErrors.push(Math.abs(predicted - actual));
    }
    const meanError = similarityErrors.reduce((sum, e) => sum + e, 0) / similarityErrors.length;

    return {
      test_paper_id,
      actual_neighbors: actualNeighbors,
      predicted_neighbors: predictedNeighbors,
      accuracy,
      mean_similarity_error: meanError,
    };
  }

  /**
   * Batch validate across multiple papers
   */
  async batchValidate(sample_size: number = 10): Promise<{
    average_accuracy: number;
    average_error: number;
    results: ValidationResult[];
  }> {
    const samplePapers = this.graphData.nodes
      .filter((n: any) => n.type === 'paper')
      .sort(() => Math.random() - 0.5)
      .slice(0, sample_size);

    const results: ValidationResult[] = [];

    for (const paper of samplePapers) {
      try {
        const result = await this.validatePrediction(paper.id);
        results.push(result);
      } catch (error) {
        console.warn(`Validation failed for ${paper.id}:`, error);
      }
    }

    const avgAccuracy = results.reduce((sum, r) => sum + r.accuracy, 0) / results.length;
    const avgError = results.reduce((sum, r) => sum + r.mean_similarity_error, 0) / results.length;

    return {
      average_accuracy: avgAccuracy,
      average_error: avgError,
      results,
    };
  }
}
