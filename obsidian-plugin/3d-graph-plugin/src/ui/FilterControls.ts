import { GraphData, GraphFilters, PaperNode } from '../types/Paper';

/**
 * FilterControls - Interactive sliders and checkboxes for filtering the graph
 * Supports filtering by dimensions and domains
 */
export class FilterControls {
  private containerEl: HTMLElement | null = null;
  private filters: GraphFilters = {
    connectivityMin: 0,
    connectivityMax: 1,
    conceptualDepthMin: 0,
    conceptualDepthMax: 1,
    temporalMin: 0,
    temporalMax: 1,
    completionMin: 0,
    completionMax: 100,
    recencyMin: 0,
    recencyMax: 1,
    domains: [],
    searchQuery: '',
  };

  private onFiltersChange: ((filters: GraphFilters, filteredPapers: PaperNode[]) => void) | null = null;
  private availableDomains: Set<string> = new Set();

  constructor(
    private parentEl: HTMLElement,
    private graphData: GraphData
  ) {
    this.extractDomains();
  }

  /**
   * Extract unique domains from graph data
   */
  private extractDomains(): void {
    this.graphData.nodes.forEach((paper) => {
      // Estimate domain from cross_domain dimension
      const domainCount = paper.dimensions.cross_domain;
      for (let i = 0; i < Math.min(domainCount, 3); i++) {
        this.availableDomains.add(`Domain ${i + 1}`);
      }
    });

    // Fallback if no domains detected
    if (this.availableDomains.size === 0) {
      ['Theory', 'Applied', 'Interdisciplinary', 'Experimental'].forEach((d) =>
        this.availableDomains.add(d)
      );
    }
  }

  /**
   * Create filter controls UI
   */
  create(): void {
    if (this.containerEl) return;

    this.containerEl = this.parentEl.createDiv('filter-controls-container');

    const header = this.containerEl.createDiv('filter-header');
    header.createEl('h3', { text: 'Filters', cls: 'filter-title' });

    const resetBtn = header.createEl('button', {
      text: 'Reset All',
      cls: 'filter-reset-btn',
    });
    resetBtn.addEventListener('click', () => this.reset());

    // Collapsible sections
    this.createDimensionFilters();
    this.createDomainFilters();
  }

  /**
   * Create dimension filter sliders
   */
  private createDimensionFilters(): void {
    if (!this.containerEl) return;

    const dimensionsSection = this.containerEl.createDiv('filter-section filter-dimensions');
    dimensionsSection.createEl('h4', { text: 'Dimensions', cls: 'filter-section-title' });

    // Connectivity
    this.createRangeSlider(
      dimensionsSection,
      'Connectivity',
      'connectivity',
      0,
      1,
      0.01,
      (min, max) => {
        this.filters.connectivityMin = min;
        this.filters.connectivityMax = max;
        this.notifyChange();
      }
    );

    // Conceptual Depth
    this.createRangeSlider(
      dimensionsSection,
      'Conceptual Depth',
      'conceptualDepth',
      0,
      1,
      0.01,
      (min, max) => {
        this.filters.conceptualDepthMin = min;
        this.filters.conceptualDepthMax = max;
        this.notifyChange();
      }
    );

    // Temporal
    this.createRangeSlider(
      dimensionsSection,
      'Temporal',
      'temporal',
      0,
      1,
      0.01,
      (min, max) => {
        this.filters.temporalMin = min;
        this.filters.temporalMax = max;
        this.notifyChange();
      }
    );

    // Completion
    this.createRangeSlider(
      dimensionsSection,
      'Completion (%)',
      'completion',
      0,
      100,
      5,
      (min, max) => {
        this.filters.completionMin = min;
        this.filters.completionMax = max;
        this.notifyChange();
      }
    );

    // Recency
    this.createRangeSlider(
      dimensionsSection,
      'Recency',
      'recency',
      0,
      1,
      0.01,
      (min, max) => {
        this.filters.recencyMin = min;
        this.filters.recencyMax = max;
        this.notifyChange();
      }
    );
  }

  /**
   * Create domain filter checkboxes
   */
  private createDomainFilters(): void {
    if (!this.containerEl) return;

    const domainsSection = this.containerEl.createDiv('filter-section filter-domains');
    domainsSection.createEl('h4', { text: 'Domains', cls: 'filter-section-title' });

    this.availableDomains.forEach((domain) => {
      const label = domainsSection.createEl('label', { cls: 'filter-checkbox-label' });
      const checkbox = label.createEl('input', { type: 'checkbox' });

      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          this.filters.domains.push(domain);
        } else {
          this.filters.domains = this.filters.domains.filter((d) => d !== domain);
        }
        this.notifyChange();
      });

      label.createEl('span', { text: domain, cls: 'filter-checkbox-text' });
    });
  }

  /**
   * Create a range slider for dimension filtering
   */
  private createRangeSlider(
    parentEl: HTMLElement,
    label: string,
    id: string,
    min: number,
    max: number,
    step: number,
    onchange: (min: number, max: number) => void
  ): void {
    const sliderContainer = parentEl.createDiv('filter-slider-group');

    const labelEl = sliderContainer.createDiv('filter-slider-label');
    labelEl.createEl('span', { text: label, cls: 'filter-slider-name' });
    labelEl.createEl('span', {
      text: `${min.toFixed(2)} - ${max.toFixed(2)}`,
      cls: 'filter-slider-value',
    });

    const sliderWrapper = sliderContainer.createDiv('filter-slider-wrapper');

    // Min slider
    const minSlider = sliderWrapper.createEl('input', {
      type: 'range',
      min: min.toString(),
      max: max.toString(),
      step: step.toString(),
      value: min.toString(),
      cls: 'filter-slider filter-slider-min',
    });

    // Max slider
    const maxSlider = sliderWrapper.createEl('input', {
      type: 'range',
      min: min.toString(),
      max: max.toString(),
      step: step.toString(),
      value: max.toString(),
      cls: 'filter-slider filter-slider-max',
    });

    // Update callback
    const updateSliders = () => {
      const minVal = parseFloat(minSlider.value);
      const maxVal = parseFloat(maxSlider.value);

      // Ensure min doesn't exceed max
      if (minVal > maxVal) {
        minSlider.value = maxVal.toString();
      }
      if (maxVal < minVal) {
        maxSlider.value = minVal.toString();
      }

      // Update label display
      const valueSpan = labelEl.querySelector('.filter-slider-value') as HTMLElement;
      if (valueSpan) {
        const displayMin =
          max - min > 10 ? minSlider.value : parseFloat(minSlider.value).toFixed(2);
        const displayMax =
          max - min > 10 ? maxSlider.value : parseFloat(maxSlider.value).toFixed(2);
        valueSpan.textContent = `${displayMin} - ${displayMax}`;
      }

      onchange(parseFloat(minSlider.value), parseFloat(maxSlider.value));
    };

    minSlider.addEventListener('input', updateSliders);
    maxSlider.addEventListener('input', updateSliders);
  }

  /**
   * Notify filter change
   */
  private notifyChange(): void {
    if (!this.onFiltersChange) return;

    const filteredPapers = this.applyFilters();
    this.onFiltersChange(this.filters, filteredPapers);
  }

  /**
   * Apply current filters to the graph data
   */
  applyFilters(): PaperNode[] {
    return this.graphData.nodes.filter((paper) => {
      const d = paper.dimensions;

      // Check dimension ranges
      if (
        d.connectivity < this.filters.connectivityMin ||
        d.connectivity > this.filters.connectivityMax
      ) {
        return false;
      }

      if (
        d.conceptual_depth < this.filters.conceptualDepthMin ||
        d.conceptual_depth > this.filters.conceptualDepthMax
      ) {
        return false;
      }

      if (
        d.temporal < this.filters.temporalMin ||
        d.temporal > this.filters.temporalMax
      ) {
        return false;
      }

      if (
        d.completion < this.filters.completionMin ||
        d.completion > this.filters.completionMax
      ) {
        return false;
      }

      if (
        d.recency < this.filters.recencyMin ||
        d.recency > this.filters.recencyMax
      ) {
        return false;
      }

      // Check domain filter (if domains selected)
      if (this.filters.domains.length > 0) {
        const paperDomains = d.cross_domain > 0;
        if (!paperDomains) return false;
      }

      return true;
    });
  }

  /**
   * Reset all filters to default
   */
  reset(): void {
    this.filters = {
      connectivityMin: 0,
      connectivityMax: 1,
      conceptualDepthMin: 0,
      conceptualDepthMax: 1,
      temporalMin: 0,
      temporalMax: 1,
      completionMin: 0,
      completionMax: 100,
      recencyMin: 0,
      recencyMax: 1,
      domains: [],
      searchQuery: '',
    };

    // Reset UI sliders and checkboxes
    if (this.containerEl) {
      const sliders = this.containerEl.querySelectorAll('input[type="range"]');
      sliders.forEach((slider: HTMLInputElement, index) => {
        const max = parseFloat(slider.max);
        slider.value = index % 2 === 0 ? '0' : max.toString();
      });

      const checkboxes = this.containerEl.querySelectorAll('input[type="checkbox"]');
      checkboxes.forEach((checkbox: HTMLInputElement) => {
        checkbox.checked = false;
      });

      // Update value displays
      const valueSpans = this.containerEl.querySelectorAll('.filter-slider-value');
      valueSpans.forEach((span) => {
        if (span.textContent?.includes('100')) {
          span.textContent = '0 - 100';
        } else {
          span.textContent = '0.00 - 1.00';
        }
      });
    }

    this.notifyChange();
  }

  /**
   * Set callback for filter changes
   */
  onFiltersChanged(
    callback: (filters: GraphFilters, filteredPapers: PaperNode[]) => void
  ): void {
    this.onFiltersChange = callback;
  }

  /**
   * Get current filter state
   */
  getFilters(): GraphFilters {
    return { ...this.filters };
  }

  /**
   * Destroy the filter controls
   */
  destroy(): void {
    if (this.containerEl) {
      this.containerEl.remove();
      this.containerEl = null;
    }
  }
}
