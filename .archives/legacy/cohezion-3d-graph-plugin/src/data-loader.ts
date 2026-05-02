/**
 * Data loader for Cohezion 3D Knowledge Graph
 * Loads 84 papers with 8-dimensional semantic metadata
 */

export interface PaperDimensions {
  connectivity: number;
  cross_domain: number;
  completion: number;
  temporal: number;
  recency: number;
  conceptual_depth: number;
  theory_applied_balance?: number;
  abstraction_level?: number;
}

export interface SimilarPaper {
  paper: string;
  similarity: number;
}

export interface Paper {
  file_path: string;
  filename: string;
  title: string;
  dimensions: PaperDimensions;
  abstract: string;
  keywords: string[];
  similar_papers: SimilarPaper[];
}

export interface SemanticData {
  timestamp: string;
  papers: Paper[];
}

export class DataLoader {
  private papers: Map<string, Paper> = new Map();
  private graph: Map<string, Set<string>> = new Map();

  /**
   * Load semantic dimensions data from JSON
   */
  async loadData(jsonData: SemanticData): Promise<void> {
    console.log(`Loading ${jsonData.papers.length} papers...`);
    
    for (const paper of jsonData.papers) {
      this.papers.set(paper.filename, paper);
      
      // Build graph connections
      if (!this.graph.has(paper.filename)) {
        this.graph.set(paper.filename, new Set());
      }
      
      // Add edges to similar papers
      for (const similar of paper.similar_papers) {
        const from = this.graph.get(paper.filename)!;
        from.add(similar.paper);
        
        // Bidirectional edge
        if (!this.graph.has(similar.paper)) {
          this.graph.set(similar.paper, new Set());
        }
        this.graph.get(similar.paper)!.add(paper.filename);
      }
    }
    
    console.log(`✅ Loaded ${this.papers.size} papers with ${this.countEdges()} connections`);
  }

  /**
   * Get all papers for visualization
   */
  getPapers(): Paper[] {
    return Array.from(this.papers.values());
  }

  /**
   * Get paper by filename
   */
  getPaper(filename: string): Paper | undefined {
    return this.papers.get(filename);
  }

  /**
   * Get connected papers for a given paper
   */
  getConnections(filename: string): string[] {
    return Array.from(this.graph.get(filename) || []);
  }

  /**
   * Count total edges in the graph
   */
  private countEdges(): number {
    let count = 0;
    for (const connections of this.graph.values()) {
      count += connections.size;
    }
    return count / 2; // Undirected edges
  }

  /**
   * Get statistics about the loaded data
   */
  getStats() {
    const papers = Array.from(this.papers.values());
    const dimensionAverages: Record<string, number> = {
      connectivity: 0,
      cross_domain: 0,
      completion: 0,
      temporal: 0,
      recency: 0,
      conceptual_depth: 0,
    };

    for (const paper of papers) {
      Object.keys(dimensionAverages).forEach(key => {
        dimensionAverages[key] += (paper.dimensions[key as keyof PaperDimensions] || 0);
      });
    }

    Object.keys(dimensionAverages).forEach(key => {
      dimensionAverages[key] /= papers.length;
    });

    return {
      totalPapers: papers.length,
      totalConnections: this.countEdges(),
      dimensionAverages,
      keywords: this.extractAllKeywords(papers),
    };
  }

  /**
   * Extract all unique keywords from papers
   */
  private extractAllKeywords(papers: Paper[]): string[] {
    const keywordSet = new Set<string>();
    for (const paper of papers) {
      paper.keywords.forEach(k => keywordSet.add(k));
    }
    return Array.from(keywordSet).sort();
  }

  /**
   * Filter papers by dimension threshold
   */
  filterByDimension(
    dimension: keyof PaperDimensions,
    minValue: number
  ): Paper[] {
    return Array.from(this.papers.values()).filter(
      p => (p.dimensions[dimension] || 0) >= minValue
    );
  }

  /**
   * Search papers by keyword
   */
  searchByKeyword(keyword: string): Paper[] {
    const lowerKeyword = keyword.toLowerCase();
    return Array.from(this.papers.values()).filter(
      p => p.keywords.some(k => k.toLowerCase().includes(lowerKeyword)) ||
           p.title.toLowerCase().includes(lowerKeyword)
    );
  }
}

export default DataLoader;
