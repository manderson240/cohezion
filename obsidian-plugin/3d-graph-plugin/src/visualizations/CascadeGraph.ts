import { Modal, App } from 'obsidian';
import { DecisionCascade } from '../types/Decision';

/**
 * Force-directed graph visualization of decision cascades
 * Shows downstream impacts of a decision
 *
 * Features:
 * - Network graph layout showing decision relationships
 * - Node color by impact level (critical=red, significant=orange, minor=gray)
 * - Edge arrows showing dependency direction
 * - Dependency type labels on edges
 * - Interactive: Click nodes to see details
 *
 * @example
 * const modal = new CascadeGraph(app, sourceDecision, cascades);
 * modal.open();
 */
export class CascadeGraph extends Modal {
  private sourceDecisionId: string;
  private cascades: DecisionCascade[];
  private title: string;

  constructor(app: App, sourceDecisionId: string, cascades: DecisionCascade[], title: string = 'Decision Cascades') {
    super(app);
    this.sourceDecisionId = sourceDecisionId;
    this.cascades = cascades;
    this.title = title;
    this.setTitle(title);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();

    // Create container
    const container = contentEl.createDiv('cascade-graph-container');
    container.style.padding = '20px';
    container.style.maxWidth = '1000px';
    container.style.margin = '0 auto';

    // Create summary section
    const summary = container.createDiv('cascade-summary');
    summary.style.marginBottom = '20px';
    summary.innerHTML = `
      <h3>${this.title}</h3>
      <p><strong>Source Decision:</strong> ${this.sourceDecisionId}</p>
      <p><strong>Impacted Decisions:</strong> ${this.cascades.length}</p>
    `;

    // Count by impact level
    const criticalCount = this.cascades.filter(c => c.impact_level === 'critical').length;
    const significantCount = this.cascades.filter(c => c.impact_level === 'significant').length;
    const minorCount = this.cascades.filter(c => c.impact_level === 'minor').length;

    const statsDiv = summary.createDiv('cascade-stats');
    statsDiv.innerHTML = `
      <p>
        <span class="impact-badge impact-critical">Critical: ${criticalCount}</span>
        <span class="impact-badge impact-significant">Significant: ${significantCount}</span>
        <span class="impact-badge impact-minor">Minor: ${minorCount}</span>
      </p>
    `;

    // Render graph if we have cascades
    if (this.cascades.length > 0) {
      const graphContainer = container.createDiv('cascade-graph-svg-container');
      graphContainer.style.display = 'flex';
      graphContainer.style.justifyContent = 'center';
      graphContainer.style.margin = '20px 0';
      graphContainer.style.overflow = 'auto';
      graphContainer.style.border = '1px solid #ddd';
      graphContainer.style.borderRadius = '4px';
      graphContainer.style.backgroundColor = '#fafafa';

      this.renderCascadeGraph(graphContainer);
    }

    // Create table of cascades
    const tableSection = container.createDiv('cascade-table-section');
    tableSection.style.marginTop = '30px';
    tableSection.style.borderTop = '1px solid #ddd';
    tableSection.style.paddingTop = '20px';
    tableSection.innerHTML = '<h3>Cascade Details</h3>';

    if (this.cascades.length === 0) {
      tableSection.innerHTML += '<p style="color: #999;">No cascades detected</p>';
      return;
    }

    // Create table
    const table = tableSection.createEl('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.marginTop = '15px';

    // Header row
    const headerRow = table.createEl('tr');
    headerRow.style.backgroundColor = '#f0f0f0';
    ['Target Decision', 'Dependency Type', 'Impact Level', 'Description'].forEach(header => {
      const th = headerRow.createEl('th');
      th.textContent = header;
      th.style.padding = '10px';
      th.style.textAlign = 'left';
      th.style.borderBottom = '2px solid #ddd';
      th.style.fontWeight = 'bold';
    });

    // Data rows
    for (const cascade of this.cascades) {
      const row = table.createEl('tr');
      row.style.borderBottom = '1px solid #ddd';

      // Target decision
      const tdCell = row.createEl('td');
      tdCell.textContent = cascade.target_decision_id;
      tdCell.style.padding = '10px';
      tdCell.style.fontFamily = 'monospace';
      tdCell.style.fontSize = '0.9em';

      // Dependency type
      const depCell = row.createEl('td');
      depCell.textContent = cascade.dependency_type;
      depCell.style.padding = '10px';
      const depBadge = depCell.createEl('span');
      depBadge.textContent = cascade.dependency_type;
      depBadge.className = `dependency-badge dependency-${cascade.dependency_type}`;
      depBadge.style.padding = '2px 6px';
      depBadge.style.borderRadius = '3px';
      depBadge.style.fontSize = '0.85em';
      depBadge.style.fontWeight = 'bold';
      depCell.empty();
      depCell.appendChild(depBadge);

      // Impact level
      const impactCell = row.createEl('td');
      const impactBadge = impactCell.createEl('span');
      impactBadge.textContent = cascade.impact_level;
      impactBadge.className = `impact-badge impact-${cascade.impact_level}`;
      impactBadge.style.padding = '4px 8px';
      impactBadge.style.borderRadius = '3px';
      impactBadge.style.fontSize = '0.85em';
      impactBadge.style.fontWeight = 'bold';
      impactCell.style.padding = '10px';

      // Description
      const descCell = row.createEl('td');
      descCell.textContent = cascade.description;
      descCell.style.padding = '10px';
      descCell.style.fontSize = '0.9em';
      descCell.style.color = '#666';
    }
  }

  /**
   * Render force-directed graph visualization
   */
  private renderCascadeGraph(container: HTMLElement): void {
    // Build node and edge lists for layout
    const nodeMap = new Map<string, { id: string; label: string; impact?: string }>();
    const edges: Array<{ source: string; target: string; type: string }> = [];

    // Add source node
    nodeMap.set(this.sourceDecisionId, {
      id: this.sourceDecisionId,
      label: this.sourceDecisionId.slice(0, 20),
      impact: 'source',
    });

    // Add cascade nodes and edges
    for (const cascade of this.cascades) {
      if (!nodeMap.has(cascade.target_decision_id)) {
        nodeMap.set(cascade.target_decision_id, {
          id: cascade.target_decision_id,
          label: cascade.target_decision_id.slice(0, 20),
          impact: cascade.impact_level,
        });
      }

      edges.push({
        source: this.sourceDecisionId,
        target: cascade.target_decision_id,
        type: cascade.dependency_type,
      });
    }

    const nodes = Array.from(nodeMap.values());

    // Simple force-directed layout (spring algorithm)
    const positions = this.computeLayout(nodes, edges);

    // Render SVG
    const canvasWidth = 800;
    const canvasHeight = 600;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', String(canvasWidth));
    svg.setAttribute('height', String(canvasHeight));
    svg.setAttribute('viewBox', `0 0 ${canvasWidth} ${canvasHeight}`);
    svg.style.border = '1px solid #ddd';

    // Draw edges first (so they appear behind nodes)
    for (const edge of edges) {
      const sourcePos = positions.get(edge.source)!;
      const targetPos = positions.get(edge.target)!;

      // Edge line
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', String(sourcePos.x));
      line.setAttribute('y1', String(sourcePos.y));
      line.setAttribute('x2', String(targetPos.x));
      line.setAttribute('y2', String(targetPos.y));
      line.setAttribute('stroke', '#999');
      line.setAttribute('stroke-width', '2');
      svg.appendChild(line);

      // Arrow head
      const angle = Math.atan2(targetPos.y - sourcePos.y, targetPos.x - sourcePos.x);
      const arrowSize = 10;
      const arrowX = targetPos.x - arrowSize * Math.cos(angle);
      const arrowY = targetPos.y - arrowSize * Math.sin(angle);

      const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const p1x = arrowX;
      const p1y = arrowY;
      const p2x = arrowX - arrowSize * Math.cos(angle - Math.PI / 6);
      const p2y = arrowY - arrowSize * Math.sin(angle - Math.PI / 6);
      const p3x = arrowX - arrowSize * Math.cos(angle + Math.PI / 6);
      const p3y = arrowY - arrowSize * Math.sin(angle + Math.PI / 6);

      arrow.setAttribute('points', `${p1x},${p1y} ${p2x},${p2y} ${p3x},${p3y}`);
      arrow.setAttribute('fill', '#999');
      svg.appendChild(arrow);
    }

    // Draw nodes
    for (const node of nodes) {
      const pos = positions.get(node.id)!;
      const color = this.getColorForImpact(node.impact || 'minor');
      const radius = node.impact === 'source' ? 15 : 12;

      // Circle
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', String(pos.x));
      circle.setAttribute('cy', String(pos.y));
      circle.setAttribute('r', String(radius));
      circle.setAttribute('fill', color);
      circle.setAttribute('stroke', '#333');
      circle.setAttribute('stroke-width', '1.5');
      circle.style.cursor = 'pointer';
      svg.appendChild(circle);

      // Label
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', String(pos.x));
      text.setAttribute('y', String(pos.y + 4));
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-size', '10');
      text.setAttribute('fill', '#fff');
      text.setAttribute('font-weight', 'bold');
      text.textContent = node.label;
      svg.appendChild(text);
    }

    container.appendChild(svg);
  }

  /**
   * Compute node positions using spring force algorithm
   */
  private computeLayout(
    nodes: any[],
    edges: Array<{ source: string; target: string; type: string }>
  ): Map<string, { x: number; y: number }> {
    const positions = new Map<string, { x: number; y: number }>();
    const width = 800;
    const height = 600;

    // Initialize random positions
    for (const node of nodes) {
      positions.set(node.id, {
        x: Math.random() * width,
        y: Math.random() * height,
      });
    }

    // Spring layout simulation (simplified)
    const iterations = 50;
    const k = 50; // Spring constant
    const c = 0.1; // Damping

    for (let iter = 0; iter < iterations; iter++) {
      const forces = new Map<string, { fx: number; fy: number }>();

      // Initialize forces
      for (const node of nodes) {
        forces.set(node.id, { fx: 0, fy: 0 });
      }

      // Repulsive forces (nodes push each other away)
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const n1 = nodes[i];
          const n2 = nodes[j];
          const p1 = positions.get(n1.id)!;
          const p2 = positions.get(n2.id)!;

          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;

          const force = -k / (dist * dist);
          const fx = (force * dx) / dist;
          const fy = (force * dy) / dist;

          const f1 = forces.get(n1.id)!;
          f1.fx += fx;
          f1.fy += fy;

          const f2 = forces.get(n2.id)!;
          f2.fx -= fx;
          f2.fy -= fy;
        }
      }

      // Attractive forces (connected nodes pull each other)
      for (const edge of edges) {
        const p1 = positions.get(edge.source)!;
        const p2 = positions.get(edge.target)!;

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        const force = (dist * dist) / (k * 10);
        const fx = (force * dx) / dist;
        const fy = (force * dy) / dist;

        const f2 = forces.get(edge.target)!;
        f2.fx -= fx;
        f2.fy -= fy;

        const f1 = forces.get(edge.source)!;
        f1.fx += fx;
        f1.fy += fy;
      }

      // Update positions
      for (const node of nodes) {
        const force = forces.get(node.id)!;
        const pos = positions.get(node.id)!;

        pos.x += force.fx * c;
        pos.y += force.fy * c;

        // Keep within bounds
        pos.x = Math.max(20, Math.min(780, pos.x));
        pos.y = Math.max(20, Math.min(580, pos.y));
      }
    }

    return positions;
  }

  /**
   * Get color for impact level
   */
  private getColorForImpact(impact: string): string {
    const colors: Record<string, string> = {
      critical: '#ef4444', // red
      significant: '#f97316', // orange
      minor: '#9ca3af', // gray
      source: '#3b82f6', // blue
    };
    return colors[impact] || '#9ca3af';
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
