import { App, TFile, Notice } from 'obsidian';
import { GraphData, PaperNode, GraphEdge, Dimension, SimilarPaper } from './types/Paper';

/** Configuration for dynamic paper ingestion */
interface DynamicIngestionConfig {
  debounceMs: number;
  notifyChanges: (paper: PaperNode) => void;
}

/**
 * YAML frontmatter parser for extracting paper metadata
 */
function parseFrontmatter(content: string): Record<string, any> {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) {
    return {};
  }

  const frontmatter: Record<string, any> = {};
  const lines = match[1].split('\n');

  let currentKey: string | null = null;
  let currentList: any[] = [];

  for (const line of lines) {
    if (!line.trim()) continue;

    // Handle nested YAML (dimensions:)
    if (line.match(/^\w+:\s*$/)) {
      if (currentKey) {
        frontmatter[currentKey] = currentList.length > 0 ? currentList : true;
        currentList = [];
      }
      currentKey = line.slice(0, -1);
      frontmatter[currentKey] = {};
      continue;
    }

    // Handle indented values (dimension sub-properties)
    if (line.startsWith('  ') && currentKey) {
      const match = line.trim().match(/^(\w+):\s*(.+?)$/);
      if (match) {
        const [, key, value] = match;
        if (typeof frontmatter[currentKey] === 'object' && !Array.isArray(frontmatter[currentKey])) {
          const numVal = parseFloat(value);
          frontmatter[currentKey][key] = isNaN(numVal) ? value : numVal;
        }
      }
      continue;
    }

    // Handle top-level key-value pairs
    const kvMatch = line.match(/^(\w+):\s*(.+?)$/);
    if (kvMatch) {
      const [, key, value] = kvMatch;
      currentKey = key;

      // Try parsing as JSON (for arrays)
      if (value.startsWith('[')) {
        try {
          frontmatter[key] = JSON.parse(value);
          continue;
        } catch {
          // Fall through to string parsing
        }
      }

      // Parse boolean
      if (value === 'true' || value === 'false') {
        frontmatter[key] = value === 'true';
        continue;
      }

      // Parse number
      const numVal = parseFloat(value);
      if (!isNaN(numVal) && !value.includes('"')) {
        frontmatter[key] = numVal;
        continue;
      }

      // Store as string
      frontmatter[key] = value.replace(/^["']|["']$/g, '');
    }
  }

  return frontmatter;
}

/**
 * Extract 8 dimensions from paper frontmatter
 * Returns defaults if any dimension is missing
 */
function extractDimensions(frontmatter: Record<string, any>): Dimension {
  // Try to get dimensions from nested dimensions object first
  const dims = frontmatter.dimensions || {};

  // Handle both nested and top-level dimension properties
  const connectivity = dims.connectivity ?? frontmatter.connectivity ?? 0.5;
  const conceptual_depth = dims.conceptual_depth ?? frontmatter.conceptual_depth ?? 0.5;
  const temporal = dims.temporal ?? frontmatter.temporal ?? 0.5;
  const cross_domain = dims.cross_domain ?? frontmatter.cross_domain ?? 5;
  const completion = dims.completion ?? frontmatter.completion ?? 50;
  const recency = dims.recency ?? frontmatter.recency ?? 0.5;
  const semantic_similarity = 0.0; // Computed later
  const similar_papers = extractSimilarPapers(frontmatter);

  return {
    connectivity: Math.max(0, Math.min(1, Number(connectivity))),
    conceptual_depth: Math.max(0, Math.min(1, Number(conceptual_depth))),
    temporal: Math.max(0, Math.min(1, Number(temporal))),
    cross_domain: Math.max(1, Math.min(15, Number(cross_domain))),
    completion: Math.max(0, Math.min(100, Number(completion))),
    recency: Math.max(0, Math.min(1, Number(recency))),
    semantic_similarity,
    similar_papers,
  };
}

/**
 * Extract similar papers list from frontmatter
 */
function extractSimilarPapers(frontmatter: Record<string, any>): SimilarPaper[] {
  const similarPapersData = frontmatter.similar_papers;

  if (!similarPapersData) {
    return [];
  }

  // Handle array of titles/ids
  if (Array.isArray(similarPapersData)) {
    return similarPapersData.map((item, index) => ({
      title: typeof item === 'string' ? item : item.title || 'Unknown',
      paperId: typeof item === 'string' ? item : item.paperId,
      score: 0.8 - index * 0.1, // Decrease score for ranked similarity
    }));
  }

  return [];
}

/**
 * Generate a unique ID from filename
 */
function generatePaperId(filename: string): string {
  return filename.replace(/\.md$/, '').replace(/\s+/g, '-').toLowerCase();
}

/**
 * Load all papers from vault and build graph data structure
 */
export async function loadPapersFromVault(app: App): Promise<GraphData> {
  const nodes: PaperNode[] = [];
  const edgeMap = new Map<string, GraphEdge>(); // Use map to avoid duplicate edges
  const papersPath = 'papers';

  try {
    // Get all markdown files in papers directory
    const files = app.vault.getFiles().filter((file) => {
      return file.path.startsWith(papersPath) && file.extension === 'md';
    });

    console.log(`Found ${files.length} paper files in ${papersPath}/`);

    if (files.length === 0) {
      console.warn('No papers found in papers/ directory');
    }

    // Load all papers
    for (const file of files) {
      try {
        const content = await app.vault.read(file);
        const frontmatter = parseFrontmatter(content);

        // Extract basic info
        const id = generatePaperId(file.basename);
        const title = frontmatter.title || file.basename.replace(/\.md$/, '').replace(/-/g, ' ');
        const dimensions = extractDimensions(frontmatter);

        // Build node
        const node: PaperNode = {
          id,
          title,
          path: file.path,
          year: frontmatter.date ? new Date(frontmatter.date).getFullYear() : undefined,
          authors: frontmatter.authors ? (Array.isArray(frontmatter.authors) ? frontmatter.authors : [frontmatter.authors]) : [],
          dimensions,
        };

        nodes.push(node);
      } catch (error) {
        console.error(`Error parsing paper ${file.path}:`, error);
      }
    }

    console.log(`Loaded ${nodes.length} papers successfully`);

    // Build edges from similar_papers relationships
    for (const node of nodes) {
      for (const similarPaper of node.dimensions.similar_papers) {
        const targetId = similarPaper.paperId || generatePaperId(similarPaper.title);
        const score = Math.max(0, Math.min(1, similarPaper.score ?? 0.7));

        // Create bidirectional edge
        const edgeKey = [node.id, targetId].sort().join('|');
        if (!edgeMap.has(edgeKey)) {
          edgeMap.set(edgeKey, {
            source: node.id,
            target: targetId,
            similarity: score,
          });
        }
      }
    }

    const edges = Array.from(edgeMap.values());

    // Calculate metadata
    const totalConnectivity = nodes.reduce((sum, node) => sum + node.dimensions.connectivity, 0);
    const avgConnectivity = nodes.length > 0 ? totalConnectivity / nodes.length : 0;

    const domainDistribution: Record<string, number> = {};
    for (const node of nodes) {
      const domain = Math.floor(node.dimensions.cross_domain);
      domainDistribution[`domain_${domain}`] = (domainDistribution[`domain_${domain}`] ?? 0) + 1;
    }

    const metadata = {
      totalPapers: nodes.length,
      totalEdges: edges.length,
      avgConnectivity,
      domainDistribution,
      loadedAt: Date.now(),
    };

    // Validate dimensions
    let missingDimensionCount = 0;
    for (const node of nodes) {
      const dims = node.dimensions;
      if (dims.connectivity === undefined || dims.conceptual_depth === undefined || dims.temporal === undefined || dims.cross_domain === undefined || dims.completion === undefined || dims.recency === undefined) {
        console.warn(`Paper ${node.id} missing some dimensions`);
        missingDimensionCount++;
      }
    }

    if (missingDimensionCount > 0) {
      console.warn(`${missingDimensionCount} papers have missing or default dimensions`);
    }

    console.log(`Graph loaded: ${nodes.length} papers, ${edges.length} edges, avg connectivity: ${avgConnectivity.toFixed(2)}`);

    return {
      nodes,
      edges,
      metadata,
    };
  } catch (error) {
    console.error('Error loading papers from vault:', error);
    throw error;
  }
}

/**
 * Validate all 8 dimensions are present in a paper
 */
export function validateDimensions(node: PaperNode): { valid: boolean; missing: string[] } {
  const required = ['connectivity', 'conceptual_depth', 'temporal', 'cross_domain', 'completion', 'recency', 'semantic_similarity', 'similar_papers'];
  const missing: string[] = [];

  for (const dim of required) {
    const key = dim as keyof Dimension;
    if (node.dimensions[key] === undefined) {
      missing.push(dim);
    }
  }

  return {
    valid: missing.length === 0,
    missing,
  };
}

/**
 * Get statistics about the loaded graph
 */
export function getGraphStatistics(data: GraphData) {
  const stats = {
    totalPapers: data.metadata.totalPapers,
    totalEdges: data.metadata.totalEdges,
    avgConnectivity: data.metadata.avgConnectivity.toFixed(3),
    avgCompletion: (data.nodes.reduce((sum, n) => sum + n.dimensions.completion, 0) / data.nodes.length).toFixed(1),
    avgRecency: (data.nodes.reduce((sum, n) => sum + n.dimensions.recency, 0) / data.nodes.length).toFixed(3),
    domainCount: Object.keys(data.metadata.domainDistribution).length,
    loadedAt: new Date(data.metadata.loadedAt).toISOString(),
  };

  console.log('Graph Statistics:', stats);
  return stats;
}

/**
 * Load a single paper from file (used for dynamic ingestion)
 * @param app Obsidian app
 * @param file Paper markdown file
 * @returns PaperNode or null
 */
export async function loadSinglePaper(app: App, file: TFile): Promise<PaperNode | null> {
  try {
    const content = await app.vault.read(file);
    const frontmatter = parseFrontmatter(content);

    // Extract basic info
    const id = generatePaperId(file.basename);
    const title = frontmatter.title || file.basename.replace(/\.md$/, '').replace(/-/g, ' ');
    const dimensions = extractDimensions(frontmatter);

    // Build node
    const node: PaperNode = {
      id,
      title,
      path: file.path,
      year: frontmatter.date ? new Date(frontmatter.date).getFullYear() : undefined,
      authors: frontmatter.authors ? (Array.isArray(frontmatter.authors) ? frontmatter.authors : [frontmatter.authors]) : [],
      dimensions,
    };

    return node;
  } catch (error) {
    console.error(`Error loading single paper ${file.path}:`, error);
    return null;
  }
}

/**
 * Add a paper to existing graph data (dynamic ingestion)
 * Recomputes edges for the new paper and updates metadata
 *
 * @param graphData Existing graph data
 * @param newPaper New paper to add
 * @param existingPaperMap Map of paper IDs for quick lookup
 * @returns Updated GraphData
 */
export function addPaperToGraph(
  graphData: GraphData,
  newPaper: PaperNode,
  existingPaperMap: Map<string, PaperNode>
): GraphData {
  // Check if paper already exists
  if (existingPaperMap.has(newPaper.id)) {
    console.warn(`Paper ${newPaper.id} already exists in graph`);
    return graphData;
  }

  // Add paper to nodes
  const updatedNodes = [...graphData.nodes, newPaper];
  existingPaperMap.set(newPaper.id, newPaper);

  // Build edges from new paper's similar_papers
  const newEdges = [...graphData.edges];
  const edgeSet = new Set(
    graphData.edges.map(e => [e.source, e.target].sort().join('|'))
  );

  for (const similarPaper of newPaper.dimensions.similar_papers) {
    const targetId = similarPaper.paperId || generatePaperId(similarPaper.title);
    const score = Math.max(0, Math.min(1, similarPaper.score ?? 0.7));

    const edgeKey = [newPaper.id, targetId].sort().join('|');
    if (!edgeSet.has(edgeKey) && existingPaperMap.has(targetId)) {
      newEdges.push({
        source: newPaper.id,
        target: targetId,
        similarity: score,
      });
      edgeSet.add(edgeKey);
    }
  }

  // Update metadata
  const totalConnectivity = updatedNodes.reduce((sum, node) => sum + node.dimensions.connectivity, 0);
  const avgConnectivity = updatedNodes.length > 0 ? totalConnectivity / updatedNodes.length : 0;

  const domainDistribution: Record<string, number> = {};
  for (const node of updatedNodes) {
    const domain = Math.floor(node.dimensions.cross_domain);
    domainDistribution[`domain_${domain}`] = (domainDistribution[`domain_${domain}`] ?? 0) + 1;
  }

  return {
    nodes: updatedNodes,
    edges: newEdges,
    metadata: {
      totalPapers: updatedNodes.length,
      totalEdges: newEdges.length,
      avgConnectivity,
      domainDistribution,
      loadedAt: Date.now(),
    },
  };
}

/**
 * Watch papers directory for new files and update graph dynamically
 * Returns an unsubscribe function to stop watching
 *
 * @param app Obsidian app
 * @param graphData Current graph data (will be updated)
 * @param onGraphUpdate Callback when graph is updated with new paper
 * @returns Unsubscribe function
 */
export function watchPapersDirectory(
  app: App,
  graphData: GraphData,
  onGraphUpdate: (updatedGraph: GraphData, newPaper: PaperNode) => void
): () => void {
  const existingPaperMap = new Map(graphData.nodes.map(n => [n.id, n]));
  const papersPath = 'papers';
  let debounceTimer: NodeJS.Timeout | null = null;
  const debounceMs = 100;

  const onModify = async (file: TFile) => {
    // Only watch papers directory
    if (!file.path.startsWith(papersPath) || file.extension !== 'md') {
      return;
    }

    // Debounce file changes
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    debounceTimer = setTimeout(async () => {
      try {
        const paper = await loadSinglePaper(app, file);
        if (!paper) return;

        const paperId = generatePaperId(file.basename);

        // Check if this is a new paper or update to existing
        if (existingPaperMap.has(paperId)) {
          console.log(`Updated existing paper: ${paperId}`);
          // In a full implementation, we'd update the paper in the graph
          // For now, just log it
          return;
        }

        console.log(`New paper detected: ${paperId}`);

        // Add paper to graph
        const updatedGraph = addPaperToGraph(graphData, paper, existingPaperMap);

        // Notify callback
        onGraphUpdate(updatedGraph, paper);

        // Show user notification
        new Notice(`📄 New paper loaded: ${paper.title}`);
      } catch (error) {
        console.error(`Error processing paper file ${file.path}:`, error);
      }
    }, debounceMs);
  };

  // Register vault event handler
  app.vault.on('create', onModify);
  app.vault.on('modify', onModify);

  // Return unsubscribe function
  return () => {
    app.vault.off('create', onModify);
    app.vault.off('modify', onModify);
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
  };
}
