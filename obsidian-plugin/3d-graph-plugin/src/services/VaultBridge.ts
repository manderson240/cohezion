import { Vault, TFile } from 'obsidian';
import { Decision } from '../types/Decision';
import YAML from 'js-yaml';

/**
 * Vault Bridge for Decision Analysis (Phase 4)
 *
 * Reads decision notes from the vault and extracts decision metadata
 * from YAML frontmatter. Supports dynamic reloading when vault changes.
 *
 * @example
 * const bridge = new VaultBridge(vault);
 * const decisions = await bridge.loadAllDecisions();
 * bridge.watchForChanges(() => {
 *   console.log('Decisions updated');
 * });
 */
export class VaultBridge {
  private vault: Vault;
  private decisionCache: Map<string, Decision> = new Map();
  private lastLoadTime: number = 0;

  constructor(vault: Vault) {
    this.vault = vault;
  }

  /**
   * Parse YAML frontmatter from a decision note
   * @param content File content (with frontmatter)
   * @returns Parsed frontmatter object
   */
  private parseFrontmatter(content: string): Record<string, any> {
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) {
      return {};
    }

    try {
      return YAML.load(match[1]) as Record<string, any>;
    } catch (error) {
      console.error('YAML parse error:', error);
      return {};
    }
  }

  /**
   * Extract decision from file
   * @param file Markdown file
   * @returns Decision object or null
   */
  private async extractDecisionFromFile(file: TFile): Promise<Decision | null> {
    try {
      const content = await this.vault.read(file);
      const frontmatter = this.parseFrontmatter(content);

      // Check if this is a decision note
      if (!frontmatter.title || frontmatter.tags?.indexOf('decision') === -1) {
        return null;
      }

      // Extract decision_reasoning section if it exists
      const reasoning = frontmatter.decision_reasoning || {};

      const decision: Decision = {
        id: file.basename,
        title: frontmatter.title || file.basename,
        chosen_option: reasoning.chosen_option || '',
        rationale: reasoning.rationale || '',
        reasoning_type: reasoning.reasoning_type || 'hybrid',
        confidence_score: reasoning.confidence_score ?? 0.5,
        reasoning_chain: {
          id: `chain-${file.basename}`,
          decision_id: file.basename,
          steps: reasoning.steps || [],
          reasoning_type: reasoning.reasoning_type || 'hybrid',
          confidence: reasoning.confidence_score ?? 0.5,
          assumptions: reasoning.assumptions || [],
          timestamp: frontmatter.date || new Date().toISOString(),
        },
        alternatives_rejected: reasoning.alternatives_rejected || [],
        related_papers: frontmatter.related_papers || [],
        status: frontmatter.status || 'proposed',
        timestamp: frontmatter.date || new Date().toISOString(),
        vault_path: file.path,
      };

      return decision;
    } catch (error) {
      console.error(`Error extracting decision from ${file.path}:`, error);
      return null;
    }
  }

  /**
   * Load all decision notes from vault
   * @returns Map of decision_id → Decision
   */
  async loadAllDecisions(): Promise<Map<string, Decision>> {
    try {
      const decisionsFolder = this.vault.getAbstractFileByPath('decisions');
      if (!decisionsFolder || !('children' in decisionsFolder)) {
        console.warn('Decisions folder not found');
        return new Map();
      }

      const decisions = new Map<string, Decision>();
      const files = (decisionsFolder as any).children || [];

      for (const file of files) {
        if (!(file instanceof TFile) || file.extension !== 'md') {
          continue;
        }

        const decision = await this.extractDecisionFromFile(file);
        if (decision) {
          decisions.set(decision.id, decision);
        }
      }

      this.decisionCache = decisions;
      this.lastLoadTime = Date.now();

      console.log(`Loaded ${decisions.size} decisions from vault`);
      return decisions;
    } catch (error) {
      console.error('Error loading decisions:', error);
      return new Map();
    }
  }

  /**
   * Get a single decision by ID
   * @param decisionId Decision ID
   * @returns Decision or null
   */
  async getDecision(decisionId: string): Promise<Decision | null> {
    // Check cache first
    if (this.decisionCache.has(decisionId)) {
      return this.decisionCache.get(decisionId) || null;
    }

    // Try to load from vault
    try {
      const file = this.vault.getAbstractFileByPath(`decisions/${decisionId}.md`);
      if (file instanceof TFile) {
        return await this.extractDecisionFromFile(file);
      }
    } catch (error) {
      console.error(`Error loading decision ${decisionId}:`, error);
    }

    return null;
  }

  /**
   * Find decisions related to a paper
   * @param paperTitle Paper title to search for
   * @returns Array of related decisions
   */
  async findDecisionsForPaper(paperTitle: string): Promise<Decision[]> {
    const related: Decision[] = [];

    for (const decision of this.decisionCache.values()) {
      if (decision.related_papers?.some(p => p.includes(paperTitle))) {
        related.push(decision);
      }
    }

    return related;
  }

  /**
   * Get decisions filtered by criteria
   * @param filter Filter function
   * @returns Filtered decisions
   */
  getDecisionsByFilter(filter: (d: Decision) => boolean): Decision[] {
    const results: Decision[] = [];
    for (const decision of this.decisionCache.values()) {
      if (filter(decision)) {
        results.push(decision);
      }
    }
    return results;
  }

  /**
   * Get all decisions with reasoning type filter
   * @param type Reasoning type
   * @returns Decisions with that type
   */
  getDecisionsByReasoningType(
    type: 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid'
  ): Decision[] {
    return this.getDecisionsByFilter(d => d.reasoning_type === type);
  }

  /**
   * Get all decisions with minimum confidence
   * @param minConfidence Minimum confidence threshold
   * @returns High-confidence decisions
   */
  getHighConfidenceDecisions(minConfidence: number = 0.8): Decision[] {
    return this.getDecisionsByFilter(d => d.confidence_score >= minConfidence);
  }

  /**
   * Watch for changes in decisions folder
   * @param callback Function to call when changes detected
   * @returns Unsubscribe function
   */
  watchForChanges(callback: () => void): () => void {
    const onModify = async (file: TFile) => {
      if (file.path.startsWith('decisions/') && file.extension === 'md') {
        // Reload this decision
        const decision = await this.extractDecisionFromFile(file);
        if (decision) {
          this.decisionCache.set(decision.id, decision);
        } else {
          this.decisionCache.delete(file.basename);
        }
        callback();
      }
    };

    const onDelete = (file: TFile) => {
      if (file.path.startsWith('decisions/') && file.extension === 'md') {
        this.decisionCache.delete(file.basename);
        callback();
      }
    };

    // Register vault event handlers
    this.vault.on('modify', onModify);
    this.vault.on('delete', onDelete);

    // Return unsubscribe function
    return () => {
      this.vault.off('modify', onModify);
      this.vault.off('delete', onDelete);
    };
  }

  /**
   * Get cache statistics
   * @returns Cache info
   */
  getCacheStats(): { size: number; lastLoadTime: string } {
    return {
      size: this.decisionCache.size,
      lastLoadTime: new Date(this.lastLoadTime).toISOString(),
    };
  }

  /**
   * Clear cache (forces reload on next access)
   */
  clearCache(): void {
    this.decisionCache.clear();
    this.lastLoadTime = 0;
  }
}
