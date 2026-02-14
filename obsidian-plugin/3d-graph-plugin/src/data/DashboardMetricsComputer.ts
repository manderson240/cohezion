/**
 * DashboardMetricsComputer - Static methods for calculating dashboard metrics
 * Processes decision data for Phase 7A health dashboard visualization
 */

import { Decision, DecisionCascade, DecisionContradiction } from '../types/Decision';

/**
 * Histogram data structure for Chart.js bar chart
 */
export interface HistogramData {
  labels: string[];
  data: number[];
}

/**
 * Pie chart data structure
 */
export interface PieChartData {
  labels: string[];
  data: number[];
  backgroundColor: string[];
}

/**
 * Line chart data structure
 */
export interface LineChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string;
    tension: number;
  }>;
}

/**
 * Quality ranking entry
 */
export interface QualityRankEntry {
  rank: number;
  title: string;
  qualityScore: number;
  status: string;
  decisionId: string;
}

/**
 * Donut chart data
 */
export interface DonutChartData {
  labels: string[];
  data: number[];
  backgroundColor: string[];
}

/**
 * Decision velocity entry
 */
export interface VelocityEntry {
  week: number;
  count: number;
}

export class DashboardMetricsComputer {
  /**
   * Compute confidence distribution histogram
   * Groups decisions by confidence ranges: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
   */
  static computeConfidenceDistribution(decisions: Decision[]): HistogramData {
    const buckets = [
      { label: '0.0-0.2', count: 0 },
      { label: '0.2-0.4', count: 0 },
      { label: '0.4-0.6', count: 0 },
      { label: '0.6-0.8', count: 0 },
      { label: '0.8-1.0', count: 0 },
    ];

    decisions.forEach((decision) => {
      const score = decision.confidence_score || 0.5;
      if (score < 0.2) buckets[0].count++;
      else if (score < 0.4) buckets[1].count++;
      else if (score < 0.6) buckets[2].count++;
      else if (score < 0.8) buckets[3].count++;
      else buckets[4].count++;
    });

    return {
      labels: buckets.map((b) => b.label),
      data: buckets.map((b) => b.count),
    };
  }

  /**
   * Compute reasoning type breakdown pie chart
   * Counts decisions by reasoning_type: research, pattern, intuition, convention, hybrid
   */
  static computeReasoningBreakdown(decisions: Decision[]): PieChartData {
    const breakdown = {
      research: 0,
      pattern: 0,
      intuition: 0,
      convention: 0,
      hybrid: 0,
    };

    decisions.forEach((decision) => {
      const type = decision.reasoning_type || 'hybrid';
      breakdown[type as keyof typeof breakdown]++;
    });

    const colors = [
      '#3b82f6', // blue - research
      '#10b981', // green - pattern
      '#f59e0b', // amber - intuition
      '#8b5cf6', // purple - convention
      '#6366f1', // indigo - hybrid
    ];

    return {
      labels: Object.keys(breakdown),
      data: Object.values(breakdown),
      backgroundColor: colors,
    };
  }

  /**
   * Compute contradiction rate trend line chart
   * Shows % of decisions with contradictions over time
   */
  static computeContradictionTrend(
    decisions: Decision[],
    contradictions: DecisionContradiction[]
  ): LineChartData {
    // Group decisions by date
    const decisionsByDate: Map<string, Decision[]> = new Map();
    decisions.forEach((d) => {
      const date = new Date(d.timestamp).toISOString().split('T')[0];
      if (!decisionsByDate.has(date)) {
        decisionsByDate.set(date, []);
      }
      decisionsByDate.get(date)!.push(d);
    });

    // Create decision ID to contradiction mapping
    const contradictionMap = new Map<string, DecisionContradiction[]>();
    contradictions.forEach((c) => {
      if (!contradictionMap.has(c.decision_id)) {
        contradictionMap.set(c.decision_id, []);
      }
      contradictionMap.get(c.decision_id)!.push(c);
    });

    // Sort dates and compute percentages
    const dates = Array.from(decisionsByDate.keys()).sort();
    const percentages: number[] = [];

    dates.forEach((date) => {
      const decisionsOnDate = decisionsByDate.get(date) || [];
      const withContradictions = decisionsOnDate.filter(
        (d) => contradictionMap.has(d.id)
      ).length;
      const percentage =
        decisionsOnDate.length > 0
          ? (withContradictions / decisionsOnDate.length) * 100
          : 0;
      percentages.push(percentage);
    });

    return {
      labels: dates.map((d) => new Date(d).toLocaleDateString()),
      datasets: [
        {
          label: 'Contradiction Rate (%)',
          data: percentages,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          tension: 0.4,
        },
      ],
    };
  }

  /**
   * Compute quality score rankings
   * Returns top 10 and bottom 10 decisions by quality score
   */
  static computeQualityRanking(decisions: Decision[]): {
    top: QualityRankEntry[];
    bottom: QualityRankEntry[];
  } {
    // Note: quality_score will be added by Phase 6D
    // This assumes decisions have a quality_score field
    const sorted = decisions.sort((a, b) => {
      const scoreA = (a as any).quality_score || 0;
      const scoreB = (b as any).quality_score || 0;
      return scoreB - scoreA;
    });

    const top: QualityRankEntry[] = sorted.slice(0, 10).map((d, idx) => ({
      rank: idx + 1,
      title: d.title,
      qualityScore: (d as any).quality_score || 0,
      status: d.status,
      decisionId: d.id,
    }));

    const bottom: QualityRankEntry[] = sorted
      .slice(-10)
      .reverse()
      .map((d, idx) => ({
        rank: decisions.length - idx,
        title: d.title,
        qualityScore: (d as any).quality_score || 0,
        status: d.status,
        decisionId: d.id,
      }));

    return { top, bottom };
  }

  /**
   * Compute impact distribution donut chart
   * Shows proportion of critical, significant, minor impact decisions
   */
  static computeImpactDistribution(impacts: Array<any>): DonutChartData {
    const distribution = {
      critical: 0,
      significant: 0,
      minor: 0,
    };

    impacts.forEach((impact) => {
      const level = impact.impact_level || 'minor';
      distribution[level as keyof typeof distribution]++;
    });

    return {
      labels: ['Critical', 'Significant', 'Minor'],
      data: [distribution.critical, distribution.significant, distribution.minor],
      backgroundColor: ['#dc2626', '#f59e0b', '#9ca3af'],
    };
  }

  /**
   * Compute decision velocity bar chart
   * Shows decisions created per week
   */
  static computeDecisionVelocity(decisions: Decision[]): LineChartData {
    // Group decisions by week
    const weekMap: Map<number, number> = new Map();
    const baseDate = new Date(decisions[0]?.timestamp || new Date());
    const baseWeek = Math.floor(baseDate.getTime() / (7 * 24 * 60 * 60 * 1000));

    decisions.forEach((d) => {
      const date = new Date(d.timestamp);
      const weekNumber = Math.floor(date.getTime() / (7 * 24 * 60 * 60 * 1000)) - baseWeek;
      weekMap.set(weekNumber, (weekMap.get(weekNumber) || 0) + 1);
    });

    // Sort by week and create labels
    const weeks = Array.from(weekMap.keys()).sort((a, b) => a - b);
    const labels = weeks.map((w) => `Week ${w}`);
    const data = weeks.map((w) => weekMap.get(w) || 0);

    return {
      labels,
      datasets: [
        {
          label: 'Decisions Created',
          data,
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.5)',
          tension: 0.4,
        },
      ],
    };
  }
}
