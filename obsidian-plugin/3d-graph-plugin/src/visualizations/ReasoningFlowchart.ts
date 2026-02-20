import { Modal, App } from 'obsidian';
import { Decision, ReasoningChain } from '../types/Decision';

/**
 * Interactive flowchart visualization of decision reasoning chains
 * Shows the logical steps and confidence levels that led to a decision
 *
 * Features:
 * - Vertical flowchart layout with step nodes
 * - Color-coded by reasoning type (research, pattern, intuition, convention, hybrid)
 * - Node size by confidence score
 * - Arrows showing step progression
 * - Labels with step content and confidence
 *
 * @example
 * const modal = new ReasoningFlowchart(app, decision);
 * modal.open();
 */
export class ReasoningFlowchart extends Modal {
  private decision: Decision;
  private svgElement: SVGSVGElement | null = null;

  constructor(app: App, decision: Decision) {
    super(app);
    this.decision = decision;
    this.setTitle(`Reasoning Chain: ${decision.title}`);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();

    // Create container
    const container = contentEl.createDiv('reasoning-flowchart-container');
    container.style.padding = '20px';
    container.style.maxWidth = '800px';
    container.style.margin = '0 auto';

    // Create header
    const header = container.createDiv('reasoning-header');
    header.style.marginBottom = '20px';
    header.innerHTML = `
      <h2>${this.decision.title}</h2>
      <p><strong>Chosen Option:</strong> ${this.decision.chosen_option}</p>
      <p><strong>Reasoning Type:</strong> <span class="reasoning-badge reasoning-${this.decision.reasoning_type}">${this.decision.reasoning_type}</span></p>
      <p><strong>Confidence:</strong> <span class="confidence-score">${(this.decision.confidence_score * 100).toFixed(1)}%</span></p>
    `;

    // Create SVG canvas for flowchart
    const svgContainer = container.createDiv('reasoning-svg-container');
    svgContainer.style.display = 'flex';
    svgContainer.style.justifyContent = 'center';
    svgContainer.style.margin = '20px 0';
    svgContainer.style.overflow = 'auto';

    const steps = this.decision.reasoning_chain?.steps || [];
    if (steps.length === 0) {
      const noDataDiv = container.createDiv();
      noDataDiv.innerHTML = '<p style="text-align: center; color: #999;">No reasoning steps available</p>';
      return;
    }

    // Render flowchart
    this.renderFlowchart(svgContainer, steps);

    // Create details section
    const detailsSection = container.createDiv('reasoning-details');
    detailsSection.style.marginTop = '30px';
    detailsSection.style.borderTop = '1px solid #ddd';
    detailsSection.style.paddingTop = '20px';

    detailsSection.innerHTML = '<h3>Details</h3>';

    // Show assumptions
    if (this.decision.reasoning_chain?.assumptions?.length > 0) {
      const assumptionsDiv = detailsSection.createDiv('assumptions-section');
      assumptionsDiv.innerHTML = '<h4>Assumptions</h4>';
      const ul = assumptionsDiv.createEl('ul');
      for (const assumption of this.decision.reasoning_chain.assumptions) {
        ul.createEl('li').textContent = assumption;
      }
    }

    // Show alternatives rejected
    if (this.decision.alternatives_rejected && this.decision.alternatives_rejected.length > 0) {
      const alternativesDiv = detailsSection.createDiv('alternatives-section');
      alternativesDiv.style.marginTop = '15px';
      alternativesDiv.innerHTML = '<h4>Alternatives Rejected</h4>';
      const ul = alternativesDiv.createEl('ul');
      for (const alt of this.decision.alternatives_rejected) {
        ul.createEl('li').textContent = alt;
      }
    }

    // Show rationale
    if (this.decision.rationale) {
      const rationaleDiv = detailsSection.createDiv('rationale-section');
      rationaleDiv.style.marginTop = '15px';
      rationaleDiv.innerHTML = `<h4>Rationale</h4><p>${this.decision.rationale}</p>`;
    }
  }

  /**
   * Render SVG flowchart from reasoning steps
   */
  private renderFlowchart(container: HTMLElement, steps: any[]): void {
    const stepWidth = 250;
    const stepHeight = 80;
    const verticalGap = 30;
    const arrowHeight = verticalGap;
    const canvasHeight = steps.length * (stepHeight + arrowHeight) + 50;
    const canvasWidth = stepWidth + 100;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', String(canvasWidth));
    svg.setAttribute('height', String(canvasHeight));
    svg.setAttribute('viewBox', `0 0 ${canvasWidth} ${canvasHeight}`);
    svg.style.border = '1px solid #ddd';
    svg.style.borderRadius = '4px';
    svg.style.backgroundColor = '#fafafa';

    let yOffset = 25;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const confidence = step.confidence || 0.5;
      const type = step.type || 'hybrid';
      const color = this.getColorForType(type);

      // Draw node background
      const nodeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      nodeRect.setAttribute('x', '25');
      nodeRect.setAttribute('y', String(yOffset));
      nodeRect.setAttribute('width', String(stepWidth));
      nodeRect.setAttribute('height', String(stepHeight));
      nodeRect.setAttribute('rx', '4');
      nodeRect.setAttribute('fill', color);
      nodeRect.setAttribute('opacity', String(0.2 + confidence * 0.8));
      nodeRect.setAttribute('stroke', color);
      nodeRect.setAttribute('stroke-width', '2');
      svg.appendChild(nodeRect);

      // Draw step number
      const stepNumText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      stepNumText.setAttribute('x', '35');
      stepNumText.setAttribute('y', String(yOffset + 25));
      stepNumText.setAttribute('font-size', '12');
      stepNumText.setAttribute('font-weight', 'bold');
      stepNumText.setAttribute('fill', color);
      stepNumText.textContent = `Step ${i + 1}`;
      svg.appendChild(stepNumText);

      // Draw step content (wrapped text)
      const contentText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      contentText.setAttribute('x', '40');
      contentText.setAttribute('y', String(yOffset + 45));
      contentText.setAttribute('font-size', '11');
      contentText.setAttribute('fill', '#333');
      contentText.setAttribute('width', String(stepWidth - 20));

      // Simple word wrap
      const content = step.content || '';
      const words = content.split(' ');
      let line = '';
      const lines = [];
      for (const word of words) {
        if ((line + word).length > 30) {
          lines.push(line.trim());
          line = word;
        } else {
          line += (line ? ' ' : '') + word;
        }
      }
      if (line) lines.push(line);

      lines.slice(0, 2).forEach((l, idx) => {
        const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
        tspan.setAttribute('x', '40');
        tspan.setAttribute('dy', idx === 0 ? '0' : '14');
        tspan.textContent = l;
        contentText.appendChild(tspan);
      });
      svg.appendChild(contentText);

      // Draw confidence indicator
      const confText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      confText.setAttribute('x', '35');
      confText.setAttribute('y', String(yOffset + stepHeight - 8));
      confText.setAttribute('font-size', '10');
      confText.setAttribute('fill', '#666');
      confText.textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;
      svg.appendChild(confText);

      yOffset += stepHeight;

      // Draw arrow to next step (if not last step)
      if (i < steps.length - 1) {
        const arrowStartY = yOffset;
        const arrowEndY = yOffset + verticalGap;

        // Arrow line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', String(25 + stepWidth / 2));
        line.setAttribute('y1', String(arrowStartY));
        line.setAttribute('x2', String(25 + stepWidth / 2));
        line.setAttribute('y2', String(arrowEndY));
        line.setAttribute('stroke', '#999');
        line.setAttribute('stroke-width', '2');
        svg.appendChild(line);

        // Arrow head
        const arrowHead = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrowHead.setAttribute('points', `${25 + stepWidth / 2},${arrowEndY} ${22 + stepWidth / 2},${arrowEndY - 5} ${28 + stepWidth / 2},${arrowEndY - 5}`);
        arrowHead.setAttribute('fill', '#999');
        svg.appendChild(arrowHead);

        yOffset += arrowHeight;
      }
    }

    container.appendChild(svg);
    this.svgElement = svg;
  }

  /**
   * Get color for reasoning type
   */
  private getColorForType(type: string): string {
    const colors: Record<string, string> = {
      research: '#3b82f6', // blue
      pattern: '#10b981', // green
      intuition: '#f59e0b', // amber
      convention: '#8b5cf6', // purple
      hybrid: '#6366f1', // indigo
    };
    return colors[type] || '#6366f1';
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
