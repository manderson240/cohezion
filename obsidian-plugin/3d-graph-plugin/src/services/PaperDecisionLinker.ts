/**
 * Paper-Decision Linker Service
 *
 * Builds bidirectional relationships between vault papers and SurrealDB decisions.
 * Extracts paper references from decision notes and maintains link confidence scores.
 *
 * Phase 2: Paper Integration
 */

import { Decision } from '../types/Decision';

export interface PaperLink {
  paper_id: string;
  decision_id: string;
  link_type: 'research' | 'validates' | 'contradicts' | 'reference' | 'evidence';
  confidence: number; // 0.0 - 1.0
  mentioned_in: string; // excerpt
  extracted_at: string; // ISO timestamp
}

export interface PaperReference {
  paper_id: string;
  title: string;
  confidence: number;
  link_type: string;
  context: string; // surrounding text
}

export class PaperDecisionLinker {
  /**
   * Extract paper references from decision text
   *
   * Looks for wiki-links: [[paper-title]] or [[file:path/to/paper]]
   * Also searches for keywords: "research shows", "evidence from", etc.
   */
  extractPaperReferences(
    decisionText: string,
    decisionTitle: string
  ): PaperReference[] {
    const references: PaperReference[] = [];

    // Pattern 1: Wiki-links [[paper-title]] or [[papers/paper-id]]
    const wikiLinkRegex = /\[\[(?:papers\/)?([^\]]+)\]\]/g;
    let match;
    while ((match = wikiLinkRegex.exec(decisionText)) !== null) {
      const paperId = match[1];
      const context = this.extractContext(decisionText, match.index);

      references.push({
        paper_id: paperId,
        title: paperId.replace(/-/g, ' '),
        confidence: 0.95, // Wiki-links are explicit, high confidence
        link_type: this.classifyLinkType(context),
        context,
      });
    }

    // Pattern 2: Keyword-based references
    const keywordPatterns = [
      { keyword: 'research shows', type: 'research', confidence: 0.65 },
      { keyword: 'evidence from', type: 'evidence', confidence: 0.75 },
      { keyword: 'validates', type: 'validates', confidence: 0.70 },
      { keyword: 'contradicts', type: 'contradicts', confidence: 0.70 },
      { keyword: 'referenced in', type: 'reference', confidence: 0.60 },
      { keyword: 'based on', type: 'research', confidence: 0.65 },
    ];

    for (const pattern of keywordPatterns) {
      const regex = new RegExp(
        `([^.]*${pattern.keyword}[^.]*\\.?)`,
        'gi'
      );
      while ((match = regex.exec(decisionText)) !== null) {
        const context = match[1];

        // Try to extract paper ID from context
        const paperId = this.extractPaperIdFromContext(context);
        if (paperId) {
          // Avoid duplicates
          if (
            !references.find(
              r => r.paper_id === paperId && r.link_type === pattern.type
            )
          ) {
            references.push({
              paper_id: paperId,
              title: paperId.replace(/-/g, ' '),
              confidence: pattern.confidence,
              link_type: pattern.type,
              context: context.substring(0, 100),
            });
          }
        }
      }
    }

    return references;
  }

  /**
   * Classify link type based on context text
   */
  private classifyLinkType(
    context: string
  ): 'research' | 'validates' | 'contradicts' | 'reference' | 'evidence' {
    const lowerContext = context.toLowerCase();

    if (lowerContext.includes('contradicts') || lowerContext.includes('however')) {
      return 'contradicts';
    }
    if (
      lowerContext.includes('validates') ||
      lowerContext.includes('confirms') ||
      lowerContext.includes('supports')
    ) {
      return 'validates';
    }
    if (
      lowerContext.includes('evidence') ||
      lowerContext.includes('based on') ||
      lowerContext.includes('shows')
    ) {
      return 'evidence';
    }
    if (
      lowerContext.includes('research') ||
      lowerContext.includes('study') ||
      lowerContext.includes('paper')
    ) {
      return 'research';
    }

    return 'reference'; // default
  }

  /**
   * Extract surrounding context (50 chars before/after)
   */
  private extractContext(text: string, index: number): string {
    const start = Math.max(0, index - 50);
    const end = Math.min(text.length, index + 100);
    return text.substring(start, end).trim();
  }

  /**
   * Try to extract paper ID from keyword context
   */
  private extractPaperIdFromContext(context: string): string | null {
    // Look for paper ID patterns like "smith-2024" or "paper-123"
    const paperIdRegex =
      /([a-z]+-\d{4}|paper-\d+|[a-z-]+\d{4})/i;
    const match = context.match(paperIdRegex);
    return match ? match[1] : null;
  }

  /**
   * Build PaperLink objects from extracted references
   */
  buildLinks(
    decision: Decision,
    references: PaperReference[]
  ): PaperLink[] {
    return references.map(ref => ({
      paper_id: ref.paper_id,
      decision_id: decision.id,
      link_type: ref.link_type as any,
      confidence: ref.confidence,
      mentioned_in: ref.context.substring(0, 200),
      extracted_at: new Date().toISOString(),
    }));
  }

  /**
   * Process all decisions, extract paper references, build links
   */
  processAllDecisions(decisions: Decision[]): PaperLink[] {
    const allLinks: PaperLink[] = [];

    for (const decision of decisions) {
      const decisionText = `${decision.title}\n${decision.rationale}`;
      const references = this.extractPaperReferences(
        decisionText,
        decision.title
      );
      const links = this.buildLinks(decision, references);
      allLinks.push(...links);
    }

    return allLinks;
  }

  /**
   * Get all papers related to a decision
   */
  getRelatedPapers(
    decision: Decision,
    links: PaperLink[]
  ): PaperLink[] {
    return links.filter(link => link.decision_id === decision.id);
  }

  /**
   * Get all decisions related to a paper
   */
  getRelatedDecisions(
    paperId: string,
    links: PaperLink[]
  ): PaperLink[] {
    return links.filter(link => link.paper_id === paperId);
  }

  /**
   * Get high-confidence links only (confidence >= threshold)
   */
  getHighConfidenceLinks(
    links: PaperLink[],
    threshold: number = 0.7
  ): PaperLink[] {
    return links.filter(link => link.confidence >= threshold);
  }
}
