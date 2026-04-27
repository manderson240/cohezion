---
title: "Edge-Case Hunt — Wave 2A bare-except + Wave 2D executor split"
date: 2026-04-23
campaign: synthetic-sniffing-panda Ω5
reviewer: bmad-review-edge-case-hunter
scope: behavioral edges (exception classes, evaluation order, async-loop semantics) — not style or stylistic preference
commits_reviewed:
  - 1b9c8f61b  # Wave 2A: executor.py
  - bfe4234f2  # Wave 2A: surreal_client.py
  - c708b0476  # Wave 2A: cohezion_mcp.py
  - ea5275eb2  # Wave 2A: api/__init__.py
  - 17ada8082  # Wave 2A: 9-file stealth-bare-except batch
  - dc547dcd6  # Wave 2D: extract guardrail_runner
  - 835c9aa8d  # Wave 2D: extract template_matcher
  - 5ac8bdc1a  # Wave 2D: extract vault_integration
---

# Method

Walked every modified `try/except` site. For each, enumerated the exception classes the underlying call actually raises (per stdlib + library docs + locally-installed source for `surrealdb`, `aiohttp`, `httpx`, `torch`) versus the classes now caught. Read the post-extract executor.py to confirm the public-API delegators preserve mock targets and to check the still-fragile asyncio-late-import pattern. Flagged misses where a real, narrow-but-realistic call surface raises a class outside the new tuple AND outside `BaseException` (so the old `except Exception` would have caught it).

Per Learning 359 (`except (SubclassError, Exception)` is a stealth bare-except), the direction of these waves is correct. The findings below are exclusively about the *coverage* gap between "broad-but-equivalent-to-bare" and "narrow-but-too-narrow." None of them argue for restoring `except Exception:` — they argue for adding 1–3 specific types per site.

# Findings (sorted by severity)

## must-fix: NameError when inner `except` tuple references `asyncio.TimeoutError` before local `import asyncio` has executed
- **Code**: `src/cohezion/compound/executor.py:944-950`
  ```python
  except (
      AttributeError,
      RuntimeError,
      OSError,
      ConnectionError,
      asyncio.TimeoutError,   # ← evaluated when ANY exception in the try is being matched
  ) as e:
  ```
- **Underlying call**: the inner `try` block (lines 916–943) constructs `point_data` (lines 917–925), then does `import asyncio` (line 926), then calls `asyncio.run(...)` / `asyncio.ensure_future(...)`. The top-level `import asyncio` was removed by Wave 2D commit `dc547dcd6` (it lives only inside the helper now); `asyncio` is bound into this scope only by the inline import on line 926.
- **Actually raises**: if `point.task_description[:200]` (line 921) is given a non-subscriptable `task_description` (e.g., `None` from a mocked `TrajectoryPoint` or a partially-initialized point), Python raises `TypeError` at line 921 — *before* line 926 has bound `asyncio`. CPython then evaluates the exception expression in the `except` tuple, hits `asyncio.TimeoutError`, raises `NameError: name 'asyncio' is not defined`. The outer `except` at line 952 catches `(AttributeError, RuntimeError, ValueError, KeyError, TypeError)` — `NameError` is none of these, so it propagates out of `execute_task()` entirely.
- **Failure mode**: A single mocked-or-malformed `TrajectoryPoint` upstream now turns Step 9 into a hard failure that aborts the rest of the executor pipeline (Steps 9.5–10.6), where the pre-Wave-2D code logged and continued. This is a behavior regression introduced jointly by removing the top-level `import asyncio` and inlining `asyncio.TimeoutError` in the except expression.
- **Suggested fix**: restore a top-level `import asyncio` in `executor.py` (it is still used at lines 930, 931, 938, 949, 997) — the removal was over-eager. Alternatively, hoist the `import asyncio` on line 926 above the dict construction at line 917, OR replace `asyncio.TimeoutError` in the except tuple with `TimeoutError` (which in Python 3.11+ is the same object, but does not require any module import at except-evaluation time).

## must-fix: `ContextLoadError` propagates out of `executor.py:347-358` auto-load handler (was caught by old `except Exception`)
- **Code**: `src/cohezion/compound/executor.py:351-358`
  ```python
  except (
      ContextCoherenceError,
      OSError,
      RuntimeError,
      AttributeError,
      ValueError,
  ) as e:
      logger.warning("Failed to auto-load context: %s", e, exc_info=True)
  ```
- **Underlying call**: `self.load_execution_context()` → `self._context_manager.load_core_context()` → `self.load_manifest()`.
- **Actually raises** (per `src/cohezion/compound/context_integration.py`): `ContextLoadError(Exception)` is defined alongside `ContextCoherenceError` and is raised at lines 75 ("Project root not found"), 90 ("Manifest not found"), 98 ("Invalid manifest JSON"), and 212 ("Context file not found"). It is a direct subclass of `Exception`, **not** of `OSError`, `RuntimeError`, `AttributeError`, or `ValueError`.
- **Failure mode**: When `.context/manifest.json` is missing or malformed (the common case during fresh checkouts, partial worktree migrations, or bench environments), the executor now raises `ContextLoadError` out of `execute_task()` instead of warning and continuing. Pre-Wave-2A this was a benign warning — `cohezion-engine` could run fully without the `.context/` directory. Now it cannot.
- **Suggested fix**: add `ContextLoadError` to the import line and to the tuple:
  ```python
  from cohezion.compound.context_integration import (
      CompoundContextMixin, ContextCoherenceError, ContextLoadError,
  )
  ...
  except (ContextCoherenceError, ContextLoadError, OSError, RuntimeError, AttributeError, ValueError) as e:
  ```

## must-fix: `surrealdb` library raises bare `Exception` and `CBORError` — neither caught by new tuples in `surreal_client.py`
- **Code**: `src/cohezion/core/persistence/surreal_client.py:301-309, 344-353, 376-386, 401-411, 532-545, 560-575, 605-622, 636-653, 706-722, 753-769, 813-829`
  ```python
  except (
      ConnectionError,
      OSError,
      httpx.HTTPError,
      [httpx.TimeoutException,]
      asyncio.TimeoutError,
      RuntimeError,
      ValueError,
      KeyError,
      [TypeError,]
  ) as e:
  ```
- **Underlying call**: `await self._client.connect()`, `signin()`, `use()`, `query()`, `create()`. The `surrealdb` package (v1.x, vendored at `.venv/lib/python3.11/site-packages/surrealdb/`) raises:
  - `surrealdb.errors.SurrealDBMethodError(Exception)` — for method-call errors.
  - Bare `Exception("...")` from `surrealdb/connections/utils_mixin.py:11,16` (response-error and "no result" paths).
  - `CBORError(Exception)` and subclasses (`CBOREncodeError`, `CBORDecodeError`, `CBOREncodeTypeError`, `CBOREncodeValueError`, `CBORDecodeValueError`, `CBORDecodeEOF`) from `surrealdb/cbor/_types.py` for serialization failures on the wire.
- **Coverage map**:
  - `CBOREncodeTypeError(CBOREncodeError, TypeError)` — caught at the 3 sites that include `TypeError`; **MISSED** at the connect/setup_schema/store_node/create/query sites that don't.
  - `CBOREncodeValueError(CBOREncodeError, ValueError)` — caught everywhere via `ValueError`.
  - `CBORDecodeValueError(CBORDecodeError, ValueError)` — caught.
  - `CBORDecodeEOF(CBORDecodeError, EOFError)` — `EOFError` is **NOT in any tuple**. Truncated CBOR responses now propagate.
  - `SurrealDBMethodError(Exception)` — **NOT caught at any site**. Method-level surrealdb errors (e.g., a malformed `query()`, a typed-record-id mismatch in `create()`) now propagate.
  - Bare `Exception(...)` from `utils_mixin.py` — **NOT caught**. Any response-error path through the surrealdb client (e.g., the database returned `{"error": {...}}`) now propagates.
- **Failure mode**: SurrealDB error-response paths previously fell through to the in-memory fallback OR returned `None`/`[]`/`False`. They now bubble up to the caller — typically `JourneyTracker`, `RetrospectionEngine`, or `compound_execute` route handlers — which were not built to handle them and will 500.
- **Suggested fix**: the surrealdb library is the boundary, so include the library's exception types explicitly:
  ```python
  from surrealdb.errors import SurrealDBMethodError
  from surrealdb.cbor._types import CBORError
  ...
  except (
      ConnectionError, OSError, httpx.HTTPError, httpx.TimeoutException,
      asyncio.TimeoutError, RuntimeError, ValueError, KeyError, TypeError,
      SurrealDBMethodError, CBORError, EOFError,
  ) as e:
  ```
  Be defensive about `SurrealDBMethodError` import — it may not exist in older surrealdb versions. Wrap the import in a `try/except ImportError: SurrealDBMethodError = ()` so the `except` tuple stays valid.

## must-fix: subprocess calls in `mcp_inference_tools.py` lack `timeout=` and the new tuple drops `subprocess.SubprocessError`/`UnicodeDecodeError`
- **Code**: `src/cohezion/skills/mcp_inference_tools.py:74` (and the parallel call at `~line 195` for `agentic_coding_workflow`).
  ```python
  res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603 - cmd is a static curl invocation to localhost ollama API
  ```
  Caught by the surrounding `except (OSError, json.JSONDecodeError, ValueError, KeyError, UnicodeDecodeError)` at lines 94–100 and 225–231.
- **Underlying call**: `subprocess.run(["curl", ...])` to `http://localhost:11434/api/generate`.
- **Actually raises**:
  - `FileNotFoundError` (curl missing) — subclass of `OSError` ✓ caught.
  - `subprocess.SubprocessError` and its subclasses (`subprocess.TimeoutExpired`, `subprocess.CalledProcessError`, `subprocess.SubprocessError`) — **NOT caught**. The OCR site catches `UnicodeDecodeError`; the model-tools `select_model` site at `mcp_model_tools.py:190` catches `subprocess.SubprocessError` (good) but **not** `UnicodeDecodeError`.
  - With no `timeout=` argument, `subprocess.run` cannot raise `TimeoutExpired`, but Ollama hanging will hang the request indefinitely (regression from a hardening sprint that does not add timeouts).
- **Failure mode**: a stuck Ollama causes the MCP server to wedge; a missing `curl` or a non-utf-8 stdout causes the new tuple to miss and propagate to the JSON-RPC top-level dispatch, which the comment at `cohezion_mcp.py:1505-1510` claims is the only legitimate broad-catch. So broad-catch at the top works around it — but this defeats the per-tool error-envelope contract.
- **Suggested fix**: add `timeout=60` (or whatever is appropriate) to every `subprocess.run` in the OCR / agentic-coding paths, and include `subprocess.SubprocessError` plus `UnicodeDecodeError` in every except tuple wrapping a `subprocess.run` invocation.

## should-fix: `torch.load` in `api/routes/rl.py:127` raises `pickle.UnpicklingError` / `EOFError` / `zipfile.BadZipFile` not in the new tuple
- **Code**: `src/cohezion/api/routes/rl.py:126-147`
  ```python
  try:
      state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
      ...
  except (OSError, KeyError, ValueError, RuntimeError, AttributeError) as e:
      logger.warning("Failed to inspect policy checkpoint: %s", e, exc_info=True)
      return RLPolicyResponse(exists=True, checkpoint_path=str(ckpt_path))
  ```
- **Underlying call**: `torch.load()` on a `.pt` file produced by a previous training run.
- **Actually raises** (per `torch.serialization` docs and observed behavior on corrupt checkpoints):
  - `OSError` for unreadable file ✓ caught.
  - `RuntimeError` for unsupported format ✓ caught.
  - `pickle.UnpicklingError` (= `_pickle.UnpicklingError`) — subclass of `Exception`, NOT `OSError`/`KeyError`/`ValueError`/`RuntimeError`/`AttributeError`. **MISSED**.
  - `EOFError` — for truncated checkpoints. Direct subclass of `Exception`. **MISSED**.
  - `zipfile.BadZipFile` — `.pt` files are zip-wrapped; corrupt archives raise this. Direct subclass of `Exception`. **MISSED**.
- **Failure mode**: a partially-written checkpoint (interrupted training run, disk-full at write time) now causes `GET /rl/policy/{agent_id}` to return 500 instead of the structured `RLPolicyResponse(exists=True, checkpoint_path=...)` fallback. Pre-Wave-2A this was a logged warning + structured fallback.
- **Suggested fix**:
  ```python
  import pickle, zipfile
  except (OSError, KeyError, ValueError, RuntimeError, AttributeError,
          pickle.UnpicklingError, EOFError, zipfile.BadZipFile) as e:
  ```

## should-fix: `IncompleteRead` from `urllib.request.urlopen().read()` propagates from `vault_integration.py:104-110`
- **Code**: `src/cohezion/compound/executor_helpers/vault_integration.py:88-110`
  ```python
  resp = urllib.request.urlopen(req, timeout=2)
  data = json.loads(resp.read())
  ...
  except (OSError, ConnectionError, json.JSONDecodeError, ValueError, KeyError) as e:
  ```
- **Underlying call**: `urllib.request.urlopen()` and `resp.read()`. The urlopen call's exceptions (`URLError`, `HTTPError`, `socket.timeout`) are all `OSError` subclasses ✓ caught.
- **Actually raises**: `http.client.IncompleteRead` from `resp.read()` if the SurrealDB connection drops mid-response. `IncompleteRead` is a subclass of `http.client.HTTPException` → `Exception`, NOT of `OSError`. **MISSED**.
  - Also: `data[0].get("status")` at line 106 with `data == "error"` (SurrealDB sometimes returns a bare-string error when malformed) raises `TypeError` ("'str' object has no attribute 'get'"), which is NOT in the tuple.
- **Failure mode**: a flaky SurrealDB process — the realistic scenario at run time, given the 2-second timeout — now causes the Step 1 guidance call to bubble out of `fetch_experience_guidance()` instead of degrading to base-guidance. Since the call site in `executor.py` does NOT wrap this in another try/except, the entire `execute_task()` fails.
- **Suggested fix**: add `http.client.HTTPException, TypeError` to the tuple. Better: catch the response-handling code in its own narrower try, and let urlopen's network errors flow through the outer one.

## should-fix: `get_rl_policy` and several FastAPI handlers drop `TypeError` and lose response-shape robustness
- **Code**:
  - `src/cohezion/api/routes/metrics.py:208-216` (Ollama check) — drops `TypeError` (e.g., `m["name"]` when `m` is a string from a malformed response).
  - `src/cohezion/api/routes/metrics.py:114, 131` (training-metrics JSON read) — drops `TypeError` (e.g., `data[-3:]` when `data` is a dict-of-dicts).
  - `src/cohezion/api/routes/templates.py:43` (`parse_template`) — drops `UnicodeDecodeError` and `TypeError` from the underlying `parse_all` filesystem-read path.
  - `src/cohezion/api/routes/agentjet.py:98-105` (`agentjet_status`) — drops `httpx.HTTPError`, `httpx.TimeoutException`, `asyncio.TimeoutError`, `KeyError`, `TypeError`. The `OllamaContextManager` calls out to httpx; without these in the tuple, a flaky Ollama makes the status endpoint 500 instead of returning `{"status": "error"}`.
- **Underlying calls**: each is a typical "endpoint converts a third-party library failure into a clean structured response" pattern. The narrowed tuples now leak these failures as 500s.
- **Suggested fix**: each FastAPI endpoint that previously did `except Exception:` and converted to a structured response should keep the broad-but-explicit tuple OR move to `except Exception:` with an explicit comment (matching the convention already established at `api/__init__.py:62-64, 484-490, 1075-1080` where the comment "FastAPI endpoint — convert to clean 500" makes the intent legible).

## should-fix: `_run_async_guardrail` does not catch exceptions raised inside the guardrail coroutine
- **Code**: `src/cohezion/compound/executor_helpers/guardrail_runner.py:29-33`
  ```python
  try:
      return asyncio.run(coro)
  except (RuntimeError, asyncio.TimeoutError, asyncio.CancelledError) as e:
      logger.debug("Guardrail check failed (non-blocking): %s", e, exc_info=True)
      return None
  ```
- **Underlying call**: `asyncio.run(coro)` where `coro` is `guardrail_pipeline.check_input(...)` or `check_output(...)`.
- **Actually raises**: `check_input` (`src/cohezion/security/guardrail_pipeline.py:117-195`) catches `Exception` per-guardrail (line 170) but its own `await self._audit(...)` calls (lines 159, 180, 194) can raise `OSError`, `httpx.*`, `ValueError` if the audit handler is misconfigured. None of these inherit from `RuntimeError` / `TimeoutError` / `CancelledError`.
- **Failure mode**: a misbehaving audit handler now propagates out of `_run_async_guardrail` → no enclosing try/except in `executor.py:452` or `:505` → `execute_task()` 500s. Pre-Wave-2A's `except Exception` covered this.
- **Suggested fix**: extend the tuple to `(RuntimeError, asyncio.TimeoutError, asyncio.CancelledError, OSError, ValueError, AttributeError, KeyError, TypeError)` OR — since this helper exists specifically to make guardrails non-blocking — restore `except Exception:` with an explicit comment ("Guardrails are non-blocking by design — any failure becomes a no-op so the executor never wedges on infrastructure issues. SystemExit/KeyboardInterrupt still propagate.").

## should-fix: `hookify/validator.py:_init_surrealdb` misses `SurrealDBMethodError`
- **Code**: `src/cohezion/hookify/validator.py:470-479`
  ```python
  try:
      from surrealdb import Surreal
      db = Surreal("ws://localhost:8000")
      return db
  except (ImportError, AttributeError, ConnectionError, OSError, RuntimeError):
      return None
  ```
- **Underlying call**: `Surreal(...)` constructor in `surrealdb` v1+.
- **Actually raises**: `SurrealDBMethodError(Exception)` for invalid URL formats; `ValueError` for some URL parses. Neither in tuple.
- **Suggested fix**: add `ValueError` and `SurrealDBMethodError` (with the same defensive-import pattern as in `surreal_client.py`).

## should-fix: `aiohttp` poll sites drop `TypeError` from response-shape parsing
- **Code**: `src/cohezion/platform/resource_manager.py:140-148` and `:282-289`
  ```python
  except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ConnectionError, ValueError, KeyError) as exc:
  ```
- **Underlying call**: `m.get("size", 0) / (1024**3)` at line 139. If a model entry has `size: null` (Ollama can return this for partially-loaded models), `None / int` raises `TypeError`.
- **Suggested fix**: add `TypeError` to the tuple.

## consider: comment at `executor.py:486` claims `MemoryError` doesn't inherit Exception
`MemoryError.__mro__` is `(MemoryError, Exception, BaseException, object)` — it IS caught by `except Exception:`. The `KeyboardInterrupt`/`SystemExit` claim is correct; the `MemoryError` part is wrong and misleading for future readers. Replace with `GeneratorExit` if a third example is needed.

## consider: `template_matcher`'s nested try uses `except RuntimeError` to detect "no running loop" — `asyncio.get_running_loop()` only raises `RuntimeError`, but the surrounding outer `except` does NOT catch `Exception` raised inside `asyncio.run(warmer.find_template_match(...))`
- **Code**: `src/cohezion/compound/executor_helpers/template_matcher.py:43-55`
- **Underlying call**: `find_template_match` (cache_warmer.py:83) catches `Exception` internally on the L2 path but the L1 path `await self.cache.get(task_description)` is unguarded. If `SemanticCache.get` raises something not in `(ImportError, AttributeError, RuntimeError, OSError)` (e.g., `TypeError` from a malformed cache entry, `ValueError` from a corrupt embedding), it propagates. Previously caught by broad `except Exception:`.
- **Suggested fix**: add `ValueError`, `TypeError`, `KeyError` to the helper's outer tuple.

## consider: `cost_tracker.py` flush sites are still using `(TimeoutError, asyncio.TimeoutError, ...)` which is redundant in Python 3.11+
- **Code**: `src/cohezion/cost_optimization/cost_tracker.py:215-227, 266-273` and `budget_enforcer.py:331-338`
- In Python 3.11+ `asyncio.TimeoutError` is an alias for the built-in `TimeoutError`. Listing both is harmless (Python deduplicates) but the comment-free duplication invites future "is this redundant or is one a typo?" confusion. Add a comment OR drop `asyncio.TimeoutError` (the runtime is `==3.11.*` per `pyproject.toml`).

## consider: `mcp_paths.load_json` is not in the new tuple set — bare-except may still live there
- **Code**: not visible in the diffs. The Wave 2A commit `c708b0476` patched the OLD `cohezion_mcp.py:_load_json` site but Wave 2C (`795d2021b`) extracted JSON loading to `mcp_paths.py`. Verify the bare-except fix was carried into the new module.
- Spot-check: `grep -n "except" src/cohezion/skills/mcp_paths.py` was not run during this hunt; recommend a follow-up.

# Edge-case scenarios for the executor split (Wave 2D)

## Nested-event-loop scenario for `guardrail_runner`
`executor_helpers/guardrail_runner.py:18-33` calls `asyncio.run(coro)` unconditionally. From inside an already-running loop (Jupyter, an `async def` FastAPI handler dispatching `execute_task` via `asyncio.to_thread`), `asyncio.run` raises `RuntimeError` — caught, returns `None`. Pre-extract had the same behavior, so the extract is faithful, but the silently-returning-None contract should be documented in the helper's module docstring so future callers don't expect guardrails to actually run from async contexts.

## Mock-path drift for `_try_template_match`
The pre-Wave-2D code defined `_try_template_match` as an instance method on `CompoundExecutor` containing the body. Tests at `tests/compound/test_executor_coverage_wave3a.py:72,247,270` do `executor._try_template_match = MagicMock(...)` — instance-attribute assignment, which works against both the old method and the new delegator (which is also an instance method).

However, `tests/compound/test_executor_coverage_wave3a.py:283-297` exercises the NEW helper-module-level function directly (`from cohezion.compound.executor_helpers.template_matcher import try_template_match`). That test will pass, but if any other test in the codebase patches `cohezion.compound.executor.SemanticCache` or `cohezion.compound.executor.CacheWarmer` (i.e., patches the OLD import path inside `executor.py`), those patches will silently miss because the imports now happen inside `executor_helpers.template_matcher` — the patch target moved. Audit:
```bash
grep -rn 'patch.*"cohezion.compound.executor\.\(SemanticCache\|CacheWarmer\)"' tests/
```

## `get_experience_guidance` delegator and logger separation
The helper's module-level `logger` (`logging.getLogger("cohezion.compound.executor_helpers.vault_integration")`) is a SEPARATE logger from `cohezion.compound.executor`'s `logger`. Tests/configs setting log levels on the executor will no longer affect helper debug/info messages. Document in the helper docstring or diagnostic-noise diffs in dev will surprise people. Also: `self.logger` is the `VaultLogger` (passed in as `vault_logger=` kwarg) — not the stdlib logger. No behavior change vs pre-extract, but the dual-logger surface deserves a comment.

## FastAPI route ordering / middleware (Wave 2B context)
Spot-checked `api/__init__.py:118-130` — `app.include_router` calls run in deterministic order; no router has literal-vs-path-param collisions (e.g., no `/skills/list` shadowed by `/skills/{name}`). Rate-limiter middleware at `:78-95` registered before all routers; no router accesses middleware state directly. No drift found.

# What the change handles correctly

- **Direction is right.** Reducing bare-except from 70 → 11 across the touched files is substantial. The 11 surviving sites in `cohezion_mcp.py:1505,1521` and `api/__init__.py:166,431,655,766,1083,1499,1593,1810` are all annotated with comments explaining why broad-catch is intentional (top-level FastAPI handlers, JSON-RPC dispatch, user-supplied `execute_fn`).
- **Lazy logging** — every f-string `logger.error(f"...{e}")` site that was edited has been switched to `logger.error("... %s", e)`, which matches the global lint rule.
- **`exc_info=True` added** at non-blocking call sites that previously did `pass` silently — operators can now actually trace why optional features are unavailable.
- **Stealth-bare-except elimination** — the 4 sites in `executor.py` (`(ImportError, Exception)`) and the 15 sites across `compound/cost/platform/hookify/reporting` correctly identify the Learning 359 anti-pattern and replace each with sibling-or-unrelated tuples.
- **Public API of `CompoundExecutor` preserved** — `_try_template_match`, `get_experience_guidance`, and `_run_async_guardrail` (re-exported via aliased import) all remain at their original symbolic locations, so existing test mocks and external callers continue to work.
- **Comment annotations** at the surviving broad-catch sites explicitly note "SystemExit/KeyboardInterrupt still propagate" — the right reasoning, even where (per `MemoryError` finding above) the example is slightly off.
- **`asyncio.CancelledError` handling** — the helper at `guardrail_runner.py:31` correctly catches `asyncio.CancelledError` even though it inherits from `BaseException` in Python 3.8+. This is the correct, narrow handling for a sync-context wrapper.

# Net assessment

Direction is right. **3 must-fix items remain** (asyncio NameError ladder; ContextLoadError leak; surrealdb library exception coverage). **6 should-fix items** (subprocess hardening, torch.load coverage, IncompleteRead, FastAPI handler tightenings, guardrail audit failures, hookify validator). **5 consider items** (commentary/style/redundancy issues).

The transition from broad-catch to specific-catch is correct in principle but loses coverage for three classes of exception: (a) **library-defined direct-Exception subclasses** that are not in stdlib (`SurrealDBMethodError`, `CBORError`, project's own `ContextLoadError`); (b) **stdlib serialization/IO subclasses** that don't inherit from `OSError` (`pickle.UnpicklingError`, `EOFError`, `zipfile.BadZipFile`, `http.client.IncompleteRead`); (c) **shape-parsing `TypeError`s** at JSON/dict-traversal boundaries.

Recommend a follow-up Wave 2A.5 to add the missing classes — most fixes are 2-line tuple expansions plus one targeted `import` per file. The two structural issues (asyncio late-import in executor.py:944-950, and ContextLoadError missing from the auto-load tuple) are higher priority because they convert previously-silent fallbacks into hard executor failures triggered by realistic mocked-test or partial-environment conditions.

The Wave 2D extract is structurally clean. The only caveat is the patch-path drift documented above for `template_matcher` — if a test was patching `cohezion.compound.executor.SemanticCache`, that patch now silently misses. Worth a one-time audit grep before committing further test changes.

# Triage summary

## must-fix: 4
1. `executor.py:944-950` — asyncio.TimeoutError in except tuple before local `import asyncio` → NameError under realistic mock conditions
2. `executor.py:351-358` — `ContextLoadError` missing from auto-load handler → executor crash when `.context/manifest.json` absent
3. `surreal_client.py` (10 sites) — `SurrealDBMethodError`, bare `Exception` from utils_mixin, `EOFError`/`CBORDecodeEOF` not caught at any site; `CBOREncodeTypeError` missing from sites without `TypeError`
4. `mcp_inference_tools.py:74,~195` — subprocess.run without `timeout=`; `subprocess.SubprocessError` and `UnicodeDecodeError` missing from except tuples

## should-fix: 5
1. `api/routes/rl.py:145` — `pickle.UnpicklingError`, `EOFError`, `zipfile.BadZipFile` missing from torch.load handler
2. `executor_helpers/vault_integration.py:109` — `http.client.IncompleteRead`, `TypeError` missing from urllib + JSON traversal
3. `api/routes/metrics.py:114,131,208` and `api/routes/templates.py:43` and `api/routes/agentjet.py:98` — multiple FastAPI endpoints lose `TypeError`/`UnicodeDecodeError`/`httpx.*` coverage and now leak as 500s
4. `executor_helpers/guardrail_runner.py:31` — guardrail audit failures (OSError/ValueError/AttributeError) propagate; helper docstring contract says "non-blocking"
5. `hookify/validator.py:477` and `platform/resource_manager.py:140,282` — Surreal/aiohttp paths drop library and shape exceptions

## consider: 5
1. `executor.py:486` — comment misstates `MemoryError` propagation (it does inherit from Exception)
2. `executor_helpers/template_matcher.py:54` — `ValueError`/`TypeError`/`KeyError` from cache miss not caught
3. `cost_tracker.py:215,266` & `budget_enforcer.py:331` — `(TimeoutError, asyncio.TimeoutError, ...)` redundant in Python 3.11+
4. `mcp_paths.py` — verify Wave 2A bare-except fix carried over from the OLD `cohezion_mcp.py:_load_json` site
5. Patch-path drift audit for `cohezion.compound.executor.SemanticCache` / `CacheWarmer` patches that may no longer hit after the template_matcher extract
