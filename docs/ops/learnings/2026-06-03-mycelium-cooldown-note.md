# Mycelium auto-promotion cooldown (2026-06-03)

## Where it lives

The cooldown guard is in `cohezion/mycelium/registry.py`,
`MyceliumRegistry._promote_pattern`:

```python
# Cooldown guard: don't promote single-universe single-agent
# clusters. Otherwise we'd write a vault note every time any
# agent produces 3+ same-signature events.
if len(cluster.member_universe_ids) < 2:
    logger.debug(
        "skip vault+db promotion for %s (only %d universe[s])",
        cluster.cluster_id,
        len(cluster.member_universe_ids),
    )
    return
```

## Mirrored to

- `~/.hermes/SOUL.md` — appended 2026-06-03 (harness context section).
- `docs/ops/two-mycelium-systems.md` — full architecture note.

## Why this cooldown

A single agent executing the same skill repeatedly will produce
3+ same-signature WITNESS_MARK events on the bus. Without the
cooldown, every 10 such events would write a vault entry — vault
spam. Requiring `len(universes) >= 2` means the auto-promote only
fires on *cross-agent* signals, which are the genuinely interesting
patterns the system is designed to surface.

## Testing the cooldown

To exercise the auto-promote end-to-end, you need to emit events
from 2+ different `universe_id` values. From the executor, the
universe is `f"cohezion.execution.{skill_name}"` — so running 3+
different skills with the same executor crosses the threshold.

## Related

- WS1 (this session): wires the executor to the bus so WITNESS_MARK
  events are emitted for every successful skill execution.
- WS6 (prior session): added the auto-promote path with this cooldown.
- See also: `cohezion/mycelium/registry.py:_promote_pattern` (the
  source of truth), and the tests in
  `tests/mycelium/test_registry_promote_pattern.py` (the cooldown
  is enforced by the single-universe skip test).
