#!/usr/bin/env ts-node
/**
 * Decision Quality Scoring Script
 *
 * Executes Phase 6D: Quality scoring for all 88 decisions
 * - Loads decisions from SurrealDB
 * - Calculates quality scores using DecisionQualityScorer
 * - Stores results back to SurrealDB
 * - Generates quality report
 *
 * Usage:
 *   npx ts-node src/scripts/scoreDecisions.ts
 *
 * Output:
 *   - decision_quality_report.txt (markdown report with top/bottom 10)
 *   - Console: Summary and metrics
 */

import { SurrealDBClient } from '../services/SurrealDBClient';
import { DecisionQualityScorer, ScoredDecision } from '../services/DecisionQualityScorer';
import fs from 'fs';
import path from 'path';

async function main() {
  console.log('🎯 Phase 6D: Decision Quality Scoring\n');
  console.log('Starting quality score calculation for all decisions...\n');

  const startTime = Date.now();

  try {
    // Initialize clients
    const surrealDb = new SurrealDBClient('http://localhost:8000');
    const scorer = new DecisionQualityScorer();

    // Check health
    console.log('📡 Checking SurrealDB connection...');
    const healthy = await surrealDb.health();
    if (!healthy) {
      throw new Error('SurrealDB is not accessible at http://localhost:8000');
    }
    console.log('✓ SurrealDB is healthy\n');

    // Query all decisions
    console.log('📥 Fetching all decisions from SurrealDB...');
    const decisions = await surrealDb.queryAllDecisionsForScoring();
    console.log(`✓ Retrieved ${decisions.length} decisions\n`);

    if (decisions.length === 0) {
      console.warn('⚠️  No decisions found in database');
      process.exit(0);
    }

    // Query contradiction counts
    console.log('📥 Fetching contradiction counts...');
    const contradictionMap = await surrealDb.queryAllContradictionCounts();
    console.log(`✓ Retrieved contradiction counts for ${contradictionMap.size} decisions\n`);

    // Score all decisions
    console.log('⚙️  Calculating quality scores...');
    const scoredDecisions = scorer.scoreAllDecisions(decisions, contradictionMap);
    console.log(`✓ Scored ${scoredDecisions.length} decisions\n`);

    // Generate and save report
    console.log('📄 Generating quality report...');
    const report = scorer.generateReport(scoredDecisions);
    const reportPath = path.join(__dirname, '../../decision_quality_report.txt');
    fs.writeFileSync(reportPath, report, 'utf-8');
    console.log(`✓ Report saved to ${reportPath}\n`);

    // Store scores back to database
    console.log('💾 Storing quality scores to SurrealDB...');
    const updateCount = await surrealDb.storeQualityScores(scoredDecisions);
    console.log(`✓ Updated ${updateCount} decision records with quality scores\n`);

    // Calculate and display summary stats
    const sorted = [...scoredDecisions].sort((a, b) => b.overall_score - a.overall_score);
    const avg = scoredDecisions.reduce((sum, d) => sum + d.overall_score, 0) / scoredDecisions.length;
    const median = sorted[Math.floor(sorted.length / 2)].overall_score;
    const stddev = Math.sqrt(
      scoredDecisions.reduce((sum, d) => sum + Math.pow(d.overall_score - avg, 2), 0) / scoredDecisions.length
    );

    console.log('📊 Quality Score Summary:');
    console.log(`   Total Decisions: ${scoredDecisions.length}`);
    console.log(`   Average Score: ${avg.toFixed(3)}`);
    console.log(`   Median Score: ${median.toFixed(3)}`);
    console.log(`   Std Dev: ${stddev.toFixed(3)}`);
    console.log(`   Range: ${Math.min(...scoredDecisions.map(d => d.overall_score)).toFixed(3)} - ${
      Math.max(...scoredDecisions.map(d => d.overall_score)).toFixed(3)
    }\n`);

    // Show top 5
    console.log('🏆 Top 5 Highest Quality Decisions:');
    sorted.slice(0, 5).forEach((d, i) => {
      console.log(`   ${i + 1}. ${d.title} (${d.overall_score.toFixed(3)})`);
    });

    console.log('\n⚠️  Bottom 5 Quality Candidates for Review:');
    sorted.slice(-5).reverse().forEach((d, i) => {
      console.log(`   ${i + 1}. ${d.title} (${d.overall_score.toFixed(3)})`);
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`\n✅ Quality scoring complete in ${elapsed}s`);
    console.log('Phase 6D: SUCCESS\n');

  } catch (error) {
    console.error('\n❌ Error during quality scoring:');
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

main();
