#!/usr/bin/env ts-node

/**
 * Cascade Inference Execution Script
 *
 * Runs Phase 6B: Cascade Impact Computation
 * Computes 2nd/3rd order effects of decisions on each other
 *
 * Usage:
 *   npx ts-node src/scripts/runCascadeInference.ts [db-url]
 *
 * Example:
 *   npx ts-node src/scripts/runCascadeInference.ts http://localhost:8000
 */

import { CascadeInferenceEngine } from '../services/CascadeInference';

async function main() {
  const dbUrl = process.argv[2] || 'http://localhost:8000';

  console.log('============================================================');
  console.log('Phase 6B: Cascade Impact Computation');
  console.log('============================================================');
  console.log(`SurrealDB URL: ${dbUrl}`);
  console.log(`Start time: ${new Date().toISOString()}`);
  console.log('');

  const engine = new CascadeInferenceEngine(dbUrl);

  try {
    // Run cascade inference
    const impacts = await engine.computeImpacts();

    // Verify with sample chains
    await engine.verifyCascadeChains(3);

    // Print summary
    console.log('\n============================================================');
    console.log('EXECUTION SUMMARY');
    console.log('============================================================');
    console.log(`Total impacts computed: ${impacts.length}`);

    // Breakdown by depth
    const byDepth: Record<number, number> = {};
    const byType: Record<string, number> = {};
    let totalScore = 0;

    impacts.forEach(impact => {
      byDepth[impact.depth] = (byDepth[impact.depth] || 0) + 1;
      byType[impact.impact_type] = (byType[impact.impact_type] || 0) + 1;
      totalScore += impact.impact_score;
    });

    console.log('\nBy Depth:');
    Object.entries(byDepth)
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .forEach(([depth, count]) => {
        console.log(`  Depth ${depth}: ${count} impacts`);
      });

    console.log('\nBy Type:');
    Object.entries(byType)
      .sort((a, b) => b[1] - a[1])
      .forEach(([type, count]) => {
        console.log(`  ${type}: ${count} impacts`);
      });

    console.log(`\nAverage impact score: ${(totalScore / impacts.length).toFixed(3)}`);
    console.log(`End time: ${new Date().toISOString()}`);
    console.log('\n✓ Phase 6B COMPLETE');
    console.log('============================================================');

    process.exit(0);
  } catch (error) {
    console.error('\n✗ Phase 6B FAILED');
    console.error('Error:', error);
    console.log('============================================================');
    process.exit(1);
  }
}

main();
