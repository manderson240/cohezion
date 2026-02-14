import { App, PluginSettingTab, Setting, Notice, SearchComponent } from 'obsidian';
import { Decision } from '../types/Decision';
import { SurrealDBClient } from '../services/SurrealDBClient';
import { VaultBridge } from '../services/VaultBridge';
import { ReasoningFlowchart } from '../visualizations/ReasoningFlowchart';
import { CascadeGraph } from '../visualizations/CascadeGraph';
import { ContradictionMatrix } from '../visualizations/ContradictionMatrix';
import { DecisionQualityScorer, QualityScoreBreakdown } from '../services/DecisionQualityScorer';
import { ReasoningInferenceEngine } from '../services/ReasoningInference';
import { CascadeInferenceEngine, DecisionImpact } from '../services/CascadeInference';
import { SemanticContradictionDetector } from '../services/SemanticContradictionDetector';

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

    // Phase 6 Action Buttons Section
    const phase6Header = containerEl.createDiv('phase6-header');
    phase6Header.style.padding = '15px 0 5px 0';
    phase6Header.style.borderTop = '1px solid #ddd';
    const phase6Label = phase6Header.createEl('small');
    phase6Label.textContent = 'Phase 6: Advanced Analysis';
    phase6Label.style.color = '#666';
    phase6Label.style.fontWeight = 'bold';
    phase6Label.style.display = 'block';
    phase6Label.style.marginBottom = '8px';

    const phase6Div = containerEl.createDiv('decision-phase6-buttons');
    phase6Div.style.display = 'grid';
    phase6Div.style.gridTemplateColumns = '1fr 1fr 1fr';
    phase6Div.style.gap = '10px';

    // Quality Score button
    const qualityBtn = phase6Div.createEl('button');
    qualityBtn.textContent = 'Quality Score';
    qualityBtn.style.padding = '10px 15px';
    qualityBtn.style.border = '1px solid #06b6d4';
    qualityBtn.style.borderRadius = '4px';
    qualityBtn.style.backgroundColor = '#06b6d4';
    qualityBtn.style.color = '#fff';
    qualityBtn.style.cursor = 'pointer';
    qualityBtn.style.fontWeight = 'bold';
    qualityBtn.style.fontSize = '0.85em';

    qualityBtn.onclick = async () => {
      await this.runQualityScore();
    };

    qualityBtn.onmouseenter = () => {
      qualityBtn.style.backgroundColor = '#0891b2';
    };
    qualityBtn.onmouseleave = () => {
      qualityBtn.style.backgroundColor = '#06b6d4';
    };

    // Cascade Analysis button
    const cascadeAnalysisBtn = phase6Div.createEl('button');
    cascadeAnalysisBtn.textContent = 'Cascade Analysis';
    cascadeAnalysisBtn.style.padding = '10px 15px';
    cascadeAnalysisBtn.style.border = '1px solid #14b8a6';
    cascadeAnalysisBtn.style.borderRadius = '4px';
    cascadeAnalysisBtn.style.backgroundColor = '#14b8a6';
    cascadeAnalysisBtn.style.color = '#fff';
    cascadeAnalysisBtn.style.cursor = 'pointer';
    cascadeAnalysisBtn.style.fontWeight = 'bold';
    cascadeAnalysisBtn.style.fontSize = '0.85em';

    cascadeAnalysisBtn.onclick = async () => {
      await this.runCascadeAnalysis();
    };

    cascadeAnalysisBtn.onmouseenter = () => {
      cascadeAnalysisBtn.style.backgroundColor = '#0d9488';
    };
    cascadeAnalysisBtn.onmouseleave = () => {
      cascadeAnalysisBtn.style.backgroundColor = '#14b8a6';
    };

    // Contradiction Detection button
    const contradictionDetectBtn = phase6Div.createEl('button');
    contradictionDetectBtn.textContent = 'Detect Contradictions';
    contradictionDetectBtn.style.padding = '10px 15px';
    contradictionDetectBtn.style.border = '1px solid #e11d48';
    contradictionDetectBtn.style.borderRadius = '4px';
    contradictionDetectBtn.style.backgroundColor = '#e11d48';
    contradictionDetectBtn.style.color = '#fff';
    contradictionDetectBtn.style.cursor = 'pointer';
    contradictionDetectBtn.style.fontWeight = 'bold';
    contradictionDetectBtn.style.fontSize = '0.85em';

    contradictionDetectBtn.onclick = async () => {
      await this.runContradictionDetection();
    };

    contradictionDetectBtn.onmouseenter = () => {
      contradictionDetectBtn.style.backgroundColor = '#be123c';
    };
    contradictionDetectBtn.onmouseleave = () => {
      contradictionDetectBtn.style.backgroundColor = '#e11d48';
    };

    // Phase 6 Results area
    const resultsDiv = containerEl.createDiv('phase6-results');
    resultsDiv.id = 'phase6-results';
    resultsDiv.style.padding = '10px 0';
  }

  /**
   * Run quality scoring for the selected decision using DecisionQualityScorer (Phase 6D)
   * Displays breakdown of confidence, alternatives, assumptions, contradictions, diversity
   */
  private async runQualityScore(): Promise<void> {
    if (!this.selectedDecision) {
      new Notice('Select a decision first');
      return;
    }

    try {
      const scorer = new DecisionQualityScorer();

      // Get contradiction counts from SurrealDB
      let contradictionMap = new Map<string, number>();
      try {
        contradictionMap = await this.surrealClient.queryAllContradictionCounts();
      } catch (e) {
        console.log('Contradiction counts not available, scoring without them');
      }

      const breakdown = scorer.calculateScore(this.selectedDecision, contradictionMap);

      // Display results in the Phase 6 results area
      const resultsDiv = this.containerEl?.querySelector('#phase6-results') as HTMLElement;
      if (resultsDiv) {
        resultsDiv.empty();

        const header = resultsDiv.createEl('h4');
        header.textContent = `Quality Score: ${(breakdown.total * 100).toFixed(1)}%`;
        header.style.marginBottom = '10px';
        header.style.color = breakdown.total >= 0.7 ? '#10b981' : breakdown.total >= 0.4 ? '#f59e0b' : '#ef4444';

        // Score breakdown grid
        const grid = resultsDiv.createDiv();
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = '1fr 1fr';
        grid.style.gap = '8px';
        grid.style.fontSize = '0.85em';

        const components = [
          { label: 'Confidence (40%)', value: breakdown.confidence, max: 0.4 },
          { label: 'Alternatives (20%)', value: breakdown.alternatives, max: 0.2 },
          { label: 'Assumptions (10%)', value: breakdown.assumptions, max: 0.1 },
          { label: 'No Contradictions (20%)', value: breakdown.contradictions, max: 0.2 },
          { label: 'Reasoning Diversity (10%)', value: breakdown.diversity, max: 0.1 },
        ];

        for (const comp of components) {
          const item = grid.createDiv();
          item.style.padding = '6px 8px';
          item.style.backgroundColor = '#f9f9f9';
          item.style.borderRadius = '3px';
          const pct = comp.max > 0 ? (comp.value / comp.max * 100).toFixed(0) : '0';
          item.innerHTML = `<small style="color:#666">${comp.label}</small><br><strong>${pct}%</strong> <small>(${comp.value.toFixed(3)}/${comp.max})</small>`;
        }
      }

      new Notice(`Quality Score: ${(breakdown.total * 100).toFixed(1)}%`);
    } catch (error) {
      console.error('Quality scoring failed:', error);
      new Notice('Quality scoring failed. Check console for details.');
    }
  }

  /**
   * Run cascade impact analysis for the selected decision using CascadeInferenceEngine (Phase 6B)
   * Computes 2nd/3rd order effects via BFS traversal
   */
  private async runCascadeAnalysis(): Promise<void> {
    if (!this.selectedDecision) {
      new Notice('Select a decision first');
      return;
    }

    try {
      new Notice('Running cascade analysis...');

      // Use SurrealDB client to analyze cascades for this decision
      const result = await this.surrealClient.analyzeDecisionCascades(
        this.selectedDecision.id,
        5
      );

      // Display results
      const resultsDiv = this.containerEl?.querySelector('#phase6-results') as HTMLElement;
      if (resultsDiv) {
        resultsDiv.empty();

        const header = resultsDiv.createEl('h4');
        header.textContent = 'Cascade Impact Analysis';
        header.style.marginBottom = '10px';

        if (result && result.cascades.length > 0) {
          const stats = resultsDiv.createDiv();
          stats.style.marginBottom = '10px';
          stats.style.padding = '8px';
          stats.style.backgroundColor = '#f0fdf4';
          stats.style.borderRadius = '4px';
          stats.style.fontSize = '0.9em';
          stats.innerHTML = `
            <strong>Total downstream impacts:</strong> ${result.total_impacted}<br>
            <strong>Critical impacts:</strong> ${result.critical_impact_count}
          `;

          // List cascades
          const list = resultsDiv.createEl('ul');
          list.style.fontSize = '0.85em';
          list.style.paddingLeft = '20px';
          for (const cascade of result.cascades.slice(0, 10)) {
            const li = list.createEl('li');
            li.style.marginBottom = '4px';
            const typeColor = cascade.impact_level === 'critical' ? '#ef4444' : cascade.impact_level === 'significant' ? '#f59e0b' : '#9ca3af';
            li.innerHTML = `<span style="color:${typeColor};font-weight:bold">[${cascade.impact_level}]</span> ${cascade.target_decision_id} <small>(${cascade.dependency_type})</small>`;
          }
          if (result.cascades.length > 10) {
            resultsDiv.createEl('small', { text: `...and ${result.cascades.length - 10} more` });
          }
        } else {
          resultsDiv.createEl('p', { text: 'No cascade data found for this decision.' }).style.color = '#999';
        }
      }

      const count = result?.total_impacted || 0;
      new Notice(`Cascade analysis complete: ${count} downstream impacts found`);
    } catch (error) {
      console.error('Cascade analysis failed:', error);
      new Notice('Cascade analysis failed. Check console for details.');
    }
  }

  /**
   * Run semantic contradiction detection for the selected decision (Phase 6C)
   * Uses existing SurrealDB contradiction queries
   */
  private async runContradictionDetection(): Promise<void> {
    if (!this.selectedDecision) {
      new Notice('Select a decision first');
      return;
    }

    try {
      new Notice('Detecting contradictions...');

      const result = await this.surrealClient.detectContradictions(this.selectedDecision.id);

      // Display results
      const resultsDiv = this.containerEl?.querySelector('#phase6-results') as HTMLElement;
      if (resultsDiv) {
        resultsDiv.empty();

        const header = resultsDiv.createEl('h4');
        header.textContent = 'Contradiction Detection Results';
        header.style.marginBottom = '10px';

        if (result && result.contradictions.length > 0) {
          // Severity summary
          const stats = resultsDiv.createDiv();
          stats.style.marginBottom = '10px';
          stats.style.padding = '8px';
          stats.style.backgroundColor = '#fef2f2';
          stats.style.borderRadius = '4px';
          stats.style.fontSize = '0.9em';

          const severityCounts = result.severity_counts;
          const parts = Object.entries(severityCounts)
            .map(([severity, count]) => `${severity}: ${count}`)
            .join(' | ');
          stats.innerHTML = `<strong>Found ${result.contradictions.length} contradiction(s):</strong> ${parts}`;

          // List contradictions
          const list = resultsDiv.createEl('ul');
          list.style.fontSize = '0.85em';
          list.style.paddingLeft = '20px';
          for (const contradiction of result.contradictions.slice(0, 10)) {
            const li = list.createEl('li');
            li.style.marginBottom = '6px';
            const severityColor =
              contradiction.severity === 'critical' ? '#ef4444' :
              contradiction.severity === 'high' ? '#f59e0b' :
              contradiction.severity === 'medium' ? '#eab308' : '#9ca3af';
            li.innerHTML = `
              <span style="color:${severityColor};font-weight:bold">[${contradiction.severity}]</span>
              <small>${contradiction.challenge_type}</small> vs. lesson <em>${contradiction.lesson_id}</em>
              <br><small style="color:#666">${contradiction.description.substring(0, 120)}${contradiction.description.length > 120 ? '...' : ''}</small>
            `;
          }
        } else {
          const msg = resultsDiv.createEl('p', { text: 'No contradictions detected for this decision.' });
          msg.style.color = '#10b981';
          msg.style.fontWeight = 'bold';
        }
      }

      const count = result?.contradictions.length || 0;
      new Notice(`Contradiction detection complete: ${count} found`);
    } catch (error) {
      console.error('Contradiction detection failed:', error);
      new Notice('Contradiction detection failed. Check console for details.');
    }
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
