/**
 * Decision Analysis Types for Phase 4
 * Extends paper visualization with decision reasoning chains and cascades
 */

/**
 * A single step in a decision reasoning chain
 * Shows the logic that led to a decision
 */
export interface ReasoningStep {
  /** Step number (1-based) */
  sequence: number;

  /** What was considered or analyzed */
  content: string;

  /** Type of reasoning: research, pattern, intuition, convention, hybrid */
  type: 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid';

  /** Confidence in this step (0.0-1.0) */
  confidence: number;

  /** Optional assumption underlying this step */
  assumption?: string;

  /** Optional timestamp when this step was recorded */
  timestamp?: string;
}

/**
 * A complete reasoning chain for a decision
 * Shows why a particular option was chosen
 */
export interface ReasoningChain {
  /** Unique identifier for this reasoning chain */
  id: string;

  /** The decision this chain supports */
  decision_id: string;

  /** Ordered steps showing the reasoning logic */
  steps: ReasoningStep[];

  /** Type of reasoning: research, pattern, intuition, convention, hybrid */
  reasoning_type: 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid';

  /** Overall confidence in this reasoning (0.0-1.0) */
  confidence: number;

  /** Key assumptions made during reasoning */
  assumptions: string[];

  /** When this reasoning was recorded */
  timestamp: string;
}

/**
 * A decision in the knowledge base
 * Represents a choice made during project execution
 */
export interface Decision {
  /** Unique identifier */
  id: string;

  /** Decision title */
  title: string;

  /** The option that was chosen */
  chosen_option: string;

  /** Why this option was chosen */
  rationale: string;

  /** Type of reasoning used */
  reasoning_type: 'research' | 'pattern' | 'intuition' | 'convention' | 'hybrid';

  /** Confidence score (0.0-1.0) */
  confidence_score: number;

  /** Reasoning chain showing the logic */
  reasoning_chain: ReasoningChain;

  /** Alternative options that were rejected */
  alternatives_rejected?: string[];

  /** Related papers (from vault YAML links) */
  related_papers?: string[];

  /** Status: active, archived, revisited */
  status: 'active' | 'archived' | 'revisited';

  /** When was this decision made */
  timestamp: string;

  /** Vault path to the decision note */
  vault_path?: string;

  /** Quality score (0-1), calculated by DecisionQualityScorer */
  quality_score?: number;
}

/**
 * A cascade showing downstream impacts of a decision
 */
export interface DecisionCascade {
  /** Source decision ID */
  source_decision_id: string;

  /** Target decision ID that is impacted */
  target_decision_id: string;

  /** Type of dependency: enables, blocks, influences, conflicts */
  dependency_type: 'enables' | 'blocks' | 'influences' | 'conflicts';

  /** Impact level: critical, significant, minor */
  impact_level: 'critical' | 'significant' | 'minor';

  /** Description of the relationship */
  description: string;
}

/**
 * A contradiction between a decision and evidence/lessons
 */
export interface DecisionContradiction {
  /** The decision being challenged */
  decision_id: string;

  /** The lesson or evidence that contradicts it */
  lesson_id: string;

  /** Type of challenge: contradicts, undermines, requires_review */
  challenge_type: 'contradicts' | 'undermines' | 'requires_review';

  /** Severity: critical, high, medium, low */
  severity: 'critical' | 'high' | 'medium' | 'low';

  /** Details of the contradiction */
  description: string;
}

/**
 * Query result: reasoning chains for a decision
 */
export interface ReasoningQueryResult {
  decision: Decision;
  chains: ReasoningChain[];
  high_confidence: boolean;
  timestamp: string;
}

/**
 * Query result: cascade analysis
 */
export interface CascadeQueryResult {
  source_decision: Decision;
  cascades: DecisionCascade[];
  total_impacted: number;
  critical_impact_count: number;
  timestamp: string;

  /** Convenience property: length of cascades array */
  length?: number;
}

/**
 * Query result: contradictions
 */
export interface ContradictionQueryResult {
  decision: Decision;
  contradictions: DecisionContradiction[];
  severity_counts: Record<string, number>;
  timestamp: string;
}

/**
 * Extended Paper type for Phase 4
 * Links papers to decisions that reference them
 */
export interface PaperWithDecisions {
  paper_id: string;
  paper_title: string;
  decision_ids: string[];
  decision_count: number;
}
