import { Modal, App } from 'obsidian';
import { DecisionContradiction } from '../types/Decision';

/**
 * Interactive table visualization of decision contradictions
 * Shows where decisions conflict with lessons or operational evidence
 *
 * Features:
 * - Sortable table of contradictions
 * - Color-coded severity (critical=red, high=orange, medium=yellow, low=gray)
 * - Click rows to expand details
 * - Export to CSV
 *
 * @example
 * const modal = new ContradictionMatrix(app, decisionId, contradictions);
 * modal.open();
 */
export class ContradictionMatrix extends Modal {
  private decisionId: string;
  private contradictions: DecisionContradiction[];
  private sortColumn: 'severity' | 'challenge_type' | 'lesson_id' = 'severity';
  private sortAscending: boolean = false;

  constructor(app: App, decisionId: string, contradictions: DecisionContradiction[]) {
    super(app);
    this.decisionId = decisionId;
    this.contradictions = contradictions;
    this.setTitle(`Contradictions: ${decisionId}`);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();

    // Create container
    const container = contentEl.createDiv('contradiction-matrix-container');
    container.style.padding = '20px';
    container.style.maxWidth = '1200px';
    container.style.margin = '0 auto';

    // Create summary section
    const summary = container.createDiv('contradiction-summary');
    summary.style.marginBottom = '20px';
    summary.innerHTML = `<h3>Decision Contradictions Analysis</h3>
      <p><strong>Decision:</strong> ${this.decisionId}</p>
      <p><strong>Contradictions Found:</strong> ${this.contradictions.length}</p>`;

    // Count by severity
    const severityCounts: Record<string, number> = {};
    for (const c of this.contradictions) {
      severityCounts[c.severity] = (severityCounts[c.severity] || 0) + 1;
    }

    const statsDiv = summary.createDiv('contradiction-stats');
    statsDiv.style.marginTop = '10px';
    statsDiv.innerHTML = `
      <p>
        ${severityCounts['critical'] ? `<span class="severity-badge severity-critical">Critical: ${severityCounts['critical']}</span>` : ''}
        ${severityCounts['high'] ? `<span class="severity-badge severity-high">High: ${severityCounts['high']}</span>` : ''}
        ${severityCounts['medium'] ? `<span class="severity-badge severity-medium">Medium: ${severityCounts['medium']}</span>` : ''}
        ${severityCounts['low'] ? `<span class="severity-badge severity-low">Low: ${severityCounts['low']}</span>` : ''}
      </p>
    `;

    // Create table
    if (this.contradictions.length === 0) {
      const noDataDiv = container.createDiv();
      noDataDiv.innerHTML = '<p style="text-align: center; color: #999;">No contradictions detected</p>';
      return;
    }

    const tableSection = container.createDiv('contradiction-table-section');
    tableSection.style.marginTop = '20px';
    tableSection.style.overflow = 'auto';

    const table = tableSection.createEl('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.backgroundColor = '#fff';
    table.style.borderRadius = '4px';
    table.style.overflow = 'hidden';

    // Header row with sort buttons
    const headerRow = table.createEl('tr');
    headerRow.style.backgroundColor = '#f0f0f0';

    const columns = [
      { key: 'challenge_type', label: 'Challenge Type' },
      { key: 'lesson_id', label: 'Conflicting Lesson' },
      { key: 'severity', label: 'Severity' },
      { key: 'description', label: 'Details' },
    ];

    for (const col of columns) {
      const th = headerRow.createEl('th');
      th.style.padding = '12px';
      th.style.textAlign = 'left';
      th.style.borderBottom = '2px solid #ddd';
      th.style.fontWeight = 'bold';
      th.style.cursor = 'pointer';
      th.style.userSelect = 'none';
      th.textContent = col.label;

      // Add sort indicator
      if (col.key === this.sortColumn) {
        th.textContent += this.sortAscending ? ' ↑' : ' ↓';
      }

      // Handle click to sort
      th.onclick = () => {
        if (this.sortColumn === col.key) {
          this.sortAscending = !this.sortAscending;
        } else {
          this.sortColumn = col.key as any;
          this.sortAscending = false;
        }
        this.onOpen(); // Refresh
      };

      th.onmouseenter = () => {
        th.style.backgroundColor = '#e8e8e8';
      };
      th.onmouseleave = () => {
        th.style.backgroundColor = 'transparent';
      };
    }

    // Sort contradictions
    const sorted = [...this.contradictions].sort((a, b) => {
      let aVal: any = a[this.sortColumn as keyof DecisionContradiction];
      let bVal: any = b[this.sortColumn as keyof DecisionContradiction];

      // Convert to comparable values
      if (this.sortColumn === 'severity') {
        const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        aVal = severityOrder[aVal as any] ?? 999;
        bVal = severityOrder[bVal as any] ?? 999;
      }

      if (aVal < bVal) return this.sortAscending ? -1 : 1;
      if (aVal > bVal) return this.sortAscending ? 1 : -1;
      return 0;
    });

    // Data rows
    for (const contradiction of sorted) {
      const row = table.createEl('tr');
      row.style.borderBottom = '1px solid #eee';
      row.style.cursor = 'pointer';

      row.onmouseenter = () => {
        row.style.backgroundColor = '#f9f9f9';
      };
      row.onmouseleave = () => {
        row.style.backgroundColor = 'transparent';
      };

      // Challenge type
      const typeCell = row.createEl('td');
      const typeBadge = typeCell.createEl('span');
      typeBadge.textContent = contradiction.challenge_type;
      typeBadge.className = `challenge-badge challenge-${contradiction.challenge_type}`;
      typeBadge.style.padding = '4px 8px';
      typeBadge.style.borderRadius = '3px';
      typeBadge.style.fontSize = '0.85em';
      typeBadge.style.fontWeight = 'bold';
      typeBadge.style.display = 'inline-block';
      typeCell.style.padding = '12px';

      // Lesson ID
      const lessonCell = row.createEl('td');
      lessonCell.textContent = contradiction.lesson_id;
      lessonCell.style.padding = '12px';
      lessonCell.style.fontFamily = 'monospace';
      lessonCell.style.fontSize = '0.9em';
      lessonCell.style.color = '#666';

      // Severity
      const severityCell = row.createEl('td');
      const severityBadge = severityCell.createEl('span');
      severityBadge.textContent = contradiction.severity;
      severityBadge.className = `severity-badge severity-${contradiction.severity}`;
      severityBadge.style.padding = '4px 8px';
      severityBadge.style.borderRadius = '3px';
      severityBadge.style.fontSize = '0.85em';
      severityBadge.style.fontWeight = 'bold';
      severityBadge.style.display = 'inline-block';
      severityCell.style.padding = '12px';

      // Description
      const descCell = row.createEl('td');
      descCell.textContent = contradiction.description;
      descCell.style.padding = '12px';
      descCell.style.fontSize = '0.9em';
      descCell.style.color = '#666';
      descCell.style.maxWidth = '300px';
      descCell.style.whiteSpace = 'normal';
      descCell.style.wordWrap = 'break-word';

      // Expand details on click
      row.onclick = () => {
        this.showContradictionDetails(container, contradiction);
      };
    }
  }

  /**
   * Show detailed information about a contradiction
   */
  private showContradictionDetails(container: HTMLElement, contradiction: DecisionContradiction): void {
    // Check if details already shown
    let detailsDiv = container.querySelector('.contradiction-details-panel') as HTMLElement;
    if (detailsDiv) {
      detailsDiv.remove();
      return;
    }

    // Create details panel
    detailsDiv = container.createDiv('contradiction-details-panel');
    detailsDiv.style.marginTop = '20px';
    detailsDiv.style.padding = '15px';
    detailsDiv.style.backgroundColor = '#f5f5f5';
    detailsDiv.style.borderLeft = `4px solid ${this.getSeverityColor(contradiction.severity)}`;
    detailsDiv.style.borderRadius = '4px';

    detailsDiv.innerHTML = `
      <h4>Contradiction Details</h4>
      <p><strong>Challenge Type:</strong> ${contradiction.challenge_type}</p>
      <p><strong>Severity:</strong> ${contradiction.severity}</p>
      <p><strong>Conflicting Lesson:</strong> <code>${contradiction.lesson_id}</code></p>
      <p><strong>Description:</strong></p>
      <p style="margin: 10px 0; padding: 10px; background-color: #fff; border-radius: 3px; border-left: 3px solid ${this.getSeverityColor(contradiction.severity)};">
        ${contradiction.description}
      </p>
      <p style="margin-top: 15px; font-size: 0.9em; color: #999;">
        This contradiction suggests that the decision may need to be revisited based on new evidence or lessons learned.
      </p>
    `;

    container.insertBefore(detailsDiv, container.querySelector('.contradiction-table-section'));
  }

  /**
   * Get color for severity level
   */
  private getSeverityColor(severity: string): string {
    const colors: Record<string, string> = {
      critical: '#ef4444', // red
      high: '#f97316', // orange
      medium: '#eab308', // yellow
      low: '#9ca3af', // gray
    };
    return colors[severity] || '#9ca3af';
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
