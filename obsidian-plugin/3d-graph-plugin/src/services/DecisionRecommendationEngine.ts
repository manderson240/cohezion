/**
 * DecisionRecommendationEngine - Phase 7B Decision Recommendation Service
 * Analyzes new papers and recommends decisions to reconsider based on semantic similarity
 * and contradiction detection
 */

import { Decision, DecisionContradiction } from '../types/Decision';
import { Paper } from '../types/Paper';

/**
 * Recommendation generated when a new paper impacts existing decisions
 */
export interface DecisionRecommendation {
  /** Unique recommendation ID */
  id: string;

  /** Related decision ID */
  decision_id: string;

  /** Related decision title */
  decision_title: string;

  /** The new paper that triggered this recommendation */
  new_paper_id: string;

  /** The new paper title */
  new_paper_title: string;

  /** Type of recommendation: contradicts, supports, requires_review */
  recommendation_type: 'contradicts' | 'supports' | 'requires_review';

  /** Score 0-1 indicating confidence */
  score: number;

  /** Reason for recommendation */
  reason: string;

  /** When was this generated */
  timestamp: string;

  /** Has the user addressed this recommendation */
  resolved: boolean;
}

export class DecisionRecommendationEngine {
  /**
   * Find recommendations for a newly added paper
   *
   * Algorithm:
   * 1. Embed new paper with Ollama
   * 2. Find 3 semantically similar existing papers
   * 3. Query: "Which decisions reference these papers?"
   * 4. For each related decision:
   *    - Check if new paper contradicts it
   *    - If similarity > 0.8 and contradiction → recommend review
   *
   * @param newPaper The new paper that was added
   * @param existingPapers All existing papers in vault
   * @param decisions All decisions in vault
   * @param contradictions All detected contradictions
   * @param paperEmbeddings Map of paper_id -> embedding vector
   * @returns Array of recommendations
   */
  static findRecommendations(
    newPaper: Paper,
    existingPapers: Paper[],
    decisions: Decision[],
    contradictions: DecisionContradiction[],
    paperEmbeddings: Map<string, number[]>
  ): DecisionRecommendation[] {
    const recommendations: DecisionRecommendation[] = [];

    // Step 1: Get embedding for new paper (assumes it was already embedded)
    const newPaperEmbedding = paperEmbeddings.get(newPaper.id);
    if (!newPaperEmbedding) {
      console.log('Paper embedding not available for:', newPaper.id);
      return [];
    }

    // Step 2: Find 3 semantically similar papers
    const similarPapers = this.findSimilarPapers(
      newPaper.id,
      newPaperEmbedding,
      existingPapers,
      paperEmbeddings,
      3
    );

    if (similarPapers.length === 0) {
      console.log('No similar papers found for:', newPaper.id);
      return [];
    }

    // Step 3: Find decisions that reference these similar papers
    const relatedDecisions = this.findRelatedDecisions(similarPapers, decisions);

    // Step 4: Evaluate each related decision
    relatedDecisions.forEach((decision) => {
      const recommendation = this.evaluateRecommendation(
        newPaper,
        decision,
        contradictions,
        similarPapers
      );

      if (recommendation && recommendation.score > 0.5) {
        recommendations.push(recommendation);
      }
    });

    return recommendations;
  }

  /**
   * Find papers semantically similar to a given embedding
   */
  private static findSimilarPapers(
    excludePaperId: string,
    targetEmbedding: number[],
    papers: Paper[],
    embeddings: Map<string, number[]>,
    topN: number = 3
  ): Paper[] {
    const similarities: Array<{ paper: Paper; score: number }> = [];

    papers.forEach((paper) => {
      if (paper.id === excludePaperId) return;

      const embedding = embeddings.get(paper.id);
      if (!embedding) return;

      const similarity = this.cosineSimilarity(targetEmbedding, embedding);
      similarities.push({ paper, score: similarity });
    });

    // Sort by similarity descending
    return similarities
      .sort((a, b) => b.score - a.score)
      .slice(0, topN)
      .map((s) => s.paper);
  }

  /**
   * Find decisions that reference the given papers
   */
  private static findRelatedDecisions(papers: Paper[], decisions: Decision[]): Decision[] {
    const paperIds = new Set(papers.map((p) => p.id));
    return decisions.filter(
      (decision) =>
        decision.related_papers && decision.related_papers.some((pid) => paperIds.has(pid))
    );
  }

  /**
   * Evaluate if a decision should be recommended for review
   */
  private static evaluateRecommendation(
    newPaper: Paper,
    decision: Decision,
    contradictions: DecisionContradiction[],
    similarPapers: Paper[]
  ): DecisionRecommendation | null {
    // Check if there are existing contradictions for this decision
    const decisionContradictions = contradictions.filter((c) => c.decision_id === decision.id);

    // Similarity score based on number of related similar papers
    const similarityScore = similarPapers.length / 3; // 0-1 scale

    // Check for contradiction indicators
    let hasContradiction = false;
    let contradiction_score = 0;

    if (decisionContradictions.length > 0) {
      hasContradiction = true;
      contradiction_score = Math.min(decisionContradictions.length / 5, 1.0); // Normalize
    }

    // Overall recommendation score
    const score = similarityScore * 0.5 + contradiction_score * 0.5;

    if (score < 0.3) {
      return null; // Low confidence
    }

    // Determine recommendation type
    let recommendation_type: 'contradicts' | 'supports' | 'requires_review' = 'requires_review';

    if (hasContradiction && score > 0.7) {
      recommendation_type = 'contradicts';
    } else if (similarityScore > 0.8 && !hasContradiction) {
      recommendation_type = 'supports';
    }

    // Generate reason
    const reason = this.generateReason(
      newPaper,
      decision,
      similarPapers,
      hasContradiction,
      recommendation_type
    );

    return {
      id: `rec-${decision.id}-${newPaper.id}`,
      decision_id: decision.id,
      decision_title: decision.title,
      new_paper_id: newPaper.id,
      new_paper_title: newPaper.title,
      recommendation_type,
      score: Math.min(score, 1.0),
      reason,
      timestamp: new Date().toISOString(),
      resolved: false,
    };
  }

  /**
   * Generate human-readable reason for recommendation
   */
  private static generateReason(
    newPaper: Paper,
    decision: Decision,
    similarPapers: Paper[],
    hasContradiction: boolean,
    type: string
  ): string {
    const paperList = similarPapers.map((p) => `"${p.title}"`).join(', ');

    if (hasContradiction) {
      return `The new paper "${newPaper.title}" is similar to existing references (${paperList}) and contradicts this decision. Review recommended.`;
    } else if (type === 'supports') {
      return `The new paper "${newPaper.title}" provides additional support for this decision through similar references (${paperList}).`;
    } else {
      return `The new paper "${newPaper.title}" is related to this decision through similar papers. Consider reviewing the relationship.`;
    }
  }

  /**
   * Cosine similarity between two vectors
   */
  private static cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;

    let dotProduct = 0;
    let magnitudeA = 0;
    let magnitudeB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      magnitudeA += a[i] * a[i];
      magnitudeB += b[i] * b[i];
    }

    magnitudeA = Math.sqrt(magnitudeA);
    magnitudeB = Math.sqrt(magnitudeB);

    if (magnitudeA === 0 || magnitudeB === 0) return 0;

    return dotProduct / (magnitudeA * magnitudeB);
  }

  /**
   * Check if a new paper contradicts a specific decision
   */
  static evaluateContradiction(
    newPaper: Paper,
    decision: Decision,
    newPaperText: string,
    decisionText: string
  ): { contradicts: boolean; score: number; reason: string } {
    // Simple heuristic: look for contradictory keywords
    const contradictoryKeywords = [
      'not',
      'avoid',
      'contra',
      'opposite',
      'reverse',
      'false',
      'invalid',
      'incorrect',
    ];
    const supportiveKeywords = ['confirm', 'support', 'validate', 'agree', 'align', 'match'];

    // Count keyword matches
    let contradictionCount = 0;
    let supportCount = 0;

    contradictoryKeywords.forEach((keyword) => {
      if (newPaperText.toLowerCase().includes(keyword)) {
        contradictionCount++;
      }
    });

    supportiveKeywords.forEach((keyword) => {
      if (newPaperText.toLowerCase().includes(keyword)) {
        supportCount++;
      }
    });

    const contradicts = contradictionCount > supportCount && contradictionCount > 0;
    const score = contradicts ? Math.min(contradictionCount / 3, 1.0) : 0;

    let reason = 'No clear contradiction detected.';
    if (contradicts) {
      reason = `Detected ${contradictionCount} potential contradictory indicators in the new paper.`;
    } else if (supportCount > 0) {
      reason = `The new paper appears to support this decision (${supportCount} supportive indicators).`;
    }

    return { contradicts, score, reason };
  }
}
