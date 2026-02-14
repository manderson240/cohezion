/**
 * Dimension definitions for paper visualization
 * Each paper is enriched with 8 dimensions that map to visual properties
 */
export interface Dimension {
  /** Connectivity: 0-1, network centrality (isolated ↔ hub papers) */
  connectivity: number;

  /** Conceptual Depth: 0-1 (theory ↔ applied), foundational ↔ applied */
  conceptual_depth: number;

  /** Temporal: 0-1 (historical ↔ recent), classic ↔ cutting-edge */
  temporal: number;

  /** Cross Domain: 1-15 count, domain clustering */
  cross_domain: number;

  /** Completion: 0-100%, research maturity (0.5x-2.0x scale) */
  completion: number;

  /** Recency: 0-1, freshness (30%-100% opacity) */
  recency: number;

  /** Semantic Similarity: 0.0-0.5, neighbor similarity (computed) */
  semantic_similarity: number;

  /** Similar Papers: List of related papers with scores */
  similar_papers: SimilarPaper[];
}

/**
 * Reference to a semantically similar paper
 */
export interface SimilarPaper {
  title: string;
  score: number;
  paperId?: string;
}

/**
 * A paper node in the 3D graph
 */
export interface PaperNode {
  id: string;
  title: string;
  path: string;
  authors?: string[];
  year?: number;

  // All 8 dimensions
  dimensions: Dimension;

  // Computed for visualization
  position?: { x: number; y: number; z: number };
  color?: number; // Hue for domain clustering
  size?: number; // Scale factor based on completion
  opacity?: number; // Based on recency
}

/**
 * Edge connecting two papers via semantic similarity
 */
export interface GraphEdge {
  source: string; // PaperNode id
  target: string; // PaperNode id
  similarity: number; // Weight
  width?: number; // Visual width
  color?: number; // Average hue of endpoints
}

/**
 * Complete graph data structure
 */
export interface GraphData {
  nodes: PaperNode[];
  edges: GraphEdge[];
  metadata: {
    totalPapers: number;
    totalEdges: number;
    avgConnectivity: number;
    domainDistribution: Record<string, number>;
    loadedAt: number;
  };
}

/**
 * Statistics about the current graph view
 */
export interface GraphStatistics {
  visiblePapers: number;
  visibleEdges: number;
  avgConnectivity: number;
  domainDistribution: Record<string, number>;
  selectedPaper?: PaperNode;
}

/**
 * Filter state for the graph
 */
export interface GraphFilters {
  connectivityMin: number;
  connectivityMax: number;

  conceptualDepthMin: number;
  conceptualDepthMax: number;

  temporalMin: number;
  temporalMax: number;

  completionMin: number;
  completionMax: number;

  recencyMin: number;
  recencyMax: number;

  domains: string[]; // Selected domain filters

  searchQuery: string; // Text search in titles
}
