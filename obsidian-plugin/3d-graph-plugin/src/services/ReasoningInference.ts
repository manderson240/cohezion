/**
 * Reasoning Chain Inference Engine (Phase 6A)
 *
 * Automatically infers missing reasoning chains for decisions by:
 * 1. Finding semantically similar existing decisions
 * 2. Extracting their reasoning_type patterns
 * 3. Generating plausible chain steps based on patterns
 *
 * Marked with confidence=0.6 and tag="inferred" for human review
 */

import { Decision, ReasoningChain, ReasoningStep } from '../types/Decision';

interface SimilarDecision {
  decision: Decision;
  similarity_score: number;
}

interface InferenceResult {
  decision_id: string;
  reasoning_chain: ReasoningChain;
  confidence: number;
  matched_similar: string[];
  timestamp: string;
}

export class ReasoningInferenceEngine {
  /**
   * Generate a reasoning chain from pattern analysis
   * @param decisionText Title + rationale of decision
   * @param reasoning_types Reasoning types from similar decisions
   * @returns Generated ReasoningChain
   */
  generateChainFromPattern(
    decisionText: string,
    reasoning_types: string[]
  ): ReasoningChain {
    // Analyze text to infer step structure
    const steps: ReasoningStep[] = [];

    // Step 1: Problem identification
    steps.push({
      sequence: 1,
      content: this.extractProblemStatement(decisionText),
      type: this.selectReasoningType(reasoning_types, 'research'),
      confidence: 0.65,
      assumption: 'Problem was clearly identified before decision',
    });

    // Step 2: Option exploration
    steps.push({
      sequence: 2,
      content: this.extractOptionExploration(decisionText),
      type: this.selectReasoningType(reasoning_types, 'pattern'),
      confidence: 0.60,
      assumption: 'Multiple options were considered',
    });

    // Step 3: Evaluation
    steps.push({
      sequence: 3,
      content: this.extractEvaluation(decisionText),
      type: this.selectReasoningType(reasoning_types, 'research'),
      confidence: 0.58,
      assumption: 'Options were evaluated against criteria',
    });

    // Step 4: Selection (if text supports it)
    if (decisionText.length > 100) {
      steps.push({
        sequence: 4,
        content: this.extractSelection(decisionText),
        type: this.selectReasoningType(reasoning_types, 'hybrid'),
        confidence: 0.62,
        assumption: 'Best option was selected based on trade-offs',
      });
    }

    const dominant_type = this.getDominantReasoningType(reasoning_types);

    return {
      id: `inferred-chain-${Date.now()}`,
      decision_id: '',
      steps,
      reasoning_type: (dominant_type as any) || 'hybrid',
      confidence: 0.6,
      assumptions: [
        'Chain inferred from semantic patterns in similar decisions',
        'Human review recommended before relying on this chain',
      ],
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Extract problem statement from decision text
   */
  private extractProblemStatement(text: string): string {
    const lines = text.split('\n');
    const firstSentence = lines[0] || text.substring(0, 100);
    return `Context: ${firstSentence.substring(0, 80)}...`;
  }

  /**
   * Extract option exploration
   */
  private extractOptionExploration(text: string): string {
    if (text.includes('options') || text.includes('alternatives')) {
      return 'Explored multiple implementation approaches';
    }
    return 'Evaluated trade-offs between approaches';
  }

  /**
   * Extract evaluation criteria
   */
  private extractEvaluation(text: string): string {
    if (text.includes('cost') || text.includes('performance')) {
      return 'Assessed cost, performance, and maintainability';
    }
    if (text.includes('time') || text.includes('schedule')) {
      return 'Evaluated timeline and resource constraints';
    }
    return 'Applied project-specific evaluation criteria';
  }

  /**
   * Extract selection rationale
   */
  private extractSelection(text: string): string {
    if (text.includes('best') || text.includes('optimal')) {
      return 'Selected approach with best overall trade-off';
    }
    if (text.includes('incremental')) {
      return 'Chose incremental approach to validate assumptions';
    }
    return 'Selected option balancing multiple constraints';
  }

  /**
   * Select reasoning type that fits context
   */
  private selectReasoningType(
    types: string[],
    defaultType: string
  ): 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid' {
    if (!types || types.length === 0) return 'hybrid';

    // Find most common type, prefer more specific types
    const typeMap = new Map<string, number>();
    for (const t of types) {
      typeMap.set(t, (typeMap.get(t) || 0) + 1);
    }

    // Try to return a reasonable type
    for (const [type, count] of Array.from(typeMap.entries()).sort(
      (a, b) => b[1] - a[1]
    )) {
      if (
        type === 'research' ||
        type === 'pattern' ||
        type === 'intuition' ||
        type === 'convention' ||
        type === 'hybrid'
      ) {
        return type as any;
      }
    }

    return 'hybrid';
  }

  /**
   * Get dominant reasoning type from list
   */
  private getDominantReasoningType(types: string[]): string {
    if (!types || types.length === 0) return 'hybrid';

    const typeMap = new Map<string, number>();
    for (const t of types) {
      typeMap.set(t, (typeMap.get(t) || 0) + 1);
    }

    let maxType = 'hybrid';
    let maxCount = 0;

    for (const [type, count] of typeMap.entries()) {
      if (count > maxCount) {
        maxCount = count;
        maxType = type;
      }
    }

    return maxType;
  }

  /**
   * Infer chains for decisions missing them
   * @param decisions All decisions from vault
   * @param similarDecisions Pre-computed semantic similarities
   * @returns Array of inferred chains
   */
  inferMissingChains(
    decisions: Map<string, Decision>,
    similarDecisions: Map<string, SimilarDecision[]>
  ): InferenceResult[] {
    const results: InferenceResult[] = [];

    for (const [id, decision] of decisions.entries()) {
      // Skip decisions that already have reasoning chains
      if (decision.reasoning_chain && decision.reasoning_chain.steps.length > 0) {
        continue;
      }

      // Get similar decisions for this one
      const similar = similarDecisions.get(id) || [];
      if (similar.length === 0) {
        continue;
      }

      // Extract reasoning types from similar decisions
      const reasoning_types = similar
        .slice(0, 3)
        .map(s => s.decision.reasoning_type);

      // Generate chain from patterns
      const decisionText = `${decision.title}\n${decision.rationale}`;
      const chain = this.generateChainFromPattern(decisionText, reasoning_types);

      // Store result
      chain.decision_id = id;
      results.push({
        decision_id: id,
        reasoning_chain: chain,
        confidence: 0.6,
        matched_similar: similar.slice(0, 3).map(s => s.decision.id),
        timestamp: new Date().toISOString(),
      });
    }

    return results;
  }
}
