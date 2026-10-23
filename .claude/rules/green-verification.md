# Green Verification — what "the repo is green" must mean (MANDATORY)

**Origin (2026-10-22):** the CI badge was green while 80% of the suite (the integration tier,
11,322 tests) ran under `continue-on-error`. 216 of them failed. When finally run locally they
failed differently WITH live services (43) than WITHOUT (3), and three "never-built feature"
xfail bridges turned out to be unmocked database calls. Every one of those errors came from
measuring "green" in the wrong environment or from the wrong instrument. This rule fixes the
environment and the instruments; `verification-depth.md` fixes the depth.

## 1. Measure green where CI measures it

- A green claim about a tier requires `bash scripts/ci/ci_equivalent_netns.sh [tier]` run from a
  normal shell (not the agent sandbox, which cannot `unshare`). It runs the tier in a network
  namespace with loopback up and nothing listening: the runner's view. Live-box results are
  evidence about the fleet, not about the repo.
- The venv's editable install points at the PRIMARY checkout. Any run from a clone or worktree
  must pin `PYTHONPATH=<that tree>/src` or it silently tests the wrong tree (the script does this).
- `len(app.routes)` undercounts on current FastAPI (`_IncludedRouter` entries). The route oracle is
  `tests/api/test_service_router_mounts.py` or `app.openapi()["paths"]`.

## 2. Classify a failure before touching it

Run the failing test (a) alone, (b) alone in the namespace, (c) in the full tier. The pattern
names the class, and the class names the fix:

| alone | netns | full tier | class | fix |
|---|---|---|---|---|
| pass | pass | fail | order/singleton pollution | fresh instance, never the process singleton |
| fail | pass | fail | live service changes the verdict | mock the call the test forgot (it is a test bug) |
| pass | fail | — | test needs a service CI lacks | `skipif(<service unreachable>)` with a reachability probe |
| fail | fail | fail, same message | genuinely broken or never built | fix, or `xfail(strict=True, reason="<gap>; <pointer>")` |
| varies | varies | varies | reads host state (swap, memory, nested userns) | declare the precondition; align thresholds with the code's own |

A strict xfail is only for the last two rows. Putting one on an environment-conditional test
produces XPASS(strict) = red the moment the environment changes (this happened).

## 3. Gates stay gates

- No test step in `.github/workflows/ci.yml` runs with `continue-on-error`. The integration step
  was made gating on 2026-10-22 with namespace evidence; if it goes red, fix or `skipif` the named
  test on its condition. Do not return it to advisory.
- Ratchets (`ruff_ratchet.py`, `mypy_ratchet.py`, `repo_hygiene_ratchet.py`) move down only, with
  a provenance stamp. A ratchet nobody measured is a lie with a number on it.

## 4. Before claiming done

State the claim in one sentence, run the command that would falsify it in CI's environment,
paste the summary line. "Tests pass" without the namespace run is a claim about this machine.
