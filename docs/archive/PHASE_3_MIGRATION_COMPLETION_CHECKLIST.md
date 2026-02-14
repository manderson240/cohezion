# Phase 3 Migration: Completion Checklist

**Critical requirement**: Data integrity is non-negotiable. Graceful shutdown MANDATORY.

---

## Pre-Migration Checklist

- [ ] SurrealDB running and accessible at ws://localhost:8000/rpc
- [ ] Genealogy schema deployed to SurrealDB (universe_genealogy_schema.sql applied)
- [ ] All tables created: `SELECT count() FROM [SYSTEM]tables;` ≥ 9
- [ ] All indexes created: `SELECT count() FROM [SYSTEM]indexes;` ≥ 19
- [ ] Backup of SurrealDB database exists
- [ ] No active transactions: `SELECT count() FROM [SYSTEM]transactions;` = 0
- [ ] No locks held: `SELECT count() FROM [SYSTEM]locks;` = 0

---

## Migration Execution Checklist

- [ ] Start migration service: `uv run python src/cohezion/knowledge_graph/universe_genealogy_migration.py`
- [ ] Phase 0 (Measure epochs): Completes successfully
- [ ] Phase 1 (Extract patterns): Completes successfully
- [ ] Phase 2 (Build schema): Completes successfully
- [ ] Phase 3 (Verify patterns): Completes successfully
- [ ] Phase 4 (Extract genealogy): Completes successfully
- [ ] Migration report generated: `/tmp/cohezion_universe_genealogy/genealogy_report.json`
- [ ] Report status = "completed": ✅
- [ ] Report errors = 0: ✅

---

## Data Integrity Verification (CRITICAL)

### Before Any Shutdown:

```bash
# Step 1: Flush all buffers
surreal sql --conn ws://localhost:8000/rpc \
  --namespace cohezion --database core \
  --query "COMMIT;"

# Step 2: Verify all data inserted
surreal sql --conn ws://localhost:8000/rpc \
  --namespace cohezion --database core \
  --query "SELECT count() FROM universe_epochs;"

# Expected: 8 (the 8 evolutionary eras)
# If ≠ 8: DO NOT PROCEED TO SHUTDOWN
```

- [ ] COMMIT executed successfully
- [ ] universe_epochs count = 8
- [ ] Pattern count matches expected (7)
- [ ] Coherence measurements recorded
- [ ] All era transitions recorded
- [ ] Design decisions populated
- [ ] Migration snapshot records exist

### Verification Queries:

```bash
# Verify each table
surreal sql --conn ws://localhost:8000/rpc \
  --namespace cohezion --database core \
  --query "SELECT 'universe_epochs' as table, count() as count FROM universe_epochs UNION
           SELECT 'coherence_timeline' as table, count() as count FROM coherence_timeline UNION
           SELECT 'universe_patterns' as table, count() as count FROM universe_patterns UNION
           SELECT 'pattern_manifestations' as table, count() as count FROM pattern_manifestations;"
```

- [ ] universe_epochs: 8 records
- [ ] coherence_timeline: ≥ 100 measurements
- [ ] universe_patterns: 7 records
- [ ] pattern_manifestations: ≥ 20 records
- [ ] optimization_milestones: populated
- [ ] era_transitions: 7 records (transitions between 8 eras)
- [ ] design_decisions: populated
- [ ] genealogy_observations: populated
- [ ] ouroboros_evidence: populated

### No Exceptions to Data Integrity:

- [ ] Row count mismatches: STOPPED and investigated
- [ ] Missing required fields: STOPPED and fixed
- [ ] Coherence values out of range: STOPPED and audited
- [ ] Epoch dates not sequential: STOPPED and corrected

**If ANY data integrity issue found**: STOP immediately, DO NOT SHUTDOWN, escalate to team-lead.

---

## Graceful Shutdown Procedure (MANDATORY)

### Only execute if ALL verification checkboxes above are COMPLETE and PASSING

```bash
# Step 1: Final transaction state check
surreal sql --conn ws://localhost:8000/rpc \
  --namespace cohezion --database core \
  --query "SELECT count() FROM [SYSTEM]transactions;"
# Expected: 0
```

- [ ] No active transactions: count = 0

```bash
# Step 2: Send graceful shutdown signal
kill -TERM $(pgrep surrealdb)
```

- [ ] Shutdown signal sent

```bash
# Step 3: Wait for clean exit (max 30 seconds)
sleep 10

# Step 4: Verify process stopped
ps aux | grep surrealdb
```

- [ ] SurrealDB process no longer running
- [ ] Shutdown completed in < 30 seconds

### If Still Running After 30 Seconds:

```bash
# Check logs first (NEVER jump to kill -9)
tail -100 /var/log/surrealdb.log

# Look for error messages or warnings
grep -i error /var/log/surrealdb.log | tail -20
```

- [ ] Logs reviewed for shutdown issues
- [ ] Issue root cause identified
- [ ] Documented for team-lead review

**ONLY AFTER logs reviewed and team-lead approves**:
```bash
# Force termination (last resort)
pkill -9 surrealdb
```

- [ ] Force kill executed (if approved)
- [ ] Issue documented and escalated

---

## Post-Shutdown Integrity Check

```bash
# Verify database files not corrupted
ls -lah /home/mike-anderson/dev/cohezion/data/surrealdb/

# Check file timestamps (should be recent)
stat /home/mike-anderson/dev/cohezion/data/surrealdb/CURRENT
```

- [ ] Database files exist
- [ ] File timestamps recent (within last 5 minutes)
- [ ] No corruption indicators in filesystem

---

## Restart Verification (Phase 4 Preparation)

```bash
# Before Phase 4 verification, restart SurrealDB cleanly
surreal start --log info --bind 0.0.0.0:8000 file:/home/mike-anderson/dev/cohezion/data/surrealdb

# Wait for startup (typically 5-10 seconds)
sleep 5

# Verify database integrity
surreal sql --conn ws://localhost:8000/rpc \
  --namespace cohezion --database core \
  --query "SELECT count() FROM universe_epochs;"

# Should still be 8
```

- [ ] SurrealDB restarted cleanly
- [ ] universe_epochs count = 8 (data persisted)
- [ ] All genealogy data intact
- [ ] No recovery messages in logs
- [ ] Ready for Phase 4 verification

---

## Golden Rules (Non-Negotiable)

✅ **Always do**:
1. COMMIT before shutdown
2. Verify data count before shutdown
3. Wait for graceful shutdown (30 seconds)
4. Check logs if not exiting cleanly
5. Verify database files after shutdown
6. Only then report Phase 3 complete

❌ **Never do**:
1. kill -9 surrealdb (corrupts data)
2. Shutdown without COMMIT
3. Skip verification
4. Restart while shutdown signal pending
5. Ignore log messages about uncommitted transactions

---

## Escalation Path

| Issue | Action | Contact |
|-------|--------|---------|
| Data count mismatch | STOP migration, investigate | team-lead |
| Shutdown > 30 seconds | Check logs, wait to 60s | team-lead |
| Still running @ 60s | Review logs, report issue | team-lead |
| Corruption on restart | Restore from backup | team-lead |
| Unknown shutdown error | Escalate immediately | team-lead |

---

## Success Criteria for Phase 3

✅ Migration service executes Phases 0-4 successfully
✅ 8 epochs recorded in universe_epochs
✅ 7 patterns recorded in universe_patterns
✅ HIHO coherence measurements populated
✅ All genealogy tables verified pre-shutdown
✅ COMMIT executed
✅ Data count verified
✅ Graceful shutdown completed
✅ Database files intact on disk
✅ Clean restart confirms data persistence

**Status**: PHASE 3 READY FOR EXECUTION

---

## Team-Lead Approval Gate

After completing entire checklist above:

```
[ ] Schema Engineer: All Phase 3 steps complete
[ ] Data integrity: VERIFIED
[ ] Graceful shutdown: EXECUTED
[ ] Database integrity: CONFIRMED
[ ] Ready for Phase 4: YES

Signature/Date: ___________________
```

**No Phase 4 begins until Phase 3 checklist 100% complete.**

---

**Critical**: This is the migration's only opportunity to guarantee data integrity. Do it right, do it carefully, do it completely.

🛡️ **Data integrity first. Always.**
