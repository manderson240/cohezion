import { GraphStatistics, PaperNode } from '../types/Paper';

/**
 * Statistics - Displays real-time statistics about the current graph view
 * Shows counts, distributions, and aggregate metrics
 */
export class Statistics {
  private containerEl: HTMLElement | null = null;
  private stats: GraphStatistics = {
    visiblePapers: 0,
    visibleEdges: 0,
    avgConnectivity: 0,
    domainDistribution: {},
  };

  constructor(private parentEl: HTMLElement) {}

  /**
   * Create the statistics panel
   */
  create(): void {
    if (this.containerEl) return;

    this.containerEl = this.parentEl.createDiv('statistics-panel');
    this.containerEl.createEl('h3', { text: 'Statistics', cls: 'stats-title' });

    this.containerEl.createDiv('stats-content-wrapper', (wrapper) => {
      wrapper.createDiv('stats-overview');
      wrapper.createDiv('stats-distribution');
      wrapper.createDiv('stats-timing');
    });
  }

  /**
   * Update statistics with current data
   */
  update(visiblePapers: PaperNode[], visibleEdgeCount: number, selectedPaper?: PaperNode): void {
    // Calculate statistics
    this.stats.visiblePapers = visiblePapers.length;
    this.stats.visibleEdges = visibleEdgeCount;
    this.stats.selectedPaper = selectedPaper;

    // Calculate average connectivity
    if (visiblePapers.length > 0) {
      const totalConnectivity = visiblePapers.reduce(
        (sum, paper) => sum + paper.dimensions.connectivity,
        0
      );
      this.stats.avgConnectivity = totalConnectivity / visiblePapers.length;
    } else {
      this.stats.avgConnectivity = 0;
    }

    // Calculate domain distribution
    this.stats.domainDistribution = this.calculateDomainDistribution(visiblePapers);

    this.render();
  }

  /**
   * Calculate domain distribution from visible papers
   */
  private calculateDomainDistribution(papers: PaperNode[]): Record<string, number> {
    const distribution: Record<string, number> = {};

    papers.forEach((paper) => {
      // Estimate domain from cross_domain dimension
      const domainCount = Math.ceil(paper.dimensions.cross_domain);
      for (let i = 0; i < Math.min(domainCount, 3); i++) {
        const domain = `Domain ${i + 1}`;
        distribution[domain] = (distribution[domain] || 0) + 1;
      }
    });

    return distribution;
  }

  /**
   * Render the statistics display
   */
  private render(): void {
    if (!this.containerEl) return;

    this.renderOverview();
    this.renderDistribution();
  }

  /**
   * Render overview statistics
   */
  private renderOverview(): void {
    const overviewEl = this.containerEl!.querySelector('.stats-overview') as HTMLElement;
    if (!overviewEl) return;

    overviewEl.empty();

    const items = [
      {
        label: 'Visible Papers',
        value: this.stats.visiblePapers.toString(),
      },
      {
        label: 'Visible Edges',
        value: this.stats.visibleEdges.toString(),
      },
      {
        label: 'Avg Connectivity',
        value: this.stats.avgConnectivity.toFixed(3),
      },
    ];

    const list = overviewEl.createEl('ul', { cls: 'stats-overview-list' });
    items.forEach(({ label, value }) => {
      const li = list.createEl('li', { cls: 'stats-overview-item' });
      li.createEl('span', { text: label, cls: 'stats-label' });
      li.createEl('span', { text: value, cls: 'stats-value' });
    });

    // Show selected paper if any
    if (this.stats.selectedPaper) {
      const selectedEl = overviewEl.createDiv('stats-selected-paper');
      selectedEl.createEl('h4', { text: 'Selected Paper' });
      selectedEl.createEl('p', { text: this.stats.selectedPaper.title, cls: 'stats-selected-title' });
    }
  }

  /**
   * Render domain distribution
   */
  private renderDistribution(): void {
    const distributionEl = this.containerEl!.querySelector(
      '.stats-distribution'
    ) as HTMLElement;
    if (!distributionEl) return;

    distributionEl.empty();
    distributionEl.createEl('h4', { text: 'Domain Distribution', cls: 'stats-section-title' });

    const domains = Object.entries(this.stats.domainDistribution);

    if (domains.length === 0) {
      distributionEl.createEl('p', { text: 'No papers selected', cls: 'stats-empty' });
      return;
    }

    // Find max count for scaling
    const maxCount = Math.max(...domains.map(([, count]) => count));

    const list = distributionEl.createEl('ul', { cls: 'stats-distribution-list' });
    domains.forEach(([domain, count]) => {
      const li = list.createEl('li', { cls: 'stats-distribution-item' });

      li.createEl('span', { text: domain, cls: 'stats-distribution-label' });

      const barContainer = li.createDiv('stats-distribution-bar-container');
      const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;
      barContainer.createDiv('stats-distribution-bar', (bar) => {
        bar.style.width = `${barWidth}%`;
        bar.createEl('span', { text: count.toString(), cls: 'stats-bar-label' });
      });
    });
  }

  /**
   * Update paper count (quick update without full recalculation)
   */
  updatePaperCount(count: number): void {
    const countEl = this.containerEl?.querySelector('.stats-overview') as HTMLElement;
    if (countEl) {
      const items = countEl.querySelectorAll('.stats-overview-item');
      if (items.length > 0) {
        const firstItem = items[0] as HTMLElement;
        const valueEl = firstItem.querySelector('.stats-value');
        if (valueEl) {
          valueEl.textContent = count.toString();
        }
      }
    }
  }

  /**
   * Destroy the statistics panel
   */
  destroy(): void {
    if (this.containerEl) {
      this.containerEl.remove();
      this.containerEl = null;
    }
  }
}
