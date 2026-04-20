---
paths:
  - "tests/**"
---

# Testing Rules

- Run tests with `uv run pytest` — never bare `pytest`
- Use `pytest-asyncio` for async test functions
- Avoid `walk_packages` import scans — they hang on modules with heavy init (quantization engine, IDE configs). Use targeted `importlib.import_module()` tests instead
- Mock external services (Ollama, SurrealDB) rather than requiring live connections
- Test HIHO coherence invariant (0.5 overlap) for any simulation or physics module
- Pydantic models at boundaries should have schema validation tests
- Never commit tests that depend on specific file counts or line counts — the codebase is actively being cleaned up

## Anti-Patterns That Cause Suite-Wide Failures (Enforced)

These anti-patterns caused 44 test failures (Session 56). Enforcement mechanisms prevent recurrence.

### 1. Hardcoded Developer Paths
**BAD:** `Path("/home/mike-anderson/dev/cohezion/.pre-commit-config.yaml")`
**GOOD:** `PROJECT_ROOT = Path(__file__).resolve().parents[2]` then `PROJECT_ROOT / ".pre-commit-config.yaml"`
**Enforcement:** Pre-commit hook `no-hardcoded-home-paths` blocks commits. CI lint `scripts/ci/lint_tests.py` catches in CI.

### 2. Git Init Without GPG Sign Disable
**BAD:** `subprocess.run(["git", "init"], cwd=tmp_path)` then commit — fails when GPG signing is globally configured
**GOOD:** Use the shared `git_repo` fixture from `tests/conftest.py` which sets `commit.gpgsign=false`
**Enforcement:** CI lint `GIT_INIT_NO_GPGSIGN` rule flags git init without gpgsign config nearby.

### 3. Logging Filters That Corrupt Arg Types
**BAD:** `record.args = tuple(str(arg) for arg in record.args)` — converts int/float args to strings, breaks `%d`/`%f`
**GOOD:** `record.args = tuple(redact(arg) if isinstance(arg, str) else arg for arg in record.args)`
**Enforcement:** Regression tests in `tests/security/test_log_redactor.py::TestRedactionFilterTypePreservation`. CI lint `LOG_FILTER_STR_CAST` rule.

### 4. Tests Depending on External State
**BAD:** `HookIntegration(".claude/hooks")` — depends on directory existing
**GOOD:** Create hooks in `tmp_path` and pass that to the class
**Enforcement:** Code review vigilance. Use `tmp_path` fixture for all filesystem-dependent tests.

### 5. `os.access()` + `chmod()` Doesn't Work as Root
**BAD:** `path.chmod(0o000); assert not os.access(path, os.R_OK)` — root can read any file
**GOOD:** `with patch("module.os.access", return_value=False):` — mock the permission check
**Enforcement:** Code review. Document pattern here.

### 6. `is_available()` Should Probe Functionality, Not Binary Existence
**BAD:** `return shutil.which("systemd-run") is not None` — binary exists but D-Bus may not
**GOOD:** `subprocess.run(["systemd-run", "--scope", "--user", "true"], timeout=5)` — actually test it works
**Enforcement:** Code review vigilance for any new `is_available()` methods.

### 7. Pre-Commit Stage Names Changed in v3+
**BAD:** `assert hook["stages"] == ["commit"]` — pre-commit v3 uses `pre-commit` instead of `commit`
**GOOD:** `assert hook["stages"][0] in ("commit", "pre-commit")`
**Enforcement:** Accept both naming conventions in assertions.

## Verification Commands

```bash
# Lint tests for anti-patterns
python scripts/ci/lint_tests.py

# Run pre-commit hooks (catches hardcoded paths)
pre-commit run no-hardcoded-home-paths --all-files

# Full test suite (must be 0 failures)
uv run pytest tests/ -q -o addopts=""
```
