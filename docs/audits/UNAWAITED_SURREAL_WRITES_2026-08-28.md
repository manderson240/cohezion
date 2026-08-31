# Un-awaited SurrealDB writes (fixed) + `quality_eval` is a length proxy (documented)

Date: 2026-08-28 · Entry point: `scripts/ci/dormancy_scan.py` notice that
`quality_eval.evaluate` is dormant on the production path.

Tracing that one notice surfaced **four** coupled findings. One was fixed and verified
live; three are documented because fixing them would have made the system worse.

| # | Finding | Disposition |
|---|---------|-------------|
| D1 | `AutoDQA` has **zero** production instantiations | documented — do NOT wire (see D4) |
| D2 | `metrics["quality_score"]` has live readers, **no writer** | documented (needs a real producer) |
| D3 | Async SurrealDB writes never awaited → **no row ever written** | **FIXED + verified live** |
| D4 | `quality_eval` score **is length** — wiring it would teach "verbose = good" | documented; blocks D1/D2 |

---

## D3 — the fix (landed)

Every public write on `SurrealClient` is `async def`. Calling one from sync code without
`await` constructs the coroutine and **discards** it: the write never happens, nothing
raises, and the caller's `try/except` never fires.

`surreal_client.run_sync` was written 2026-07-30 specifically to fix this, and its own
docstring **names the two live sites**. Neither was ever changed — *the helper shipped, the
fix did not.*

```python
# before — coroutine built, dropped, no row, no error
client.create("autodqa_results", {...})
# after
run_sync(client.create("autodqa_results", {...}))
```

Sites fixed: `compound/autodqa.py::_persist_result`,
`inference/gemini_cli_tier.py::_persist_tier_experience`.

### Why `await_count`, not `call_count`

An `AsyncMock` records a **call** the moment the coroutine is constructed — which the broken
code does. Only awaiting increments `await_count`. `call_count` therefore passes against the
defect and cannot discriminate it. Choosing the wrong counter here yields a green test over a
permanently dead write.

### Class bounded at 2 by an independent oracle

An AST scan that **binds the receiver** to a `SurrealClient(...)` construction finds exactly
the two sites — agreeing with the 2026-07-30 docstring while having been written without
reference to it (a structural oracle, not a second opinion).

Name-matching alone reports **~56** sites, of which ~54 are file locks, Docker containers and
threads that merely share the method names `close` / `create` / `query`. **Type-proving the
receiver is the entire difference between a usable check and unusable noise** — the check is
kept as a test (`TestDefectClassStaysClosed`) rather than a new CI script, because the class
is small and the existing pytest gate already runs.

### Live verification (un-mocked)

`cohezion/vault.tier_experience` **did not exist** before the fix; after two real calls it
holds rows. Three traps were hit on the way, each of which reads as "the fix doesn't work":

- The client defaults to `database="vault"`, **not** `main`. Querying `db=main` returns
  *"table does not exist"* — a false negative from aiming at the wrong database.
- SurrealDB returns **HTTP 200 with a statement-level `ERR`** for that case; a caller checking
  only the status code records success.
- A profiler using two `asyncio.run()` calls on one client fails with *"attached to a
  different loop"* — the probe's bug, not the code's (`run_sync` uses a single loop).

### Latency constraint (measured — read before wiring either path)

In a single event loop: **`connect()` = 2.24 s, `create()` = 2 ms.** Both call sites construct
a **fresh client per write**, so each write costs ~1.7 s end-to-end.

Neither path has a production consumer today (`gemini_cli_tier`: zero; `AutoDQA`: zero `.py`
constructions), so this is **not** on a live hot path — which is precisely why no
connection-pooling worker was built here. **Amortize the connection before wiring either
one**, or the write adds ~1.7 s to a response budget of 24 ms (NPU) – 800 ms (CPU).

---

## D4 — `quality_eval` is a length proxy (this is what blocked the "obvious" fix)

```python
_eval_short_answer: score = min(1.0, len(text) / 50)
_eval_generation:   score = min(1.0, len(text) / (min_len * 3))
```

Measured with `classify` + `evaluate`, no mocks:

| input | output_type | score | accept |
|---|---|---|---|
| `"Use pathlib.Path: Path(a)/b normalizes separators."` | short_answer | 1.00 | True |
| `"Great question! I totally agree, excellent point."` | short_answer | **0.98** | **True** |
| `"Well, it depends... I cannot say."` | short_answer | **1.00** | **True** |
| `"yes"` (correct answer to a yes/no question) | short_answer | **0.00** | **False** |
| `"blah " * 12` (content-free repetition) | short_answer | **1.00** | **True** |

- `_UNCERTAINTY_MARKERS[:4]` is a deliberate **strict slice** that excludes `"i cannot"`
  (index 4), so evasive non-answers pass. The slice is intentional; the *name* implies
  coverage it does not have.
- `"yes"` fails because `classify` routes a yes/no question to `short_answer` (min 10 chars)
  instead of `categorical` — a separate classifier defect worth its own pass.

**Consequence:** wiring `AutoDQA` / `quality_eval` as the producer of
`ExecutionMetrics.quality_score` would feed a length monotone into `DifficultyEstimator`
(GIC2 `QUALITY_FLOOR = 0.6` → tier routing), the RL process reward (RL1–RL4) → `mgpo_weight`,
and AdaJEPA world-model calibration — **teaching the compound loop that verbose = good.**
That is strictly worse than today's anomaly proxy, which is at least not systematically
biased.

Closing a dormancy with a biased signal is the "constant-anti-signal gate" mistake that
`.claude/rules/verification-depth.md` was written about. **Dormant beats biased.**

---

## D2 — `metrics["quality_score"]`: readers, no writer

`grep 'metrics\["quality_score"\]' executor.py` returns **zero assignments**, yet it is read on
the production path by:

- `executor.py` — AdaJEPA world-model calibration (falls back to `coherence`)
- `compound_persist.py:158` (falls back to `coherence`)
- `coherence_v3.py:173` — `float(metrics.get("quality_score", 0.0) or 0.0)`, structurally
  always `0.0`. (`coherence_v3` itself has zero production callers — second-order dormancy.)

Separately, `SkillRefiner._extract_metrics` sets `quality_score = anomaly_score`: the two
fields are **the same number under different names**, so any consumer combining them
double-counts one measurement.

Fixing D2 requires a **real** quality producer. D4 is why the available one cannot be used.

---

## I6 is overstated — harness correction owed

`.claude/rules/harness.md` → `### I6: AUTODQA must reject sycophantic outputs` verifies with
`dqa.evaluate('', ...)` — the **empty string**. It proves `if not output.strip(): reject` and
says nothing about sycophancy; a non-empty sycophantic answer scores 0.98 / accept=True.

The edit to `harness.md` was **denied** (protected file). Two changes are proposed:

1. Narrow I6's claim to "empty-output rejection", with the D4 measurements attached and an
   explicit *do-not-wire-as-`quality_score`-producer* warning.
2. Add **PW1**: a sync caller of an async `SurrealClient` method must drive the coroutine;
   `await_count` is the instrument; the class is bounded at 2 by receiver-typed AST scan; the
   2.24 s connect cost gates any future production wiring.

---

## Verification

```
uv run pytest tests/test_unawaited_surreal_writes.py -q   → 10 passed
```

Discriminating: against the pre-fix code **5 fail** (the assertions) and **5 pass** (the
detector's positive/negative controls — these must pass in the RED phase too, since they
validate the instrument independently of the defect).

Regression: `tests/unit/compound/test_autodqa.py`, `tests/inference/test_agreement.py`,
`tests/unit/inference/test_fractal_metrics.py` → 66 passed.

## Cleanup owed

Probe rows were written to `cohezion/vault.tier_experience` during live verification
(`prompt_snippet` = `probe prompt` / `probe prompt 2`; `tier` = `probe` / `__profile__`). They
are left in place — deleting from a shared database was not authorized. The table was empty
before this session, so every row in it is a probe artifact.
