# Autonomous Recursive Expansion Engine (AREE)

**Branch:** `feat/autonomous-recursive-expansion-engine`

A self-improving recursive loop that expands in scope each tick, grounded in Obsidian vault and SurrealDB, with Ouroboros self-monitoring and Mycelium pattern propagation.

## Philosophy

> *"Each feature created makes every new feature easier to obtain."*

This is **compound engineering**: unlike linear progression where each step requires equal effort, AREE implements exponential leverage where prior capabilities accelerate future capability acquisition.

## Architecture

```
Tick 1: INITIALIZE   → Ground in vault, load prior learnings
Tick 2: RESEARCH     → Synthesize bleeding-edge research
Tick 3: SYNTHESIZE   → Generate PRIME skills (compound returns)
Tick 4: ORCHESTRATE  → Spawn agent swarms
Tick 5: PROPAGATE    → Mycelium capture, Ouroboros validation
Tick N: EXPAND       → Each prior feature enables the next
```

### Compound Returns Formula

```
efficiency_gain = 0.02 × scope_size + 0.01 × depth
max_gain = 30% (hard cap)
```

Each skill in scope adds 2% efficiency. Each mycelium pattern adds 1%. Maximum compound gain is 30%.

## Safety First: OOM Guards

**Critical:** AREE includes multiple layers of OOM protection to prevent system crashes:

1. **28GB Threshold**: Maximum memory on 32GB systems
2. **5GB Warning**: Automatic GC trigger
3. **2GB Critical**: Loop pauses (does not crash)
4. **φ-floor**: Early exit at φ < 0.3 (degeneration detection)
5. **Checkpointing**: State saved every 10 ticks

```python
if available_mb < 2_000:
    logger.error(f"OOM GUARD: Only {available_mb:.0f}MB available. Pausing.")
    return False  # Loop pauses, system stays stable
```

## Grounding

### Obsidian Vault
- **Path**: `cloud-vault-mcp/vault/cerebellum/`
- **Writes**: `aree_{tick_id}_{timestamp}.md`
- **Queries**: Cerebellum notes, pattern library

### SurrealDB
- **Endpoint**: `http://localhost:8001`
- **Table**: `aree_tick`
- **Namespace**: `cohezion/expansion`

### High-Sigma Research
- SAGE (2512.17102): Skill library RL
- EVOLVE (2502.05605): Sequential rollout
- Tool-R0 (2602.21320): Tool learning RL
- TwinRouterBench (2605.18859): Dynamic routing

## Usage

### Prerequisites

```bash
# Lemonade on port 13305
lemonade serve nomic-embed-text-v2-moe-GGUF --port 13305

# SurrealDB on port 8001
surreal start --bind 0.0.0.0:8001
```

### Run

```bash
# Basic run (50 ticks)
python scripts/run_recursive_expansion.py --ticks 50

# With custom parameters
python scripts/run_recursive_expansion.py \
    --ticks 100 \
    --phi-floor 0.35 \
    --checkpoint-every 5 \
    --log-level DEBUG

# Daemon mode (run until interrupted)
python scripts/run_recursive_expansion.py --daemon
```

### Python API

```python
from cohezion.compound.autonomous_recursive_expansion_engine import create_expansion_engine

async def run():
    engine = create_expansion_engine(
        engine_id="my_expansion",
        vault_path="cloud-vault-mcp/vault",
    )
    
    results = await engine.run_recursive_loop(
        max_ticks=50,
        phi_floor=0.3,
        checkpoint_every=10,
    )
    
    print(f"Mean φ: {sum(r.phi_score for r in results) / len(results):.3f}")
    print(f"Capabilities: {list(engine.state.cumulative_scope.keys())}")

asyncio.run(run())
```

## Ouroboros Integration

Each tick validates via Ouroboros:

```python
# Check coherence drop from previous tick
if prev_coherence - current_coherence > threshold:
    await ouroboros.check_coherence(drop, task_id=tick_id)
```

This self-monitoring prevents drift and maintains coherence across recursive depths.

## Mycelium Propagation

Learnings are captured and propagated:

```python
from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry

mycelium = MyceliumRegistry()
entry = JournalEntry(
    entry_id=str(uuid.uuid4()),
    content=learning,
    domain="aree.recursive_expansion",
    timestamp=time.time(),
)
mycelium.ingest_entry(entry)
```

Patterns tagged with `aree.recursive_expansion` become available for future tick grounding.

## φ Scoring

| Tick | Phase | φ Range | Driver |
|------|-------|---------|--------|
| 1 | INITIALIZE | 0.50 | Baseline |
| 2 | RESEARCH | 0.50-0.70 | Papers synthesized |
| 3 | SYNTHESIZE | 0.60-0.85 | Skills generated |
| 4 | ORCHESTRATE | 0.70-0.90 | Agents spawned |
| 5 | PROPAGATE | 0.85 | Patterns captured |
| N | EXPAND | 0.80-0.95+ | Compound returns |

## Files

- `src/cohezion/compound/autonomous_recursive_expansion_engine.py` - Core engine
- `src/cohezion/skills/RECURSIVE_EXPANSION_ENGINE_PRIME.md` - PRIME specification
- `scripts/run_recursive_expansion.py` - CLI runner
- `tests/compound/test_recursive_expansion_engine.py` - Test suite

## Integration with EVO Loop

AREE can be composed with the existing EVO recursive tracer:

```python
# EVO provides the agentic substrate
from cohezion.evo.recursive_tracer import RecursiveTracer

# AREE provides the expansion orchestration
from cohezion.compound.autonomous_recursive_expansion_engine import RecursiveExpansionEngine

# Together: recursive agents that expand their own capabilities
engine = RecursiveExpansionEngine()
tracer = RecursiveTracer()

# Each tick of AREE can spawn EVO agents
# Each EVO voyage can trigger AREE expansion
```

## Testing

```bash
# Run tests
pytest tests/compound/test_recursive_expansion_engine.py -v

# Specific test
pytest tests/compound/test_recursive_expansion_engine.py::TestOOMGuard -v
```

## Safety Checklist

Before running AREE:

- [ ] Lemonade available on port 13305
- [ ] SurrealDB available on port 8001 (or vault-only mode)
- [ ] >5GB free memory
- [ ] Vault path writable
- [ ] OOM guard enabled (default)

## Monitoring

Watch for these logs:

```
INFO  | === TICK aree_xxx_t1 | Phase: INITIALIZE | Depth: 0 ===
INFO  | φ-trend=0.650 entropy=0.823 → σ_factor=0.85
INFO  | Vault learning written: cloud-vault-mcp/vault/cerebellum/aree_xxx.md
INFO  | Tick aree_xxx_t1: EXPAND | φ=0.892 | coherence=0.823 | memory=12432MB
```

## License

Same as Cohezion project.
