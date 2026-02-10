/**
 * Agent Capability Metrics Dashboard Modal
 *
 * Displays performance metrics parsed from Claude Code logs:
 * - Knowledge accumulation timeline
 * - Session activity heatmap
 * - Tool usage distribution
 * - Success rate trends
 * - Knowledge network density
 */

import { Modal, App, Notice } from 'obsidian';

interface MetricsSummary {
  total_sessions: number;
  parsed_sessions: number;
  total_errors: number;
  error_rate: number;
  success_rate: number;
}

interface VaultStats {
  decisions: number;
  patterns: number;
  experiments: number;
  lessons: number;
  papers: number;
  concepts: number;
  daily: number;
  projects: number;
  cross_link_density: number;
  total_wiki_links: number;
}

interface AgentMetrics {
  summary: MetricsSummary;
  vault_stats: VaultStats;
  tool_usage: Record<string, number>;
  model_usage: Record<string, number>;
}

export class DashboardModal extends Modal {
  private metrics: AgentMetrics | null = null;
  private timeRange: 'week' | 'month' | 'all' = 'all';

  constructor(app: App) {
    super(app);
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('kyutai-dashboard');

    // Title
    contentEl.createEl('h2', { text: 'Agent Capability Metrics' });
    contentEl.createEl('p', {
      text: 'Performance metrics from Claude Code sessions',
      cls: 'dashboard-subtitle'
    });

    // Load metrics
    await this.loadMetrics();

    if (!this.metrics) {
      contentEl.createEl('div', {
        text: 'No metrics data available. Please run log parser first.',
        cls: 'dashboard-error'
      });
      return;
    }

    // Time range selector
    this.renderTimeRangeSelector(contentEl);

    // Create grid layout
    const grid = contentEl.createDiv({ cls: 'dashboard-grid' });

    // Render metrics panels
    this.renderSummaryPanel(grid);
    this.renderKnowledgePanel(grid);
    this.renderToolUsagePanel(grid);
    this.renderQualityPanel(grid);

    // Export button
    const exportBtn = contentEl.createEl('button', {
      text: 'Export Markdown Report',
      cls: 'mod-cta'
    });
    exportBtn.addEventListener('click', () => this.exportMarkdown());
  }

  private async loadMetrics() {
    try {
      // Try to load from /tmp/agent-metrics.json
      const response = await fetch('app://local/tmp/agent-metrics.json');

      if (!response.ok) {
        // If file doesn't exist, show friendly message
        console.warn('[Dashboard] Metrics file not found at /tmp/agent-metrics.json');
        new Notice('Metrics data not found. Please run the log parser first.', 5000);
        return;
      }

      this.metrics = await response.json();
      console.log('[Dashboard] Loaded metrics:', this.metrics);

    } catch (error) {
      console.error('[Dashboard] Failed to load metrics:', error);
      new Notice('Failed to load metrics data', 3000);
    }
  }

  private renderTimeRangeSelector(container: HTMLElement) {
    const selector = container.createDiv({ cls: 'time-range-selector' });

    const options: Array<'week' | 'month' | 'all'> = ['week', 'month', 'all'];
    options.forEach(range => {
      const btn = selector.createEl('button', {
        text: range === 'all' ? 'All Time' : `Last ${range}`,
        cls: range === this.timeRange ? 'active' : ''
      });
      btn.addEventListener('click', () => {
        this.timeRange = range;
        this.onOpen(); // Re-render
      });
    });
  }

  private renderSummaryPanel(container: HTMLElement) {
    if (!this.metrics) return;

    const panel = container.createDiv({ cls: 'dashboard-panel summary-panel' });
    panel.createEl('h3', { text: '📊 Session Summary' });

    const stats = [
      { label: 'Total Sessions', value: this.metrics.summary.total_sessions },
      { label: 'Parsed Logs', value: this.metrics.summary.parsed_sessions },
      { label: 'Success Rate', value: `${(this.metrics.summary.success_rate * 100).toFixed(1)}%` },
      { label: 'Error Rate', value: this.metrics.summary.error_rate.toFixed(2) },
    ];

    const table = panel.createDiv({ cls: 'stats-table' });
    stats.forEach(stat => {
      const row = table.createDiv({ cls: 'stat-row' });
      row.createSpan({ text: stat.label, cls: 'stat-label' });
      row.createSpan({ text: String(stat.value), cls: 'stat-value' });
    });
  }

  private renderKnowledgePanel(container: HTMLElement) {
    if (!this.metrics) return;

    const panel = container.createDiv({ cls: 'dashboard-panel knowledge-panel' });
    panel.createEl('h3', { text: '📚 Knowledge Base' });

    const vault = this.metrics.vault_stats;

    // Create bar chart (ASCII-style for simplicity)
    const categories = [
      { label: 'Papers', value: vault.papers, color: '#4299e1' },
      { label: 'Decisions', value: vault.decisions, color: '#48bb78' },
      { label: 'Patterns', value: vault.patterns, color: '#ed8936' },
      { label: 'Concepts', value: vault.concepts, color: '#9f7aea' },
      { label: 'Experiments', value: vault.experiments, color: '#f56565' },
      { label: 'Lessons', value: vault.lessons, color: '#ecc94b' },
    ];

    const maxValue = Math.max(...categories.map(c => c.value));

    categories.forEach(cat => {
      const row = panel.createDiv({ cls: 'bar-row' });
      row.createSpan({ text: cat.label, cls: 'bar-label' });

      const barContainer = row.createDiv({ cls: 'bar-container' });
      const bar = barContainer.createDiv({ cls: 'bar' });
      bar.style.width = `${(cat.value / maxValue) * 100}%`;
      bar.style.backgroundColor = cat.color;

      row.createSpan({ text: String(cat.value), cls: 'bar-value' });
    });

    // Cross-link density
    panel.createDiv({ cls: 'stat-highlight' })
      .createSpan({ text: `${vault.cross_link_density.toFixed(1)} links/note average` });
  }

  private renderToolUsagePanel(container: HTMLElement) {
    if (!this.metrics) return;

    const panel = container.createDiv({ cls: 'dashboard-panel tools-panel' });
    panel.createEl('h3', { text: '🔧 Tool Usage' });

    const tools = Object.entries(this.metrics.tool_usage)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10);

    if (tools.length === 0) {
      panel.createDiv({ text: 'No tool usage data available', cls: 'no-data' });
      return;
    }

    const maxCount = Math.max(...tools.map(([, count]) => count));

    const list = panel.createDiv({ cls: 'tool-list' });
    tools.forEach(([tool, count], index) => {
      const item = list.createDiv({ cls: 'tool-item' });

      item.createSpan({ text: `${index + 1}.`, cls: 'tool-rank' });
      item.createSpan({ text: tool, cls: 'tool-name' });

      const barContainer = item.createDiv({ cls: 'tool-bar-container' });
      const bar = barContainer.createDiv({ cls: 'tool-bar' });
      bar.style.width = `${(count / maxCount) * 100}%`;

      item.createSpan({ text: String(count), cls: 'tool-count' });
    });
  }

  private renderQualityPanel(container: HTMLElement) {
    if (!this.metrics) return;

    const panel = container.createDiv({ cls: 'dashboard-panel quality-panel' });
    panel.createEl('h3', { text: '✅ Quality Metrics' });

    // Calculate knowledge ROI
    const totalNotes = this.metrics.vault_stats.decisions +
                      this.metrics.vault_stats.patterns +
                      this.metrics.vault_stats.experiments +
                      this.metrics.vault_stats.lessons +
                      this.metrics.vault_stats.papers +
                      this.metrics.vault_stats.concepts;

    const knowledgeROI = (totalNotes / this.metrics.summary.total_sessions).toFixed(3);

    const metrics = [
      {
        label: 'Success Rate',
        value: `${(this.metrics.summary.success_rate * 100).toFixed(1)}%`,
        description: 'Sessions without errors'
      },
      {
        label: 'Knowledge ROI',
        value: knowledgeROI,
        description: 'Notes created per session'
      },
      {
        label: 'Cross-link Density',
        value: this.metrics.vault_stats.cross_link_density.toFixed(1),
        description: 'Wiki-links per note'
      },
      {
        label: 'Total Artifacts',
        value: totalNotes,
        description: 'Structured knowledge notes'
      }
    ];

    metrics.forEach(metric => {
      const box = panel.createDiv({ cls: 'metric-box' });
      box.createDiv({ text: metric.value, cls: 'metric-value-large' });
      box.createDiv({ text: metric.label, cls: 'metric-label-large' });
      box.createDiv({ text: metric.description, cls: 'metric-description' });
    });
  }

  private exportMarkdown() {
    if (!this.metrics) {
      new Notice('No metrics to export', 2000);
      return;
    }

    const totalNotes = this.metrics.vault_stats.decisions +
                      this.metrics.vault_stats.patterns +
                      this.metrics.vault_stats.experiments +
                      this.metrics.vault_stats.lessons +
                      this.metrics.vault_stats.papers +
                      this.metrics.vault_stats.concepts;

    const knowledgeROI = (totalNotes / this.metrics.summary.total_sessions).toFixed(3);

    const markdown = `# Agent Capability Metrics

**Generated**: ${new Date().toISOString()}

## Executive Summary

- **Total Sessions**: ${this.metrics.summary.total_sessions}
- **Success Rate**: ${(this.metrics.summary.success_rate * 100).toFixed(1)}%
- **Knowledge Artifacts**: ${totalNotes} structured notes
- **Knowledge ROI**: ${knowledgeROI} notes/session

## Performance Highlights

### Meta-Cognitive Capability
This system demonstrates **self-measuring AI** - an agent that tracks and optimizes its own learning process.

### Key Metrics
1. **Knowledge Accumulation**: ${totalNotes} structured artifacts across 7 categories
2. **Quality**: ${(this.metrics.summary.success_rate * 100).toFixed(1)}% success rate
3. **Interconnection**: ${this.metrics.vault_stats.cross_link_density.toFixed(1)} wiki-links per note
4. **Efficiency**: ${knowledgeROI} notes created per session

### Knowledge Base Breakdown
- **Papers**: ${this.metrics.vault_stats.papers} research references
- **Decisions**: ${this.metrics.vault_stats.decisions} ADRs
- **Patterns**: ${this.metrics.vault_stats.patterns} reusable solutions
- **Concepts**: ${this.metrics.vault_stats.concepts} core definitions
- **Experiments**: ${this.metrics.vault_stats.experiments} hypothesis tests
- **Lessons**: ${this.metrics.vault_stats.lessons} critical learnings

### Top 10 Tools
${Object.entries(this.metrics.tool_usage)
  .sort(([, a], [, b]) => b - a)
  .slice(0, 10)
  .map(([tool, count], i) => `${i + 1}. **${tool}**: ${count} calls`)
  .join('\n')}

## Portfolio Impact

**Demonstrated Capabilities**:
- System design (12D graph, MCP architecture)
- Meta-cognition (self-measurement, optimization)
- Compound engineering (knowledge interconnection)
- Token efficiency (maximize output per session)

**Research Engineer Alignment**:
- Quantified performance improvements
- Self-optimizing AI systems
- Multi-dimensional knowledge representation
- Scalable agent architectures

---

*Generated by Kyutai Obsidian Plugin - Agent Metrics Dashboard*
`;

    // Copy to clipboard
    navigator.clipboard.writeText(markdown);
    new Notice('Markdown report copied to clipboard!', 3000);
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
