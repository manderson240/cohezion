/**
 * Decision Fork Simulator - Phase 4 Universe Simulation
 *
 * Simulates "what if" scenarios by exploring alternative decisions from past ADRs.
 * Uses Ollama for inference and Cloud Vault MCP for vault access.
 *
 * Architecture:
 * 1. User clicks decision node in 3D graph
 * 2. Load ADR from vault (decisions/*.md)
 * 3. Parse "Alternatives Considered" section
 * 4. Use Ollama to simulate: "If we chose Alternative 2 instead..."
 * 5. Generate simulated universe with ghost nodes (translucent papers/patterns)
 * 6. Calculate impact metrics (# patterns affected, token cost difference)
 * 7. Render side-by-side 3D view (actual vs simulated)
 */

import { Notice } from 'obsidian';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Parsed ADR (Architecture Decision Record)
 */
interface ADR {
  title: string;
  status: string;
  date: string;
  context: string;
  decision: string;
  consequences: string;
  alternatives: Alternative[];
  file_path: string;
}

/**
 * Alternative decision option from ADR
 */
interface Alternative {
  name: string;
  description: string;
  pros: string[];
  cons: string[];
}

/**
 * Simulated universe representing alternative timeline
 */
interface SimulatedUniverse {
  alternative_name: string;
  alternative_description: string;

  // Predicted artifacts
  hypothetical_papers: GhostNode[];
  hypothetical_patterns: GhostNode[];
  modified_edges: ModifiedEdge[];

  // Impact metrics
  impact: {
    patterns_affected: number;
    papers_affected: number;
    token_cost_delta: number; // Positive = more expensive, negative = cheaper
    time_delta_hours: number; // Positive = slower, negative = faster
    cross_domain_connectivity_delta: number; // Change in cross-domain links
    knowledge_gap_changes: string[]; // New gaps created or filled
  };
}

/**
 * Ghost node (translucent) for hypothetical artifacts
 */
interface GhostNode {
  id: string;
  label: string;
  type: 'paper' | 'pattern' | 'decision';
  confidence: number; // 0.0-1.0 (Ollama prediction confidence)
  reason: string; // Why this would exist in alternative timeline
  semantic_similarity: number; // Cosine similarity to existing nodes
  predicted_position: { x: number; y: number; z: number }; // 3D coordinates
}

/**
 * Modified edge showing different connections
 */
interface ModifiedEdge {
  source: string;
  target: string;
  edge_type: 'added' | 'removed' | 'strengthened' | 'weakened';
  confidence: number;
  reason: string;
}

/**
 * Side-by-side comparison view data
 */
interface ComparisonView {
  actual_universe: {
    nodes: any[]; // From .obsidian/3d-graph-data.json
    edges: any[];
  };
  simulated_universe: SimulatedUniverse;
  diff_summary: {
    nodes_added: number;
    nodes_removed: number;
    edges_added: number;
    edges_removed: number;
    quantified_metrics: {
      token_cost_delta: number;
      time_delta_hours: number;
      connectivity_delta: number;
    };
  };
}

// ============================================================================
// MCP CLIENT WRAPPER
// ============================================================================

/**
 * Lightweight MCP client for vault operations
 */
class MCPVaultClient {
  private serverUrl: string;

  constructor(serverUrl: string = 'http://localhost:8360') {
    this.serverUrl = serverUrl;
  }

  /**
   * Read a decision file from vault
   */
  async readDecision(decision_id: string): Promise<string> {
    const response = await fetch(`${this.serverUrl}/tools/vault_read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: `decisions/${decision_id}.md`,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to read decision: ${response.statusText}`);
    }

    const data = await response.json();
    return data.content;
  }

  /**
   * List all papers in vault
   */
  async listPapers(): Promise<string[]> {
    const response = await fetch(`${this.serverUrl}/tools/vault_list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: 'papers',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to list papers: ${response.statusText}`);
    }

    const data = await response.json();
    return data.files || [];
  }

  /**
   * List all patterns in vault
   */
  async listPatterns(): Promise<string[]> {
    const response = await fetch(`${this.serverUrl}/tools/vault_list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: 'patterns',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to list patterns: ${response.statusText}`);
    }

    const data = await response.json();
    return data.files || [];
  }
}

// ============================================================================
// OLLAMA CLIENT
// ============================================================================

/**
 * Ollama local LLM client for inference and embeddings
 */
class OllamaClient {
  private baseUrl: string;
  private inferenceModel: string;
  private embeddingModel: string;

  constructor(
    baseUrl: string = 'http://localhost:11434',
    inferenceModel: string = 'qwen3:8b',
    embeddingModel: string = 'nomic-embed-text'
  ) {
    this.baseUrl = baseUrl;
    this.inferenceModel = inferenceModel;
    this.embeddingModel = embeddingModel;
  }

  /**
   * Query Ollama for inference
   */
  async query(prompt: string, model?: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: model || this.inferenceModel,
        prompt: prompt,
        stream: false,
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama query failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data.response;
  }

  /**
   * Generate embeddings for semantic similarity
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
// ADR PARSER
// ============================================================================

/**
 * Parse ADR markdown file into structured data
 */
class ADRParser {
  /**
   * Parse decision file content
   */
  parseADR(content: string): ADR {
    // Extract YAML frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]+?)\n---/);
    const frontmatter = frontmatterMatch ? this.parseYAML(frontmatterMatch[1]) : {};

    // Extract sections
    const context = this.extractSection(content, 'Context');
    const decision = this.extractSection(content, 'Decision');
    const consequences = this.extractSection(content, 'Consequences');
    const alternativesText = this.extractSection(content, 'Alternatives Considered') ||
                             this.extractSection(content, 'Alternatives');

    // Parse alternatives
    const alternatives = this.parseAlternatives(alternativesText);

    return {
      title: frontmatter.title || 'Untitled Decision',
      status: frontmatter.status || 'unknown',
      date: frontmatter.date || '',
      context,
      decision,
      consequences,
      alternatives,
      file_path: '',
    };
  }

  /**
   * Simple YAML parser for frontmatter
   */
  private parseYAML(yaml: string): any {
    const result: any = {};
    const lines = yaml.split('\n');

    for (const line of lines) {
      const match = line.match(/^(\w+):\s*(.+)$/);
      if (match) {
        result[match[1]] = match[2].replace(/^["']|["']$/g, '');
      }
    }

    return result;
  }

  /**
   * Extract section content by heading
   */
  private extractSection(content: string, heading: string): string {
    const regex = new RegExp(`## ${heading}\\s*\\n([\\s\\S]*?)(?=\\n##|$)`, 'i');
    const match = content.match(regex);
    return match ? match[1].trim() : '';
  }

  /**
   * Parse alternatives from text
   */
  private parseAlternatives(text: string): Alternative[] {
    const alternatives: Alternative[] = [];

    // Match numbered alternatives: ### 1. Alternative Name
    const altRegex = /###\s+(\d+)\.\s+(.+?)\n([\s\S]*?)(?=###\s+\d+\.|$)/g;
    let match;

    while ((match = altRegex.exec(text)) !== null) {
      const name = match[2].trim();
      const description = match[3].trim();

      // Extract pros and cons
      const pros = this.extractBulletPoints(description, 'Pros');
      const cons = this.extractBulletPoints(description, 'Cons');

      alternatives.push({ name, description, pros, cons });
    }

    return alternatives;
  }

  /**
   * Extract bullet points from section
   */
  private extractBulletPoints(text: string, heading: string): string[] {
    const regex = new RegExp(`\\*\\*${heading}\\*\\*:?\\s*\\n([\\s\\S]*?)(?=\\n\\*\\*|$)`, 'i');
    const match = text.match(regex);

    if (!match) return [];

    const bullets = match[1]
      .split('\n')
      .filter((line) => line.trim().startsWith('-') || line.trim().startsWith('*'))
      .map((line) => line.replace(/^[-*]\s*/, '').trim());

    return bullets;
  }
}

// ============================================================================
// DECISION FORK SIMULATOR
// ============================================================================

/**
 * Main simulator class
 */
export class DecisionForkSimulator {
  private mcpClient: MCPVaultClient;
  private ollamaClient: OllamaClient;
  private adrParser: ADRParser;
  private graphData: any; // From .obsidian/3d-graph-data.json

  constructor(graphData: any) {
    this.mcpClient = new MCPVaultClient();
    this.ollamaClient = new OllamaClient();
    this.adrParser = new ADRParser();
    this.graphData = graphData;
  }

  /**
   * Simulate alternative decision fork
   *
   * @param decision_id - ID of decision node clicked (e.g., "2026-02-09-12d-graph-refined-plan")
   * @param alternative_index - Index of alternative to simulate (0-based)
   */
  async simulateFork(decision_id: string, alternative_index: number): Promise<SimulatedUniverse> {
    new Notice('Simulating alternative decision fork...', 3000);

    try {
      // 1. Load ADR from vault
      const content = await this.mcpClient.readDecision(decision_id);
      const adr = this.adrParser.parseADR(content);

      if (alternative_index >= adr.alternatives.length) {
        throw new Error(`Alternative ${alternative_index} does not exist`);
      }

      const alternative = adr.alternatives[alternative_index];

      // 2. Use Ollama to predict impact
      const simulationPrompt = this.buildSimulationPrompt(adr, alternative);
      const predictionJSON = await this.ollamaClient.query(simulationPrompt);

      // 3. Parse prediction (expect JSON output from Ollama)
      let prediction;
      try {
        prediction = JSON.parse(predictionJSON);
      } catch (e) {
        // Fallback: extract JSON from markdown code blocks
        const jsonMatch = predictionJSON.match(/```json\n([\s\S]+?)\n```/);
        if (jsonMatch) {
          prediction = JSON.parse(jsonMatch[1]);
        } else {
          throw new Error('Ollama did not return valid JSON');
        }
      }

      // 4. Generate ghost nodes with embeddings
      const ghostNodes = await this.generateGhostNodes(prediction.hypothetical_artifacts || []);

      // 5. Compute modified edges
      const modifiedEdges = await this.computeModifiedEdges(prediction.edge_changes || []);

      // 6. Calculate impact metrics
      const impact = this.calculateImpact(ghostNodes, modifiedEdges, prediction.metrics || {});

      return {
        alternative_name: alternative.name,
        alternative_description: alternative.description,
        hypothetical_papers: ghostNodes.filter((n) => n.type === 'paper'),
        hypothetical_patterns: ghostNodes.filter((n) => n.type === 'pattern'),
        modified_edges: modifiedEdges,
        impact,
      };
    } catch (error) {
      new Notice(`Simulation failed: ${error.message}`, 5000);
      throw error;
    }
  }

  /**
   * Build prompt for Ollama to predict alternative timeline
   */
  private buildSimulationPrompt(adr: ADR, alternative: Alternative): string {
    return `You are a counterfactual reasoning engine analyzing a past decision in a knowledge management system.

**Decision Context:**
Title: ${adr.title}
Date: ${adr.date}
Status: ${adr.status}

Context: ${adr.context}

Actual Decision Made: ${adr.decision}

Consequences of Actual Decision: ${adr.consequences}

**Alternative NOT Chosen:**
Name: ${alternative.name}
Description: ${alternative.description}
Pros: ${alternative.pros.join(', ')}
Cons: ${alternative.cons.join(', ')}

**Task:**
Predict what would have happened if we chose "${alternative.name}" instead of the actual decision.

Consider:
1. What papers/patterns would exist in the vault that don't currently exist?
2. What papers/patterns would NOT exist that currently do?
3. How would cross-domain connectivity change?
4. Would it have been faster/slower, cheaper/more expensive?
5. What new knowledge gaps would emerge or be filled?

**Output Format (JSON):**
{
  "hypothetical_artifacts": [
    {
      "id": "paper-or-pattern-id",
      "label": "Human-readable name",
      "type": "paper" | "pattern",
      "reason": "Why this would exist in alternative timeline",
      "confidence": 0.0-1.0
    }
  ],
  "edge_changes": [
    {
      "source": "node-id",
      "target": "node-id",
      "change": "added" | "removed" | "strengthened" | "weakened",
      "reason": "Explanation",
      "confidence": 0.0-1.0
    }
  ],
  "metrics": {
    "token_cost_delta": <positive or negative number>,
    "time_delta_hours": <positive or negative number>,
    "cross_domain_connectivity_delta": <positive or negative number>,
    "knowledge_gaps": ["Gap 1", "Gap 2"]
  }
}

Be realistic and specific. Provide JSON only, no additional text.`;
  }

  /**
   * Generate ghost nodes with semantic positioning
   */
  private async generateGhostNodes(artifacts: any[]): Promise<GhostNode[]> {
    const ghostNodes: GhostNode[] = [];

    for (const artifact of artifacts) {
      // Generate embedding for artifact
      const embedding = await this.ollamaClient.embed(artifact.label + ' ' + artifact.reason);

      // Find nearest neighbors in existing graph (k=3)
      const neighbors = await this.findNearestNeighbors(embedding, 3);

      // Predict position (average of nearest neighbors)
      const predictedPosition = this.computeAveragePosition(neighbors);

      ghostNodes.push({
        id: artifact.id,
        label: artifact.label,
        type: artifact.type,
        confidence: artifact.confidence,
        reason: artifact.reason,
        semantic_similarity: neighbors[0]?.similarity || 0.5,
        predicted_position: predictedPosition,
      });
    }

    return ghostNodes;
  }

  /**
   * Find k nearest neighbors in graph using embeddings
   */
  private async findNearestNeighbors(
    embedding: number[],
    k: number
  ): Promise<Array<{ node: any; similarity: number }>> {
    const similarities: Array<{ node: any; similarity: number }> = [];

    // NOTE: This is a simplified version. In production, we'd cache embeddings.
    // For now, we'll use a subset of nodes and compute similarity on-the-fly.
    const sampleNodes = this.graphData.nodes.slice(0, 20); // Sample 20 nodes

    for (const node of sampleNodes) {
      const nodeEmbedding = await this.ollamaClient.embed(node.label);
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
      // Assume nodes have x, y, z positions (from Force-Atlas layout)
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
   * Compute modified edges
   */
  private async computeModifiedEdges(edgeChanges: any[]): Promise<ModifiedEdge[]> {
    return edgeChanges.map((change) => ({
      source: change.source,
      target: change.target,
      edge_type: change.change,
      confidence: change.confidence,
      reason: change.reason,
    }));
  }

  /**
   * Calculate impact metrics
   */
  private calculateImpact(
    ghostNodes: GhostNode[],
    modifiedEdges: ModifiedEdge[],
    metricsFromOllama: any
  ): SimulatedUniverse['impact'] {
    const patternsAffected = ghostNodes.filter((n) => n.type === 'pattern').length;
    const papersAffected = ghostNodes.filter((n) => n.type === 'paper').length;

    const addedEdges = modifiedEdges.filter((e) => e.edge_type === 'added').length;
    const removedEdges = modifiedEdges.filter((e) => e.edge_type === 'removed').length;
    const crossDomainDelta = addedEdges - removedEdges;

    return {
      patterns_affected: patternsAffected,
      papers_affected: papersAffected,
      token_cost_delta: metricsFromOllama.token_cost_delta || 0,
      time_delta_hours: metricsFromOllama.time_delta_hours || 0,
      cross_domain_connectivity_delta: crossDomainDelta,
      knowledge_gap_changes: metricsFromOllama.knowledge_gaps || [],
    };
  }

  /**
   * Generate side-by-side comparison view
   */
  async generateComparisonView(
    decision_id: string,
    alternative_index: number
  ): Promise<ComparisonView> {
    const simulatedUniverse = await this.simulateFork(decision_id, alternative_index);

    const nodesAdded = simulatedUniverse.hypothetical_papers.length +
                       simulatedUniverse.hypothetical_patterns.length;
    const edgesAdded = simulatedUniverse.modified_edges.filter((e) => e.edge_type === 'added').length;
    const edgesRemoved = simulatedUniverse.modified_edges.filter((e) => e.edge_type === 'removed').length;

    return {
      actual_universe: {
        nodes: this.graphData.nodes,
        edges: this.graphData.edges,
      },
      simulated_universe: simulatedUniverse,
      diff_summary: {
        nodes_added: nodesAdded,
        nodes_removed: 0, // Simplified: we only add ghost nodes, don't remove
        edges_added: edgesAdded,
        edges_removed: edgesRemoved,
        quantified_metrics: {
          token_cost_delta: simulatedUniverse.impact.token_cost_delta,
          time_delta_hours: simulatedUniverse.impact.time_delta_hours,
          connectivity_delta: simulatedUniverse.impact.cross_domain_connectivity_delta,
        },
      },
    };
  }
}
