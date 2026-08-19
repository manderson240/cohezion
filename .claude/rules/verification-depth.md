# Verification Depth — the V-model's missing upper rungs (MANDATORY)

**Origin (2026-06-30):** a session of "V-model rigor" still shipped backwards routing, a constant-
anti-signal gate, a dead-port keystone, and an entire eval chain that was wired component-by-component
yet **dormant end-to-end**. Root cause: we ran the *bottom rung only* — unit tests, mocked boundaries,
self-authored discriminating tests, documented invariants — and called the truncation rigor. High green
counts, near-zero system assurance. This rule is the standing corrective so we never re-learn it.

## The Four Correctives (apply to EVERY non-trivial change)

1. **Test the CLAIM, not the component.** Before saying "fixed/verified/done", state the claim in one
   sentence, then run the command that would FALSIFY it. "Categorical → NPU ✓" did not prove "essays
   escalate." A test can be discriminating *and aimed at the wrong half of the input space*.

2. **Consumption, not declaration.** A capability is not "wired" because a kwarg is accepted, an
   attribute is set, or an invariant is logged. It is wired only when a **production consumer reads it
   and acts on it**. For every producer (a metric written, a provider passed, a method defined), grep
   for a non-test, non-`def` consumer. No consumer = DORMANT, regardless of how green the unit tests are.
   (Killed this session: H1 gate, `inference_provider`, `jepa_coherence`, CR1, `moe_router`,
   `get_singleton`, the 4 never-landed subsystems.)

3. **Un-mocked boundary smoke.** Unit tests mock `route`/the orchestrator/SurrealDB — so a wrong port
   (:13306 vs :13305), an empty thinking-model reply, or SurrealDB returning errors as HTTP-200 are
   structurally invisible. Run ONE live probe per real boundary. The dead-port keystone was only ever
   catchable against the live system, never against a mock.

4. **Break the author–test correlation.** The person who wrote the (incomplete) requirement writes the
   (matching incomplete) test — correlated blind spots. For load-bearing changes, get an **adversarial
   second pass** (a different agent, assuming it's broken, tracing producer→consumer in the *assembled*
   system). This is why adversarial review found what the V-model didn't — not more rigor, rigor pointed
   at the integration/system levels the bottom rung skips.

   **Prefer a STRUCTURAL oracle over a social one where the change claims to preserve behaviour.**
   The adversarial-second-pass mechanism is *social* — a different agent, fresh context, told to
   assume it is broken. That is a real control, and it degrades precisely when the second reviewer
   inherits the first's model of what the code is *for*. Canonical/Bristol's automated C→Rust work
   (2026-08-19) uses a structural one instead: the oracle **is the pre-existing implementation**.
   Nobody authored it to test this change, so it cannot share the author's blind spot, and unlike
   a reviewer it cannot be argued with. So: **for a change claimed to be behaviour-preserving, the
   prior revision is a free unbiased oracle and is stronger than a second opinion.** Reserve the
   reviewer for changes that are *supposed* to change behaviour, where no oracle exists.

   **Its limit, measured, so this is not oversold: differential verification detects REGRESSION and
   is blind to NEVER-WORKED.** `SelfHealingSystem.heal_manifold` was called by
   `core/journey_worker.py` and defined nowhere — `git log -S 'def heal_manifold' --all` returns
   **0 commits** (control: `async def heal` returns 3). A diff between any two revisions compares
   two implementations that both never healed and reports no difference: green. Only consumption
   invariants, narrow-guard shape analysis (`scripts/ci/narrow_guard_scan.py`), and un-mocked
   boundary smoke catch that class. The two approaches are **orthogonal, not nested** — use the
   prior revision for drift, the checks below for capability that never functioned.

   **This applies RECURSIVELY to delegated work (BMAD Dev→QA on GAIA SDK).** A local-inference agent
   that BUILDS a fix must NOT be the agent that signs off on it — that re-creates the author–test
   correlation one tier down. Route every producer's output to a DIFFERENT agent (a QA / test-architect
   role, fresh context, "assume broken") that *executes* the falsification + traces consumption
   independently. Local inference makes this ~$0, so there is no cost excuse. A producer's
   "falsification-proven, all green" is a *claim*, not QA — it is unverified until an independent agent
   has tried to break it. (Verifier-agent must have execution tools; a read-only reviewer reasons but
   cannot run the PoC.)

## Meta-invariant for harness.md entries

Every new invariant must be a **CONSUMPTION invariant** (asserts a consumer reads/acts), not a
DECLARATION invariant (asserts a symbol exists). `hasattr(...)` / `inspect.signature(...)` / grep-for-def
prove existence, never reachability. Pair every "X is wired" with a discriminating test that FAILS when
the consumer is neutralized (the standard the H1 keystone met: neutralize population → gate promotes a
regressing candidate → test fails).

## Enforcement (so this isn't just advice)

- `tests/integration/` — un-mocked end-to-end smoke: assemble `make_executor`, run a REAL task, assert
  non-empty output + a sane tier. Skips gracefully when local inference is down; REQUIRED when live.
  (Catches the dead-port / dormant-routing / empty-output class in one test.)
- `scripts/ci/dormancy_scan.py` — deterministic "defined-but-only-referenced-in-tests" scan over a
  curated capability registry. **Wired as a BLOCKING gate** in `.github/workflows/ci.yml` (validate
  job) and `scripts/ci/automerge_guard.sh` (Step 6c) as of 2026-07-22 — re-dormancy of a fixed
  capability now fails CI, not just an advisory report. Discriminating self-test:
  `python scripts/ci/dormancy_scan.py --self-test`; unit coverage in `tests/scripts/test_dormancy_scan.py`.
- Routine adversarial pass before committing load-bearing changes — a different lens, "assume broken."

**The test of whether a fix is real:** can you make it FAIL by breaking the thing it claims to do? If
neutralizing the mechanism leaves the test green, the test verifies the existence of code, not the
behavior of the system — and you have learned nothing yet.
