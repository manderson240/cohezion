/**
 * Dimension definitions for paper visualization
 * Each paper is enriched with 8 independent dimensions that map to visual properties
 *
 * @example
 * const dimension: Dimension = {
 *   connectivity: 0.75,           // Well-connected hub paper
 *   conceptual_depth: 0.3,        // Theory-focused
 *   temporal: 0.9,                // Recent work
 *   cross_domain: 8,              // Active across 8 domains
 *   completion: 85,               // Mature research
 *   recency: 0.95,                // Frequently accessed
 *   semantic_similarity: 0.42,    // Highly similar to neighbors
 *   similar_papers: [...]         // Related papers
 * }
 */
export interface Dimension {
  /**
   * Network Centrality (0-1 scale)
   * 0 = isolated paper (few connections), 1 = hub paper (many connections)
   * Maps to node X position in 3D space
   */
  connectivity: number;

  /**
   * Theory vs Applied balance (0-1 scale)
   * 0 = foundational theory, 1 = practical application
   * Maps to node Y position in 3D space
   */
  conceptual_depth: number;

  /**
   * Historical vs Recent timeline (0-1 scale)
   * 0 = classic/historical papers, 1 = cutting-edge recent work
   * Maps to node Z position in 3D space
   */
  temporal: number;

  /**
   * Cross-domain presence count (1-15 scale)
   * Number of research domains this paper appears in
   * Maps to node hue/color for visual clustering
   */
  cross_domain: number;

  /**
   * Research maturity percentage (0-100 scale)
   * 0% = emerging topic, 100% = mature, well-studied field
   * Maps to node size (0.5x to 2.0x scale factor)
   */
  completion: number;

  /**
   * Freshness/Recency (0-1 scale)
   * 0 = not recently accessed, 1 = recently accessed/updated
   * Maps to node opacity (30% to 100% transparency)
   */
  recency: number;

  /**
   * Average semantic similarity to neighbors (0.0-0.5 scale)
   * 0.0 = unique content, 0.5 = highly similar to neighbors
   * Used to compute edge weight and visual appearance
   */
  semantic_similarity: number;

  /**
   * List of semantically similar papers with their similarity scores
   * Used to create edges in the graph and show relationships
   */
  similar_papers: SimilarPaper[];

  /**
   * Phase 3: Technical complexity of methods (0-1 scale)
   * 0 = simple overview, 1 = novel algorithms/proofs
   */
  algorithm_complexity?: number;

  /**
   * Phase 3: Practical implementation difficulty (0-1 scale)
   * 0 = conceptual only, 1 = requires specialized expertise
   */
  implementation_difficulty?: number;

  /**
   * Phase 4: Impact score based on vault connectivity (0-1 scale)
   * Proxy for citation count / influence
   */
  impact_score?: number;

  /**
   * Phase 4: Cross-domain transfer potential (0-1 scale)
   * 0 = domain-specific, 1 = broadly applicable
   */
  interdisciplinary_transfer?: number;
}

/**
 * Reference to a semantically similar paper
 * Used to define edges in the graph and show relationships
 *
 * @example
 * {
 *   title: "Knowledge Graphs in NLP",
 *   score: 0.85,
 *   paperId: "paper-42"
 * }
 */
export interface SimilarPaper {
  /** Title of the similar paper */
  title: string;

  /** Semantic similarity score (0-1, typically 0.5-1.0 for significant similarity) */
  score: number;

  /** Optional ID reference for this paper (if loaded in graph) */
  paperId?: string;
}

/**
 * A paper node in the 3D graph
 * Represents a single research paper with metadata and computed visual properties
 *
 * The plugin loads papers from vault YAML frontmatter and computes position,
 * color, size, and opacity based on the 8 dimensions.
 *
 * @example
 * {
 *   id: "paper-42",
 *   title: "Knowledge Graphs for AI",
 *   path: "papers/ai/knowledge-graphs.md",
 *   authors: ["Alice", "Bob"],
 *   year: 2023,
 *   dimensions: { ... },
 *   position: { x: 150, y: -50, z: 200 },
 *   color: 240,      // HSL hue: 240° (blue)
 *   size: 1.5,       // 1.5x scale based on completion
 *   opacity: 0.95    // 95% opaque based on recency
 * }
 */
export interface PaperNode {
  /** Unique identifier for this paper */
  id: string;

  /** Full title of the paper */
  title: string;

  /** Vault file path to the paper note */
  path: string;

  /** Authors of the paper (optional) */
  authors?: string[];

  /** Publication year (optional) */
  year?: number;

  /** All 8 dimensions enriching this paper */
  dimensions: Dimension;

  /** 3D position in space (computed by ForceLayout) */
  position?: { x: number; y: number; z: number };

  /** X coordinate in 3D space (for direct access by ForceLayout) */
  x?: number;

  /** Y coordinate in 3D space (for direct access by ForceLayout) */
  y?: number;

  /** Z coordinate in 3D space (for direct access by ForceLayout) */
  z?: number;

  /** HSL hue value for color (0-360) based on cross_domain */
  color?: number;

  /** Scale factor (0.5-2.0) based on completion percentage */
  size?: number;

  /** Opacity (0.3-1.0) based on recency */
  opacity?: number;

  /** IDs of decisions that reference this paper (Phase 2: Paper Integration) */
  decision_ids?: string[];

  /** Timestamp when decisions were linked (for dynamic ingestion) */
  decision_links_updated_at?: string;
}

/**
 * Edge connecting two papers via semantic similarity
 * Edges represent semantic relationships between papers
 *
 * @example
 * {
 *   source: "paper-10",
 *   target: "paper-42",
 *   similarity: 0.85,
 *   width: 3,
 *   color: 250
 * }
 */
export interface GraphEdge {
  /** Source paper ID */
  source: string;

  /** Target paper ID */
  target: string;

  /** Similarity weight (0-1, typically 0.5-1.0) determines edge importance */
  similarity: number;

  /** Visual width of edge (computed based on similarity) */
  width?: number;

  /** Average hue of source and target nodes (for visual consistency) */
  color?: number;
}

/**
 * Complete graph data structure
 * Represents all papers and their relationships
 *
 * This is the central data structure passed between components:
 * DataLoader → GraphData → ForceLayout → ThreeRenderer
 */
export interface GraphData {
  /** Array of all paper nodes (84 papers in typical vault) */
  nodes: PaperNode[];

  /** Array of all semantic connections between papers (~300-500 edges) */
  edges: GraphEdge[];

  /** Metadata about the graph */
  metadata: {
    /** Total number of papers loaded */
    totalPapers: number;

    /** Total number of edges (connections) */
    totalEdges: number;

    /** Average connectivity across all papers (0-1) */
    avgConnectivity: number;

    /** Distribution of papers across domains (domain → count) */
    domainDistribution: Record<string, number>;

    /** Timestamp when graph was loaded */
    loadedAt: number;
  };
}

/**
 * Statistics about the current graph view
 * Computed from the current filters and visible nodes
 *
 * Used to show overview info and guide user exploration
 */
export interface GraphStatistics {
  /** Number of papers visible after filtering */
  visiblePapers: number;

  /** Number of edges visible after filtering */
  visibleEdges: number;

  /** Average connectivity of visible papers */
  avgConnectivity: number;

  /** Domain distribution of visible papers */
  domainDistribution: Record<string, number>;

  /** Currently selected paper (if any) */
  selectedPaper?: PaperNode;
}

/**
 * Filter state for the graph
 * Determines which papers and edges are visible
 *
 * All filters are inclusive (AND logic):
 * A paper is visible if it matches ALL active filters
 *
 * @example
 * {
 *   connectivityMin: 0.3,
 *   connectivityMax: 1.0,
 *   conceptualDepthMin: 0,
 *   conceptualDepthMax: 1,
 *   temporalMin: 0.5,        // Only recent papers
 *   temporalMax: 1.0,
 *   completionMin: 50,       // Only mature research
 *   completionMax: 100,
 *   recencyMin: 0.2,
 *   recencyMax: 1.0,
 *   domains: ["NLP", "AI"],  // Only papers in these domains
 *   searchQuery: "knowledge graph"  // Title contains this text
 * }
 */
export interface GraphFilters {
  /** Connectivity range filter (min, 0-1) */
  connectivityMin: number;

  /** Connectivity range filter (max, 0-1) */
  connectivityMax: number;

  /** Conceptual depth range filter (min, 0-1) */
  conceptualDepthMin: number;

  /** Conceptual depth range filter (max, 0-1) */
  conceptualDepthMax: number;

  /** Temporal range filter (min, 0-1) */
  temporalMin: number;

  /** Temporal range filter (max, 0-1) */
  temporalMax: number;

  /** Completion range filter (min, 0-100%) */
  completionMin: number;

  /** Completion range filter (max, 0-100%) */
  completionMax: number;

  /** Recency range filter (min, 0-1) */
  recencyMin: number;

  /** Recency range filter (max, 0-1) */
  recencyMax: number;

  /** Selected domain names (empty = all domains) */
  domains: string[];

  /** Text search query (searches paper titles) */
  searchQuery: string;
}
