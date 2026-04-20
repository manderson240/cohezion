/**
 * Modal UI Components
 */

import { App, Modal, Notice } from 'obsidian';
import { HyperdimPluginSettings, ProjectionPreset, PROJECTION_PRESETS } from '../types';
import { MCPClient } from '../services/mcp-client';
import { GraphView } from '../graph/GraphView';

export class GraphViewModal extends Modal {
  private settings: HyperdimPluginSettings;
  private mcpClient: MCPClient;
  private graphView: GraphView | null = null;
  private graphContainer: HTMLElement | null = null;

  constructor(app: App, settings: HyperdimPluginSettings, mcpClient: MCPClient) {
    super(app);
    this.settings = settings;
    this.mcpClient = mcpClient;
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('hyperdim-graph-modal');

    // Set modal to full screen
    this.modalEl.addClass('hyperdim-fullscreen-modal');

    // Create header with controls
    const header = contentEl.createDiv('hyperdim-header');
    header.createEl('h2', { text: '12D Compound Engineering Graph' });

    // Projection selector
    const projectionDiv = header.createDiv('hyperdim-projection-selector');
    projectionDiv.createEl('span', { text: 'Projection: ' });

    const projectionSelect = projectionDiv.createEl('select');
    Object.entries(PROJECTION_PRESETS).forEach(([key, config]) => {
      const option = projectionSelect.createEl('option', {
        text: config.name,
        value: key,
      });
      if (key === this.settings.visualization.defaultProjection) {
        option.selected = true;
      }
    });

    projectionSelect.addEventListener('change', () => {
      const newProjection = projectionSelect.value as ProjectionPreset;
      if (this.graphView) {
        this.graphView.switchProjection(newProjection);
        new Notice(`Switched to ${PROJECTION_PRESETS[newProjection].name}`);
      }
    });

    // Close button
    const closeBtn = header.createEl('button', { text: 'Close' });
    closeBtn.addEventListener('click', () => this.close());

    // Create graph container
    this.graphContainer = contentEl.createDiv('hyperdim-graph-container');
    this.graphContainer.style.width = '100%';
    this.graphContainer.style.height = 'calc(100vh - 100px)';
    this.graphContainer.style.position = 'relative';

    // Load and render graph
    try {
      new Notice('Loading graph data from vault...', 2000);
      const graphData = await this.loadGraphData();

      if (!graphData || graphData.nodes.length === 0) {
        throw new Error('No graph data available');
      }

      console.log(`[GraphViewModal] Loaded ${graphData.nodes.length} nodes, ${graphData.edges.length} edges`);

      // Create GraphView
      this.graphView = new GraphView(
        this.graphContainer,
        graphData,
        this.app,
        this.settings.visualization.defaultProjection
      );

      new Notice(`Rendered ${graphData.nodes.length} nodes successfully`, 3000);
    } catch (error) {
      console.error('[GraphViewModal] Failed to load graph:', error);
      new Notice(`Failed to load graph: ${error.message}`, 5000);

      contentEl.createEl('p', {
        text: `Error: ${error.message}`,
        cls: 'hyperdim-error',
      });
    }
  }

  /**
   * Load graph data from JSON file or MCP server
   */
  private async loadGraphData() {
    // Try loading from local JSON file first (faster for MVP)
    try {
      const vaultPath = (this.app.vault.adapter as any).basePath;
      const graphDataPath = `${vaultPath}/.obsidian/3d-graph-data.json`;

      console.log(`[GraphViewModal] Loading graph data from: ${graphDataPath}`);

      const response = await fetch(`file://${graphDataPath}`);
      if (!response.ok) {
        throw new Error('Graph data file not found');
      }

      const graphData = await response.json();
      return graphData;
    } catch (fileError) {
      console.warn('[GraphViewModal] Failed to load from file, trying MCP server:', fileError);

      // Fallback to MCP server
      try {
        return await this.mcpClient.fetchGraphData();
      } catch (mcpError) {
        console.error('[GraphViewModal] Failed to load from MCP server:', mcpError);
        throw new Error('Could not load graph data from file or MCP server');
      }
    }
  }

  onClose() {
    const { contentEl } = this;

    // Cleanup GraphView
    if (this.graphView) {
      this.graphView.dispose();
      this.graphView = null;
    }

    contentEl.empty();
  }
}
