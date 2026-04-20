# AIMO Compound Engineering - Quick Start

## Run Your First Session

### Option 1: Quick Validation (15 minutes)
```bash
cd sandbox/aimo
./run_compound_session.sh 0.25 4
```

### Option 2: Standard Session (1 hour)
```bash
./run_compound_session.sh 1 10
```

### Option 3: Full Research Sprint (8 hours)
```bash
./run_compound_session.sh 8 10
```

## Monitor Session

### Watch Logs
```bash
tail -f sessions/aimo_*/session.log
```

### Check Checkpoints
```bash
ls -lh data/checkpoints/aimo_*/
cat data/checkpoints/aimo_*/summary.json
```

### View Vault
```bash
cat ~/vaults/cohezion-vault/regions/cerebrum/aimo/*.json
```

## Resume Interrupted Session
```bash
# Automatically resumes from latest checkpoint
python aimo_compound_driver.py --duration 8
```

## Expected Output

```
========================================
AIMO Compound Research Journey
========================================
Journey ID: aimo_20260324_120000
Duration: 1.0h
Ralph threshold: 0.5
========================================

============================================================
Compound Cycle 1
============================================================
  Running benchmark on 4 problems...
  Results: 50.0% accuracy, 50.0% stability
  Ralph coherence: 0.500 (threshold: 0.5) - PASS
  Coherence threshold met - cycle complete
  Checkpoint saved: cycle 1

============================================================
Journey Summary
============================================================
Journey ID: aimo_20260324_120000
Cycles: 1
Best accuracy: 50.0%
Best stability: 50.0%
Best coherence: 0.500
Failures logged: 2
Mutations applied: 0
Checkpoints: 1
Summary saved to: data/checkpoints/aimo_20260324_120000/summary.json
```

## Configuration Options

```bash
python aimo_compound_driver.py \
    --duration 8 \           # Hours
    --problems 10 \          # Number of problems
    --threshold 0.5 \        # Ralph coherence threshold
    --max-cycles 20 \        # Maximum iterations
    --no-vault               # Disable vault logging
```

## Troubleshooting

### Session Interrupted
- Checkpoints auto-saved every cycle
- Restart: automatically resumes from latest

### Thermal Throttling
- Pauses at 90°C
- Resumes at 80°C
- Check `data/checkpoints/*/thermal_events.json`

### Vault Access Issues
- Use `--no-vault` flag
- Checkpoints still saved to disk

## Next Steps

1. Run quick validation (15 min)
2. Review results in `data/checkpoints/`
3. Run full session (8h) overnight
4. Analyze summary next morning
5. Trigger skill refinement if needed
