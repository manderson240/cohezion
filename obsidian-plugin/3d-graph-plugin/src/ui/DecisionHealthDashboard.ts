/**
 * DecisionHealthDashboard - Phase 7A Health Dashboard for Decision Analysis
 * Displays 6 interactive metrics for decision health and velocity
 * Uses Chart.js for lightweight visualizations
 */

import { Modal, App, Notice } from 'obsidian';
import { Decision, DecisionContradiction, DecisionCascade } from '../types/Decision';
import {
  DashboardMetricsComputer,
  HistogramData,
  PieChartData,
  LineChartData,
  QualityRankEntry,
  DonutChartData,
} from '../data/DashboardMetricsComputer';
import { SurrealDBClient } from '../services/SurrealDBClient';

/**
 * Chart.js types (minimal - only what we need)
 */
interface ChartJS {
  Chart: any;
}

declare global {
  interface Window {
    Chart?: any;
  }
}

export class DecisionHealthDashboard extends Modal {
  private decisions: Decision[] = [];
  private contradictions: DecisionContradiction[] = [];
  private impacts: Array<any> = [];
  private dbClient: SurrealDBClient;
  private refreshInterval: number | null = null;
  private charts: Map<string, any> = new Map();
  private activeTab: string = 'confidence';

  constructor(
    app: App,
    decisions: Decision[],
    dbClient: SurrealDBClient
  ) {
    super(app);
    this.decisions = decisions;
    this.dbClient = dbClient;
    this.setTitle('Decision Health Dashboard');
  }

  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.addClass('decision-health-dashboard');

    // Check if Chart.js is available
    if (!window.Chart) {
      new Notice('Warning: Chart.js not loaded. Metrics will display as tables.');
    }

    // Create dashboard structure
    this.createDashboard(contentEl);

    // Load data from SurrealDB
    await this.loadData();

    // Render all metrics
    await this.render();

    // Set up auto-refresh (every 30 seconds)
    this.refreshInterval = window.setInterval(() => {
      this.refresh();
    }, 30000);
  }

  onClose(): void {
    if (this.refreshInterval !== null) {
      clearInterval(this.refreshInterval);
    }
    // Destroy all charts
    this.charts.forEach((chart) => {
      if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
      }
    });
  }

  /**
   * Create dashboard HTML structure with tabs
   */
  private createDashboard(parentEl: HTMLElement): void {
    // Header
    const header = parentEl.createDiv('dashboard-header');
    header.createEl('h2', { text: 'Decision Health Dashboard' });
    header.createEl('p', {
      text: 'Real-time metrics for decision quality and organizational velocity',
      cls: 'subtitle',
    });

    // Tab navigation
    const tabNav = parentEl.createDiv('dashboard-tabs');
    const tabs = [
      { id: 'confidence', label: 'Confidence Distribution' },
      { id: 'reasoning', label: 'Reasoning Breakdown' },
      { id: 'contradiction', label: 'Contradiction Trend' },
      { id: 'quality', label: 'Quality Ranking' },
      { id: 'impact', label: 'Impact Distribution' },
      { id: 'velocity', label: 'Decision Velocity' },
    ];

    tabs.forEach((tab) => {
      const button = tabNav.createEl('button', {
        text: tab.label,
        cls: `tab-button ${tab.id === this.activeTab ? 'active' : ''}`,
      });
      button.onclick = () => this.switchTab(tab.id, parentEl);
    });

    // Content area
    parentEl.createDiv('dashboard-content', (el) => {
      el.id = 'dashboard-content';
    });

    // Status bar
    const statusBar = parentEl.createDiv('dashboard-status');
    statusBar.createEl('span', { text: `Loaded ${this.decisions.length} decisions`, cls: 'status-text' });
    statusBar.createEl('span', { text: 'Updating...', cls: 'status-indicator' });
  }

  /**
   * Switch between tabs
   */
  private switchTab(tabId: string, parentEl: HTMLElement): void {
    this.activeTab = tabId;

    // Update tab buttons
    const buttons = parentEl.querySelectorAll('.tab-button');
    buttons.forEach((btn) => {
      btn.classList.toggle('active', btn.textContent?.includes(this.getTabLabel(tabId)) ?? false);
    });

    // Re-render content
    this.renderContent();
  }

  /**
   * Get tab label by ID
   */
  private getTabLabel(tabId: string): string {
    const labels: Record<string, string> = {
      confidence: 'Confidence Distribution',
      reasoning: 'Reasoning Breakdown',
      contradiction: 'Contradiction Trend',
      quality: 'Quality Ranking',
      impact: 'Impact Distribution',
      velocity: 'Decision Velocity',
    };
    return labels[tabId] || tabId;
  }

  /**
   * Load data from SurrealDB
   */
  private async loadData(): Promise<void> {
    try {
      // Note: These queries assume Phase 6 has populated the SurrealDB tables
      // Contradictions
      try {
        const contradictionsResult = await this.dbClient.executeQuery(
          'SELECT * FROM decision_contradictions;'
        );
        this.contradictions = (contradictionsResult as any)?.result || [];
      } catch (e) {
        console.log('Contradictions table not yet available');
        this.contradictions = [];
      }

      // Impacts
      try {
        const impactsResult = await this.dbClient.executeQuery(
          'SELECT * FROM decision_impacts;'
        );
        this.impacts = (impactsResult as any)?.result || [];
      } catch (e) {
        console.log('Impacts table not yet available');
        this.impacts = [];
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  }

  /**
   * Render all dashboard metrics
   */
  private async render(): Promise<void> {
    this.renderContent();
  }

  /**
   * Render content for active tab
   */
  private renderContent(): void {
    const contentEl = document.getElementById('dashboard-content');
    if (!contentEl) return;

    contentEl.innerHTML = '';

    switch (this.activeTab) {
      case 'confidence':
        this.renderConfidenceDistribution(contentEl);
        break;
      case 'reasoning':
        this.renderReasoningBreakdown(contentEl);
        break;
      case 'contradiction':
        this.renderContradictionTrend(contentEl);
        break;
      case 'quality':
        this.renderQualityRanking(contentEl);
        break;
      case 'impact':
        this.renderImpactDistribution(contentEl);
        break;
      case 'velocity':
        this.renderDecisionVelocity(contentEl);
        break;
    }
  }

  /**
   * Render Confidence Distribution histogram
   */
  private renderConfidenceDistribution(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Confidence Distribution' });

    const data = DashboardMetricsComputer.computeConfidenceDistribution(this.decisions);

    if (window.Chart) {
      const canvas = section.createEl('canvas');
      this.createBarChart(canvas, {
        labels: data.labels,
        datasets: [
          {
            label: 'Decision Count',
            data: data.data,
            backgroundColor: '#3b82f6',
          },
        ],
      });
    } else {
      this.renderHistogramTable(section, data);
    }

    const stats = section.createDiv('metric-stats');
    const avgConfidence =
      this.decisions.reduce((sum, d) => sum + (d.confidence_score || 0), 0) /
      this.decisions.length;
    stats.createEl('p', {
      text: `Average Confidence: ${(avgConfidence * 100).toFixed(1)}%`,
    });
  }

  /**
   * Render Reasoning Type Breakdown pie chart
   */
  private renderReasoningBreakdown(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Reasoning Type Breakdown' });

    const data = DashboardMetricsComputer.computeReasoningBreakdown(this.decisions);

    if (window.Chart) {
      const canvas = section.createEl('canvas');
      this.createPieChart(canvas, {
        labels: data.labels,
        datasets: [
          {
            data: data.data,
            backgroundColor: data.backgroundColor,
          },
        ],
      });
    } else {
      this.renderPieTable(section, data);
    }
  }

  /**
   * Render Contradiction Rate Trend line chart
   */
  private renderContradictionTrend(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Contradiction Rate Trend' });

    const data = DashboardMetricsComputer.computeContradictionTrend(
      this.decisions,
      this.contradictions
    );

    if (window.Chart) {
      const canvas = section.createEl('canvas');
      this.createLineChart(canvas, data);
    } else {
      this.renderLineChartTable(section, data);
    }

    const stats = section.createDiv('metric-stats');
    const withContradictions = this.contradictions.length;
    stats.createEl('p', {
      text: `Detected Contradictions: ${withContradictions}`,
    });
  }

  /**
   * Render Quality Score Ranking table
   */
  private renderQualityRanking(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Quality Score Ranking' });

    const ranking = DashboardMetricsComputer.computeQualityRanking(this.decisions);

    // Top 10
    const topSection = section.createDiv('ranking-subsection');
    topSection.createEl('h4', { text: 'Top 10 - Highest Quality' });
    const topTable = topSection.createEl('table', { cls: 'quality-ranking-table' });
    this.renderQualityTable(topTable, ranking.top);

    // Bottom 10
    const bottomSection = section.createDiv('ranking-subsection');
    bottomSection.createEl('h4', { text: 'Bottom 10 - Lowest Quality' });
    const bottomTable = bottomSection.createEl('table', { cls: 'quality-ranking-table' });
    this.renderQualityTable(bottomTable, ranking.bottom);
  }

  /**
   * Render Impact Distribution donut chart
   */
  private renderImpactDistribution(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Impact Distribution' });

    const data = DashboardMetricsComputer.computeImpactDistribution(this.impacts);

    if (window.Chart) {
      const canvas = section.createEl('canvas');
      this.createDonutChart(canvas, {
        labels: data.labels,
        datasets: [
          {
            data: data.data,
            backgroundColor: data.backgroundColor,
          },
        ],
      });
    } else {
      this.renderDonutTable(section, data);
    }
  }

  /**
   * Render Decision Velocity bar chart
   */
  private renderDecisionVelocity(parentEl: HTMLElement): void {
    const section = parentEl.createDiv('metric-section');
    section.createEl('h3', { text: 'Decision Velocity' });

    const data = DashboardMetricsComputer.computeDecisionVelocity(this.decisions);

    if (window.Chart) {
      const canvas = section.createEl('canvas');
      this.createLineChart(canvas, data);
    } else {
      this.renderLineChartTable(section, data);
    }

    const stats = section.createDiv('metric-stats');
    const avgPerWeek = this.decisions.length / (Math.max(data.labels.length, 1));
    stats.createEl('p', {
      text: `Average per Week: ${avgPerWeek.toFixed(1)} decisions`,
    });
  }

  /**
   * Create bar chart with Chart.js
   */
  private createBarChart(canvas: HTMLCanvasElement, config: any): void {
    if (!window.Chart) return;

    const chart = new window.Chart(canvas, {
      type: 'bar',
      data: config,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: { beginAtZero: true },
        },
      },
    });

    this.charts.set('bar-' + Math.random(), chart);
  }

  /**
   * Create pie chart with Chart.js
   */
  private createPieChart(canvas: HTMLCanvasElement, config: any): void {
    if (!window.Chart) return;

    const chart = new window.Chart(canvas, {
      type: 'pie',
      data: config,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { position: 'right' },
        },
      },
    });

    this.charts.set('pie-' + Math.random(), chart);
  }

  /**
   * Create line chart with Chart.js
   */
  private createLineChart(canvas: HTMLCanvasElement, config: any): void {
    if (!window.Chart) return;

    const chart = new window.Chart(canvas, {
      type: 'line',
      data: config,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: true },
        },
        scales: {
          y: { beginAtZero: true },
        },
      },
    });

    this.charts.set('line-' + Math.random(), chart);
  }

  /**
   * Create donut chart with Chart.js
   */
  private createDonutChart(canvas: HTMLCanvasElement, config: any): void {
    if (!window.Chart) return;

    const chart = new window.Chart(canvas, {
      type: 'doughnut',
      data: config,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { position: 'right' },
        },
      },
    });

    this.charts.set('donut-' + Math.random(), chart);
  }

  /**
   * Render histogram as fallback table
   */
  private renderHistogramTable(parentEl: HTMLElement, data: HistogramData): void {
    const table = parentEl.createEl('table', { cls: 'metric-table' });
    const header = table.createEl('tr');
    header.createEl('th', { text: 'Confidence Range' });
    header.createEl('th', { text: 'Count' });

    data.labels.forEach((label, idx) => {
      const row = table.createEl('tr');
      row.createEl('td', { text: label });
      row.createEl('td', { text: data.data[idx].toString() });
    });
  }

  /**
   * Render pie chart as fallback table
   */
  private renderPieTable(parentEl: HTMLElement, data: PieChartData): void {
    const table = parentEl.createEl('table', { cls: 'metric-table' });
    const header = table.createEl('tr');
    header.createEl('th', { text: 'Type' });
    header.createEl('th', { text: 'Count' });
    header.createEl('th', { text: 'Percentage' });

    const total = data.data.reduce((a, b) => a + b, 0);
    data.labels.forEach((label, idx) => {
      const row = table.createEl('tr');
      row.createEl('td', { text: label });
      row.createEl('td', { text: data.data[idx].toString() });
      const pct = total > 0 ? ((data.data[idx] / total) * 100).toFixed(1) : '0';
      row.createEl('td', { text: `${pct}%` });
    });
  }

  /**
   * Render line chart as fallback table
   */
  private renderLineChartTable(parentEl: HTMLElement, data: LineChartData): void {
    const table = parentEl.createEl('table', { cls: 'metric-table' });
    const header = table.createEl('tr');
    header.createEl('th', { text: 'Period' });
    data.datasets.forEach((ds) => {
      header.createEl('th', { text: ds.label });
    });

    data.labels.forEach((label, idx) => {
      const row = table.createEl('tr');
      row.createEl('td', { text: label });
      data.datasets.forEach((ds) => {
        row.createEl('td', { text: (ds.data[idx] as number).toFixed(2) });
      });
    });
  }

  /**
   * Render donut chart as fallback table
   */
  private renderDonutTable(parentEl: HTMLElement, data: DonutChartData): void {
    const table = parentEl.createEl('table', { cls: 'metric-table' });
    const header = table.createEl('tr');
    header.createEl('th', { text: 'Category' });
    header.createEl('th', { text: 'Count' });

    const total = data.data.reduce((a, b) => a + b, 0);
    data.labels.forEach((label, idx) => {
      const row = table.createEl('tr');
      row.createEl('td', { text: label });
      row.createEl('td', { text: data.data[idx].toString() });
    });
  }

  /**
   * Render quality ranking table
   */
  private renderQualityTable(tableEl: HTMLTableElement, entries: QualityRankEntry[]): void {
    const header = tableEl.createEl('tr');
    header.createEl('th', { text: 'Rank' });
    header.createEl('th', { text: 'Decision' });
    header.createEl('th', { text: 'Quality Score' });
    header.createEl('th', { text: 'Status' });

    entries.forEach((entry) => {
      const row = tableEl.createEl('tr');
      row.createEl('td', { text: entry.rank.toString() });
      const titleCell = row.createEl('td', { text: entry.title, cls: 'decision-title' });
      titleCell.onclick = () => this.openDecisionExplorer(entry.decisionId);
      row.createEl('td', { text: (entry.qualityScore * 100).toFixed(1) + '%' });
      row.createEl('td', { text: entry.status });
    });
  }

  /**
   * Open decision in Decision Explorer
   */
  private openDecisionExplorer(decisionId: string): void {
    console.log('Opening decision:', decisionId);
    // This will be wired to open the Decision Explorer with this decision
  }

  /**
   * Refresh dashboard data
   */
  private async refresh(): Promise<void> {
    try {
      await this.loadData();
      this.renderContent();
    } catch (error) {
      console.error('Dashboard refresh failed:', error);
    }
  }
}
