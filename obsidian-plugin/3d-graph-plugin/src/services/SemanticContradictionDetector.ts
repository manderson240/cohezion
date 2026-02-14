import { DecisionContradiction } from '../types/Decision';
import { SurrealDBClient } from './SurrealDBClient';

/**
 * Semantic Contradiction Detector for Phase 6C
 *
 * Uses Ollama embeddings to find semantic contradictions between decisions and lessons.
 * Computes cosine similarity matrix and extracts contradictions above threshold.
 *
 * Algorithm:
 * 1. Embed all decisions (rationale + chosen_option) with Ollama
 * 2. Embed all lessons (key_insight + implications) with Ollama
 * 3. Build similarity matrix (88 × 44)
 * 4. For pairs where similarity > threshold:
 *    - Extract opposing concepts (heuristic: "not", "avoid", "contra" prefixes)
 *    - Classify contradiction type
 *    - Assign severity based on: (decision_confidence × lesson_importance × similarity) / 3
 *    - Store in SurrealDB
 *
 * Performance target:
 * - Embeddings: <10s for 88 decisions, <5s for 44 lessons
 * - Similarity: <5s
 * - Total: <20s end-to-end
 */
export class SemanticContradictionDetector {
  private ollamaUrl: string;
  private ollamaModel: string = 'nomic-embed-text';

  constructor(ollamaUrl: string = 'http://localhost:11434') {
    this.ollamaUrl = ollamaUrl;
  }

  /**
   * Main entry point: detect semantic contradictions
   * @param decisions Array of decision objects with id, rationale, chosen_option, confidence_score
   * @param lessons Array of lesson objects with id, key_insight, implications, incoming_links
   * @param threshold Similarity threshold (0.0-1.0), default 0.7
   * @returns Array of detected contradictions
   */
  async detectContradictions(
    decisions: any[],
    lessons: any[],
    threshold: number = 0.7
  ): Promise<DecisionContradiction[]> {
    console.log(
      `[SemanticContradictionDetector] Starting detection for ${decisions.length} decisions vs ${lessons.length} lessons`
    );

    const startTime = Date.now();

    try {
      // Step 1: Embed decisions
      console.log('[SemanticContradictionDetector] Embedding decisions...');
      const decisionTexts = decisions.map(d => this.prepareDecisionText(d));
      const decisionEmbeddings = await this.batchEmbed(decisionTexts);

      console.log(
        `[SemanticContradictionDetector] Embedded ${decisionEmbeddings.length} decisions in ${Date.now() - startTime}ms`
      );

      // Step 2: Embed lessons
      console.log('[SemanticContradictionDetector] Embedding lessons...');
      const lessonTexts = lessons.map(l => this.prepareLessonText(l));
      const lessonEmbeddings = await this.batchEmbed(lessonTexts);

      console.log(
        `[SemanticContradictionDetector] Embedded ${lessonEmbeddings.length} lessons in ${Date.now() - startTime}ms`
      );

      // Step 3: Compute similarity matrix and detect contradictions
      console.log('[SemanticContradictionDetector] Computing similarity matrix...');
      const contradictions: DecisionContradiction[] = [];

      for (let i = 0; i < decisionEmbeddings.length; i++) {
        for (let j = 0; j < lessonEmbeddings.length; j++) {
          const similarity = this.cosineSimilarity(decisionEmbeddings[i], lessonEmbeddings[j]);

          if (similarity > threshold) {
            // Found a high-similarity pair - likely a contradiction
            const contradiction = this.buildContradiction(
              decisions[i],
              lessons[j],
              similarity,
              decisionTexts[i],
              lessonTexts[j]
            );
            contradictions.push(contradiction);
          }
        }
      }

      const duration = Date.now() - startTime;
      console.log(
        `[SemanticContradictionDetector] Detected ${contradictions.length} contradictions in ${duration}ms`
      );

      return contradictions;
    } catch (error) {
      console.error('[SemanticContradictionDetector] Detection failed:', error);
      throw error;
    }
  }

  /**
   * Prepare decision text for embedding (rationale + chosen_option)
   */
  private prepareDecisionText(decision: any): string {
    const rationale = decision.rationale || '';
    const chosen = decision.chosen_option || '';
    const alternatives = decision.alternatives_rejected?.join(' ') || '';
    return `${rationale} ${chosen} ${alternatives}`.trim();
  }

  /**
   * Prepare lesson text for embedding (key_insight + implications)
   */
  private prepareLessonText(lesson: any): string {
    const insight = lesson.key_insight || '';
    const implications = lesson.implications || '';
    return `${insight} ${implications}`.trim();
  }

  /**
   * Batch embed texts using Ollama API
   * @param texts Array of text strings to embed
   * @returns Array of embeddings (vectors)
   */
  private async batchEmbed(texts: string[]): Promise<number[][]> {
    const embeddings: number[][] = [];

    // Process in batches to avoid overwhelming the API
    const batchSize = 10;
    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const batchEmbeddings = await Promise.all(
        batch.map(text => this.embedText(text))
      );
      embeddings.push(...batchEmbeddings);

      if (i % 50 === 0 && i > 0) {
        console.log(
          `[SemanticContradictionDetector] Embedded ${i} texts (${Math.round((i / texts.length) * 100)}%)`
        );
      }
    }

    return embeddings;
  }

  /**
   * Embed a single text using Ollama
   * @param text Text to embed
   * @returns Embedding vector
   */
  private async embedText(text: string): Promise<number[]> {
    try {
      const response = await fetch(`${this.ollamaUrl}/api/embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.ollamaModel,
          input: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.embeddings || data.embeddings.length === 0) {
        throw new Error('No embeddings returned from Ollama');
      }

      // data.embeddings is an array of embeddings
      // For single text, return first embedding
      return data.embeddings[0];
    } catch (error) {
      console.error(`[SemanticContradictionDetector] Failed to embed text: "${text.substring(0, 50)}..."`, error);
      throw error;
    }
  }

  /**
   * Compute cosine similarity between two vectors
   * @param vecA First vector
   * @param vecB Second vector
   * @returns Similarity score (0.0-1.0)
   */
  private cosineSimilarity(vecA: number[], vecB: number[]): number {
    if (vecA.length !== vecB.length) {
      throw new Error('Vectors must have the same length');
    }

    // Compute dot product
    let dotProduct = 0;
    for (let i = 0; i < vecA.length; i++) {
      dotProduct += vecA[i] * vecB[i];
    }

    // Compute magnitudes
    const magA = Math.sqrt(vecA.reduce((sum, val) => sum + val * val, 0));
    const magB = Math.sqrt(vecB.reduce((sum, val) => sum + val * val, 0));

    // Avoid division by zero
    if (magA === 0 || magB === 0) {
      return 0;
    }

    // Return normalized similarity
    return dotProduct / (magA * magB);
  }

  /**
   * Extract opposing concepts using simple heuristics
   * @param decisionText Decision text
   * @param lessonText Lesson text
   * @returns Array of opposing concept pairs
   */
  private extractOpposingConcepts(decisionText: string, lessonText: string): string[] {
    const concepts: string[] = [];

    // Simple heuristic: look for negation words or opposite patterns
    const negationPatterns = ['not', 'avoid', 'don\'t', 'don\'t', 'cannot', 'should not', 'contra'];
    const lessonTokens = lessonText.toLowerCase().split(/\s+/);

    // Check if lesson contains negations that might oppose decision
    for (const pattern of negationPatterns) {
      if (lessonText.toLowerCase().includes(pattern)) {
        concepts.push(`lesson contains negation: "${pattern}"`);
      }
    }

    // Extract key decision concepts
    const decisionWords = decisionText.toLowerCase().split(/\s+/).filter(w => w.length > 4);
    const lessonWords = lessonText.toLowerCase().split(/\s+/).filter(w => w.length > 4);

    // Simple overlap detection - if decision uses different key terms than lesson, it's a contradiction
    const decisionSet = new Set(decisionWords.slice(0, 10));
    const lessonSet = new Set(lessonWords.slice(0, 10));

    let overlapCount = 0;
    for (const word of decisionSet) {
      if (lessonSet.has(word)) overlapCount++;
    }

    if (overlapCount === 0) {
      concepts.push('no vocabulary overlap');
    }

    return concepts;
  }

  /**
   * Assign severity level based on multiple factors
   * @param decision Decision object
   * @param lesson Lesson object
   * @param similarity Similarity score (0.7-1.0)
   * @returns Severity level
   */
  private assignSeverity(
    decision: any,
    lesson: any,
    similarity: number
  ): 'critical' | 'high' | 'medium' | 'low' {
    // Severity calculation: (confidence × importance × similarity) / 3
    // confidence: decision confidence_score (0-1)
    // importance: inferred from lesson incoming_links (more links = more important)
    // similarity: already normalized (0.7-1.0, but could be higher)

    const confidence = decision.confidence_score || 0.5;
    const linkCount = lesson.incoming_links || 0;
    const importance = Math.min(1.0, linkCount / 10); // Normalize links to 0-1 scale
    const normalizedSimilarity = similarity / 1.0; // Already 0-1

    const severity = (confidence * importance * normalizedSimilarity) / 3;

    if (severity > 0.66) return 'critical';
    if (severity > 0.44) return 'high';
    if (severity > 0.22) return 'medium';
    return 'low';
  }

  /**
   * Classify contradiction type based on text patterns
   * @param decisionText Decision text
   * @param lessonText Lesson text
   * @returns Contradiction type
   */
  private classifyContradictionType(
    decisionText: string,
    lessonText: string
  ): 'contradicts' | 'undermines' | 'requires_review' {
    const lessonLower = lessonText.toLowerCase();
    const decisionLower = decisionText.toLowerCase();

    // Strong contradiction indicators
    if (
      lessonLower.includes('not ') ||
      lessonLower.includes('avoid ') ||
      lessonLower.includes('never ')
    ) {
      return 'contradicts';
    }

    // Undermining indicators
    if (
      lessonLower.includes('reduce ') ||
      lessonLower.includes('limit ') ||
      lessonLower.includes('risk ')
    ) {
      return 'undermines';
    }

    // Default to requires_review
    return 'requires_review';
  }

  /**
   * Build a DecisionContradiction object
   */
  private buildContradiction(
    decision: any,
    lesson: any,
    similarity: number,
    decisionText: string,
    lessonText: string
  ): DecisionContradiction {
    const concepts = this.extractOpposingConcepts(decisionText, lessonText);
    const severity = this.assignSeverity(decision, lesson, similarity);
    const challengeType = this.classifyContradictionType(decisionText, lessonText);

    return {
      decision_id: decision.id,
      lesson_id: lesson.id,
      challenge_type: challengeType,
      severity,
      description: `Semantic contradiction detected (similarity: ${similarity.toFixed(3)}). ${concepts.join('; ')}`,
    };
  }
}
