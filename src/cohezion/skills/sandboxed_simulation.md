# Sandboxed Simulation

## Skill ID
`sandboxed_simulation`

## Category
Infrastructure / Isolation

## Description
Execute Python simulation scripts inside resource-limited sandboxes with automatic output collection and result persistence. Supports three isolation tiers (light/medium/heavy) and three backends (Docker, systemd-run, subprocess).

## API

### CLI
```bash
# Run a built-in example
cohezion simulate --tier light --example hello --backend subprocess

# Run a custom script
cohezion simulate --tier medium --script path/to/sim.py --backend docker

# Available examples: hello, coherence_walk
# Available tiers: light, medium, heavy
# Available backends: docker, systemd, subprocess (auto-selected if omitted)
```

### Python
```python
from cohezion.universe.sandbox_manager import get_sandbox_manager
from cohezion.universe.sandbox_profiles import SandboxTier
from cohezion.universe.sandbox_results import persist_result

manager = get_sandbox_manager()
result = await manager.run_simulation(script, tier=SandboxTier.LIGHT)

if result.success:
    run_dir = persist_result(result, run_id="my_run", tier="light")
```

## Tier Profiles

| Tier   | Memory  | CPU  | Timeout | Network | GPU |
|--------|---------|------|---------|---------|-----|
| light  | 1 GB   | 100% | 60s     | No      | No  |
| medium | 4 GB   | 200% | 300s    | No      | No  |
| heavy  | 64 GB  | 400% | 1800s   | No      | Yes |

## Backend Selection

1. **Docker** (strongest): Full container isolation. Requires Docker daemon.
2. **systemd-run** (medium): Native cgroups via `systemd-run --scope --user`. Linux only.
3. **subprocess** (weakest): `resource.setrlimit` in child process. Always available.

Use `select_backend()` for automatic strongest-available selection, or pass `--backend` to the CLI.

## Output Collection

Simulations write files to an `output/` directory relative to their working directory. All files found in `output/` after execution are collected into `BackendResult.output_files` as `{filename: bytes}`.

## Result Persistence

Results are saved to `data/simulations/{run_id}/`:
- `meta.json` -- run metadata (tier, backend, success, duration)
- `stdout.txt` -- captured stdout
- `stderr.txt` -- captured stderr
- `output/` -- collected output files

## Example Scripts

- **hello**: Minimal validation. Prints JSON with Python version and cwd, writes `output/result.json`.
- **coherence_walk**: Mean-reverting random walk tracking HIHO coherence (0.5 target). Writes trajectory and summary to `output/`.

## Safety

- Memory budget enforced system-wide (100 GB of 128 GB)
- Circuit breaker trips after 3 consecutive failures
- Backpressure delay when system dilation factor < 0.3
- DivergenceDetector attached to each sandbox instance
