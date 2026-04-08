# Overnight Autoresearch Runner

Run long-horizon optimization experiments for 8+ hours with checkpointing and recovery.

## Quick Start

```bash
# Run 50 experiments overnight (8 hour timeout)
python overnight_pi.py --runs 50 --hours 8

# Resume from checkpoint (if interrupted)
python overnight_pi.py --runs 50 --checkpoint 5

# Generate morning report
grep -E "(KEEP|DISCARD)" overnight_*.log | tail -20
```

## Architecture

```
overnight_pi.py
├── OvernightState (JSON checkpoint)
├── _run_benchmark() → METRIC lines
├── _generate_hypothesis() → Pattern rotation
├── _apply_optimization() → Code changes
└── _generate_report() → Morning summary
```

## Checkpoint Format

```json
{
  "session_name": "datamesh_overnight",
  "run_number": 23,
  "best_metric": 45.2,
  "experiments": [...],
  "status": "running"
}
```

## Integration with pi tools

Uses actual pi autoresearch infrastructure:
- `run_experiment` for benchmark execution
- `log_experiment` for result tracking
- `autoresearch.jsonl` for history

## Files Generated

| File | Purpose |
|------|---------|
| `.checkpoint_*.json` | Resume state |
| `overnight_*.log` | Experiment log |
| `report_*.md` | Morning summary |

## Charter Compliance

- ✅ **Idempotency**: Checkpoint before each run
- ✅ **Transparency**: Full log and metrics
- ✅ **0.5 Coherence**: HIHO checks every experiment
- ✅ **Persistence**: No experiment lost

## Troubleshooting

**Q: Session interrupted?**  
A: Re-run same command - auto-resumes from checkpoint.

**Q: Want to start fresh?**  
A: Delete `.checkpoint_*.json` file.

**Q: Benchmark too slow?**  
A: Adjust timeout in `datamesh_query.py`.
