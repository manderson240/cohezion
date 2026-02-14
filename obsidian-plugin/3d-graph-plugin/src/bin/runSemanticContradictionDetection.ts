#!/usr/bin/env node
/**
 * Phase 6C: Semantic Contradiction Detection Runner
 *
 * Orchestrates the semantic contradiction detection process:
 * 1. Query all decisions and lessons from SurrealDB
 * 2. Run SemanticContradictionDetector with Ollama embeddings
 * 3. Store results back to SurrealDB
 * 4. Output summary and sample contradictions
 *
 * Usage: npx ts-node src/bin/runSemanticContradictionDetection.ts
 */

import { SemanticContradictionDetector } from '../services/SemanticContradictionDetector';
import { SurrealDBClient } from '../services/SurrealDBClient';

async function main() {
  const startTime = Date.now();
  console.log('[SemanticContradictionDetection] ========== Phase 6C: Semantic Contradiction Detection ==========');
  console.log(`[SemanticContradictionDetection] Start time: ${new Date().toISOString()}`);

  try {
    // Initialize clients
    const dbClient = new SurrealDBClient('http://localhost:8000');
    const detector = new SemanticContradictionDetector('http://localhost:11434');

    // Step 1: Query all decisions and lessons
    console.log('[SemanticContradictionDetection] [1/4] Querying decisions and lessons...');
    const [decisions, lessons] = await Promise.all([
      dbClient.queryAllDecisionsForEmbedding(),
      dbClient.queryAllLessonsForEmbedding(),
    ]);

    console.log(`[SemanticContradictionDetection] Found ${decisions.length} decisions and ${lessons.length} lessons`);

    if (decisions.length === 0 || lessons.length === 0) {
      console.error('[SemanticContradictionDetection] ERROR: No decisions or lessons found');
      process.exit(1);
    }

    // Step 2: Run semantic contradiction detection
    console.log('[SemanticContradictionDetection] [2/4] Detecting semantic contradictions...');
    const detectionStartTime = Date.now();
    const contradictions = await detector.detectContradictions(decisions, lessons, 0.7);
    const detectionDuration = Date.now() - detectionStartTime;

    console.log(
      `[SemanticContradictionDetection] Detected ${contradictions.length} contradictions in ${detectionDuration}ms`
    );

    // Step 3: Store results to SurrealDB
    console.log('[SemanticContradictionDetection] [3/4] Storing results to SurrealDB...');
    const storageStartTime = Date.now();
    const storedCount = await dbClient.storeSemanticContradictions(contradictions);
    const storageDuration = Date.now() - storageStartTime;

    console.log(
      `[SemanticContradictionDetection] Stored ${storedCount} contradictions in ${storageDuration}ms`
    );

    // Step 4: Output summary and samples
    console.log('[SemanticContradictionDetection] [4/4] Summary & Validation');
    console.log('========================================');

    // Group by severity
    const bySeverity: Record<string, number> = {};
    const byType: Record<string, number> = {};

    contradictions.forEach(c => {
      bySeverity[c.severity] = (bySeverity[c.severity] || 0) + 1;
      byType[c.challenge_type] = (byType[c.challenge_type] || 0) + 1;
    });

    console.log('\nContradictions by Severity:');
    Object.entries(bySeverity).forEach(([severity, count]) => {
      console.log(`  ${severity}: ${count}`);
    });

    console.log('\nContradictions by Type:');
    Object.entries(byType).forEach(([type, count]) => {
      console.log(`  ${type}: ${count}`);
    });

    // Show sample contradictions (first 10)
    console.log('\nSample Detected Contradictions (first 10):');
    contradictions.slice(0, 10).forEach((c, i) => {
      console.log(
        `  ${i + 1}. ${c.decision_id} vs ${c.lesson_id} [${c.severity}] (${c.challenge_type})`
      );
      console.log(`     ${c.description.substring(0, 100)}...`);
    });

    // Performance metrics
    const totalDuration = Date.now() - startTime;
    console.log('\nPerformance Metrics:');
    console.log(`  Detection: ${detectionDuration}ms`);
    console.log(`  Storage: ${storageDuration}ms`);
    console.log(`  Total: ${totalDuration}ms`);

    // Success criteria check
    console.log('\nSuccess Criteria:');
    console.log(`  ✓ Decisions embedded: ${decisions.length}`);
    console.log(`  ✓ Lessons embedded: ${lessons.length}`);
    console.log(`  ${contradictions.length >= 20 ? '✓' : '✗'} Contradictions detected: ${contradictions.length} (target: 20+)`);
    console.log(`  ${detectionDuration < 20000 ? '✓' : '✗'} Detection time: ${detectionDuration}ms (target: <20s)`);
    console.log(`  ${storedCount > 0 ? '✓' : '✗'} Storage successful: ${storedCount} stored`);

    console.log('\n[SemanticContradictionDetection] ========== COMPLETE ==========');
    console.log(`[SemanticContradictionDetection] End time: ${new Date().toISOString()}`);

    process.exit(0);
  } catch (error) {
    console.error('[SemanticContradictionDetection] FATAL ERROR:', error);
    process.exit(1);
  }
}

main();
