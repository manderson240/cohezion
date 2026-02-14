/**
 * CascadeTimeline - Phase 7B Cascade Timeline Visualization
 * Shows temporal impacts of decisions with cascading effects
 * Color-coded by impact level (red=critical, orange=significant, gray=minor)
 */

import { Modal, App } from 'obsidian';
import { Decision, DecisionCascade } from '../types/Decision';

/**
 * Timeline event with cascade information
 */
export interface TimelineEvent {
  date: string;
  decision: Decision;
  cascades: TimelineCascade[];
  impactLevel: 'critical' | 'significant' | 'minor';
}

/**
 * Cascade effect in timeline
 */
export interface TimelineCascade {
  targetDecisionId: string;
  targetDecisionTitle: string;
  dependencyType: 'enables' | 'blocks' | 'influences' | 'conflicts';
  depth: number;
  delay: number; // Days until this becomes relevant
}

export class CascadeTimeline extends Modal {
  private decisions: Decision[] = [];
  private cascades: DecisionCascade[] = [];
  private timelineEvents: TimelineEvent[] = [];
  private selectedEvent: TimelineEvent | null = null;

  constructor(
    app: App,
    decisions: Decision[],
    cascades: DecisionCascade[]
  ) {
    super(app);
    this.decisions = decisions;
    this.cascades = cascades;
    this.setTitle('Decision Cascade Timeline');
  }

  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.addClass('cascade-timeline');

    // Build timeline
    this.buildTimeline();

    // Render timeline
    this.renderTimeline(contentEl);
  }

  /**
   * Build timeline from decisions and cascades
   */
  private buildTimeline(): void {
    // Create decision map for quick lookup
    const decisionMap = new Map<string, Decision>();
    this.decisions.forEach((d) => {
      decisionMap.set(d.id, d);
    });

    // Create cascade map: decision_id -> cascades[]
    const cascadeMap = new Map<string, DecisionCascade[]>();
    this.cascades.forEach((c) => {
      if (!cascadeMap.has(c.source_decision_id)) {
        cascadeMap.set(c.source_decision_id, []);
      }
      cascadeMap.get(c.source_decision_id)!.push(c);
    });

    // Build timeline events
    const events: TimelineEvent[] = [];

    this.decisions.forEach((decision) => {
      const cascadesForDecision = cascadeMap.get(decision.id) || [];

      // Convert to timeline cascades
      const timelineCascades: TimelineCascade[] = cascadesForDecision.map((c) => {
        const targetDecision = decisionMap.get(c.target_decision_id);
        return {
          targetDecisionId: c.target_decision_id,
          targetDecisionTitle: targetDecision?.title || 'Unknown',
          dependencyType: c.dependency_type,
          depth: 1, // Will be computed by BFS
          delay: this.computeDelay(c.dependency_type),
        };
      });

      events.push({
        date: decision.timestamp,
        decision,
        cascades: timelineCascades,
        impactLevel: this.computeImpactLevel(cascadesForDecision),
      });
    });

    // Sort by date
    this.timelineEvents = events.sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Compute deeper cascades using BFS
    this.computeDeepCascades();
  }

  /**
   * Compute delay based on dependency type
   */
  private computeDelay(dependencyType: string): number {
    // Model: (depth × 3 days) = when target becomes relevant
    const baseDelay = {
      enables: 1, // Immediate
      influences: 3, // A few days
      blocks: 2, // Soon
      conflicts: 2, // Soon
    };
    return (baseDelay[dependencyType as keyof typeof baseDelay] || 1) * 3;
  }

  /**
   * Compute impact level from cascades
   */
  private computeImpactLevel(
    cascades: DecisionCascade[]
  ): 'critical' | 'significant' | 'minor' {
    const hasCritical = cascades.some((c) => c.impact_level === 'critical');
    const hasSignificant = cascades.some((c) => c.impact_level === 'significant');

    if (hasCritical) return 'critical';
    if (hasSignificant) return 'significant';
    return 'minor';
  }

  /**
   * Compute deeper cascades using BFS
   */
  private computeDeepCascades(): void {
    const cascadeMap = new Map<string, DecisionCascade[]>();
    this.cascades.forEach((c) => {
      if (!cascadeMap.has(c.source_decision_id)) {
        cascadeMap.set(c.source_decision_id, []);
      }
      cascadeMap.get(c.source_decision_id)!.push(c);
    });

    // For each decision, do BFS to depth 3
    this.timelineEvents.forEach((event) => {
      const visited = new Set<string>();
      const queue: Array<{ id: string; depth: number }> = [
        { id: event.decision.id, depth: 0 },
      ];

      while (queue.length > 0) {
        const { id, depth } = queue.shift()!;

        if (visited.has(id) || depth > 3) continue;
        visited.add(id);

        const childCascades = cascadeMap.get(id) || [];
        childCascades.forEach((c) => {
          const existing = event.cascades.find((tc) => tc.targetDecisionId === c.target_decision_id);

          if (!existing) {
            event.cascades.push({
              targetDecisionId: c.target_decision_id,
              targetDecisionTitle: this.decisions.find((d) => d.id === c.target_decision_id)
                ?.title || 'Unknown',
              dependencyType: c.dependency_type,
              depth: depth + 1,
              delay: this.computeDelay(c.dependency_type) * (depth + 1),
            });
          }

          queue.push({ id: c.target_decision_id, depth: depth + 1 });
        });
      }
    });
  }

  /**
   * Render timeline visualization
   */
  private renderTimeline(parentEl: HTMLElement): void {
    // Header
    const header = parentEl.createDiv('timeline-header');
    header.createEl('h2', { text: 'Decision Cascade Timeline' });
    header.createEl('p', {
      text: 'Chronological view of decisions and their downstream impacts',
      cls: 'subtitle',
    });

    // Timeline container
    const timelineContainer = parentEl.createDiv('timeline-container');
    const timeline = timelineContainer.createDiv('timeline');

    // Add timeline events
    this.timelineEvents.forEach((event, idx) => {
      this.renderTimelineEvent(timeline, event, idx);
    });

    // Details panel
    if (this.selectedEvent) {
      const detailsPanel = parentEl.createDiv('timeline-details');
      this.renderEventDetails(detailsPanel, this.selectedEvent);
    }
  }

  /**
   * Render a single timeline event
   */
  private renderTimelineEvent(
    parentEl: HTMLElement,
    event: TimelineEvent,
    index: number
  ): void {
    const eventEl = parentEl.createDiv('timeline-event');

    // Color by impact level
    const colorClass = `impact-${event.impactLevel}`;
    eventEl.addClass(colorClass);

    // Date marker
    const dateEl = eventEl.createDiv('timeline-date');
    const date = new Date(event.date);
    dateEl.createEl('span', { text: date.toLocaleDateString(), cls: 'date-text' });

    // Event content
    const contentEl = eventEl.createDiv('timeline-content');

    // Decision title
    const titleEl = contentEl.createEl('h3', { text: event.decision.title, cls: 'event-title' });
    titleEl.onclick = () => this.selectEvent(event);

    // Decision metadata
    const metaEl = contentEl.createDiv('event-meta');
    metaEl.createEl('span', {
      text: `Status: ${event.decision.status}`,
      cls: 'status-badge',
    });
    metaEl.createEl('span', {
      text: `Confidence: ${(event.decision.confidence_score * 100).toFixed(0)}%`,
      cls: 'confidence-badge',
    });

    // Cascades summary
    if (event.cascades.length > 0) {
      const cascadesEl = contentEl.createDiv('cascades-list');
      cascadesEl.createEl('span', { text: `Cascades (${event.cascades.length}):`, cls: 'cascades-label' });

      const cascadesList = cascadesEl.createDiv('cascades');
      const depthGroups = new Map<number, TimelineCascade[]>();

      event.cascades.forEach((c) => {
        if (!depthGroups.has(c.depth)) {
          depthGroups.set(c.depth, []);
        }
        depthGroups.get(c.depth)!.push(c);
      });

      // Group by depth
      Array.from(depthGroups.entries())
        .sort((a, b) => a[0] - b[0])
        .forEach(([depth, cascades]) => {
          const depthEl = cascadesList.createDiv('cascade-depth');
          depthEl.createEl('span', {
            text: depth === 1 ? 'Direct' : `L${depth}`,
            cls: 'depth-label',
          });

          cascades.forEach((cascade) => {
            const cascadeEl = depthEl.createDiv('cascade-item');
            cascadeEl.addClass(`type-${cascade.dependencyType}`);

            // Icon representing dependency type
            const iconMap: Record<string, string> = {
              enables: '✓',
              blocks: '✗',
              influences: '⊛',
              conflicts: '⚠',
            };
            cascadeEl.createEl('span', {
              text: iconMap[cascade.dependencyType] || '→',
              cls: 'cascade-icon',
            });

            cascadeEl.createEl('span', {
              text: cascade.targetDecisionTitle.substring(0, 40),
              cls: 'cascade-title',
            });

            // Delay indicator
            if (cascade.delay > 0) {
              cascadeEl.createEl('span', {
                text: `+${cascade.delay}d`,
                cls: 'cascade-delay',
              });
            }
          });
        });
    }

    // Click handler
    eventEl.onclick = () => this.selectEvent(event);
  }

  /**
   * Render event details panel
   */
  private renderEventDetails(parentEl: HTMLElement, event: TimelineEvent): void {
    parentEl.createEl('h3', { text: 'Decision Details' });

    const detailsTable = parentEl.createEl('table', { cls: 'details-table' });

    const rows = [
      { label: 'Title', value: event.decision.title },
      { label: 'Status', value: event.decision.status },
      { label: 'Confidence', value: `${(event.decision.confidence_score * 100).toFixed(1)}%` },
      { label: 'Reasoning Type', value: event.decision.reasoning_type },
      { label: 'Chosen Option', value: event.decision.chosen_option },
      { label: 'Rationale', value: event.decision.rationale },
    ];

    rows.forEach(({ label, value }) => {
      const tr = detailsTable.createEl('tr');
      tr.createEl('td', { text: label, cls: 'detail-label' });
      tr.createEl('td', { text: value, cls: 'detail-value' });
    });

    // Cascades detail
    if (event.cascades.length > 0) {
      parentEl.createEl('h4', { text: 'Downstream Impacts' });

      const cascadesTable = parentEl.createEl('table', { cls: 'cascades-detail-table' });
      const header = cascadesTable.createEl('tr');
      header.createEl('th', { text: 'Decision' });
      header.createEl('th', { text: 'Type' });
      header.createEl('th', { text: 'Depth' });
      header.createEl('th', { text: 'Delay (days)' });

      event.cascades.forEach((cascade) => {
        const tr = cascadesTable.createEl('tr');
        tr.createEl('td', { text: cascade.targetDecisionTitle });
        tr.createEl('td', { text: cascade.dependencyType });
        tr.createEl('td', { text: cascade.depth.toString() });
        tr.createEl('td', { text: cascade.delay.toString() });
      });
    }
  }

  /**
   * Select a timeline event
   */
  private selectEvent(event: TimelineEvent): void {
    this.selectedEvent = event;
    this.onOpen(); // Re-render
  }
}
