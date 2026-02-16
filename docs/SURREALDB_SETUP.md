# SurrealDB Setup for Phase 5-7 Decision Analysis System

This guide explains how to set up SurrealDB for the decision analysis system.

## Prerequisites

- SurrealDB installed and available in PATH
- Node.js and npm installed
- Vault with 105+ decisions in `/decisions/` folder
- TypeScript environment set up

## Quick Start

1. **Ensure SurrealDB is running**:
   ```bash
   surreal start
   # Or check if already running: lsof -i :8000
   ```

2. **Create schema and populate data**:
   ```bash
   cd obsidian-plugin/3d-graph-plugin
   npx ts-node scripts/populate-test-data.ts
   ```

3. **Verify setup**:
   ```bash
   surreal query "SELECT COUNT(*) FROM decisions;"
   # Expected: 105+
   ```

Done! The system is ready to use.

## Detailed Setup Steps

### Step 1: Start SurrealDB

```bash
surreal start
# Listens on http://localhost:8000
```

Verify it's running:
```bash
lsof -i :8000
# Should show surreal process listening on port 8000
```

### Step 2: Create Tables (Migration)

```bash
cd obsidian-plugin/3d-graph-plugin
surreal query < scripts/surrealdb-migrations.sql
```

This creates 4 tables:
- `decisions` - Core decision records
- `decision_cascades` - Relationships between decisions
- `decision_contradictions` - Contradictions detected
- `decision_impacts` - Computed impacts

### Step 3: Populate Test Data

```bash
npx ts-node scripts/populate-test-data.ts
```

Expected output:
```
Step 1: Loading decisions from vault...
✓ Loaded 105+ decisions

Step 2: Inserting decisions into SurrealDB...
✓ Inserted 105+/105+ decision records

Step 3: Computing decision cascades...
✓ Computed 500+ cascade relationships

Step 4: Inserting cascades into SurrealDB...
✓ Inserted 500+/500+ cascade records

Step 5: Verifying data counts...
  Decisions: 105+
  Cascades: 500+

✓ Setup complete!
```

### Step 4: Verify Setup

```bash
# Check table counts
surreal query "SELECT COUNT(*) FROM decisions;"
# Expected: 105+

surreal query "SELECT COUNT(*) FROM decision_cascades;"
# Expected: 500+ (actual count may vary)

surreal query "SELECT COUNT(*) FROM decision_contradictions;"
# Expected: 20+ (if populated)

# View sample data
surreal query "SELECT * FROM decisions LIMIT 1;"

# Check database info
surreal info for database;
```

## Troubleshooting

### SurrealDB won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Try custom port
surreal start --bind http://0.0.0.0:9999

# Update connection strings to use new port
```

### Tables don't exist
```bash
# Verify tables were created
surreal query "INFO FOR DATABASE;"

# If missing, re-run migration
surreal query < scripts/surrealdb-migrations.sql
```

### Data population fails
```bash
# Check VaultBridge can load decisions
npx ts-node -e "
  import { VaultBridge } from './src/services/VaultBridge';
  VaultBridge.loadAllDecisions().then(d => {
    console.log('Loaded', d.length, 'decisions');
  });
"

# If count is wrong, check vault structure
ls -1 /home/mike-anderson/vaults/cohezion-vault/decisions/*.md | wc -l
```

### SurrealDB connection errors
```bash
# Verify SurrealDB is listening
curl http://localhost:8000/health

# Check firewall/port availability
netstat -an | grep 8000
```

## Testing

### Test direct SurrealDB access
```bash
# Query via surreal CLI
surreal query "SELECT * FROM decisions LIMIT 3;"

# Query via HTTP API
curl -X POST http://localhost:8000/sql \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM decisions LIMIT 1;"}'
```

### Test CascadeInference directly
```bash
npx ts-node -e "
  import { CascadeInferenceEngine } from './src/services/CascadeInference';
  const engine = new CascadeInferenceEngine();
  engine.computeImpacts().then(impacts => {
    console.log('Computed', impacts.length, 'impacts');
  }).catch(err => {
    console.error('ERROR:', err.message);
  });
"
```

## Next Steps

Once setup is complete:

1. Run Phase 1 integration tests (see PHASE_1_FIXES_EXECUTION_PLAN.md)
2. Verify CascadeInference.computeImpacts() works end-to-end
3. Verify DecisionHealthDashboard can query real data
4. Proceed to Phase 1 Fix #2 (Dashboard error handling)

## Support

For issues, see:
- PHASE_1_FIXES_EXECUTION_PLAN.md - Detailed requirements
- PRE_EXECUTION_VALIDATION_RESULTS.md - Validation status
- FIX_1_SCHEMA_IMPLEMENTATION_PACKAGE.md - Full implementation guide
