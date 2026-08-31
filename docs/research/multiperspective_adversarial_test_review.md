# Multiperspective Adversarial Review: Test Suite Architecture & Anti-Patterns

**Execution Timestamp**: 2026-08-17 17:04:49 EDT

**Sovereign Evaluation Engine**: Cloud Consensus Swarm (`deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`)

---

## Perspective: Senior Principal QA & Compiler Architect (`deepseek-v4-pro:cloud`)

*Latency: 65.11s*


# Adversarial Review: Test Suite Refactoring & Anti-Patterns

## Verdict

Renaming `Test*` domain classes is directionally correct and superior to `__test__ = False` for long‑term hygiene, but it introduces **contract drift, serialization, and namespace risks** that the quick fix would not. The 107 remaining failures are a **symptom of non‑hermetic test architecture**; they must be quarantined and rearchitected, not patched with more mocks.

---

## 1. Renaming vs `__test__ = False` — Hidden Risks & Regression Vectors

### 1.1 Serialization & Schema Contract Drift

| Class | Risk |
|-------|------|
| `TestMetrics` → `SystemVerificationReport` | Pydantic uses the class name as the default JSON Schema `title` and `$defs` key. Any generated OpenAPI clients, stored JSON Schemas, or external consumers referencing `#/$defs/TestMetrics` will break. |
| `TestGenStatus` → `GenerationStatus` | If used in FastAPI/Pydantic response models, the enum’s schema title changes. Persisted enum **values** may be safe, but any code doing `type(obj).__name__` or `repr()` will see the new name. |
| `TestGenerator` → `CodeSuiteGenerator` | If the class name is used as a registry key, plugin entry point, CLI command name, or in generated code/configuration, renaming breaks those references. |

**Action**: Add explicit `model_config = {"title": "TestMetrics"}` (or a custom `schema_extra`) if backward compatibility is required. For enums, verify that serialization is by value, not by class name. For the generator, search for string references to `"TestGenerator"` in configs, entry points, and docs.

### 1.2 Backwards Compatibility Aliases Are an Illusion

```python
TestMetrics = SystemVerificationReport
```

- **Pickle compatibility**: Old pickles store `module.TestMetrics`. If the module path changed, the alias must exist in the **old module path** (e.g., a shim module). Otherwise unpickling fails.
- **`__name__` mismatch**: `TestMetrics.__name__` is now `"SystemVerificationReport"`. Any code that uses `__name__` for logging, metrics, or serialization will silently change output.
- **Type checkers & docs**: Aliases are often rendered as “alias of SystemVerificationReport” in Sphinx/IDE, which can confuse maintainers. They do not create a distinct type.

**Action**: If true backward compatibility is required, keep the old class as a **subclass** with a deprecation warning, or provide a custom `__getattr__` in the old module. Otherwise, accept the break and document it.

### 1.3 Namespace Collisions & Import Graph

- `GenerationStatus` may already exist in another domain module or third‑party dependency. A global `grep`/`rg` is mandatory.
- `SystemVerificationReport` is a broad name; it could collide with a future concept or an existing class in a different bounded context.
- `CodeSuiteGenerator` might conflict with a package name or a class in a plugin system.

**Action**: Run `rg "class GenerationStatus|SystemVerificationReport|CodeSuiteGenerator"` across the entire monorepo, including generated code and virtual environments. Use `import-linter` or `pytest-archunit` to enforce naming boundaries.

### 1.4 Pytest Warning Suppression Risk

If `pyproject.toml` now contains a global filter like:

```toml
filterwarnings = ["ignore::pytest.PytestCollectionWarning"]
```

this will **mask future real test classes** accidentally named `Test*` in production code. The warning exists for a reason.

**Action**: Remove the filter after renaming. If a narrow filter is still needed, scope it to the exact message and module, e.g.:

```toml
filterwarnings = [
  "ignore:.*TestGenStatus.*:pytest.PytestCollectionWarning:old.module.path"
]
```

### 1.5 Why Renaming Is Still Better Than `__test__ = False`

- `__test__ = False` is a Pytest‑specific magic attribute; it does not prevent `unittest` discovery, `nose`, or other tools from collecting the class.
- It can be accidentally removed during refactoring, reintroducing the warning.
- It does not address the root cause: domain classes should not have a `Test*` prefix.

**Verdict**: Renaming is correct, but it must be treated as a **breaking change** with a migration plan, not a cosmetic fix.

---

## 2. Critique of the 107 Remaining Failing Tests

### 2.1 Root Cause Taxonomy

| Category | Likely Cause | Impact |
|----------|--------------|--------|
| Missing mock fixtures | Fixture not defined, wrong scope, or `conftest.py` not loaded | Tests fail immediately, often with `FixtureLookupError` |
| Live services | Real HTTP, DB, message queue, LLM API, or file system access | Slow, flaky, non‑deterministic, cannot run offline or in parallel |
| Multi‑agent swarm races | Shared state via external services, real concurrency, timeouts | Intermittent failures, order‑dependent results |

### 2.2 Why “Missing Mocks” Is a Symptom, Not a Cause

- Tests that require mocks but don’t define them are **not self‑contained**. They depend on an implicit environment that may exist on a developer’s machine but not in CI.
- This suggests **fixture scope mismanagement** (e.g., `@pytest.fixture(scope="session")` used for a function‑level mock) or **conftest.py not being discovered** due to directory structure.
- Simply adding the missing mocks will not fix the underlying design flaw: the code under test is **tightly coupled to external services**.

### 2.3 Specific Risks in Multi‑Agent Swarms

- **Shared external state**: Agents may write to the same database, queue, or file system, causing cross‑test interference.
- **Real concurrency**: Threads/processes introduce race conditions that are impossible to reproduce deterministically.
- **Time & randomness**: Agents often use `time.sleep`, `random`, or real clocks, making tests order‑dependent and flaky.
- **Network timeouts**: Live LLM or API calls can hang or return rate‑limit errors, causing false failures.

**Verdict**: The 107 failures are not a test suite problem; they are an **architecture problem**. The code under test lacks seams for dependency injection, and the tests lack a hermetic harness.

---

## 3. Recommendations for Zero‑Flakiness, Pure Hermetic Execution

### 3.1 Test Tiering & CI Gates

Define explicit tiers and run them separately:

| Tier | Description | Default CI? |
|------|-------------|-------------|
| **Unit** | No I/O, no network, no filesystem, no time, no randomness. Use fakes. | ✅ Yes |
| **Component** | In‑memory fakes for external services, real domain logic. | ✅ Yes |
| **Contract** | Recorded interactions (VCR cassettes) or consumer‑driven contracts. | ✅ Yes (replay only) |
| **E2E / Live** | Real services, explicit opt‑in, separate pipeline. | ❌ No |

Use markers:

```python
@pytest.mark.unit
@pytest.mark.component
@pytest.mark.contract
@pytest.mark.e2e
```

Default command: `pytest -m "not e2e and not live"`

### 3.2 Enforce Hermeticity

- **Disable network** in unit/component tests with `pytest-socket` (allow only `localhost` if needed).
- **Disable file system** access outside `tmp_path` using `pytest-mock` or a custom fixture.
- **Freeze time** with `freezegun` or a custom virtual clock.
- **Seed randomness** with `pytest-randomly` and a fixed seed in CI.
- **Isolate environment variables** with `monkeypatch.setenv` / `monkeypatch.delenv`.

### 3.3 Deterministic Multi‑Agent Test Harness

For multi‑agent swarms, replace all real infrastructure with in‑memory, deterministic fakes:

| Real Component | Hermetic Replacement |
|----------------|----------------------|
| Message bus (Kafka, RabbitMQ) | In‑memory `asyncio.Queue` or a simple event bus |
| LLM / Agent clients | Fake clients with scripted responses or replay from cassettes |
| Database | `sqlite:///:memory:` or `mongomock` |
| Clock | Virtual clock (`freezegun` or custom `Clock` protocol) |
| Randomness | Seeded `random.Random` / `numpy.random.default_rng(seed)` |
| Threads / processes | `asyncio` with a controlled event loop (`pytest-asyncio`, `loop_scope="function"`) |

**Key principle**: Every external dependency must be behind a **Protocol/ABC** so tests can inject fakes without touching real services.

### 3.4 CI Enforcement

- Run `pytest -m "not e2e and not live"` as the **only** required gate for PRs.
- Run `pytest -m e2e` in a separate nightly or manual pipeline with real services.
- Use `pytest-timeout` to prevent hangs (e.g., `--timeout=30`).
- Use `pytest-xdist` for parallel execution **only after** tests are proven isolated.
- Add a static analysis step to detect:
  - `Test*` classes in non‑test directories.
  - Network calls (`requests.get`, `httpx.get`, `socket.socket`) in unit/component tests.
  - Use of `time.sleep` or `random` without seeding.

### 3.5 Migration Plan for the 107 Failing Tests

1. **Quarantine immediately**: Move all failing tests to `tests/live/` or mark them `@pytest.mark.e2e` and exclude from default CI. This restores a green default suite.
2. **Triage each test**:
   - If it fails due to a missing fixture, fix the fixture import/scope.
   - If it fails due to a live service, rewrite it as a component test with fakes or a contract test with recorded interactions.
3. **Introduce seams**: Refactor production code to accept dependencies via constructor injection or context managers.
4. **Re‑enable gradually**: Move tests back into the default suite only when they pass hermetically and deterministically.
5. **Remove the `filterwarnings` entry** after renaming is complete.

---

## Final Verdict

The renaming from `Test*` to domain‑appropriate names is **correct and necessary**, but it must be treated as a breaking change with explicit serialization compatibility tests and alias shims where needed. The 107 failing tests are a **red flag** indicating systemic non‑hermetic design. Zero‑flakiness is achievable only by enforcing strict test tiering, dependency injection, and deterministic fakes for all external services—especially in multi‑agent swarms. Patchwork mocking will not suffice; the test architecture itself must be reengineered.


---

## Perspective: Systems Verification & Security Red Team Lead (`qwen3.5:397b-cloud`)

*Latency: 43.13s*


# ADVERSARIAL REVIEW: TEST SUITE REFACTORING & INTEGRITY SWEEP
**TO:** Engineering Lead, Cohezion Core
**FROM:** Systems Verification & Security Red Team
**SUBJECT:** Critical Risk Assessment: Class Renaming, Test Leakage, and Swarm Hermeticity
**DATE:** 2023-10-27
**STATUS:** **ACTION REQUIRED**

---

## 1. REFACTORING RISK ASSESSMENT: RENAME VS. `__test__ = False`

The decision to rename domain classes (`Test*` → `Domain*`) over flagging `__test__ = False` is architecturally sound but introduces specific migration vectors that must be audited.

### Findings & Risks
*   **Pydantic Discriminator Collision:** `TestMetrics` → `SystemVerificationReport`.
    *   **Risk:** If these models are serialized/deserialized across service boundaries, the `title` or `class_key` in the JSON schema may have shifted. External consumers expecting `TestMetrics` will break.
    *   **Verification:** Audit all API contracts and message queues for hardcoded string references to the old class names.
*   **AST/Code Generation Integrity:** `TestGenerator` → `CodeSuiteGenerator`.
    *   **Risk:** If this tool generates code that instantiates itself or references its own class name in output strings, the generated code will now reference the new name. If legacy scripts expect the old name, execution will fail.
    *   **Verification:** Run a diff on generated artifacts from the old vs. new generator.
*   **Alias Technical Debt:** Backwards compatibility aliases were added.
    *   **Risk:** Aliases allow legacy imports to persist, delaying the cleanup. They also clutter the namespace, increasing the attack surface for confusion-based bugs.
    *   **Recommendation:** Tag aliases with `@deprecated` and set a hard sunset date (e.g., v2.5). Do not allow aliases in new code.

### Verdict
**Renaming was the correct security hygiene decision.** `__test__ = False` masks semantic debt and allows production logic to hide in test namespaces. However, the **serialization contract** is the primary vulnerability introduced here.

---

## 2. CRITIQUE: THE 107 FAILING TEST VECTORS

**Context:** 107 failures in 12,515 tests (0.85% failure rate).
**Red Team Assessment:** In a high-assurance system, **107 non-hermetic tests are 107 potential security boundaries violations.** The attribution to "missing mock fixtures or live services" is unacceptable for a CI/CD pipeline.

### Critical Vulnerabilities Identified
1.  **Live Service Leakage (High Severity):**
    *   **Issue:** Tests hitting live services imply API keys/secrets are present in the CI environment.
    *   **Risk:** Credential leakage, cost explosion (LLM token usage), and rate-limiting of production endpoints by test noise.
    *   **Action:** **Immediate network blocking** in CI. If a test needs network, it is an Integration Test, not a Unit Test. Move to a separate suite.
2.  **Missing Mock Fixtures (Medium Severity):**
    *   **Issue:** Indicates tight coupling between domain logic and infrastructure (DB, FS, Network).
    *   **Risk:** Non-deterministic execution order. Test A modifies state, causing Test B to fail (Flakiness).
    *   **Action:** Enforce Dependency Injection. No test should instantiate a real database connection.
3.  **The "Flaky" Precedent:**
    *   **Issue:** Allowing 107 failures normalizes instability.
    *   **Risk:** Engineers begin to ignore CI red lights. Real regressions will be buried in the noise.
    *   **Action:** **Quarantine.** Move these 107 tests to a `tests/quarantine` directory. They do not count towards pass/fail gates until fixed.

---

## 3. RECOMMENDATIONS: ZERO-FLAKINESS & HERMETIC SWARMS

To support multi-agent swarms, tests must be **deterministic, isolated, and side-effect free.**

### A. Enforce Hermetic Boundaries
*   **Network:** Install `pytest-socket`. Block all outbound traffic by default. Whitelist only `localhost` for specific integration tests.
*   **Filesystem:** Enforce `tmp_path` usage. No writes to `/tmp` or project root. Agents running in parallel will collide on file locks otherwise.
*   **Environment:** Use `pytest-env` to freeze environment variables. Agents must not inherit host OS variables that could alter behavior.
*   **Time:** Enforce `freezegun`. No reliance on `datetime.now()`. Time-skew between swarm nodes causes race conditions.

### B. Multi-Agent Swarm Safety
*   **Namespace Isolation:** Each agent process must run with a unique `PYTEST_WORKER_ID` aware fixture scope. Database schemas or cache keys must be suffixed by worker ID to prevent cross-test pollution.
*   **Resource Limits:** Apply `ulimit` constraints within test containers. Prevent a single runaway test from starving the swarm node of RAM/CPU.
*   **Deterministic Seeding:** Global random seed enforcement (`--randomly-seed=0`). If a test passes locally but fails in the swarm, it is a threading/ordering bug, not a swarm bug.

### C. Process & Governance
*   **Test Classification:** Strictly categorize tests:
    *   `unit/`: Hermetic, <10ms, no I/O.
    *   `integration/`: Dockerized deps, network allowed, isolated namespace.
    *   `e2e/`: Live services, run manually or on nightly builds only.
*   **Fail-Fast Policy:** CI must fail on *any* unit test failure. The 107 quarantined tests must be fixed or deleted within 2 sprints.

---

## 4. EXECUTIVE DIRECTIVE

1.  **Audit Serialization:** Verify no external contracts rely on `TestMetrics` or `TestGenerator` class names immediately.
2.  **Quarantine the 107:** Move failing tests out of the main suite within 24 hours. Stop the noise.
3.  **Block Network:** Enable `pytest-socket` in the CI pipeline. If tests break, they were incorrectly classified.
4.  **Sunset Aliases:** Deprecate `Test*` aliases in the next minor release.

**Signed,**
*Red Team Lead*
*Systems Verification & Security*


---

## Perspective: Frontier Formal Methods & Invariant Verifier (`glm-5.2:cloud`)

*Latency: 26.92s*


# Adversarial Review: Test Suite Refactoring & Anti-Patterns

## Executive Summary

The decision to refactor `Test*`-prefixed domain classes rather than relying on `__test__ = False` is architecturally sound but introduces a distinct class of risks that must be audited. The 107 remaining failures in a 12,515-test suite suggest a **0.85% failure rate**, which is acceptable for a transitional state but unacceptable as a steady state. Below is a multi-perspective critique.

---

## 1. Hidden Risks of Renaming Domain Models vs. `__test__ = False`

### 1.1 The `__test__ = False` Quick-Fix Was a Smell, Not a Solution

`__test__ = False` is a **pytest collection escape hatch**, not a semantic declaration. Using it on production domain classes (`Enum`, `Pydantic BaseModel`, AST tooling) would have:

- **Polluted the domain layer with test-framework concerns.** Production code should have zero knowledge of pytest's collection protocol.
- **Created silent coupling**: any future tool that introspects `__test__` (e.g., hypothesis, coverage plugins, custom collectors) would misinterpret the attribute.
- **Masked the root cause**: the prefix `Test` on non-test classes is a naming-convention violation, not a collection bug.

**Verdict:** Refactoring was the correct call. The quick-fix would have been technical debt with compounding interest.

### 1.2 Risks Introduced by Renaming

| Risk | Severity | Detail |
|---|---|---|
| **Serialization drift** | High | `TestMetrics` → `SystemVerificationReport`: if any persisted state (DB rows, JSON blobs, cached pickles, Redis keys) used the old class name via `__class__.__name__` or Pydantic's model serialization, deserialization will break silently. Pydantic v2 does **not** auto-alias class names. |
| **Backwards-compat alias fragility** | Medium | Aliases like `TestMetrics = SystemVerificationReport` preserve import paths but **do not preserve** `isinstance()` semantics if any code does `type(x).__name__ == "TestMetrics"`. They also break `get_type_hints()` resolution in some edge cases with forward references. |
| **Enum identity loss** | Medium | `TestGenStatus` → `GenerationStatus`: Enum members are identity-sensitive. If any code serializes enum *by class name* (e.g., `"TestGenStatus.GENERATED"`) and deserializes by lookup, it will fail. Aliases via `TestGenStatus = GenerationStatus` work for attribute access but **not** for `enum.Enum` dynamic lookup patterns. |
| **AST tool rename** | Low-Medium | `TestGenerator` → `CodeSuiteGenerator`: lower risk if purely internal, but any plugin registration, entry point, or factory pattern keyed on the class name will silently fail to register. |
| **Import cycle exposure** | Low | Renaming can surface previously masked circular imports if the alias module is imported eagerly by a different path than the original. |

### 1.3 Namespace Collision Audit

- **`SystemVerificationReport`**: This is a generic-sounding name. Risk of collision with future classes in verification, QA, or reporting subsystems. Recommend a domain-scoped prefix (e.g., `GenerationVerificationReport`) if the class is specific to the generation pipeline.
- **`CodeSuiteGenerator`**: Acceptable, but verify no existing `CodeSuite*` namespace exists in the codebase.
- **`GenerationStatus`**: High collision risk. This name is extremely common. Audit for shadowing in nested scopes or submodule imports.

### 1.4 `pyproject.toml` `filterwarnings` Update

Adding `filterwarnings` to suppress `PytestCollectionWarning` is **dangerous if over-broad**. If the filter is:

```toml
filterwarnings = ["ignore::pytest.PytestCollectionWarning"]
```

…this will **silently hide future collection warnings** from genuinely misnamed test classes or broken collection. Recommended:

```toml
filterwarnings = [
    "error::pytest.PytestCollectionWarning",  # Treat as error going forward
]
```

Only suppress specific, documented, time-bounded warnings.

---

## 2. Critique of the 107 Remaining Failures

### 2.1 Failure Taxonomy (Inferred)

| Category | Estimated Count | Root Cause | Severity |
|---|---|---|---|
| Missing mock fixtures | ~60-70 | Fixture refactoring incomplete; fixtures not migrated to new class names | High — indicates incomplete refactor |
| Live service dependencies | ~20-30 | Tests hitting real LLM APIs, DBs, or network endpoints | Critical — violates hermeticity |
| Stale imports of old names | ~5-15 | Tests still importing `TestMetrics`, `TestGenerator` etc. | Medium — alias masks these |
| Flaky / timing-dependent | ~5-10 | Race conditions in async test paths | High |

### 2.2 Critical Observations

1. **The alias backwards-compat layer is hiding failures.** If 107 tests are failing, some fraction are likely *passing for the wrong reason* — importing the alias, exercising old behavior, and not testing the refactored contract. **Recommend: temporarily remove aliases, run suite, fix all import errors, then re-add aliases as deprecated.**

2. **"Missing mock fixtures" is a symptom, not a diagnosis.** The real question: *why* are fixtures missing? Likely causes:
   - Fixture factories were keyed on `TestMetrics` / `TestGenerator` class identity.
   - `pytest.fixture` params used string-based class names for parametrization.
   - Mock builders used `spec=TestMetrics` — now `spec=SystemVerificationReport` but old mocks still reference the alias.

3. **Live service tests should not exist in the default suite.** They belong in a separate `pytest -m live` marker-gated suite. Their presence in the default run is an **architectural defect**, not a "known issue."

### 2.3 The 0.85% Failure Rate Is Misleadingly Low

In a 12,515-test suite, 107 failures can hide:
- **Critical path regressions** (if the 107 are concentrated in generation/verification pipelines).
- **Silent pass-throughs** where the alias makes old code "work" without testing new contracts.

Recommend: **classify every failure by module, not by count.** A heatmap of failures by subsystem will reveal whether the refactoring introduced localized regression clusters.

---

## 3. Recommendations for Zero-Flakiness, Hermetic Multi-Agent Swarm Testing

### 3.1 Hermeticity Mandates

| Principle | Implementation |
|---|---|
| **No network in default suite** | `pytest -m "not live and not network"` as default. Use `pytest-socket` to hard-block sockets. |
| **No real LLM calls** | All LLM clients must be injected and mocked by default. Use a `MockLLMClient` fixture as the default provider. |
| **No filesystem leakage** | Use `tmp_path` for all file I/O. Audit for hardcoded paths. Use `pyfakefs` for legacy code. |
| **No time-dependent assertions** | Inject a `Clock` abstraction. Freeze time in tests via `freezegun` or a custom `Clock` protocol. |
| **No shared mutable state** | Each test gets fresh fixture instances. Use `function` scope by default; `session` scope only for immutable read-only data. |

### 3.2 Multi-Agent Swarm Specifics

For swarms of agents generating/executing tests concurrently:

1. **Deterministic test ordering.** Disable `pytest-randomly` or pin its seed in CI. Swarm agents must reproduce identical failure states.

2. **Test isolation by process, not just function.** Use `pytest-forked` or `pytest-xdist` with `--forked` to prevent state leakage between tests in the same worker.

3. **Fixture registry as a contract.** Publish a `fixtures.json` manifest listing all available fixtures, their scopes, and their dependencies. Swarm agents must reference this manifest when generating tests — preventing the "missing mock fixture" class of failure.

4. **Class-name-to-fixture mapping.** After this refactor, establish a convention: every domain model `X` has a corresponding `make_x` fixture. This prevents the exact failure mode seen here.

5. **Ban `Test*` prefixes via linting.** Add a `ruff` or custom AST check:
   ```python
   # Forbid Test* prefix on non-test modules
   if node.name.startswith("Test") and not is_test_file(filename):
       raise NamingViolation(...)
   ```

6. **Deprecation timeline for aliases.** Aliases must emit `DeprecationWarning` on import:
   ```python
   def __getattr__(name):
       if name == "TestMetrics":
           warnings.warn("TestMetrics is deprecated; use SystemVerificationReport", DeprecationWarning, stacklevel=2)
           return SystemVerificationReport
   ```
   Remove aliases after one release cycle.

### 3.3 Zero-Flakiness Protocol

```
1. Flaky test detection: pytest-repeat + pytest-rerunfailures with --reruns=5
2. Quarantine: any test failing >1/5 reruns is auto-marked @pytest.mark.flaky and excluded from CI gating
3. Root-cause SLA: flaky tests must be fixed or deleted within 7 days
4. Swarm convergence: all agents must agree on test outcomes; divergence triggers re-run with --forked
```

---

## 4. Action Items (Prioritized)

| Priority | Action | Owner | ETA |
|---|---|---|---|
| P0 | Audit all serialized state for old class names (`TestMetrics`, `TestGenStatus`, `TestGenerator`) | Backend | 2 days |
| P0 | Temporarily remove aliases, run suite, fix all import errors, re-add as deprecated | QA | 1 day |
| P0 | Gate live-service tests behind `@pytest.mark.live`; exclude from default run | Infra | 1 day |
| P1 | Add `pytest-socket` to hard-block network in default suite | Infra | 2 days |
| P1 | Classify all 107 failures by subsystem; produce heatmap | QA | 1 day |
| P1 | Tighten `filterwarnings` to `error::pytest.PytestCollectionWarning` | QA | 1 hour |
| P2 | Add lint rule banning `Test*` prefix on non-test classes | Tooling | 3 days |
| P2 | Publish fixture manifest for swarm agents | Tooling | 5 days |
| P3 | Remove backwards-compat aliases after one release cycle | Backend | 1 sprint |

---

## Final Verdict

The refactoring was the **correct architectural decision** but the execution is **incomplete**. The 107 failures are not "mostly missing mocks" — they are **evidence that the refactor did not propagate fully through the test contract layer.** The alias layer is currently **masking the true scope of breakage.** Until aliases are temporarily removed and the suite is run clean, the team cannot claim the refactor is done.

**The single highest-leverage action: remove the aliases for one test run.** The resulting failure count will be the true cost of the refactor, and only then can remediation be properly scoped.


---
