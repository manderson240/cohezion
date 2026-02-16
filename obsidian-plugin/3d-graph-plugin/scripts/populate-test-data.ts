import { VaultBridge } from '../src/services/VaultBridge';
import { CascadeInferenceEngine } from '../src/services/CascadeInference';
import { SurrealDBClient } from '../src/services/SurrealDBClient';

async function populateTestData(): Promise<void> {
  console.log('Starting test data population...\n');

  // Initialize services
  const vault = new VaultBridge();
  const db = new SurrealDBClient('http://localhost:8000');
  const cascadeEngine = new CascadeInferenceEngine();

  try {
    // Step 1: Load decisions from vault
    console.log('Step 1: Loading decisions from vault...');
    const decisions = await vault.loadAllDecisions();
    console.log(`✓ Loaded ${decisions.length} decisions\n`);

    if (decisions.length === 0) {
      console.error('❌ ERROR: No decisions loaded from vault. Check VaultBridge.');
      process.exit(1);
    }

    // Step 2: Insert decisions into SurrealDB
    console.log('Step 2: Inserting decisions into SurrealDB...');
    let insertedCount = 0;
    for (const decision of decisions) {
      try {
        // Use simple INSERT syntax that SurrealDB supports
        const query = `
          CREATE decisions SET
            id = '${decision.id}',
            title = '${decision.title?.replace(/'/g, "\\'")}',
            chosen_option = '${decision.chosen_option?.replace(/'/g, "\\'") || ''}',
            rationale = '${decision.rationale?.replace(/'/g, "\\'") || ''}',
            reasoning_type = '${decision.reasoning_type || 'hybrid'}',
            confidence_score = ${decision.confidence_score || 0.7},
            status = '${decision.status || 'approved'}',
            timestamp = '${decision.timestamp || new Date().toISOString()}'
        `;

        await (db as any).executeQuery(query);
        insertedCount++;
      } catch (err) {
        console.warn(`  ⚠️  Could not insert ${decision.id}: ${(err as Error).message}`);
      }
    }
    console.log(`✓ Inserted ${insertedCount}/${decisions.length} decision records\n`);

    // Step 3: Compute cascades
    console.log('Step 3: Computing decision cascades...');
    let cascades: any[] = [];
    try {
      cascades = await cascadeEngine.computeImpacts();
      console.log(`✓ Computed ${cascades.length} cascade relationships\n`);
    } catch (err) {
      console.warn(`⚠️  Cascade computation failed: ${(err as Error).message}`);
      console.log('   This is expected if CascadeInference has issues. Continuing with empty cascades.\n');
    }

    // Step 4: Insert cascades into SurrealDB
    if (cascades.length > 0) {
      console.log('Step 4: Inserting cascades into SurrealDB...');
      let cascadeInsertedCount = 0;
      for (const cascade of cascades.slice(0, 1000)) {  // Limit to 1000 for testing
        try {
          const query = `
            CREATE decision_cascades SET
              source_decision_id = '${cascade.source_decision_id}',
              target_decision_id = '${cascade.target_decision_id}',
              dependency_type = '${cascade.dependency_type || 'depends_on'}',
              impact_level = '${cascade.impact_level || 'minor'}',
              description = '${cascade.description?.replace(/'/g, "\\'") || ''}',
              depth = ${cascade.depth || 1}
          `;

          await (db as any).executeQuery(query);
          cascadeInsertedCount++;
        } catch (err) {
          console.warn(`  ⚠️  Could not insert cascade: ${(err as Error).message}`);
        }
      }
      console.log(`✓ Inserted ${cascadeInsertedCount}/${Math.min(cascades.length, 1000)} cascade records\n`);
    }

    // Step 5: Verify data
    console.log('Step 5: Verifying data counts...');
    try {
      const decisionCountResult = await (db as any).executeQuery(
        'SELECT COUNT(*) as count FROM decisions'
      );
      const cascadeCountResult = await (db as any).executeQuery(
        'SELECT COUNT(*) as count FROM decision_cascades'
      );

      const decisionCount = (decisionCountResult as any)?.result?.[0]?.count || 0;
      const cascadeCount = (cascadeCountResult as any)?.result?.[0]?.count || 0;

      console.log(`  Decisions: ${decisionCount}`);
      console.log(`  Cascades: ${cascadeCount}`);

      if (decisionCount > 0) {
        console.log('\n✓ Setup complete!');
        console.log('Test data population finished successfully.');
      } else {
        console.warn('\n⚠️  WARNING: Data inserted but count query returned 0. This may indicate a query issue.');
      }
    } catch (err) {
      console.warn(`⚠️  Could not verify counts: ${(err as Error).message}`);
      console.log('   But data may still have been inserted. Please verify manually.');
    }

  } catch (err) {
    console.error('❌ ERROR:', (err as Error).message);
    process.exit(1);
  }
}

// Run population
populateTestData().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
