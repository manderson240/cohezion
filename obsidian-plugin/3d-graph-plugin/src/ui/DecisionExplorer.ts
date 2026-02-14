import { App, PluginSettingTab, Setting, Notice, SearchComponent } from 'obsidian';
import { Decision } from '../types/Decision';
import { SurrealDBClient } from '../services/SurrealDBClient';
import { VaultBridge } from '../services/VaultBridge';
import { ReasoningFlowchart } from '../visualizations/ReasoningFlowchart';
import { CascadeGraph } from '../visualizations/CascadeGraph';
import { ContradictionMatrix } from '../visualizations/ContradictionMatrix';

/**
 * Decision Explorer Panel for Phase 4
 *
 * Main UI component for exploring decisions and their reasoning chains.
 * Provides:
 * - Decision search with autocomplete
 * - Reasoning chain visualization
 * - Cascade impact analysis
 * - Contradiction detection
 * - Metadata display
 *
 * @example
 * const explorer = new DecisionExplorer(app, surrealClient, vaultBridge);
 * explorer.loadPanel(containerElement);
 */
export class DecisionExplorer {
  private app: App;
  private surrealClient: SurrealDBClient;
  private vaultBridge: VaultBridge;
  private decisions: Map<string, Decision> = new Map();
  private selectedDecision: Decision | null = null;
  private containerEl: HTMLElement | null = null;

  constructor(app: App, surrealClient: SurrealDBClient, vaultBridge: VaultBridge) {
    this.app = app;
    this.surrealClient = surrealClient;
    this.vaultBridge = vaultBridge;
  }

  /**
   * Load all decisions from vault
   */
  async loadDecisions(): Promise<void> {
    try {
      this.decisions = await this.vaultBridge.loadAllDecisions();
      console.log(`Loaded ${this.decisions.size} decisions for explorer`);
    } catch (error) {
      console.error('Error loading decisions:', error);
      new Notice('Failed to load decisions from vault');
    }
  }

  /**
   * Create and attach the explorer panel to a container
   */
  loadPanel(containerEl: HTMLElement): void {
    this.containerEl = containerEl;
    containerEl.empty();
    containerEl.addClass('decision-explorer-panel');

    // Create main sections
    this.createSearchSection(containerEl);
    this.createMetadataSection(containerEl);
    this.createActionButtons(containerEl);
  }

  /**
   * Create search and selection section
   */
  private createSearchSection(containerEl: HTMLElement): void {
    const searchDiv = containerEl.createDiv('decision-search-section');
    searchDiv.style.paddingBottom = '20px';
    searchDiv.style.borderBottom = '1px solid #ddd';

    // Header
    const header = searchDiv.createEl('h3');
    header.textContent = 'Decision Explorer';
    header.style.marginBottom = '15px';

    // Search input
    const searchContainer = searchDiv.createDiv('decision-search-container');
    const input = searchContainer.createEl('input', { type: 'text' });
    input.placeholder = 'Search decisions...';
    input.style.width = '100%';
    input.style.padding = '8px 12px';
    input.style.border = '1px solid #ccc';
    input.style.borderRadius = '4px';
    input.style.marginBottom = '10px';
    input.style.fontFamily = 'inherit';

    // Results dropdown
    const resultsDiv = searchContainer.createDiv('decision-results');
    resultsDiv.style.maxHeight = '300px';
    resultsDiv.style.overflow = 'auto';
    resultsDiv.style.border = '1px solid #ddd';
    resultsDiv.style.borderRadius = '4px';
    resultsDiv.style.backgroundColor = '#fff';
    resultsDiv.style.display = 'none';

    // Handle search input
    input.addEventListener('input', (e) => {
      const query = (e.target as HTMLInputElement).value.toLowerCase();

      if (query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
      }

      resultsDiv.empty();
      resultsDiv.style.display = 'block';

      // Search decisions
      let count = 0;
      for (const [id, decision] of this.decisions) {
        if (
          decision.title.toLowerCase().includes(query) ||
          id.toLowerCase().includes(query) ||
          decision.chosen_option.toLowerCase().includes(query)
        ) {
          if (count >= 10) break; // Limit results

          const resultItem = resultsDiv.createDiv('decision-result-item');
          resultItem.style.padding = '10px';
          resultItem.style.borderBottom = '1px solid #eee';
          resultItem.style.cursor = 'pointer';
          resultItem.style.fontSize = '0.9em';

          const titleSpan = resultItem.createEl('strong');
          titleSpan.textContent = decision.title;

          const idSpan = resultItem.createEl('div');
          idSpan.style.fontSize = '0.8em';
          idSpan.style.color = '#999';
          idSpan.textContent = id;

          const confidenceSpan = resultItem.createEl('span');
          confidenceSpan.style.float = 'right';
          confidenceSpan.style.fontSize = '0.8em';
          confidenceSpan.style.color = '#666';
          confidenceSpan.textContent = `${(decision.confidence_score * 100).toFixed(0)}%`;

          resultItem.onmouseenter = () => {
            resultItem.style.backgroundColor = '#f0f0f0';
          };
          resultItem.onmouseleave = () => {
            resultItem.style.backgroundColor = 'transparent';
          };

          resultItem.onclick = () => {
            this.selectDecision(decision);
            resultsDiv.style.display = 'none';
            input.value = '';
          };

          count++;
        }
      }

      if (count === 0) {
        const noResults = resultsDiv.createDiv();
        noResults.textContent = 'No decisions found';
        noResults.style.padding = '10px';
        noResults.style.color = '#999';
        noResults.style.textAlign = 'center';
      }
    });

    // Recent decisions list
    const recentDiv = searchDiv.createDiv('decision-recent');
    recentDiv.style.marginTop = '15px';

    const recentHeader = recentDiv.createEl('small');
    recentHeader.textContent = 'Recent Decisions';
    recentHeader.style.display = 'block';
    recentHeader.style.color = '#666';
    recentHeader.style.marginBottom = '8px';
    recentHeader.style.fontWeight = 'bold';

    // Show 5 most recent
    const recent = Array.from(this.decisions.values())
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 5);

    for (const decision of recent) {
      const item = recentDiv.createEl('button');
      item.textContent = decision.title;
      item.style.display = 'block';
      item.style.width = '100%';
      item.style.padding = '6px 8px';
      item.style.marginBottom = '4px';
      item.style.border = '1px solid #ddd';
      item.style.borderRadius = '3px';
      item.style.backgroundColor = '#f9f9f9';
      item.style.cursor = 'pointer';
      item.style.fontSize = '0.85em';
      item.style.textAlign = 'left';

      item.onmouseenter = () => {
        item.style.backgroundColor = '#e8e8e8';
      };
      item.onmouseleave = () => {
        item.style.backgroundColor = '#f9f9f9';
      };

      item.onclick = (e) => {
        e.preventDefault();
        this.selectDecision(decision);
      };
    }
  }

  /**
   * Create metadata display section
   */
  private createMetadataSection(containerEl: HTMLElement): void {
    const metadataDiv = containerEl.createDiv('decision-metadata-section');
    metadataDiv.style.padding = '20px 0';
    metadataDiv.style.borderBottom = '1px solid #ddd';

    metadataDiv.id = 'decision-metadata';

    if (!this.selectedDecision) {
      const placeholder = metadataDiv.createDiv();
      placeholder.textContent = 'Select a decision to view details';
      placeholder.style.color = '#999';
      placeholder.style.textAlign = 'center';
      placeholder.style.padding = '40px 0';
      return;
    }

    // Decision title
    const titleDiv = metadataDiv.createDiv();
    const titleEl = titleDiv.createEl('h4');
    titleEl.textContent = this.selectedDecision.title;
    titleEl.style.marginBottom = '10px';

    // Key metadata
    const metaGrid = metadataDiv.createDiv('decision-meta-grid');
    metaGrid.style.display = 'grid';
    metaGrid.style.gridTemplateColumns = '1fr 1fr';
    metaGrid.style.gap = '10px';
    metaGrid.style.marginBottom = '15px';

    // Chosen option
    const optionDiv = metaGrid.createDiv();
    optionDiv.innerHTML = `
      <small style="color: #666;">Chosen Option</small>
      <div style="font-weight: bold; margin-top: 4px;">${this.selectedDecision.chosen_option}</div>
    `;

    // Reasoning type
    const typeDiv = metaGrid.createDiv();
    const typeBadge = typeDiv.createEl('small');
    typeBadge.textContent = 'Reasoning Type';
    typeBadge.style.display = 'block';
    typeBadge.style.color = '#666';
    typeBadge.style.marginBottom = '4px';
    const typeName = typeDiv.createEl('span');
    typeName.textContent = this.selectedDecision.reasoning_type;
    typeName.className = `reasoning-badge reasoning-${this.selectedDecision.reasoning_type}`;
    typeName.style.padding = '2px 6px';
    typeName.style.borderRadius = '3px';
    typeName.style.fontSize = '0.85em';
    typeName.style.fontWeight = 'bold';
    typeName.style.display = 'inline-block';

    // Confidence score with bar
    const confDiv = metaGrid.createDiv();
    confDiv.innerHTML = `
      <small style="color: #666;">Confidence Score</small>
      <div style="font-weight: bold; margin-top: 4px;">
        ${(this.selectedDecision.confidence_score * 100).toFixed(1)}%
      </div>
    `;
    const confBar = confDiv.createDiv();
    confBar.style.width = '100%';
    confBar.style.height = '6px';
    confBar.style.backgroundColor = '#eee';
    confBar.style.borderRadius = '3px';
    confBar.style.marginTop = '4px';
    confBar.style.overflow = 'hidden';
    const confFill = confBar.createDiv();
    confFill.style.height = '100%';
    confFill.style.width = `${this.selectedDecision.confidence_score * 100}%`;
    confFill.style.backgroundColor = this.getConfidenceColor(this.selectedDecision.confidence_score);
    confFill.style.transition = 'width 0.3s ease';

    // Status
    const statusDiv = metaGrid.createDiv();
    const statusBadge = statusDiv.createEl('small');
    statusBadge.textContent = 'Status';
    statusBadge.style.display = 'block';
    statusBadge.style.color = '#666';
    statusBadge.style.marginBottom = '4px';
    const statusName = statusDiv.createEl('span');
    statusName.textContent = this.selectedDecision.status;
    statusName.style.padding = '2px 6px';
    statusName.style.borderRadius = '3px';
    statusName.style.fontSize = '0.85em';
    statusName.style.fontWeight = 'bold';
    statusName.style.display = 'inline-block';
    statusName.style.backgroundColor = this.getStatusColor(this.selectedDecision.status);
    statusName.style.color = '#fff';

    // Rationale
    if (this.selectedDecision.rationale) {
      const rationaleDiv = metadataDiv.createDiv();
      rationaleDiv.style.marginTop = '15px';
      const rationaleLabel = rationaleDiv.createEl('small');
      rationaleLabel.textContent = 'Rationale';
      rationaleLabel.style.display = 'block';
      rationaleLabel.style.color = '#666';
      rationaleLabel.style.fontWeight = 'bold';
      rationaleLabel.style.marginBottom = '6px';
      const rationaleContent = rationaleDiv.createDiv();
      rationaleContent.innerHTML = this.selectedDecision.rationale;
      rationaleContent.style.fontSize = '0.9em';
      rationaleContent.style.lineHeight = '1.5';
      rationaleContent.style.color = '#555';
      rationaleContent.style.padding = '10px';
      rationaleContent.style.backgroundColor = '#f9f9f9';
      rationaleContent.style.borderRadius = '3px';
    }

    // Alternatives
    if (this.selectedDecision.alternatives_rejected && this.selectedDecision.alternatives_rejected.length > 0) {
      const altDiv = metadataDiv.createDiv();
      altDiv.style.marginTop = '15px';
      const altLabel = altDiv.createEl('small');
      altLabel.textContent = 'Alternatives Rejected';
      altLabel.style.display = 'block';
      altLabel.style.color = '#666';
      altLabel.style.fontWeight = 'bold';
      altLabel.style.marginBottom = '6px';
      const altList = altDiv.createEl('ul');
      altList.style.margin = '0';
      altList.style.paddingLeft = '20px';
      altList.style.fontSize = '0.9em';
      for (const alt of this.selectedDecision.alternatives_rejected) {
        altList.createEl('li').textContent = alt;
      }
    }
  }

  /**
   * Create action buttons
   */
  private createActionButtons(containerEl: HTMLElement): void {
    if (!this.selectedDecision) {
      return;
    }

    const buttonDiv = containerEl.createDiv('decision-action-buttons');
    buttonDiv.style.padding = '20px 0';
    buttonDiv.style.display = 'grid';
    buttonDiv.style.gridTemplateColumns = '1fr 1fr';
    buttonDiv.style.gap = '10px';

    // View Reasoning Chain
    const reasoningBtn = buttonDiv.createEl('button');
    reasoningBtn.textContent = '🔗 View Reasoning Chain';
    reasoningBtn.style.padding = '10px 15px';
    reasoningBtn.style.border = '1px solid #3b82f6';
    reasoningBtn.style.borderRadius = '4px';
    reasoningBtn.style.backgroundColor = '#3b82f6';
    reasoningBtn.style.color = '#fff';
    reasoningBtn.style.cursor = 'pointer';
    reasoningBtn.style.fontWeight = 'bold';

    reasoningBtn.onclick = async () => {
      const flowchart = new ReasoningFlowchart(this.app, this.selectedDecision!);
      flowchart.open();
    };

    reasoningBtn.onmouseenter = () => {
      reasoningBtn.style.backgroundColor = '#2563eb';
    };
    reasoningBtn.onmouseleave = () => {
      reasoningBtn.style.backgroundColor = '#3b82f6';
    };

    // View Cascades
    const cascadeBtn = buttonDiv.createEl('button');
    cascadeBtn.textContent = '📊 View Cascades';
    cascadeBtn.style.padding = '10px 15px';
    cascadeBtn.style.border = '1px solid #10b981';
    cascadeBtn.style.borderRadius = '4px';
    cascadeBtn.style.backgroundColor = '#10b981';
    cascadeBtn.style.color = '#fff';
    cascadeBtn.style.cursor = 'pointer';
    cascadeBtn.style.fontWeight = 'bold';

    cascadeBtn.onclick = async () => {
      try {
        const result = await this.surrealClient.analyzeDecisionCascades(this.selectedDecision!.id, 3);
        if (result) {
          const graph = new CascadeGraph(this.app, this.selectedDecision!.id, result.cascades);
          graph.open();
        } else {
          new Notice('No cascade data available');
        }
      } catch (error) {
        console.error('Error loading cascades:', error);
        new Notice('Failed to load cascade data');
      }
    };

    cascadeBtn.onmouseenter = () => {
      cascadeBtn.style.backgroundColor = '#059669';
    };
    cascadeBtn.onmouseleave = () => {
      cascadeBtn.style.backgroundColor = '#10b981';
    };

    // View Contradictions
    const contradictionBtn = buttonDiv.createEl('button');
    contradictionBtn.textContent = '⚠️ View Contradictions';
    contradictionBtn.style.padding = '10px 15px';
    contradictionBtn.style.border = '1px solid #f59e0b';
    contradictionBtn.style.borderRadius = '4px';
    contradictionBtn.style.backgroundColor = '#f59e0b';
    contradictionBtn.style.color = '#fff';
    contradictionBtn.style.cursor = 'pointer';
    contradictionBtn.style.fontWeight = 'bold';

    contradictionBtn.onclick = async () => {
      try {
        const result = await this.surrealClient.detectContradictions(this.selectedDecision!.id);
        if (result) {
          const matrix = new ContradictionMatrix(this.app, this.selectedDecision!.id, result.contradictions);
          matrix.open();
        } else {
          new Notice('No contradictions found');
        }
      } catch (error) {
        console.error('Error loading contradictions:', error);
        new Notice('Failed to load contradiction data');
      }
    };

    contradictionBtn.onmouseenter = () => {
      contradictionBtn.style.backgroundColor = '#d97706';
    };
    contradictionBtn.onmouseleave = () => {
      contradictionBtn.style.backgroundColor = '#f59e0b';
    };

    // Open in Vault
    const vaultBtn = buttonDiv.createEl('button');
    vaultBtn.textContent = '📝 Open in Vault';
    vaultBtn.style.padding = '10px 15px';
    vaultBtn.style.border = '1px solid #8b5cf6';
    vaultBtn.style.borderRadius = '4px';
    vaultBtn.style.backgroundColor = '#8b5cf6';
    vaultBtn.style.color = '#fff';
    vaultBtn.style.cursor = 'pointer';
    vaultBtn.style.fontWeight = 'bold';

    vaultBtn.onclick = () => {
      if (this.selectedDecision?.vault_path) {
        const file = this.app.vault.getAbstractFileByPath(this.selectedDecision.vault_path);
        if (file) {
          this.app.workspace.openLinkText(this.selectedDecision.vault_path, '', false);
        }
      }
    };

    vaultBtn.onmouseenter = () => {
      vaultBtn.style.backgroundColor = '#7c3aed';
    };
    vaultBtn.onmouseleave = () => {
      vaultBtn.style.backgroundColor = '#8b5cf6';
    };
  }

  /**
   * Select a decision and update the UI
   */
  private selectDecision(decision: Decision): void {
    this.selectedDecision = decision;
    if (this.containerEl) {
      this.loadPanel(this.containerEl);
    }
    new Notice(`Selected: ${decision.title}`);
  }

  /**
   * Get color for confidence score
   */
  private getConfidenceColor(score: number): string {
    if (score >= 0.8) return '#10b981'; // green
    if (score >= 0.6) return '#f59e0b'; // orange
    return '#ef4444'; // red
  }

  /**
   * Get color for status
   */
  private getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      active: '#3b82f6',
      archived: '#9ca3af',
      revisited: '#f59e0b',
    };
    return colors[status] || '#9ca3af';
  }
}
